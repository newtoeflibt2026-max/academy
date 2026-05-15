import os, time
from config import UPLOAD_FOLDER

def save_audio_blob(audio_data, student_id, filename=None):
    ts = int(time.time())
    if not filename:
        filename = f"audio_{student_id}_{ts}.webm"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, "wb") as f:
        f.write(audio_data)
    return filepath, filename

def estimate_duration(filepath):
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(filepath)
        return len(audio) / 1000.0
    except:
        return 0

def try_transcribe(filepath):
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(filepath) as source:
            audio = r.record(source)
        return r.recognize_google(audio)
    except:
        return ""

def evaluate_speaking(filepath, expected_text=""):
    duration = estimate_duration(filepath)
    transcript = try_transcribe(filepath)
    score = min(10.0, max(1.0, duration / 6.0))  # ~60s = 10/10
    return {"score": round(score,1), "transcript": transcript, "duration": round(duration,1)}

def evaluate_writing(content, expected=""):
    word_count = len(content.split())
    # 150+ words = 10/10
    score = min(10.0, max(1.0, word_count / 15.0))
    return {"score": round(score,1), "word_count": word_count}
