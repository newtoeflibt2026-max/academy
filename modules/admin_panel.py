"""
admin_panel.py v17.0 — لوحة الإمبراطورة: دورات + أسئلة امتحان + باقات + طلاب
"""
from flask import Blueprint, render_template, jsonify, request
from modules.models import query_db, execute_db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/")
def admin_dashboard():
    return render_template("admin.html")

# ═══ إحصائيات ═══
@admin_bp.route("/api/stats")
def api_stats():
    sc = query_db("SELECT COUNT(*) as c FROM students", one=True)
    pc = query_db("SELECT COUNT(*) as c FROM placement_results", one=True)
    qc = query_db("SELECT COUNT(*) as c FROM placement_questions WHERE is_active=1", one=True)
    kc = query_db("SELECT COUNT(*) as c FROM daily_skills WHERE is_active=1", one=True)
    bc = query_db("SELECT COUNT(*) as c FROM subscriptions WHERE status='active'", one=True)
    return jsonify({
        "students": sc["c"] if sc else 0,
        "placements": pc["c"] if pc else 0,
        "questions": qc["c"] if qc else 0,
        "skills": kc["c"] if kc else 0,
        "active_subs": bc["c"] if bc else 0
    })

# ═══ ① إدارة أسئلة امتحان المستوى ═══
@admin_bp.route("/api/placement/questions")
def api_placement_questions():
    rows = query_db("SELECT * FROM placement_questions ORDER BY id DESC")
    return jsonify([dict(r) for r in rows] if rows else [])

@admin_bp.route("/api/placement/questions/add", methods=["POST"])
def api_add_placement_question():
    d = request.get_json()
    required = ["question_text","option_a","option_b","option_c","option_d","correct_option"]
    for field in required:
        if not d.get(field):
            return jsonify({"error": f"{field} مطلوب"}), 400

    execute_db(
        """INSERT INTO placement_questions (question_text,option_a,option_b,option_c,option_d,correct_option,difficulty,skill_area,time_limit_seconds,points)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (d["question_text"], d["option_a"], d["option_b"], d["option_c"], d["option_d"],
         d["correct_option"].strip().upper(),
         d.get("difficulty","medium"), d.get("skill_area","general"),
         int(d.get("time_limit_seconds",60)), int(d.get("points",10))))

    return jsonify({"success": True, "message": "✅ تمت إضافة السؤال"})

@admin_bp.route("/api/placement/questions/delete/<int:qid>", methods=["DELETE"])
def api_delete_placement_question(qid):
    execute_db("DELETE FROM placement_questions WHERE id=?", (qid,))
    return jsonify({"success": True})

@admin_bp.route("/api/placement/questions/toggle/<int:qid>", methods=["POST"])
def api_toggle_placement_question(qid):
    row = query_db("SELECT is_active FROM placement_questions WHERE id=?", (qid,), one=True)
    if row:
        new_state = 0 if row["is_active"] else 1
        execute_db("UPDATE placement_questions SET is_active=? WHERE id=?", (new_state, qid))
    return jsonify({"success": True})

# ═══ ② نتائج الطلاب ═══
@admin_bp.route("/api/placement/results")
def api_placement_results():
    rows = query_db(
        """SELECT pr.*, s.first_name, s.username FROM placement_results pr
           LEFT JOIN students s ON pr.user_id = s.telegram_id
           ORDER BY pr.completed_at DESC LIMIT 100""")
    return jsonify([dict(r) for r in rows] if rows else [])

# ═══ ③ قائمة الطلاب ═══
@admin_bp.route("/api/students")
def api_students():
    rows = query_db(
        """SELECT s.*, sub.plan_name as subscription_plan, sub.status as subscription_status
           FROM students s
           LEFT JOIN subscriptions sub ON s.telegram_id = sub.user_id AND sub.status='active'
           ORDER BY s.xp DESC""")
    return jsonify([dict(r) for r in rows] if rows else [])

# ═══ ④ الباقات (للإدارة) ═══
@admin_bp.route("/api/billing/plans")
def api_billing_plans():
    rows = query_db("SELECT * FROM billing_plans ORDER BY sort_order")
    return jsonify([dict(r) for r in rows] if rows else [])

@admin_bp.route("/api/billing/plans/update", methods=["POST"])
def api_update_plan():
    d = request.get_json()
    pid = d.get("id")
    execute_db(
        "UPDATE billing_plans SET name=?,description=?,price_monthly=?,price_yearly=?,features=?,is_active=? WHERE id=?",
        (d.get("name"), d.get("description"), d.get("price_monthly"), d.get("price_yearly"),
         d.get("features"), d.get("is_active",1), pid))
    return jsonify({"success": True})
