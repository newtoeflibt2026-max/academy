from flask import Flask, request, jsonify
from flask_cors import CORS
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from database import (
    get_conn, get_stats, get_all_students, toggle_student_active,
    get_pending_payments, update_payment_status, add_subscription,
    add_payment, get_admin_setting, set_admin_setting,
    get_leaderboard, add_xp, upsert_student,
    get_due_reviews, add_to_error_bank, record_correct_review,
    log_activity, get_absent_students, init_db
)

app = Flask(__name__)
CORS(app)

# ───── Health ─────
@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

# ───── Dashboard ─────
@app.route('/api/admin/stats', methods=['POST', 'GET'])
def stats():
    stats = get_stats()
    conn = get_conn()
    stats['total_xp'] = conn.execute("SELECT COALESCE(SUM(xp), 0) FROM students").fetchone()[0]
    conn.close()
    return jsonify(stats)

# ───── Students ─────
@app.route('/api/admin/students', methods=['POST', 'GET'])
def students():
    students = get_all_students()
    return jsonify({'students': [dict(s) for s in students]})

@app.route('/api/admin/toggle_student', methods=['POST'])
def toggle_student():
    data = request.json
    toggle_student_active(data['user_id'])
    return jsonify({'success': True})

# ───── Courses ─────
@app.route('/api/admin/courses', methods=['POST', 'GET'])
def courses():
    conn = get_conn()
    courses = conn.execute("SELECT * FROM courses ORDER BY id").fetchall()
    conn.close()
    return jsonify({'courses': [dict(c) for c in courses]})

@app.route('/api/courses', methods=['GET'])
def public_courses():
    conn = get_conn()
    courses = conn.execute("SELECT id, name, level, price, duration_days, skill_type, time_limit, target_score FROM courses ORDER BY id").fetchall()
    conn.close()
    return jsonify({'courses': [dict(c) for c in courses]})

@app.route('/api/admin/add_course', methods=['POST'])
def add_course():
    d = request.json
    conn = get_conn()
    conn.execute("INSERT INTO courses (name,level,price,duration_days,is_vip,skill_type,time_limit,target_score) VALUES (?,?,?,?,?,?,?,?)",
                 (d['name'], d['level'], d['price'], d['duration_days'], d.get('is_vip', 0), d.get('skill_type', 'speaking'), d.get('time_limit', 45), d.get('target_score', 59)))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/delete_course', methods=['POST'])
def delete_course():
    conn = get_conn()
    conn.execute("DELETE FROM courses WHERE id=?", (request.json['id'],))
    conn.commit(); conn.close()
    return jsonify({'success': True})

# ───── Payments ─────
@app.route('/api/admin/payments', methods=['POST', 'GET'])
def payments():
    flt = (request.json or {}).get('filter', 'pending')
    conn = get_conn()
    payments = conn.execute("SELECT * FROM payments WHERE status=? ORDER BY created_at DESC", (flt,)).fetchall()
    conn.close()
    return jsonify({'payments': [dict(p) for p in payments]})

@app.route('/api/admin/approve_payment', methods=['POST'])
def approve_payment():
    pid = request.json['id']
    conn = get_conn()
    update_payment_status(pid, 'approved')
    p = conn.execute("SELECT user_id, plan_name FROM payments WHERE id=?", (pid,)).fetchone()
    if p:
        days = 90 if "Excellence" in p[1] else (60 if "VIP" in p[1] else 30)
        add_subscription(p[0], p[1], days)
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/reject_payment', methods=['POST'])
def reject_payment():
    update_payment_status(request.json['id'], 'rejected')
    return jsonify({'success': True})

# ───── Vault ─────
@app.route('/api/admin/vault', methods=['POST', 'GET'])
def vault():
    conn = get_conn()
    items = conn.execute("SELECT * FROM vault_items ORDER BY id").fetchall()
    conn.close()
    return jsonify({'items': [dict(i) for i in items]})

@app.route('/api/admin/add_vault', methods=['POST'])
def add_vault():
    d = request.json
    conn = get_conn()
    conn.execute("INSERT INTO vault_items (title,content,unlock_level,category) VALUES (?,?,?,?)",
                 (d['title'], d['content'], d.get('unlock_level', 1), d.get('category', 'speaking')))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/delete_vault', methods=['POST'])
def delete_vault():
    conn = get_conn()
    conn.execute("DELETE FROM vault_items WHERE id=?", (request.json['id'],))
    conn.commit(); conn.close()
    return jsonify({'success': True})

# ───── Error Bank ─────
@app.route('/api/error_bank/<int:user_id>', methods=['GET'])
def error_bank(user_id):
    reviews = get_due_reviews(user_id)
    return jsonify({'reviews': reviews})

@app.route('/api/error_bank/correct', methods=['POST'])
def correct_review():
    d = request.json
    record_correct_review(d['user_id'], d['error_bank_id'])
    return jsonify({'success': True})

# ───── Leaderboard ─────
@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    lb = get_leaderboard(10)
    return jsonify({'leaderboard': lb})

# ───── Gamification ─────
@app.route('/api/admin/gamification', methods=['POST', 'GET'])
def gamification():
    timer = get_admin_setting('challenge_timer', '5')
    multiplier = get_admin_setting('xp_multiplier', '1')
    leaderboard = get_leaderboard(10)
    return jsonify({
        'challenge_timer': timer,
        'xp_multiplier': multiplier,
        'leaderboard': [dict(r) for r in leaderboard]
    })

# ───── Settings ─────
@app.route('/api/admin/settings', methods=['POST', 'GET'])
def settings():
    return jsonify({
        'show_writing': get_admin_setting('show_writing', '1'),
        'show_speaking': get_admin_setting('show_speaking', '1'),
        'vault_locked': get_admin_setting('vault_locked', '1'),
        'usage_cap': get_admin_setting('usage_cap', '3'),
        'wallet_number': get_admin_setting('wallet_number', '0798919150'),
        'speaking_strict': get_admin_setting('speaking_strict', '0'),
        'speaking_bitrate_check': get_admin_setting('speaking_bitrate_check', '0'),
        'xp_multiplier': get_admin_setting('xp_multiplier', '1'),
        'challenge_timer': get_admin_setting('challenge_timer', '5'),
    })

@app.route('/api/admin/save_setting', methods=['POST'])
def save_setting():
    d = request.json
    set_admin_setting(d['key'], str(d['value']))
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5050, debug=True)
