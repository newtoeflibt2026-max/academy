import os, logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from database import get_db_connection, init_db
import sqlite3
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

# ===== Safe DB wrapper =====
def with_db(fn):
    conn = None
    try:
        conn = get_db_connection()
        return fn(conn)
    except Exception as e:
        logger.error(f"DB Error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            try: conn.close()
            except: pass

# ===== Routes =====
@app.route('/')
def index():
    try:
        return send_from_directory('.', 'index.html')
    except Exception as e:
        logger.error(f"Index error: {e}")
        return "<h1>Yamen Academy</h1><p>Welcome</p>", 200

@app.route('/<path:f>')
def serve(f):
    try:
        return send_from_directory('.', f)
    except:
        if f == 'favicon.ico':
            return '', 204
        return jsonify({"error": "not_found"}), 404

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/courses')
def courses():
    def q(conn):
        try:
            rows = conn.execute("SELECT * FROM courses WHERE is_active=1").fetchall()
            return jsonify([dict(r) for r in rows])
        except sqlite3.OperationalError as e:
            return jsonify([])  # return empty on lock
    return with_db(q)

@app.route('/api/courses', methods=['POST'])
def add_course():
    d = request.get_json(silent=True) or {}
    def q(conn):
        conn.execute("INSERT INTO courses (title,description,level) VALUES (?,?,?)",
                    (d.get('title',''), d.get('description',''), d.get('level','A1')))
        return jsonify({"status":"ok"}), 201
    return with_db(q)

@app.route('/api/leaderboard')
def leaderboard():
    def q(conn):
        rows = conn.execute("SELECT first_name,username,xp,streak FROM students WHERE is_banned=0 ORDER BY xp DESC LIMIT 20").fetchall()
        return jsonify([dict(r) for r in rows])
    return with_db(q)

@app.route('/api/admin/stats')
def admin_stats():
    def q(conn):
        s = conn.execute("SELECT COUNT(*) FROM students WHERE is_banned=0").fetchone()[0]
        c = conn.execute("SELECT COUNT(*) FROM courses WHERE is_active=1").fetchone()[0]
        return jsonify({"students":s,"courses":c})
    return with_db(q)

# ===== Error handlers =====
@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "internal_error"}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not_found"}), 404

if __name__ == '__main__':
    try:
        init_db()
    except Exception as e:
        logger.error(f"DB init failed: {e}")
    
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
