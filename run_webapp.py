import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS

from database import (
    init_db, get_db_connection, get_conn, get_stats, get_all_students,
    toggle_student_active, get_pending_payments, update_payment_status,
    add_subscription, add_payment, get_admin_setting, set_admin_setting,
    get_leaderboard, add_xp, upsert_student, log_activity
)

app = Flask(__name__)
CORS(app)

# ═══════ STATIC FILES ═══════
@app.route('/')
def index():
    return render_template('admin.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/app.js')
def serve_js():
    return send_from_directory('static', 'app.js', mimetype='application/javascript')

@app.route('/style.css')
def serve_css():
    return send_from_directory('static', 'style.css', mimetype='text/css')

# ═══════ HEALTH ═══════
@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "message": "Yamen Academy API is running"})

# ═══════ DASHBOARD ═══════
@app.route('/api/admin/stats', methods=['POST', 'GET'])
def stats():
    s = get_stats()
    conn = get_conn()
    try:
        s['total_xp'] = conn.execute("SELECT COALESCE(SUM(xp), 0) FROM students").fetchone()[0]
    except:
        s['total_xp'] = 0
    finally:
        conn.close()
    return jsonify(s)

# ═══════ STUDENTS ═══════
@app.route('/api/admin/students', methods=['POST', 'GET'])
def students():
    ss = get_all_students()
    return jsonify({'students': [dict(s) for s in ss]})

@app.route('/api/admin/toggle_student', methods=['POST'])
def toggle_student():
    data = request.json
    toggle_student_active(data['user_id'])
    return jsonify({'success': True})

# ═══════ COURSES ═══════
@app.route('/api/admin/courses', methods=['POST', 'GET'])
def courses():
    conn = get_conn()
    try:
        cs = conn.execute("SELECT * FROM courses ORDER BY id").fetchall()
        return jsonify({'courses': [dict(c) for c in cs]})
    finally:
        conn.close()

@app.route('/api/courses', methods=['GET'])
def public_courses():
    conn = get_conn()
    try:
        cs = conn.execute("SELECT id, name, level, price, duration_days, skill_type, time_limit, target_score, is_active FROM courses WHERE is_active=1 ORDER BY id").fetchall()
        return jsonify({'courses': [dict(c) for c in cs]})
    finally:
        conn.close()

@app.route('/api/admin/add_course', methods=['POST'])
def add_course():
    d = request.json
    conn = get_conn()
    try:
        conn.execute("INSERT INTO courses (name,level,price,duration_days,is_vip,skill_type,time_limit,target_score) VALUES (?,?,?,?,?,?,?,?)",
                     (d['name'], d['level'], d['price'], d['duration_days'], d.get('is_vip', 0),
                      d.get('skill_type', 'speaking'), d.get('time_limit', 45), d.get('target_score', 59)))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/delete_course', methods=['POST'])
def delete_course():
    conn = get_conn()
    try:
        conn.execute("DELETE FROM courses WHERE id=?", (request.json['id'],))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'success': True})

# ═══════ PAYMENTS ═══════
@app.route('/api/admin/payments', methods=['POST', 'GET'])
def payments():
    conn = get_conn()
    try:
        ps = conn.execute("SELECT * FROM payments WHERE status='pending' ORDER BY created_at DESC").fetchall()
        return jsonify({'payments': [dict(p) for p in ps]})
    finally:
        conn.close()

@app.route('/api/admin/approve_payment', methods=['POST'])
def approve_payment():
    pid = request.json['id']
    conn = get_conn()
    try:
        update_payment_status(pid, 'approved')
        p = conn.execute("SELECT user_id, plan_name FROM payments WHERE id=?", (pid,)).fetchone()
        if p:
            days = 90 if "Excellence" in p[1] else (60 if "VIP" in p[1] else 30)
            add_subscription(p[0], p[1], days)
    finally:
        conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/reject_payment', methods=['POST'])
def reject_payment():
    update_payment_status(request.json['id'], 'rejected')
    return jsonify({'success': True})

# ═══════ VAULT ═══════
@app.route('/api/admin/vault', methods=['POST', 'GET'])
def vault():
    conn = get_conn()
    try:
        items = conn.execute("SELECT * FROM vault_items ORDER BY id").fetchall()
        return jsonify({'items': [dict(i) for i in items]})
    finally:
        conn.close()

@app.route('/api/admin/add_vault', methods=['POST'])
def add_vault():
    d = request.json
    conn = get_conn()
    try:
        conn.execute("INSERT INTO vault_items (title,content,unlock_level,category) VALUES (?,?,?,?)",
                     (d['title'], d['content'], d.get('unlock_level', 1), d.get('category', 'speaking')))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/delete_vault', methods=['POST'])
def delete_vault():
    conn = get_conn()
    try:
        conn.execute("DELETE FROM vault_items WHERE id=?", (request.json['id'],))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'success': True})

# ═══════ LEADERBOARD ═══════
@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    lb = get_leaderboard(10)
    return jsonify({'leaderboard': lb})

# ═══════ SETTINGS ═══════
@app.route('/api/admin/settings', methods=['POST', 'GET'])
def settings():
    return jsonify({
        'show_writing': get_admin_setting('show_writing', '1'),
        'show_speaking': get_admin_setting('show_speaking', '1'),
        'wallet_number': get_admin_setting('wallet_number', '0798919150'),
        'xp_multiplier': get_admin_setting('xp_multiplier', '1'),
        'challenge_timer': get_admin_setting('challenge_timer', '5'),
    })

@app.route('/api/admin/save_setting', methods=['POST'])
def save_setting():
    d = request.json
    set_admin_setting(d['key'], str(d['value']))
    return jsonify({'success': True})

# ═══════ ERROR HANDLERS ═══════
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

# ═══════ MAIN ═══════
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Yamen Academy Admin running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
