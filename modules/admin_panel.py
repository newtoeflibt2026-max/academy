from flask import Blueprint, request, jsonify, send_from_directory
from modules.models import query_db, execute_db
from modules.ai_engine import assess_speaking_submission, assess_writing_submission
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from werkzeug.utils import secure_filename
import os, time

admin_bp = Blueprint("admin", __name__)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ========== STATS ==========
@admin_bp.route("/api/admin/stats")
def admin_stats():
    students  = query_db("SELECT COUNT(*) as c FROM students", one=True)["c"]
    courses   = query_db("SELECT COUNT(*) as c FROM courses", one=True)["c"]
    lessons   = query_db("SELECT COUNT(*) as c FROM library_items", one=True)["c"]
    questions = query_db("SELECT COUNT(*) as c FROM questions", one=True)["c"]
    skills    = query_db("SELECT COUNT(*) as c FROM daily_skills", one=True)["c"]
    placements = query_db("SELECT COUNT(*) as c FROM placement_results", one=True)["c"]
    errors    = query_db("SELECT COUNT(*) as c FROM error_bank WHERE is_corrected=0", one=True)["c"]
    audio_subs = query_db("SELECT COUNT(*) as c FROM audio_submissions", one=True)["c"]
    writing_subs = query_db("SELECT COUNT(*) as c FROM writing_submissions", one=True)["c"]

    return jsonify({
        "students": students, "courses": courses, "library_items": lessons,
        "questions": questions, "skills": skills, "placement_tests": placements,
        "pending_errors": errors, "audio_submissions": audio_subs, "writing_submissions": writing_subs
    })

# ========== STUDENTS LIST ==========
@admin_bp.route("/api/admin/students")
def admin_students():
    rows = query_db("""
        SELECT s.*, pr.level as placement_level, pr.score as placement_score
        FROM students s
        LEFT JOIN placement_results pr ON s.telegram_id = pr.student_id
        ORDER BY s.xp DESC
    """)
    return jsonify([dict(r) for r in rows])

# ========== SKILLS CRUD ==========
@admin_bp.route("/api/admin/skills")
def admin_skills():
    rows = query_db("SELECT * FROM daily_skills ORDER BY sort_order")
    return jsonify([dict(r) for r in rows])

@admin_bp.route("/api/admin/skills/add", methods=["POST"])
def add_skill():
    data = request.get_json()
    sid = execute_db(
        """INSERT INTO daily_skills (title, skill_type, task_type, icon, time_limit, telegram_link, sort_order)
           VALUES (?,?,?,?,?,?, (SELECT COALESCE(MAX(sort_order),0)+1 FROM daily_skills))""",
        (data["title"], data.get("skill_type","text"), data.get("task_type","mcq"),
         data.get("icon","fa-star"), data.get("time_limit",45), data.get("telegram_link"))
    )
    return jsonify({"id": sid, "ok": True})

@admin_bp.route("/api/admin/skills/update/<int:skill_id>", methods=["PUT"])
def update_skill(skill_id):
    data = request.get_json()
    execute_db(
        "UPDATE daily_skills SET title=?, skill_type=?, task_type=?, icon=?, time_limit=?, telegram_link=?, is_active=? WHERE id=?",
        (data["title"], data.get("skill_type"), data.get("task_type"), data.get("icon"),
         data.get("time_limit"), data.get("telegram_link"), data.get("is_active",1), skill_id)
    )
    return jsonify({"ok": True})

@admin_bp.route("/api/admin/skills/delete/<int:skill_id>", methods=["DELETE"])
def delete_skill(skill_id):
    execute_db("DELETE FROM daily_skills WHERE id=?", (skill_id,))
    return jsonify({"ok": True})

@admin_bp.route("/api/admin/skills/toggle/<int:skill_id>", methods=["POST"])
def toggle_skill(skill_id):
    execute_db("UPDATE daily_skills SET is_active = 1 - is_active WHERE id=?", (skill_id,))
    return jsonify({"ok": True})

@admin_bp.route("/api/admin/skills/reorder", methods=["POST"])
def reorder_skills():
    data = request.get_json()
    for item in data.get("order", []):
        execute_db("UPDATE daily_skills SET sort_order=? WHERE id=?", (item["order"], item["id"]))
    return jsonify({"ok": True})

# ========== LIBRARY CRUD ==========
@admin_bp.route("/api/admin/library")
def admin_library():
    rows = query_db("SELECT * FROM library_items ORDER BY created_at DESC")
    return jsonify([dict(r) for r in rows])

@admin_bp.route("/api/admin/library/add", methods=["POST"])
def add_library():
    title = request.form.get("title", "Untitled")
    item_type = request.form.get("item_type", "pdf")
    external_url = request.form.get("external_url", "")
    course_id = request.form.get("course_id", 1)

    file_path = None
    if "file" in request.files:
        file = request.files["file"]
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{int(time.time())}_{file.filename}")
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            full_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(full_path)
            file_path = f"/static/uploads/{filename}"

    lid = execute_db(
        "INSERT INTO library_items (title, item_type, file_path, external_url, course_id) VALUES (?,?,?,?,?)",
        (title, item_type, file_path, external_url, course_id)
    )
    return jsonify({"id": lid, "ok": True})

