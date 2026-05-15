from flask import Blueprint, request, jsonify, send_from_directory
from modules.models import query_db, execute_db
from modules.ai_engine import assess_speaking_submission, assess_writing_submission, update_ai_config as set_ai_config, get_ai_config
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from werkzeug.utils import secure_filename
import os, time

admin_bp = Blueprint("admin", __name__)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ========== STATS ==========
@admin_bp.route("/api/admin/stats")
def admin_stats():
    def cnt(table, where=""):
        q = f"SELECT COUNT(*) as c FROM {table}"
        if where: q += f" WHERE {where}"
        return query_db(q, one=True)["c"]
    return jsonify({
        "students": cnt("students"),
        "courses": cnt("courses"),
        "library_items": cnt("library_items"),
        "questions": cnt("questions"),
        "skills": cnt("daily_skills"),
        "placement_tests": cnt("placement_results"),
        "pending_errors": cnt("error_bank", "is_corrected=0"),
        "audio_submissions": cnt("audio_submissions"),
        "writing_submissions": cnt("writing_submissions"),
    })

# ========== STUDENTS ==========
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
    data = request.form if request.form else request.get_json() or {}
    title = data.get("title", "New Skill")
    skill_type = data.get("skill_type", "text")
    task_type = data.get("task_type", "mcq")
    icon = data.get("icon", "fa-star")
    time_limit = data.get("time_limit", "45")
    telegram_link = data.get("telegram_link", "")
    content_path = None

    # Handle skill content file upload
    if "content_file" in request.files:
        file = request.files["content_file"]
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"skill_{int(time.time())}_{file.filename}")
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            full = os.path.join(UPLOAD_FOLDER, filename)
            file.save(full)
            content_path = f"/static/uploads/{filename}"

    sid = execute_db(
        """INSERT INTO daily_skills (title, skill_type, task_type, icon, time_limit, telegram_link, content_path, sort_order)
           VALUES (?,?,?,?,?,?,?, (SELECT COALESCE(MAX(sort_order),0)+1 FROM daily_skills))""",
        (title, skill_type, task_type, icon, int(time_limit) if str(time_limit).isdigit() else 45, telegram_link, content_path)
    )
    return jsonify({"id": sid, "ok": True})

@admin_bp.route("/api/admin/skills/update/<int:skill_id>", methods=["PUT"])
def update_skill(skill_id):
    data = request.get_json()
    execute_db(
        "UPDATE daily_skills SET title=?, skill_type=?, task_type=?, icon=?, time_limit=?, telegram_link=?, is_active=? WHERE id=?",
        (data["title"], data.get("skill_type"), data.get("task_type"), data.get("icon"),
         data.get("time_limit"), data.get("telegram_link"), data.get("is_active", 1), skill_id)
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

# ========== LIBRARY CRUD (with file upload) ==========
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
            filename = secure_filename(f"lib_{int(time.time())}_{file.filename}")
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            full_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(full_path)
            file_path = f"/static/uploads/{filename}"

    lid = execute_db(
        "INSERT INTO library_items (title, item_type, file_path, external_url, course_id) VALUES (?,?,?,?,?)",
        (title, item_type, file_path, external_url, course_id)
    )
    return jsonify({"id": lid, "ok": True})

@admin_bp.route("/api/admin/library/delete/<int:item_id>", methods=["DELETE"])
def delete_library(item_id):
    row = query_db("SELECT file_path FROM library_items WHERE id=?", (item_id,), one=True)
    if row and row["file_path"]:
        fp = os.path.join(UPLOAD_FOLDER, os.path.basename(row["file_path"]))
        if os.path.exists(fp):
            os.remove(fp)
    execute_db("DELETE FROM library_items WHERE id=?", (item_id,))
    return jsonify({"ok": True})

@admin_bp.route("/api/admin/library/toggle/<int:item_id>", methods=["POST"])
def toggle_library(item_id):
    execute_db("UPDATE library_items SET is_active = 1 - is_active WHERE id=?", (item_id,))
    return jsonify({"ok": True})

# ========== SUBMISSIONS ==========
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

@admin_bp.route("/api/admin/submissions/evaluate_audio/<int:sid>", methods=["POST"])
def evaluate_audio(sid):
    result = assess_speaking_submission(sid)
    return jsonify({"ok": True, "result": result})

@admin_bp.route("/api/admin/submissions/evaluate_writing/<int:sid>", methods=["POST"])
def evaluate_writing_admin(sid):
    result = assess_writing_submission(sid)
    return jsonify({"ok": True, "result": result})

# ========== AI CONFIG ==========
@admin_bp.route("/api/admin/ai_config")
def ai_config():
    rows = query_db("SELECT * FROM ai_config")
    return jsonify([dict(r) for r in rows])

@admin_bp.route("/api/admin/ai_config/update", methods=["POST"])
def update_ai_config_route():
    data = request.get_json()
    set_ai_config(data)
    return jsonify({"ok": True})

# ========== BILLING ==========
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

# ========== SERVE UPLOADS ==========
@admin_bp.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ========== QUESTIONS CRUD (for daily skills) ==========
@admin_bp.route("/api/admin/questions")
def admin_questions():
    rows = query_db("SELECT q.*, ds.title as skill_title FROM questions q LEFT JOIN daily_skills ds ON q.skill_id=ds.id ORDER BY q.id DESC")
    return jsonify([dict(r) for r in rows])

@admin_bp.route("/api/admin/questions/add", methods=["POST"])
def add_question():
    data = request.get_json()
    qid = execute_db(
        "INSERT INTO questions (skill_id, question_text, option_a, option_b, option_c, option_d, correct_answer) VALUES (?,?,?,?,?,?,?)",
        (data["skill_id"], data["question_text"], data["option_a"], data["option_b"], data["option_c"], data["option_d"], data["correct_answer"])
    )
    return jsonify({"id": qid, "ok": True})

@admin_bp.route("/api/admin/questions/delete/<int:qid>", methods=["DELETE"])
def delete_question(qid):
    execute_db("DELETE FROM questions WHERE id=?", (qid,))
    return jsonify({"ok": True})
