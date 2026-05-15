"""
student_api.py v17.0 — API الطالب: مهارات، أسئلة، XP، متصدرين
"""
from flask import Blueprint, jsonify, request
from modules.models import query_db, execute_db

student_bp = Blueprint("student", __name__, url_prefix="/api")

@student_bp.route("/courses")
def api_courses():
    rows = query_db("SELECT * FROM courses WHERE is_active=1")
    return jsonify([dict(r) for r in rows] if rows else [])

@student_bp.route("/skills")
def api_skills():
    rows = query_db("SELECT * FROM daily_skills WHERE is_active=1 ORDER BY sort_order, id")
    return jsonify([dict(r) for r in rows] if rows else [])

@student_bp.route("/question/next", methods=["POST"])
def api_next_question():
    d = request.get_json()
    skill_type = d.get("skill_type")
    student_id = d.get("student_id")
    last_qid = d.get("last_question_id", 0)
    if not skill_type: return jsonify({"error":"نوع المهارة مطلوب"}),400
    q = query_db("SELECT * FROM questions WHERE skill_type=? AND is_active=1 AND id>? ORDER BY id LIMIT 1",(skill_type,last_qid),one=True)
    if not q: q = query_db("SELECT * FROM questions WHERE skill_type=? AND is_active=1 ORDER BY id LIMIT 1",(skill_type,),one=True)
    if not q: return jsonify({"error":"لا توجد أسئلة"}),404
    if student_id: execute_db("UPDATE students SET last_active=CURRENT_TIMESTAMP WHERE telegram_id=?",(student_id,))
    return jsonify({"question":dict(q)})

@student_bp.route("/student/xp", methods=["POST"])
def api_update_xp():
    d = request.get_json()
    sid = d.get("student_id"); xp = d.get("xp_gain",10)
    execute_db("UPDATE students SET xp=COALESCE(xp,0)+?, last_active=CURRENT_TIMESTAMP WHERE telegram_id=?",(xp,sid))
    row = query_db("SELECT xp,level FROM students WHERE telegram_id=?",(sid,),one=True)
    return jsonify({"xp":row["xp"],"level":row["level"]}) if row else jsonify({"error":"غير موجود"}),404

@student_bp.route("/leaderboard")
def api_leaderboard():
    rows = query_db("SELECT telegram_id,first_name,username,xp,level FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT 10")
    return jsonify([dict(r) for r in rows] if rows else [])

@student_bp.route("/error_bank/<int:user_id>")
def api_error_bank(user_id):
    rows = query_db("SELECT e.*,q.question_text FROM error_bank e LEFT JOIN questions q ON e.question_id=q.id WHERE e.user_id=?",(user_id,))
    return jsonify([dict(r) for r in rows] if rows else [])

@student_bp.route("/error_bank/add", methods=["POST"])
def api_error_add():
    d=request.get_json()
    execute_db("INSERT OR IGNORE INTO error_bank (user_id,question_id,skill_type) VALUES (?,?,?)",(d.get("user_id"),d.get("question_id"),d.get("skill_type")))
    return jsonify({"success":True})

@student_bp.route("/library")
def api_library():
    rows = query_db("SELECT * FROM library_items WHERE is_active=1 ORDER BY sort_order, id")
    return jsonify([dict(r) for r in rows] if rows else [])

@student_bp.route("/profile/<int:user_id>")
def api_profile(user_id):
    row = query_db("SELECT * FROM students WHERE telegram_id=?",(user_id,),one=True)
    if not row: return jsonify({"error":"غير موجود"}),404
    pr = query_db("SELECT * FROM placement_results WHERE user_id=? ORDER BY id DESC LIMIT 1",(user_id,),one=True)
    sub = query_db("SELECT * FROM subscriptions WHERE user_id=? AND status='active' ORDER BY id DESC LIMIT 1",(user_id,),one=True)
    return jsonify({
        "student": dict(row),
        "placement": dict(pr) if pr else None,
        "subscription": dict(sub) if sub else None
    })
