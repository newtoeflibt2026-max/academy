"""
app.py — الملف الرئيسي: استيراد + تسجيل Blueprints + تشغيل
لا يحوي منطق أعمال — فقط تجميع الوحدات.
"""
import os, sys

# إضافة المجلد الحالي للمسار
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, redirect, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime

# ═══ استيراد الوحدات ═══
from modules.models import init_db
from modules.admin_panel import admin_bp
from modules.student_api import student_bp

# ═══ إنشاء التطبيق ═══
app = Flask(__name__)
CORS(app)

# ═══ تسجيل Blueprints ═══
app.register_blueprint(admin_bp)    # /admin/*
app.register_blueprint(student_bp)  # /api/*

# ═══ الصفحات الرئيسية ═══
@app.route("/")
def home():
    return redirect("/dashboard")

@app.route("/dashboard")
@app.route("/dashboard/<int:student_id>")
def dashboard(student_id=None):
    from modules.models import query_db

    empty = {"student": {"first_name": "طالب", "xp": 0, "level": 0, "streak": 0, "id": 0},
             "library": [], "skills": [], "leaderboard": [], "progress": {}}

    if student_id is None:
        return render_template("dashboard.html", **empty)

    try:
        s = query_db("SELECT * FROM students WHERE telegram_id=?", (student_id,), one=True)
        if not s:
            return render_template("dashboard.html", **empty), 200

        student = dict(s)
        student.setdefault("first_name", student.get("username") or "طالب")
        student.setdefault("xp", 0)
        student.setdefault("level", 0)
        student.setdefault("streak", 0)

        library = query_db("SELECT * FROM library_items WHERE is_active=1 ORDER BY sort_order, id") or []
        skills = query_db("SELECT * FROM daily_skills WHERE is_active=1 ORDER BY sort_order, id") or []
        lb = query_db("SELECT * FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT 5") or []

        return render_template("dashboard.html",
            student=student,
            library=[dict(r) for r in library],
            skills=[dict(r) for r in skills],
            leaderboard=[dict(r) for r in lb])
    except Exception as e:
        print(f"❌ Dashboard Error: {e}")
        return render_template("dashboard.html", **empty), 200

@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "app": "يامن أكاديمي — Modular TOEFL Platform",
        "modules": ["models", "audio_logic", "ai_engine", "admin_panel", "student_api"],
        "timestamp": str(datetime.now())
    })

# ═══ Static ═══
@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

# ═══ طباعة المسارات المسجّلة ═══
with app.app_context():
    print("\n" + "=" * 60)
    print("🛣️  يامن أكاديمي — Modular Routes:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if not rule.rule.startswith("/static"):
            methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
            print(f"   {methods:8s} → {rule.rule}")
    print("=" * 60 + "\n")

# ═══ Entry Point ═══
if __name__ == "__main__":
    from config import WEBAPP_PORT, DATABASE_PATH

    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    init_db()

    print(f"\n🦅 يامن أكاديمي — Modular Architecture")
    print(f"   📁 5 Modules loaded")
    print(f"   🌐 Port: {WEBAPP_PORT}")
    print(f"   🔗 /dashboard  /admin  /health\n")

    app.run(host="0.0.0.0", port=WEBAPP_PORT, debug=False)
