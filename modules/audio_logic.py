"""
audio_logic.py — معالجة الملفات الصوتية: حفظ، تحويل WebM→WAV، نسخ
يعتمد على SpeechRecognition + pydub (اختياري)
"""
import os, uuid, json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "static", "audio")

# تأكد من وجود مجلد الصوت
os.makedirs(AUDIO_DIR, exist_ok=True)

def save_audio_blob(blob_data: bytes, user_id: int, skill_id: int = 0) -> dict:
    """
    حفظ ملف صوتي من المتصفح (WebM blob).
    يُرجع: {filename, filepath, duration_seconds}
    """
    filename = f"speaking_{user_id}_{uuid.uuid4().hex[:8]}.webm"
    filepath = os.path.join(AUDIO_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(blob_data)

    duration = estimate_duration(filepath)

    print(f"🎙️ Audio saved: {filename} | {len(blob_data)} bytes | ~{duration:.1f}s")
    return {
        "filename": filename,
        "filepath": filepath,
        "duration_seconds": round(duration, 1)
    }

def estimate_duration(filepath: str) -> float:
    """تقدير مدة الملف الصوتي بالثواني (تقريبي لـ WebM)"""
    try:
        size = os.path.getsize(filepath)
        # WebM opus ~16 kbps → bytes ≈ 2000 per second
        return size / 2000.0
    except:
        return 0.0

def try_transcribe(filepath: str) -> str:
    """
    محاولة نسخ الملف الصوتي إلى نص (Speech-to-Text).
    يتطلب تثبيت: pip install SpeechRecognition pydub
    """
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()

        # تحويل WebM → WAV إذا لزم الأمر
        wav_path = filepath.replace(".webm", ".wav")
        if not os.path.exists(wav_path):
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(filepath)
                audio.export(wav_path, format="wav")
            except ImportError:
                print("⚠️ pydub غير مثبت — تخطي التحويل")
                return "[pydub not available]"

        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="en-US")
            print(f"📝 Transcribed: {text[:100]}...")
            return text
    except ImportError:
        print("⚠️ SpeechRecognition غير مثبت — تخطي النسخ")
        return "[Speech-to-Text offline]"
    except Exception as e:
        print(f"⚠️ Transcription failed: {e}")
        return f"[Transcription error: {e}]"

def evaluate_speaking(transcript: str, expected_keywords: list = None) -> dict:
    """
    تقييم بسيط للإجابة الصوتية بناءً على:
    - طول النص
    - وجود كلمات مفتاحية
    - تنوع المفردات
    """
    words = transcript.split()
    word_count = len(words)
    unique_words = len(set(words))

    # Score أساسي
    score = min(5.0, max(1.0, word_count / 15 + 2.0))

    # مكافأة على تنوع المفردات
    if unique_words > 20:
        score += 0.5

    # خصم للقصير جداً
    if word_count < 10:
        score = max(1.0, score - 1.0)

    # كلمات مفتاحية
    keywords_found = []
    if expected_keywords:
        keywords_found = [kw for kw in expected_keywords if kw.lower() in transcript.lower()]
        score += len(keywords_found) * 0.2

    score = min(5.0, round(score, 1))

    feedback_parts = []
    if word_count < 15:
        feedback_parts.append("حاول التحدث لمدة أطول")
    if unique_words < 12:
        feedback_parts.append("نوّع مفرداتك")
    if keywords_found:
        feedback_parts.append(f"أحسنت ذكر: {', '.join(keywords_found[:3])}")
    if score >= 4:
        feedback_parts.append("أداء ممتاز!")

    return {
        "score": score,
        "word_count": word_count,
        "unique_words": unique_words,
        "keywords_found": keywords_found,
        "feedback": " | ".join(feedback_parts) if feedback_parts else "حاول مرة أخرى"
    }

def evaluate_writing(essay: str, expected_keywords: list = None) -> dict:
    """
    تقييم بسيط للكتابة: عدد الكلمات، جودة، أخطاء شائعة
    """
    words = essay.split()
    word_count = len(words)
    sentences = [s.strip() for s in essay.replace('!','.').replace('?','.').split('.') if s.strip()]
    sentence_count = len(sentences)
    avg_words_per_sentence = word_count / max(sentence_count, 1)

    # Score
    score = min(5.0, max(1.0, word_count / 50 + 2.5))

    # خصم للجمل القصيرة جداً
    if avg_words_per_sentence < 5:
        score -= 0.5

    # أخطاء شائعة
    common_errors = {
        " i ": "I",
        "dont": "don't",
        "cant": "can't",
        "wont": "won't",
        "its ": "it's " if "it is" in essay.lower() else "its ",
    }
    error_count = sum(1 for err in common_errors if err in essay.lower())

    score = max(1.0, round(score - error_count * 0.2, 1))

    feedback_parts = []
    if word_count < 100:
        feedback_parts.append("حاول كتابة 100 كلمة على الأقل")
    if sentence_count < 3:
        feedback_parts.append("قسّم النص إلى جمل أوضح")
    if error_count:
        feedback_parts.append(f"راجع الأخطاء الإملائية ({error_count})")
    if score >= 4:
        feedback_parts.append("كتابة ممتازة!")

    return {
        "score": score,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_words_per_sentence": round(avg_words_per_sentence, 1),
        "grammar_issues": error_count,
        "feedback": " | ".join(feedback_parts) if feedback_parts else "جيد"
    }
