from flask import Flask, render_template, request, jsonify, url_for, redirect, send_file, json
from flask_sqlalchemy import SQLAlchemy
from waitress import serve
import os
from datetime import datetime
from before_whisper import convert_to_wav
from after_whisper import clean_text
from whisper_deploy import transcribe_chunk
from utils.chunking import chunk_audio_with_overlap
import shutil
import tempfile
from docx import Document
import io
from pydub import AudioSegment
import math

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

from summarisation import process_transcript_for_summary

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql+psycopg2://newaifyuser:user2@db:5432/new_db"
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

with app.app_context():
    db.create_all()

class AudioFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(10000), nullable=False)
    mimetype = db.Column(db.String(500))
    transcript = db.Column(db.Text)
    upload_time = db.Column(db.DateTime, server_default=db.func.now())


class ModelFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(10000), nullable=False)
    Modeloutput = db.Column(db.Text)
    processed_time = db.Column(db.DateTime, server_default=db.func.now())
    



@app.route('/')
def index():
    return render_template("Convertask.html")

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400

    save_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(save_path)

    audio_file = AudioFile(filename=file.filename, mimetype=file.mimetype)
    db.session.add(audio_file)
    db.session.commit()


    return jsonify({
        'success': True,
        'filename': file.filename,
    })

@app.route('/transcribe', methods=['POST'])
def transcribe_file():
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({'success': False, 'error': 'Filename not provided'}), 400

    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    base_name = os.path.splitext(filename)[0]
    wav_path = os.path.join("uploads", f"{base_name}_converted.wav")

    try:
        print("[INFO] Starting conversion to WAV")
        convert_to_wav(input_path, wav_path)

        print("[INFO] Starting chunking")
        chunks = chunk_audio_with_overlap(wav_path)

        transcripts = []
        for i, chunk in enumerate(chunks):
            print(f"[INFO] Transcribing chunk {i + 1}/{len(chunks)}: {chunk}")
            transcripts.append(transcribe_chunk(chunk))
            os.remove(chunk)

        print("[INFO] Cleaning final transcript")
        full_text = clean_text(" ".join(transcripts))

        audio_record = AudioFile.query.filter_by(filename=filename).first()
        if audio_record:
            audio_record.transcript = full_text
            db.session.commit()
        


        print("[INFO] Transcription complete")
        return jsonify({'success': True,'redirect_url': url_for('display_transcript', transcript=full_text, original_filename = filename)})

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/display_transcript')
def display_transcript():
    transcript = request.args.get('transcript', '') 
    original_filename = request.args.get('original_filename', '')
    return render_template('t_display.html', transcript=transcript, original_filename=original_filename)

@app.route('/download_transcript', methods=['POST'])
def download_transcript():
    
    data = request.get_json()
    transcript_text = data.get('transcript', '')
    download_format = data.get('format', '')
    filename = data.get('filename')

    if not transcript_text:
        return jsonify({'success': False, 'error': 'No transcript provided.'}), 400

    if download_format == 'docx':
        
        document = Document()
        document.add_paragraph(transcript_text)

        
        byte_stream = io.BytesIO()
        document.save(byte_stream)
        byte_stream.seek(0) 

        return send_file(
            byte_stream,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=f'{filename}_transcript.docx'
        )
    elif download_format == 'pdf':
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph(transcript_text, styles['Normal']))
        doc.build(story)
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{filename}_transcript.pdf'
        )
    else:
        return jsonify({'success': False, 'error': 'Invalid download format requested.'}), 400
    

@app.route('/summarise_transcript', methods=['POST'])
def summarise_transcript():
    data = request.get_json()
    transcript_text = data.get('transcript', '')
    original_filename = data.get('original_filename', 'unknown_audio')


    if not transcript_text:
        return jsonify({'success': False, 'error': 'No transcript provided.'}), 400
    
    try:
        print("[INFO] Calling structured summarization module...")
        summary_results = process_transcript_for_summary(transcript_text)
        print("[INFO] Structured summarization complete.")

        if "error" in summary_results:
            return jsonify({'success': False, 'error': summary_results["error"]}), 500
        
        summary_json_string = json.dumps(summary_results, indent=2)

        new_model_file_entry = ModelFile(
            filename=original_filename,
            Modeloutput=summary_json_string
        )

        db.session.add(new_model_file_entry)
        db.session.commit()
        print(f"[INFO] Summarization results for {original_filename} committed to ModelFile database.")

        return jsonify({
            'success': True,
            'redirect_url': url_for(
                'display_summary',
                summary_data=summary_json_string, 
                original_filename=original_filename 
            )
        })
    except Exception as e:
        print(f"[ERROR] Fatal error during summarization route: {str(e)}")
        import traceback
        traceback.print_exc() 
        return jsonify({'success': False, 'error': f"Server error during summarization: {str(e)}"}), 500
    


@app.route('/display_summary')
def display_summary():
    summary_data_json_string = request.args.get('summary_data', '{}')
    original_filename = request.args.get('original_filename', 'Unknown')
    try:
        summary_data = json.loads(summary_data_json_string)
    except json.JSONDecodeError:
        summary_data = {"error": "Invalid summary data format. Could not parse JSON."}
        print("[ERROR] Failed to decode summary_data_json_string:", summary_data_json_string)

    return render_template('summary.html', summary_data=summary_data, original_filename=original_filename)
        




@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))




if __name__ == "__main__":
    print("Runs only when app1.py")


    
    