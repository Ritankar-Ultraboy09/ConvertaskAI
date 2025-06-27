from faster_whisper import WhisperModel


model = WhisperModel("medium", device="cpu", compute_type="float32")

def transcribe_chunk(file_path):

    prompt_text = "Aman. a month. Amand . Udit. U dict. you dict. uuu diiittt. Priyo. pre yo. AIFY. AI five. AISI.This is a conversation "
    segments, info = model.transcribe(
        file_path,
        beam_size=5,
        language=None,
        task="translate" ,
        initial_prompt= prompt_text,

    )
    
    transcript = ""
    for segment in segments:
        print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
        transcript += segment.text.strip() + " "
    
    return transcript.strip()