import os, logging, json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from database import get_db_connection, init_db, DB_PATH
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

# ===== DB helper - always close connection =====
def db_query(query_func):
    conn = None
    try:
        conn = get_db_connection()
        result = query_func(conn)
        return result
    except sqlite3.OperationalError as e:
        logger.error(f"DB Lock: {e}")
        return jsonify({"error": "database_locked"}), 503
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            try: conn.close()
            except: pass

# ===== Routes =====
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_file(filename):
    try:
        return send_from_directory('.', filename)
    except:
        return jsonify({"error": "not_found"}), 404

@app.route('/api/health')
def health():
    db_exists = os.path.exists(DB_PATH)
    return jsonify({"status": "ok", "app": "yamen-academy", "database": db_exists})

@app.route('/api/courses')
def courses():
    def q(conn):
        rows = conn.execute("SELECT * FROM courses WHERE is_active=1 ORDER BY id").fetchall()
        return jsonify([dict(r) for r in rows])
    return db_query(q)

@app.route('/api/courses', methods=['POST'])
def create_course():
    data = request.get_json(silent=True) or {}
    def q(conn):
        conn.execute(
            "INSERT INTO courses (title, description, level) VALUES (?, ?, ?)",
            (data.get('title', 'دورة جديدة'), data.get('description', ''), data.get('level', 'A1'))
        )
        return jsonify({"status": "created"}), 201
    return db_query(q)

@app.route('/api/lessons/<int:course_id>')
def lessons(course_id):
    def q(conn):
        rows = conn.execute("SELECT * FROM lessons WHERE course_id=? ORDER BY order_index", (course_id,)).fetchall()
        return jsonify([dict(r) for r in rows])
    return db_query(q)

@app.route('/api/leaderboard')
def leaderboard():
    def q(conn):
        rows = conn.execute("SELECT first_name, username, xp, streak FROM students WHERE is_banned=0 ORDER BY xp DESC LIMIT 20").fetchall()
        return jsonify([dict(r) for r in rows])
    return db_query(q)

@app.route('/api/placement/questions')
def placement():
    def q(conn):
        rows = conn.execute("SELECT * FROM questions LIMIT 20").fetchall()
        return jsonify([dict(r) for r in rows])
    return db_query(q)

@app.route('/api/spelling')
def spelling():
    def q(conn):
        rows = conn.execute("SELECT * FROM spelling_words ORDER BY RANDOM() LIMIT 10").fetchall()
        return jsonify([dict(r) for r in rows])
    return db_query(q)

@app.route('/api/daily-challenge')
def daily():
    def q(conn):
        row = conn.execute("SELECT * FROM daily_challenges WHERE challenge_date=date('now','localtime')").fetchone()
        return jsonify(dict(row) if row else {"challenge": None})
    return db_query(q)

@app.route('/api/progress', methods=['POST'])
def save_progress():
    data = request.get_json(silent=True) or {}
    def q(conn):
        conn.execute(
            "INSERT OR REPLACE INTO progress (student_id, lesson_id, score, completed, completed_at) VALUES (?,?,?,?,datetime('now','localtime'))",
            (data.get('student_id'), data.get('lesson_id'), data.get('score', 0), data.get('completed', 0))
        )
        return jsonify({"status": "saved"})
    return db_query(q)

@app.route('/api/evaluate/writing', methods=['POST'])
def eval_writing():
    return jsonify({"status": "ok", "score": 85, "feedback": "Good writing!"})

@app.route('/api/evaluate/speaking', methods=['POST'])
def eval_speaking():
    return jsonify({"status": "ok", "score": 80, "feedback": "Good speaking!"})

@app.route('/api/admin/stats')
def admin_stats():
    def q(conn):
        s = conn.execute("SELECT COUNT(*) FROM students WHERE is_banned=0").fetchone()[0]
        c = conn.execute("SELECT COUNT(*) FROM courses WHERE is_active=1").fetchone()[0]
        return jsonify({"students": s, "courses": c})
    return db_query(q)

@app.route('/api/admin/students')
def admin_students():
    def q(conn):
        rows = conn.execute("SELECT * FROM students ORDER BY xp DESC").fetchall()
        return jsonify([dict(r) for r in rows])
    return db_query(q)

if __name__ == '__main__':
    init_db()
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Yamen Academy WebApp starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
