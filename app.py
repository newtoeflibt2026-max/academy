from flask import Flask, render_template, jsonify, send_from_directory, request, redirect, url_for
from flask_cors import CORS
import os, sys
from config import WEBAPP_PORT, UPLOAD_FOLDER

# Ensure data & upload folders
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

# ---------- Import & register modules ----------
from modules.models import init_db, query_db
init_db()

from modules.placement_middleware import placement_mw, check_placement
from modules.student_api import student_bp
from modules.admin_panel import admin_bp
from modules.billing import billing_bp

app.register_blueprint(placement_mw)
app.register_blueprint(student_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(billing_bp)

# ---------- BEFORE REQUEST: Placement gate ----------
EXEMPT_PATHS = [
    "/health", "/placement", "/api/placement", "/static",
    "/admin", "/api/admin", "/dashboard"
]

@app.before_request
def placement_gate():
    # Skip if path is exempt or if it's an API call not related to learning content
    path = request.path
    if any(path.startswith(p) for p in EXEMPT_PATHS):
        return None

    # Check if student_id is in query params
    student_id = request.args.get("student_id") or request.args.get("user_id")
    if not student_id and request.method == "GET":
        return None

    if student_id and not check_placement(int(student_id)):
        # If trying to access API content routes without placement
        if path.startswith("/api/") and path not in ["/api/placement/questions", "/api/placement/submit", "/api/placement/status"]:
            return jsonify({"error": "Placement test required", "redirect": f"/placement?user_id={student_id}"}), 403

    return None

# ---------- BASIC ROUTES ----------
@app.route("/")
def index():
    return redirect("/dashboard")

@app.route("/health")
def health():
    from config import ADMIN_IDS
    routes = [r.rule for r in app.url_map.iter_rules() if not r.rule.startswith("/static")]
    return jsonify({
        "status": "healthy",
        "version": "18.0.0",
        "admin_ids": ADMIN_IDS,
        "routes": sorted(routes)
    })

@app.route("/dashboard")
@app.route("/dashboard/<int:student_id>")
def dashboard(student_id=None):
    if student_id is None:
        student_id = request.args.get("user_id", 5602495831)
    student = query_db("SELECT * FROM students WHERE telegram_id=?", (student_id,), one=True)
    courses = query_db("SELECT * FROM courses WHERE is_active=1")
    skills = query_db("SELECT * FROM daily_skills WHERE is_active=1 ORDER BY sort_order")
    leaderboard = query_db("SELECT telegram_id, name, xp, level FROM students ORDER BY xp DESC LIMIT 5")
    placement = query_db("SELECT * FROM placement_results WHERE student_id=? ORDER BY id DESC LIMIT 1", (student_id,), one=True)
    error_count = query_db("SELECT COUNT(*) as c FROM error_bank WHERE student_id=? AND is_corrected=0", (student_id,), one=True)
    return render_template("dashboard.html",
        student=student, courses=courses, skills=skills,
        leaderboard=leaderboard, placement=placement,
        error_count=error_count["c"] if error_count else 0,
        student_id=student_id
    )

@app.route("/placement")
def placement_page():
    user_id = request.args.get("user_id", 0)
    return render_template("placement.html", user_id=user_id)

@app.route("/admin")
def admin_page():
    return render_template("admin.html")

# ---------- STATIC FILES ----------
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

# ---------- APP PRINT & RUN ----------
if __name__ == "__main__":
    print("[APP] Registered Routes:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        print(f"  {rule.rule}  [{','.join(rule.methods - {'HEAD','OPTIONS'})}]")
    app.run(host="0.0.0.0", port=WEBAPP_PORT, debug=False)