@admin_bp.route("/api/admin/library/update/<int:item_id>", methods=["PUT"])
def update_library(item_id):
    data = request.get_json() if request.is_json else request.form
    title = data.get("title")
    is_active = data.get("is_active", 1)
    execute_db("UPDATE library_items SET title=?, is_active=? WHERE id=?", (title, is_active, item_id))
    return jsonify({"ok": True})

@admin_bp.route("/api/admin/library/delete/<int:item_id>", methods=["DELETE"])
def delete_library(item_id):
    execute_db("DELETE FROM library_items WHERE id=?", (item_id,))
    return jsonify({"ok": True})

@admin_bp.route("/api/admin/library/toggle/<int:item_id>", methods=["POST"])
def toggle_library(item_id):
    execute_db("UPDATE library_items SET is_active = 1 - is_active WHERE id=?", (item_id,))
    return jsonify({"ok": True})

# ========== PLACEMENT QUESTIONS CRUD ==========
@admin_bp.route("/api/admin/placement_questions")
def placement_questions():
    rows = query_db("SELECT * FROM placement_questions")
    return jsonify([dict(r) for r in rows])

@admin_bp.route("/api/admin/placement_questions/add", methods=["POST"])
def add_placement_question():
    data = request.get_json()
    qid = execute_db(
        "INSERT INTO placement_questions (question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty) VALUES (?,?,?,?,?,?,?)",
        (data["question_text"], data["option_a"], data["option_b"], data["option_c"], data["option_d"], data["correct_answer"], data.get("difficulty","medium"))
    )
    return jsonify({"id": qid, "ok": True})

@admin_bp.route("/api/admin/placement_questions/delete/<int:qid>", methods=["DELETE"])
def delete_placement_question(qid):
    execute_db("DELETE FROM placement_questions WHERE id=?", (qid,))
    return jsonify({"ok": True})

@admin_bp.route("/api/admin/placement_questions/toggle/<int:qid>", methods=["POST"])
def toggle_placement_question(qid):
    execute_db("UPDATE placement_questions SET is_active = 1 - is_active WHERE id=?", (qid,))
    return jsonify({"ok": True})

# ========== PLACEMENT RESULTS ==========
@admin_bp.route("/api/admin/placement_results")
def placement_results():
    rows = query_db("""
        SELECT pr.*, s.name as student_name
        FROM placement_results pr
        JOIN students s ON pr.student_id = s.telegram_id
        ORDER BY pr.completed_at DESC
    """)
    return jsonify([dict(r) for r in rows])

# ========== SUBMISSIONS HUB ==========
@admin_bp.route("/api/admin/submissions/audio")
def audio_submissions():
    rows = query_db("""
        SELECT asub.*, s.name as student_name, ds.title as skill_title
        FROM audio_submissions asub
        JOIN students s ON asub.student_id = s.telegram_id
        LEFT JOIN daily_skills ds ON asub.skill_id = ds.id
        ORDER BY asub.submitted_at DESC
    """)
    return jsonify([dict(r) for r in rows])

@admin_bp.route("/api/admin/submissions/writing")
def writing_submissions():
    rows = query_db("""
        SELECT wsub.*, s.name as student_name, ds.title as skill_title
        FROM writing_submissions wsub
        JOIN students s ON wsub.student_id = s.telegram_id
        LEFT JOIN daily_skills ds ON wsub.skill_id = ds.id
        ORDER BY wsub.submitted_at DESC
    """)
    return jsonify([dict(r) for r in rows])

@admin_bp.route("/api/admin/submissions/evaluate_audio/<int:submission_id>", methods=["POST"])
def evaluate_audio(submission_id):
    result = assess_speaking_submission(submission_id)
    return jsonify({"ok": True, "result": result})

@admin_bp.route("/api/admin/submissions/evaluate_writing/<int:submission_id>", methods=["POST"])
def evaluate_writing_admin(submission_id):
    result = assess_writing_submission(submission_id)
    return jsonify({"ok": True, "result": result})

# ========== AI CONFIG ==========
@admin_bp.route("/api/admin/ai_config")
def ai_config():
    rows = query_db("SELECT * FROM ai_config")
    return jsonify([dict(r) for r in rows])

@admin_bp.route("/api/admin/ai_config/update", methods=["POST"])
def update_ai_config():
    data = request.get_json()
    for key, value in data.items():
        execute_db("UPDATE ai_config SET config_value=? WHERE config_key=?", (str(value), key))
    return jsonify({"ok": True})

# ========== SERVE UPLOADS (for audio playback) ==========
@admin_bp.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ========== BILLING ADMIN ==========
@admin_bp.route("/api/admin/subscriptions")
def admin_subscriptions():
    rows = query_db("""
        SELECT sub.*, s.name as student_name, p.name as plan_name, p.price_monthly
        FROM subscriptions sub
        JOIN students s ON sub.student_id = s.telegram_id
        JOIN billing_plans p ON sub.plan_id = p.id
        ORDER BY sub.started_at DESC
    """)
    return jsonify([dict(r) for r in rows])

# ========== ACTIVITY LOG ==========
@admin_bp.route("/api/admin/activity_log")
def activity_log():
    rows = query_db("""
        SELECT al.*, s.name as student_name
        FROM activity_log al
        LEFT JOIN students s ON al.student_id = s.telegram_id
        ORDER BY al.created_at DESC LIMIT 100
    """)
    return jsonify([dict(r) for r in rows])
