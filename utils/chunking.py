from pydub import AudioSegment
import tempfile
import os



def chunk_audio_with_overlap(input_path, chunk_length_ms=300000, overlap_ms=10000):
    audio = AudioSegment.from_wav(input_path)
    chunks = []
    temp_dir = tempfile.mkdtemp()

    for start in range(0, len(audio), chunk_length_ms - overlap_ms):
        end = start + chunk_length_ms
        chunk = audio[start:end]
        chunk_path = os.path.join(temp_dir, f"chunk_{start//1000}.wav")
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    return chunks