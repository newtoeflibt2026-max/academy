from flask import Blueprint, jsonify, request
from modules.models import query_db, execute_db
from modules.placement_middleware import check_placement
from modules.ai_engine import log_activity, get_ai_config
import os, time
from config import UPLOAD_FOLDER

student_bp = Blueprint("student_api", __name__)

# --- Skills list ---
@student_bp.route("/api/skills")
def skills():
    rows = query_db("SELECT * FROM daily_skills WHERE is_active=1 ORDER BY sort_order")
    return jsonify([dict(r) for r in rows])

# --- Next question for a skill ---
@student_bp.route("/api/question/next", methods=["POST"])
def next_question():
    data = request.get_json()
    skill_id = data.get("skill_id")
    student_id = data.get("student_id")
    row = query_db("SELECT * FROM questions WHERE skill_id=? AND is_active=1 ORDER BY RANDOM() LIMIT 1", (skill_id,), one=True)
    if not row:
        return jsonify({"question": None, "message": "No questions available"})
    log_activity(student_id, "fetch_question", f"skill={skill_id}, qid={row['id']}")
    return jsonify(dict(row))

# --- XP Update ---
@student_bp.route("/api/student/xp", methods=["POST"])
def add_xp():
    data = request.get_json()
    sid = data.get("student_id")
    xp = data.get("xp", 0)
    execute_db("INSERT OR IGNORE INTO students (telegram_id) VALUES (?)", (sid,))
    execute_db("UPDATE students SET xp=xp+? WHERE telegram_id=?", (xp, sid))
    row = query_db("SELECT xp, level FROM students WHERE telegram_id=?", (sid,), one=True)
    return jsonify({"xp": row["xp"], "level": row["level"]})

# --- Leaderboard ---
@student_bp.route("/api/leaderboard")
def leaderboard():
    rows = query_db("SELECT telegram_id, name, xp, level FROM students ORDER BY xp DESC LIMIT 10")
    return jsonify([dict(r) for r in rows])

# --- Error bank ---
@student_bp.route("/api/error_bank/<int:student_id>")
def error_bank(student_id):
    count = query_db("SELECT COUNT(*) as cnt FROM error_bank WHERE student_id=? AND is_corrected=0", (student_id,), one=True)
    rows = query_db("SELECT * FROM error_bank WHERE student_id=? ORDER BY created_at DESC LIMIT 20", (student_id,))
    return jsonify({"pending": count["cnt"] if count else 0, "items": [dict(r) for r in rows]})

@student_bp.route("/api/error_bank/add", methods=["POST"])
def add_error():
    data = request.get_json()
    execute_db("INSERT INTO error_bank (student_id, question_id, skill_type) VALUES (?,?,?)",
        (data["student_id"], data.get("question_id"), data.get("skill_type")))
    return jsonify({"ok": True})

# --- Library ---
@student_bp.route("/api/library")
def library():
    rows = query_db("SELECT * FROM library_items WHERE is_active=1")
    return jsonify([dict(r) for r in rows])

# --- Student profile ---
@student_bp.route("/api/profile/<int:student_id>")
def profile(student_id):
    row = query_db("SELECT * FROM students WHERE telegram_id=?", (student_id,), one=True)
    if not row:
        return jsonify({"error": "Student not found"}), 404
    placement = query_db("SELECT level FROM placement_results WHERE student_id=? ORDER BY id DESC LIMIT 1", (student_id,), one=True)
    sub = query_db("SELECT s.*, p.name FROM subscriptions s JOIN billing_plans p ON s.plan_id=p.id WHERE s.student_id=? AND s.status='active' ORDER BY s.id DESC LIMIT 1", (student_id,), one=True)
    return jsonify({
        "student": dict(row),
        "placement_level": placement["level"] if placement else None,
        "subscription": dict(sub) if sub else None
    })

# --- Audio submission ---
@student_bp.route("/api/ai/speaking", methods=["POST"])
def submit_speaking():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file"}), 400
    file = request.files["audio"]
    student_id = int(request.form.get("student_id", 0))
    skill_id = int(request.form.get("skill_id", 0))
    from modules.audio_logic import save_audio_blob, evaluate_speaking
    filepath, filename = save_audio_blob(file.read(), student_id, file.filename)
    result = evaluate_speaking(filepath)
    sid = execute_db(
        "INSERT INTO audio_submissions (student_id, skill_id, file_path, ai_score, ai_feedback, transcript) VALUES (?,?,?,?,?,?)",
        (student_id, skill_id, filepath, result["score"], f"Score: {result['score']}/10", result["transcript"])
    )
    log_activity(student_id, "submit_speaking", f"submission={sid}")
    return jsonify({"id": sid, **result})

# --- Writing submission ---
@student_bp.route("/api/ai/writing", methods=["POST"])
def submit_writing():
    data = request.get_json()
    from modules.audio_logic import evaluate_writing
    result = evaluate_writing(data["content"])
    sid = execute_db(
        "INSERT INTO writing_submissions (student_id, skill_id, content, ai_score, ai_feedback) VALUES (?,?,?,?,?)",
        (data["student_id"], data.get("skill_id"), data["content"], result["score"], f"Word count: {result['word_count']}")
    )
    log_activity(data["student_id"], "submit_writing", f"submission={sid}")
    return jsonify({"id": sid, **result})

# --- Courses list ---
@student_bp.route("/api/courses")
def courses():
    rows = query_db("SELECT * FROM courses WHERE is_active=1")
    return jsonify([dict(r) for r in rows])
