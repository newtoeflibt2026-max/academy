from flask import Flask, request, jsonify
from flask_cors import CORS
import sys, os

sys.path.insert(0, 'C:/yamen_academy')
from database import (
    get_conn, get_stats, get_all_students, toggle_student_active,
    get_pending_payments, update_payment_status, add_subscription,
    add_payment, get_admin_setting, set_admin_setting,
    get_leaderboard, add_xp, upsert_student
)

app = Flask(__name__)
CORS(app)

# ───── Dashboard ─────
@app.route('/api/admin/stats', methods=['POST'])
def stats():
    stats = get_stats()
    conn = get_conn()
    stats['total_xp'] = conn.execute("SELECT COALESCE(SUM(xp), 0) FROM students").fetchone()[0]
    return jsonify(stats)

# ───── Students ─────
@app.route('/api/admin/students', methods=['POST'])
def students():
    students = get_all_students()
    return jsonify({'students': [dict(s) for s in students]})

@app.route('/api/admin/toggle_student', methods=['POST'])
def toggle_student():
    data = request.json
    toggle_student_active(data['user_id'])
    return jsonify({'success': True})

# ───── Courses ─────
@app.route('/api/admin/courses', methods=['POST'])
def courses():
    conn = get_conn()
    courses = conn.execute("SELECT * FROM courses ORDER BY id").fetchall()
    return jsonify({'courses': [dict(c) for c in courses]})

@app.route('/api/admin/add_course', methods=['POST'])
def add_course():
    d = request.json
    conn = get_conn()
    conn.execute("INSERT INTO courses (name,level,price,duration_days,is_vip) VALUES (?,?,?,?,?)",
                 (d['name'], d['level'], d['price'], d['duration_days'], d['is_vip']))
    conn.commit()
    return jsonify({'success': True})

@app.route('/api/admin/delete_course', methods=['POST'])
def delete_course():
    conn = get_conn()
    conn.execute("DELETE FROM courses WHERE id=?", (request.json['id'],))
    conn.commit()
    return jsonify({'success': True})

# ───── Payments ─────
@app.route('/api/admin/payments', methods=['POST'])
def payments():
    flt = request.json.get('filter', 'pending')
    conn = get_conn()
    payments = conn.execute("SELECT * FROM payments WHERE status=? ORDER BY created_at DESC", (flt,)).fetchall()
    return jsonify({'payments': [dict(p) for p in payments]})

@app.route('/api/admin/approve_payment', methods=['POST'])
def approve_payment():
    pid = request.json['id']
    conn = get_conn()
    update_payment_status(pid, 'approved')
    p = conn.execute("SELECT user_id, plan_name FROM payments WHERE id=?", (pid,)).fetchone()
    if p:
        days = 30
        if "Excellence" in p[1]: days = 90
        elif "VIP" in p[1]: days = 60
        add_subscription(p[0], p[1], days)
    return jsonify({'success': True})

@app.route('/api/admin/reject_payment', methods=['POST'])
def reject_payment():
    update_payment_status(request.json['id'], 'rejected')
    return jsonify({'success': True})

# ───── Vault ─────
@app.route('/api/admin/vault', methods=['POST'])
def vault():
    conn = get_conn()
    items = conn.execute("SELECT * FROM vault_items ORDER BY id").fetchall()
    return jsonify({'items': [dict(i) for i in items]})

@app.route('/api/admin/add_vault', methods=['POST'])
def add_vault():
    d = request.json
    conn = get_conn()
    conn.execute("INSERT INTO vault_items (title,content,unlock_level) VALUES (?,?,?)",
                 (d['title'], d['content'], d['unlock_level']))
    conn.commit()
    return jsonify({'success': True})

@app.route('/api/admin/delete_vault', methods=['POST'])
def delete_vault():
    conn = get_conn()
    conn.execute("DELETE FROM vault_items WHERE id=?", (request.json['id'],))
    conn.commit()
    return jsonify({'success': True})

# ───── Gamification ─────
@app.route('/api/admin/gamification', methods=['POST'])
def gamification():
    timer = get_admin_setting('challenge_timer', '5')
    multiplier = get_admin_setting('xp_multiplier', '1')
    leaderboard = get_leaderboard(10)
    return jsonify({
        'challenge_timer': timer,
        'xp_multiplier': multiplier,
        'leaderboard': [dict(r) for r in leaderboard]
    })

@app.route('/api/admin/send_challenge', methods=['POST'])
def send_challenge():
    return jsonify({'success': True})

# ───── Settings ─────
@app.route('/api/admin/settings', methods=['POST'])
def settings():
    return jsonify({
        'show_writing': get_admin_setting('show_writing', '1'),
        'show_speaking': get_admin_setting('show_speaking', '1'),
        'vault_locked': get_admin_setting('vault_locked', '1'),
        'usage_cap': get_admin_setting('usage_cap', '3'),
        'wallet_number': get_admin_setting('wallet_number', '0798919150'),
        'speaking_strict': get_admin_setting('speaking_strict', '0'),
        'speaking_bitrate_check': get_admin_setting('speaking_bitrate_check', '0'),
    })

@app.route('/api/admin/save_setting', methods=['POST'])
def save_setting():
    d = request.json
    set_admin_setting(d['key'], str(d['value']))
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(port=5050, debug=True)
