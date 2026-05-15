from flask import Flask, render_template, jsonify, send_from_directory, request, redirect
from flask_cors import CORS
import os
from config import WEBAPP_PORT, UPLOAD_FOLDER

os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 150 * 1024 * 1024

# ===== Init DB =====
from modules.models import init_db, query_db
init_db()

# ===== Register Blueprints =====
from modules.placement_test import placement_bp
from modules.student_api import student_bp
from modules.admin_panel import admin_bp
from modules.billing import billing_bp

app.register_blueprint(placement_bp)
app.register_blueprint(student_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(billing_bp)

# ===== Middleware: Placement Gate =====
EXEMPT_PATHS = ["/health", "/placement", "/api/placement", "/static", "/admin", "/api/admin", "/dashboard"]

@app.before_request
def placement_gate():
    path = request.path
    if any(path.startswith(p) for p in EXEMPT_PATHS):
        return None
    student_id = request.args.get("student_id") or request.args.get("user_id")
    if not student_id:
        return None
    try:
        sid = int(student_id)
    except:
        return None
    row = query_db("SELECT placement_done FROM students WHERE telegram_id=?", (sid,), one=True)
    if not row or not row["placement_done"]:
        locked_apis = ["/api/skills", "/api/question", "/api/student/xp", "/api/ai/", "/api/error_bank"]
        if any(path.startswith(p) for p in locked_apis):
            return jsonify({
                "error": "Placement test required",
                "redirect": f"/placement?user_id={sid}",
                "message": "يجب إكمال اختبار تحديد المستوى أولاً"
            }), 403
    return None

# ===== ROUTES =====
@app.route("/")
def index():
    return redirect("/dashboard")

@app.route("/health")
def health():
    from config import ADMIN_IDS, JSON_PLACEMENT
    import json as j
    rules = [r.rule for r in app.url_map.iter_rules() if not r.rule.startswith("/static")]
    qcount = 0
    try:
        with open(JSON_PLACEMENT, "r") as f:
            qcount = len(j.load(f))
    except:
        pass
    return jsonify({
        "status": "healthy",
        "version": "19.0.0",
        "admin_ids": ADMIN_IDS,
        "placement_questions_count": qcount,
        "routes": sorted(rules)[:30]
    })

@app.route("/dashboard")
@app.route("/dashboard/<int:student_id>")
def dashboard(student_id=None):
    if student_id is None:
        student_id = request.args.get("user_id", 5602495831)
    student = query_db("SELECT * FROM students WHERE telegram_id=?", (student_id,), one=True)
    courses = query_db("SELECT * FROM courses WHERE is_active=1")
    skills = query_db("SELECT * FROM daily_skills WHERE is_active=1 ORDER BY sort_order")
    leaderboard = query_db(
        "SELECT telegram_id, name, xp, level FROM students WHERE placement_done=1 ORDER BY xp DESC LIMIT 5"
    )
    placement = query_db(
        "SELECT * FROM placement_results WHERE student_id=? ORDER BY id DESC LIMIT 1",
        (student_id,), one=True
    )
    error_count = query_db(
        "SELECT COUNT(*) as c FROM error_bank WHERE student_id=? AND is_corrected=0",
        (student_id,), one=True
    )
    library_items = query_db("SELECT * FROM library_items WHERE is_active=1 LIMIT 6")
    return render_template("dashboard.html",
        student=student, courses=courses, skills=skills,
        leaderboard=leaderboard, placement=placement,
        error_count=error_count["c"] if error_count else 0,
        student_id=student_id, library_items=library_items
    )

@app.route("/placement")
def placement_page():
    user_id = request.args.get("user_id", 0)
    return render_template("placement.html", user_id=user_id)

@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

# ===== PRINT ROUTES =====
print("\n[APP] Registered Routes:")
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    methods = ",".join(rule.methods - {"HEAD","OPTIONS"})
    print(f"  {rule.rule:50s}  [{methods}]")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=WEBAPP_PORT, debug=False)
