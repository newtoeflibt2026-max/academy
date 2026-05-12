from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)

# ====== API للموبايل ======
@app.route('/api/student/<int:user_id>')
def api_student(user_id):
    import sys; sys.path.insert(0, r'C:\yamen_academy')
    from database import get_student
    s = get_student(user_id)
    return jsonify(s if s else {"error": "not found"})

@app.route('/api/lessons/<level>')
def api_lessons(level):
    import sys; sys.path.insert(0, r'C:\yamen_academy')
    from database import get_conn
    conn = get_conn()
    course_map = {"Foundation": 1, "Intermediate": 2, "Advanced": 3}
    cid = course_map.get(level, 1)
    rows = conn.execute("SELECT * FROM lessons WHERE course_id=? AND is_active=1 ORDER BY order_num", (cid,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/leaderboard')
def api_leaderboard():
    import sys; sys.path.insert(0, r'C:\yamen_academy')
    from database import get_leaderboard
    return jsonify(get_leaderboard(20))

@app.route('/api/plans')
def api_plans():
    plans = [
        {"name":"Flexible","price":25,"days":30,"desc":"دروس موزعة على 30 يوم"},
        {"name":"Excellence","price":60,"days":90,"desc":"دروس موزعة على 90 يوم"},
        {"name":"Emergency","price":35,"days":30,"desc":"كل الدروس دفعة واحدة"},
        {"name":"VIP","price":50,"days":60,"desc":"دروس + تصحيح + تقييم"},
        {"name":"Self Study","price":15,"days":120,"desc":"كتاب IELTS + استماع"},
    ]
    return jsonify(plans)

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "version": "1.0.0"})

# ====== واجهة الموقع ======
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
