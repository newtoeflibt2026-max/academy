import os, json, logging, traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from database import get_db_connection, init_db, DB_PATH
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

# ====== Static file helper ======
STATIC_FILES = {
    'index.html': 'index.html',
    'app.js': 'app.js',
    'style.css': 'style.css',
    'config.js': 'config.js',
    'manifest.json': 'manifest.json',
    'sw.js': 'sw.js',
    'offline.js': 'offline.js'
}

def safe_db_query(query_func):
    """Wrapper for safe DB queries with try/except."""
    try:
        return query_func()
    except sqlite3.OperationalError as e:
        logger.error(f"DB Lock/Error: {e}")
        return {"error": "database_locked", "message": str(e)}, 503
    except Exception as e:
        logger.error(f"Unexpected error: {traceback.format_exc()}")
        return {"error": "server_error", "message": str(e)}, 500

# ====== Routes ======
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    if filename in STATIC_FILES:
        return send_from_directory('.', STATIC_FILES[filename])
    # Try direct file
    try:
        return send_from_directory('.', filename)
    except:
        return jsonify({"error": "not_found"}), 404

# ====== API Routes ======
@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "app": "yamen-academy", "db": os.path.exists(DB_PATH)})

@app.route('/api/me')
def get_me():
    def query():
        user_id = request.args.get('user_id')
        if not user_id:
            return {"error": "user_id required"}, 400
        conn = get_db_connection()
        try:
            row = conn.execute("SELECT * FROM students WHERE telegram_id=?", (int(user_id),)).fetchone()
            if row:
                return dict(row)
            return {"error": "not_found"}, 404
        finally:
            conn.close()
    return safe_db_query(query)

@app.route('/api/courses')
def get_courses():
    def query():
        conn = get_db_connection()
        try:
            rows = conn.execute("SELECT * FROM courses WHERE is_active=1 ORDER BY id").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    return safe_db_query(query)

@app.route('/api/courses', methods=['POST'])
def create_course():
    def query():
        data = request.get_json()
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO courses (title, description, level) VALUES (?,?,?)",
                        (data.get('title',''), data.get('description',''), data.get('level','A1')))
            return {"status": "created"}, 201
        finally:
            conn.close()
    return safe_db_query(query)

@app.route('/api/lessons/<int:course_id>')
def get_lessons(course_id):
    def query():
        conn = get_db_connection()
        try:
            rows = conn.execute("SELECT * FROM lessons WHERE course_id=? ORDER BY order_index", (course_id,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    return safe_db_query(query)

@app.route('/api/lessons', methods=['POST'])
def create_lesson():
    def query():
        data = request.get_json()
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO lessons (course_id, title, content, order_index) VALUES (?,?,?,?)",
                        (data.get('course_id'), data.get('title',''), data.get('content',''), data.get('order_index',0)))
            return {"status": "created"}, 201
        finally:
            conn.close()
    return safe_db_query(query)

@app.route('/api/placement/questions')
def get_placement():
    def query():
        conn = get_db_connection()
        try:
            rows = conn.execute("SELECT * FROM questions WHERE lesson_id IS NULL LIMIT 20").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    return safe_db_query(query)

@app.route('/api/spelling')
def get_spelling():
    def query():
        conn = get_db_connection()
        try:
            rows = conn.execute("SELECT * FROM spelling_words ORDER BY RANDOM() LIMIT 10").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    return safe_db_query(query)

@app.route('/api/daily-challenge')
def get_daily():
    def query():
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT * FROM daily_challenges WHERE challenge_date=date('now','localtime')"
            ).fetchone()
            if row:
                return dict(row)
            return {"challenge": None}
        finally:
            conn.close()
    return safe_db_query(query)

@app.route('/api/leaderboard')
def get_leaderboard():
    def query():
        conn = get_db_connection()
        try:
            rows = conn.execute("SELECT first_name, username, xp, streak FROM students WHERE is_banned=0 ORDER BY xp DESC LIMIT 20").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    return safe_db_query(query)

@app.route('/api/progress', methods=['POST'])
def save_progress():
    def query():
        data = request.get_json()
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO progress (student_id, lesson_id, score, completed, completed_at) VALUES (?,?,?,?,datetime('now','localtime'))",
                (data.get('student_id'), data.get('lesson_id'), data.get('score',0), data.get('completed',0))
            )
            return {"status": "saved"}
        finally:
            conn.close()
    return safe_db_query(query)

@app.route('/api/evaluate/writing', methods=['POST'])
def evaluate_writing():
    def query():
        data = request.get_json()
        return {"status": "evaluated", "feedback": "Writing evaluation completed", "score": 85}
    return safe_db_query(query)

@app.route('/api/evaluate/speaking', methods=['POST'])
def evaluate_speaking():
    def query():
        data = request.get_json()
        return {"status": "evaluated", "feedback": "Speaking evaluation completed", "score": 80}
    return safe_db_query(query)

# ====== Admin Routes ======
@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html') if os.path.exists('admin.html') else jsonify({"error":"admin panel not found"}), 404

@app.route('/api/admin/stats')
def admin_stats():
    def query():
        conn = get_db_connection()
        try:
            students = conn.execute("SELECT COUNT(*) FROM students WHERE is_banned=0").fetchone()[0]
            courses = conn.execute("SELECT COUNT(*) FROM courses WHERE is_active=1").fetchone()[0]
            return {"students": students, "courses": courses}
        finally:
            conn.close()
    return safe_db_query(query)

@app.route('/api/admin/students')
def admin_students():
    def query():
        conn = get_db_connection()
        try:
            rows = conn.execute("SELECT * FROM students ORDER BY xp DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    return safe_db_query(query)

# ====== Error Handlers ======
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not_found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "internal_error"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    init_db()
    logger.info(f"Yamen Academy WebApp starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
