import os, logging, traceback, json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

_db_loaded = False

def _lazy_db():
    global _db_loaded
    if not _db_loaded:
        try:
            from database import init_db
            init_db()
            _db_loaded = True
            logger.info("DB initialized")
        except Exception as e:
            logger.warning(f"DB deferred: {e}")

def with_db(fn):
    _lazy_db()
    conn = None
    try:
        from database import get_db_connection
        conn = get_db_connection()
        return fn(conn)
    except Exception as e:
        logger.error(f"DB error: {e}")
        return jsonify({"error": str(e)}), 503
    finally:
        if conn:
            try: conn.close()
            except: pass

# ===== STATIC =====
@app.route('/')
def index():
    try:
        return send_from_directory('.', 'index.html')
    except:
        return '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Yamen Academy</title><style>body{background:linear-gradient(135deg,#1E3A5F,#3B82F6);color:white;font-family:Cairo,sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;text-align:center;direction:rtl}h1{font-size:48px;margin:0}</style></head><body><div><h1>🕌</h1><h1>Yamen Academy</h1><p style="font-size:20px;margin-top:15px">المنصة تعمل</p></div></body></html>', 200

@app.route('/<path:f>')
def serve(f):
    try: return send_from_directory('.', f)
    except: return jsonify({"error":"not_found"}), 404

# ===== HEALTH =====
@app.route('/api/health')
def health():
    return jsonify({"status":"ok","app":"yamen-academy","server":"running"})

# ===== /api/data - FALLBACK COURSES (no DB needed) =====
@app.route('/api/data')
def fallback_data():
    """Returns sample data when DB is unavailable"""
    return jsonify({
        "courses": [
            {
                "id": 1,
                "title": "📚 دورة اللغة الإنجليزية - المستوى الأول",
                "description": "تعلم أساسيات اللغة الإنجليزية من الصفر. القواعد، المفردات، والمحادثة.",
                "level": "A1"
            },
            {
                "id": 2,
                "title": "📝 دورة المحادثة المتقدمة",
                "description": "تطوير مهارات التحدث والاستماع للمستوى المتوسط والمتقدم.",
                "level": "B2"
            },
            {
                "id": 3,
                "title": "✍️ دورة الكتابة الأكاديمية",
                "description": "تعلم كتابة المقالات والتقارير باللغة الإنجليزية بأسلوب أكاديمي.",
                "level": "C1"
            },
            {
                "id": 4,
                "title": "🎯 التحضير لاختبار IELTS",
                "description": "دورة شاملة للتحضير لاختبار IELTS بجميع أقسامه.",
                "level": "B2-C1"
            }
        ],
        "message": "Sample data - add courses via admin panel for real data",
        "source": "fallback"
    })

# ===== API =====
@app.route('/api/courses')
def courses():
    def q(conn):
        rows = conn.execute("SELECT * FROM courses WHERE is_active=1").fetchall()
        result = [dict(r) for r in rows]
        if not result:
            # Return fallback if DB is empty
            return jsonify([
                {"id":0,"title":"🎯 لا توجد دورات بعد","description":"أضف دورات من لوحة التحكم","level":"-"}
            ])
        return jsonify(result)
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

@app.route('/api/lessons/<int:cid>')
def lessons(cid):
    def q(conn):
        rows = conn.execute("SELECT * FROM lessons WHERE course_id=? ORDER BY order_index", (cid,)).fetchall()
        return jsonify([dict(r) for r in rows])
    return with_db(q)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Yamen Academy LMS starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
