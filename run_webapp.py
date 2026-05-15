import os
import sqlite3
import json
from flask import Flask, render_template, jsonify, request, send_from_directory, redirect
from flask_cors import CORS
from datetime import datetime

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH  = os.path.join(BASE_DIR, "data", "yamen_academy.db")
PORT           = int(os.environ.get("PORT", 5050))

app = Flask(__name__)
CORS(app)

# ── DB Helpers ───────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def query_db(query, args=(), one=False):
    conn = get_db()
    try:
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        conn.commit()
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(f"DB Error: {e}")
        return None
    finally:
        conn.close()

def execute_db(query, args=()):
    conn = get_db()
    try:
        conn.execute(query, args)
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Exec Error: {e}")
        return False
    finally:
        conn.close()

# ════════════════════════════════════════════════════════════
#  Routes
# ════════════════════════════════════════════════════════════
@app.route("/")
def home():
    return redirect("/dashboard")

@app.route("/dashboard")
@app.route("/dashboard/<int:student_id>")
def dashboard(student_id=None):
    empty = {"student": {"first_name":"طالب","xp":0,"level":0,"streak":0,"id":0},
             "courses":[], "error_count":0, "leaderboard":[]}

    if student_id is None:
        return render_template("dashboard.html", **empty)

    s = query_db("SELECT * FROM students WHERE telegram_id = ?", (student_id,), one=True)
    if not s:
        return render_template("dashboard.html", **empty), 200

    student = dict(s)
    student.setdefault("first_name", student.get("username") or "طالب")
    student.setdefault("xp", 0)
    student.setdefault("level", 0)
    student.setdefault("streak", 0)

    courses  = query_db("SELECT * FROM courses WHERE is_active=1") or []
    err      = query_db("SELECT COUNT(*) as cnt FROM error_bank WHERE user_id=?", (student_id,), one=True)
    lb       = query_db("SELECT * FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT 5") or []

    return render_template("dashboard.html",
        student=student,
        courses=[dict(r) for r in courses],
        error_count=err["cnt"] if err else 0,
        leaderboard=[dict(r) for r in lb])

@app.route("/admin")
def admin_panel():
    return render_template("admin.html")

# ── API ────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({"status":"healthy","timestamp":str(datetime.now())})

@app.route("/api/courses")
def api_courses():
    rows = query_db("SELECT * FROM courses WHERE is_active=1")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/leaderboard")
def api_leaderboard():
    rows = query_db("SELECT telegram_id,first_name,username,xp,level FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT 10")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/admin/stats")
def admin_stats():
    sc=query_db("SELECT COUNT(*) as c FROM students", one=True)
    cc=query_db("SELECT COUNT(*) as c FROM courses", one=True)
    return jsonify({"students":sc["c"] if sc else 0,"courses":cc["c"] if cc else 0})

@app.route("/api/admin/students")
def admin_students():
    rows = query_db("SELECT * FROM students ORDER BY xp DESC")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/style.css")
def serve_css():
    return send_from_directory("static","style.css")

@app.route("/app.js")
def serve_js():
    return send_from_directory("static","app.js")

if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_DIR,"data"), exist_ok=True)
    app.run(host="0.0.0.0", port=PORT, debug=False)
