"""
student_api.py — Blueprint خاص بواجهة الطالب: مهارات، أسئلة، XP، متصدرين
"""
from flask import Blueprint, jsonify, request
from modules.models import query_db, execute_db
from modules.ai_engine import assess_speaking_submission, assess_writing_submission, log_activity
from modules.audio_logic import save_audio_blob
import os

student_bp = Blueprint("student", __name__, url_prefix="/api")

# ═══ المهارات النشطة ═══
@student_bp.route("/skills")
def api_skills():
    rows = query_db("SELECT * FROM daily_skills WHERE is_active=1 ORDER BY sort_order, id")
    return jsonify([dict(r) for r in rows] if rows else [])

# ═══ السؤال التالي ═══
@student_bp.route("/question/next", methods=["POST"])
def api_next_question():
    d = request.get_json()
    skill_type = d.get("skill_type")
    student_id = d.get("student_id")
    last_qid = d.get("last_question_id", 0)

    if not skill_type:
        return jsonify({"error": "نوع المهارة مطلوب"}), 400

    q = query_db(
        "SELECT * FROM questions WHERE skill_type=? AND is_active=1 AND id>? ORDER BY id ASC LIMIT 1",
        (skill_type, last_qid), one=True)
    if not q:
        q = query_db(
            "SELECT * FROM questions WHERE skill_type=? AND is_active=1 ORDER BY id ASC LIMIT 1",
            (skill_type,), one=True)
    if not q:
        return jsonify({"error": "لا توجد أسئلة لهذه المهارة"}), 404

    if student_id:
        execute_db("UPDATE students SET last_active=CURRENT_TIMESTAMP WHERE telegram_id=?", (student_id,))
        log_activity(student_id, "question_fetch", f"skill={skill_type}")

    return jsonify({
        "question": dict(q),
        "has_timer": True,
        "time_limit": dict(q).get("time_limit", 45)
    })

# ═══ تحديث XP ═══
@student_bp.route("/student/xp", methods=["POST"])
def api_update_xp():
    d = request.get_json()
    sid = d.get("student_id")
    xp = d.get("xp_gain", 10)
    if not sid:
        return jsonify({"error": "ID مطلوب"}), 400

    execute_db("UPDATE students SET xp=COALESCE(xp,0)+?, last_active=CURRENT_TIMESTAMP WHERE telegram_id=?", (xp, sid))
    log_activity(sid, "xp_gain", f"+{xp} XP")

    row = query_db("SELECT xp, level FROM students WHERE telegram_id=?", (sid,), one=True)
    return jsonify({"xp": row["xp"], "level": row["level"]}) if row else jsonify({"error": "غير موجود"}), 404

# ═══ المتصدرين ═══
@student_bp.route("/leaderboard")
def api_leaderboard():
    rows = query_db(
        "SELECT telegram_id, first_name, username, xp, level FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT 10")
    return jsonify([dict(r) for r in rows] if rows else [])

# ═══ بنك الأخطاء ═══
@student_bp.route("/error_bank/<int:user_id>")
def api_error_bank(user_id):
    rows = query_db(
        """SELECT e.*, q.question_text, q.correct_answer FROM error_bank e
           LEFT JOIN questions q ON e.question_id = q.id
           WHERE e.user_id=?""", (user_id,))
    return jsonify([dict(r) for r in rows] if rows else [])

@student_bp.route("/error_bank/add", methods=["POST"])
def api_error_add():
    d = request.get_json()
    execute_db(
        "INSERT OR IGNORE INTO error_bank (user_id, question_id, skill_type) VALUES (?,?,?)",
        (d.get("user_id"), d.get("question_id"), d.get("skill_type")))
    return jsonify({"success": True})

@student_bp.route("/error_bank/correct", methods=["POST"])
def api_error_correct():
    d = request.get_json()
    qid = d.get("question_id")
    uid = d.get("user_id")
    execute_db("UPDATE error_bank SET correct_count=COALESCE(correct_count,0)+1 WHERE question_id=? AND user_id=?", (qid, uid))
    row = query_db("SELECT correct_count FROM error_bank WHERE question_id=? AND user_id=?", (qid, uid), one=True)
    if row and row["correct_count"] >= 2:
        execute_db("DELETE FROM error_bank WHERE question_id=? AND user_id=?", (qid, uid))
    return jsonify({"success": True})

# ═══ AI Assessment ═══
@student_bp.route("/ai/speaking", methods=["POST"])
def api_ai_speaking():
    """استقبال ملف صوتي وتحليله"""
    if 'audio' not in request.files:
        return jsonify({"error": "لا يوجد ملف صوتي"}), 400

    file = request.files['audio']
    user_id = int(request.form.get("user_id", 0))
    skill_id = int(request.form.get("skill_id", 0))

    blob_data = file.read()
    audio_info = save_audio_blob(blob_data, user_id, skill_id)
    result = assess_speaking_submission(user_id, skill_id, audio_info["filepath"])

    log_activity(user_id, "speaking_submit", f"score={result['score']}", result["xp_earned"])
    return jsonify(result)

@student_bp.route("/ai/writing", methods=["POST"])
def api_ai_writing():
    """استقبال نص كتابي وتحليله"""
    d = request.get_json()
    user_id = d.get("user_id")
    skill_id = d.get("skill_id", 0)
    essay = d.get("essay", "")

    if not user_id or not essay:
        return jsonify({"error": "البيانات مطلوبة"}), 400

    result = assess_writing_submission(user_id, skill_id, essay)
    log_activity(user_id, "writing_submit", f"score={result['score']}", result["xp_earned"])
    return jsonify(result)

# ═══ المكتبة ═══
@student_bp.route("/library")
def api_library():
    rows = query_db("SELECT * FROM library_items WHERE is_active=1 ORDER BY sort_order, id")
    return jsonify([dict(r) for r in rows] if rows else [])
