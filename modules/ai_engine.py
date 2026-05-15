"""
ai_engine.py — محرك تقييم التوفل (Audio + Writing)
يستورد دوال audio_logic ويضيف طبقة تقييم متقدمة
"""
from modules.audio_logic import evaluate_speaking, evaluate_writing, try_transcribe
from modules.models import query_db, execute_db
import json

def assess_speaking_submission(user_id: int, skill_id: int, filepath: str) -> dict:
    """
    تقييم كامل لإجابة صوتية:
    1. نسخ الملف الصوتي إلى نص
    2. تحليل النص
    3. حفظ النتيجة في قاعدة البيانات
    """
    # 1. النسخ
    transcript = try_transcribe(filepath)

    # 2. تحميل الكلمات المفتاحية المتوقعة من المهارة
    skill = query_db("SELECT title, target_score FROM daily_skills WHERE id=?", (skill_id,), one=True)
    expected_keywords = []
    if skill:
        expected_keywords = skill["title"].split() if skill["title"] else []

    # 3. التقييم
    eval_result = evaluate_speaking(transcript, expected_keywords)

    # 4. حفظ
    execute_db(
        """INSERT INTO audio_submissions (user_id, skill_id, filename, transcription, ai_score, ai_feedback, duration_seconds)
           VALUES (?, ?, ?, ?, ?, ?, 30)""",
        (user_id, skill_id, filepath.split("/")[-1], transcript,
         eval_result["score"], eval_result["feedback"]))

    # 5. XP
    xp_earned = int(eval_result["score"] * 2)
    execute_db("UPDATE students SET xp=COALESCE(xp,0)+?, last_active=CURRENT_TIMESTAMP WHERE telegram_id=?",
               (xp_earned, user_id))

    return {
        "score": eval_result["score"],
        "feedback": eval_result["feedback"],
        "transcript": transcript[:200],
        "word_count": eval_result["word_count"],
        "xp_earned": xp_earned
    }

def assess_writing_submission(user_id: int, skill_id: int, essay: str) -> dict:
    """
    تقييم كامل لإجابة كتابية
    """
    eval_result = evaluate_writing(essay)

    execute_db(
        """INSERT INTO writing_submissions (user_id, skill_id, essay_text, ai_score, ai_feedback, word_count, grammar_issues)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, skill_id, essay, eval_result["score"], eval_result["feedback"],
         eval_result["word_count"], eval_result["grammar_issues"]))

    xp_earned = int(eval_result["score"] * 3)
    execute_db("UPDATE students SET xp=COALESCE(xp,0)+? WHERE telegram_id=?",
               (xp_earned, user_id))

    return {
        "score": eval_result["score"],
        "feedback": eval_result["feedback"],
        "word_count": eval_result["word_count"],
        "xp_earned": xp_earned
    }

def get_ai_config() -> dict:
    """جلب جميع إعدادات AI"""
    rows = query_db("SELECT config_key, config_value, description FROM ai_config")
    return {r["config_key"]: {"value": r["config_value"], "desc": r["description"]} for r in rows} if rows else {}

def log_activity(user_id: int, action: str, details: str = "", xp_change: int = 0):
    """تسجيل نشاط المستخدم"""
    execute_db(
        "INSERT INTO activity_log (user_id, action, details, xp_change) VALUES (?,?,?,?)",
        (user_id, action, details, xp_change))
