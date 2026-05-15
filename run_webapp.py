import os
import sqlite3
import json
from flask import Flask, render_template, jsonify, request, send_from_directory, redirect, url_for
from flask_cors import CORS
from datetime import datetime

# ── التهيئة ──────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "data", "yamen_academy.db")
PORT = int(os.environ.get("PORT", 5050))

app = Flask(__name__)
CORS(app)

# ── دوال قاعدة البيانات ──────────────────────────────────────
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
        print(f"⚠️ DB Error: {e}")
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
        print(f"⚠️ DB Exec Error: {e}")
        return False
    finally:
        conn.close()

# ==============================================================
#  ✅ ROUTE 1: لوحة التحكم الرئيسية (ترحيبية)
# ==============================================================
@app.route("/")
def home():
    return redirect("/dashboard")

# ==============================================================
#  ✅ ROUTE 2: Dashboard الطالب
# ==============================================================
@app.route("/dashboard")
@app.route("/dashboard/<int:student_id>")
def dashboard(student_id=None):
    if student_id is None:
        return render_template("dashboard.html",
            student={"first_name": "طالب", "xp": 0, "level": 0, "streak": 0, "id": 0},
            courses=[], error_count=0, leaderboard=[])

    # جلب بيانات الطالب
    s = query_db(
        "SELECT telegram_id, username, first_name, xp, level, is_active, last_active, streak "
        "FROM students WHERE telegram_id = ?", (student_id,), one=True)

    if not s:
        return render_template("dashboard.html",
            student={"first_name": "غير معروف", "xp": 0, "level": 0, "streak": 0, "id": 0},
            courses=[], error_count=0, leaderboard=[]), 200

    student = {
        "id": s["telegram_id"],
        "username": s["username"] or "طالب",
        "first_name": s["first_name"] or s["username"] or "طالب",
        "xp": s["xp"] or 0,
        "level": s["level"] or 0,
        "is_active": bool(s["is_active"]),
        "last_active": s["last_active"],
        "streak": s["streak"] or 0
    }

    # الكورسات النشطة
    courses_data = query_db(
        "SELECT id, title, skill_type, time_limit, target_score, is_active "
        "FROM courses WHERE is_active = 1")
    courses = [dict(r) for r in courses_data] if courses_data else []

    # بنك الأخطاء
    err = query_db("SELECT COUNT(*) as cnt FROM error_bank WHERE user_id = ?", (student_id,), one=True)
    error_count = err["cnt"] if err else 0

    # المتصدرين
    lb = query_db(
        "SELECT telegram_id, first_name, username, xp, level "
        "FROM students WHERE is_active = 1 ORDER BY xp DESC LIMIT 5")
    leaderboard = [dict(r) for r in lb] if lb else []

    return render_template("dashboard.html",
        student=student, courses=courses,
        error_count=error_count, leaderboard=leaderboard)

# ==============================================================
#  ✅ ROUTE 3: Admin Dashboard
# ==============================================================
@app.route("/admin")
def admin_panel():
    return render_template("admin.html")

# ==============================================================
#  📡 API Routes
# ==============================================================
@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "timestamp": str(datetime.now())})

@app.route("/api/courses")
def api_courses():
    rows = query_db("SELECT * FROM courses WHERE is_active = 1")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/admin/stats")
def admin_stats():
    sc = query_db("SELECT COUNT(*) as c FROM students", one=True)
    cc = query_db("SELECT COUNT(*) as c FROM courses", one=True)
    return jsonify({
        "students": sc["c"] if sc else 0,
        "courses": cc["c"] if cc else 0
    })

@app.route("/api/admin/students")
def admin_students():
    rows = query_db("SELECT * FROM students ORDER BY xp DESC")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/leaderboard")
def api_leaderboard():
    rows = query_db(
        "SELECT telegram_id, first_name, username, xp, level "
        "FROM students WHERE is_active = 1 ORDER BY xp DESC LIMIT 10")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/error_bank/<int:user_id>")
def api_error_bank(user_id):
    rows = query_db("SELECT * FROM error_bank WHERE user_id = ?", (user_id,))
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/error_bank/correct", methods=["POST"])
def api_error_correct():
    data = request.get_json()
    qid = data.get("question_id")
    uid = data.get("user_id")
    if not qid or not uid:
        return jsonify({"error": "Missing"}), 400
    execute_db(
        "UPDATE error_bank SET correct_count = correct_count + 1 WHERE question_id = ? AND user_id = ?",
        (qid, uid))
    row = query_db(
        "SELECT correct_count FROM error_bank WHERE question_id = ? AND user_id = ?",
        (qid, uid), one=True)
    if row and row["correct_count"] >= 2:
        execute_db("DELETE FROM error_bank WHERE question_id = ? AND user_id = ?", (qid, uid))
    return jsonify({"success": True})

# ── Static files ─────────────────────────────────────────────
@app.route("/style.css")
def serve_css():
    return send_from_directory("static", "style.css")

@app.route("/app.js")
def serve_js():
    return send_from_directory("static", "app.js")

@app.route("/manifest.json")
def serve_manifest():
    return send_from_directory("static", "manifest.json")

# ── تشغيل ────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    app.run(host="0.0.0.0", port=PORT, debug=False)
