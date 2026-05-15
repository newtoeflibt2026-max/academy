import os
import sqlite3
import json
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime

# ─── تهيئة Flask ──────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "data", "yamen_academy.db")
PORT = int(os.environ.get("PORT", 5050))

app = Flask(__name__)
CORS(app)

# ─── دوال مساعدة لقاعدة البيانات ──────────────────────────
def get_db():
    """يفتح اتصال SQLite آمن لكل طلب"""
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
        print(f"⚠️ DB Query Error: {e}")
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
        print(f"⚠️ DB Execute Error: {e}")
        return False
    finally:
        conn.close()

# ─── صفحة Dashboard الطالب ────────────────────────────────
@app.route("/dashboard")
@app.route("/dashboard/<int:student_id>")
def dashboard(student_id=None):
    """تعرض لوحة التحكم التفاعلية للطالب ببيانات حية"""

    # --- إفتراضي: لوحة ترحيبية (بدون ID) ---
    if student_id is None:
        return render_template("dashboard.html",
            student={"first_name": "طالب", "xp": 0, "level": 0, "streak": 0},
            courses=[],
            error_count=0,
            leaderboard=[]
        )

    # --- جلب بيانات الطالب ────────────────────────────────
    student_row = query_db(
        "SELECT telegram_id, username, first_name, xp, level, is_active, last_active, streak "
        "FROM students WHERE telegram_id = ?",
        (student_id,), one=True
    )
    if not student_row:
        return render_template("dashboard.html",
            student={"first_name": "غير معروف", "xp": 0, "level": 0, "streak": 0},
            courses=[],
            error_count=0,
            leaderboard=[]
        ), 200

    student = {
        "id": student_row["telegram_id"],
        "username": student_row["username"] or "طالب",
        "first_name": student_row["first_name"] or student_row["username"] or "طالب",
        "xp": student_row["xp"] or 0,
        "level": student_row["level"] or 0,
        "is_active": bool(student_row["is_active"]),
        "last_active": student_row["last_active"],
        "streak": student_row["streak"] or 0
    }

    # --- الكورسات المتاحة والنشطة ─────────────────────────
    courses_data = query_db(
        "SELECT id, title, skill_type, time_limit, target_score, is_active "
        "FROM courses WHERE is_active = 1"
    ) or []

    # --- عدد الأخطاء في بنك الأخطاء ────────────────────────
    error_row = query_db(
        "SELECT COUNT(*) as cnt FROM error_bank WHERE user_id = ?",
        (student_id,), one=True
    )
    error_count = error_row["cnt"] if error_row else 0

    # --- لوحة المتصدرين (أفضل 5) ──────────────────────────
    lb_rows = query_db(
        "SELECT telegram_id, first_name, username, xp, level "
        "FROM students WHERE is_active = 1 "
        "ORDER BY xp DESC LIMIT 5"
    ) or []

    leaderboard = []
    for r in lb_rows:
        leaderboard.append({
            "id": r["telegram_id"],
            "name": r["first_name"] or r["username"] or "طالب",
            "xp": r["xp"] or 0,
            "level": r["level"] or 0
        })

    courses = [dict(r) for r in courses_data]

    return render_template("dashboard.html",
        student=student,
        courses=courses,
        error_count=error_count,
        leaderboard=leaderboard
    )

# ============================================================
#  مسارات API الحالية (موجودة مسبقاً - مختصرة هنا)
# ============================================================

@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "timestamp": str(datetime.now())})

@app.route("/api/courses")
def api_courses():
    rows = query_db("SELECT * FROM courses WHERE is_active = 1")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/admin/stats")
def admin_stats():
    students_count = query_db("SELECT COUNT(*) as c FROM students", one=True)
    courses_count = query_db("SELECT COUNT(*) as c FROM courses", one=True)
    return jsonify({
        "students": students_count["c"] if students_count else 0,
        "courses": courses_count["c"] if courses_count else 0
    })

@app.route("/api/admin/students")
def admin_students():
    rows = query_db("SELECT * FROM students ORDER BY xp DESC")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/leaderboard")
def api_leaderboard():
    rows = query_db(
        "SELECT telegram_id, first_name, username, xp, level "
        "FROM students WHERE is_active = 1 ORDER BY xp DESC LIMIT 10"
    )
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
        return jsonify({"error": "Missing fields"}), 400
    execute_db(
        "UPDATE error_bank SET correct_count = correct_count + 1 WHERE question_id = ? AND user_id = ?",
        (qid, uid)
    )
    row = query_db(
        "SELECT correct_count FROM error_bank WHERE question_id = ? AND user_id = ?",
        (qid, uid), one=True
    )
    if row and row["correct_count"] >= 2:
        execute_db("DELETE FROM error_bank WHERE question_id = ? AND user_id = ?", (qid, uid))
    return jsonify({"success": True})

# ─── الملفات الثابتة ─────────────────────────────────────
@app.route("/style.css")
def serve_style():
    return send_from_directory("static", "style.css")

@app.route("/app.js")
def serve_app_js():
    return send_from_directory("static", "app.js")

@app.route("/manifest.json")
def serve_manifest():
    return send_from_directory("static", "manifest.json")

# ─── تشغيل التطبيق ─────────────────────────────────────────
if __name__ == "__main__":
    # تأكد من وجود مجلد data + قاعدة بيانات
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    app.run(host="0.0.0.0", port=PORT, debug=False)

