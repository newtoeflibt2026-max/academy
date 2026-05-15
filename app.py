"""
app.py v17.0 — الملف الرئيسي: استيراد + تسجيل Blueprints + تشغيل
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, redirect, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime

from modules.models import init_db, query_db
from modules.admin_panel import admin_bp
from modules.student_api import student_bp
from modules.placement_test import placement_bp
from modules.billing import billing_bp

app = Flask(__name__)
CORS(app)

# تسجيل Blueprints
app.register_blueprint(admin_bp)
app.register_blueprint(student_bp)
app.register_blueprint(placement_bp)
app.register_blueprint(billing_bp)

@app.route("/")
def home(): return redirect("/dashboard")

@app.route("/dashboard")
@app.route("/dashboard/<int:student_id>")
def dashboard(student_id=None):
    empty = {"student":{"first_name":"طالب","xp":0,"level":0,"streak":0,"id":0,"placement_done":False},"library":[],"skills":[],"leaderboard":[],"courses":[],"subscription":None}
    if student_id is None: return render_template("dashboard.html", **empty)
    try:
        s = query_db("SELECT * FROM students WHERE telegram_id=?",(student_id,),one=True)
        if not s: return render_template("dashboard.html", **empty), 200
        student = dict(s)
        student.setdefault("first_name", student.get("username") or "طالب");student.setdefault("xp",0);student.setdefault("level",0);student.setdefault("streak",0)
        library = query_db("SELECT * FROM library_items WHERE is_active=1 ORDER BY sort_order, id") or []
        skills = query_db("SELECT * FROM daily_skills WHERE is_active=1 ORDER BY sort_order, id") or []
        lb = query_db("SELECT * FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT 5") or []
        courses = query_db("SELECT * FROM courses WHERE is_active=1") or []
        sub = query_db("SELECT * FROM subscriptions WHERE user_id=? AND status='active' ORDER BY id DESC LIMIT 1",(student_id,),one=True)
        return render_template("dashboard.html",student=student,library=[dict(r) for r in library],skills=[dict(r) for r in skills],leaderboard=[dict(r) for r in lb],courses=[dict(r) for r in courses],subscription=dict(sub) if sub else None)
    except Exception as e:
        print(f"Dashboard Error: {e}")
        return render_template("dashboard.html", **empty), 200

@app.route("/health")
def health():
    return jsonify({"status":"online","app":"يامن أكاديمي v17.0","modules":["models","placement_test","billing","admin_panel","student_api"],"timestamp":str(datetime.now())})

@app.route("/static/<path:filename>")
def serve_static(filename): return send_from_directory("static", filename)

with app.app_context():
    print("\n"+"="*60);print("🛣️  يامن أكاديمي v17.0 Routes:")
    for rule in sorted(app.url_map.iter_rules(),key=lambda r:r.rule):
        if not rule.rule.startswith('/static'):print(f"   {','.join(sorted(rule.methods-{'HEAD','OPTIONS'})):8s} → {rule.rule}")
    print("="*60+"\n")

if __name__ == "__main__":
    from config import WEBAPP_PORT, DATABASE_PATH
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    init_db()
    print(f"\n🦅 يامن أكاديمي v17.0 | Port: {WEBAPP_PORT}\n")
    app.run(host="0.0.0.0", port=WEBAPP_PORT, debug=False)
