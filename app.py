# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template, send_file
import json, os, re
from datetime import datetime
from database import (
    init_db, seed_demo_data, get_db,
    get_student_by_id, get_student_by_telegram,
    get_all_students, get_daily_tasks, toggle_task,
    get_errors, get_leaderboard, get_admin_stats,
    get_all_questions, get_all_payments,
    get_writing_corrections_today, increment_writing_corrections,
    save_writing_submission, save_speaking_submission
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "yamen-secret-2025")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# تهيئة قاعدة البيانات عند بدء التشغيل
with app.app_context():
    init_db()
    seed_demo_data()
# ─── Admin Routes Registration ───────────────────────────────
try:
    from admin_routes import register_admin_routes
    register_admin_routes(app)
    print('✅ Admin routes registered')
except Exception as _e:
    print(f'[WARN] admin_routes: {_e}')


@app.route('/sw.js')
def service_worker():
    from flask import send_from_directory
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/api/admin/students')
def api_admin_students():
    try:
        import sqlite3, os as _os
        db_path = _os.environ.get('DB_PATH',
            _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'academy.db'))
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cols = [r[1] for r in conn.execute('PRAGMA table_info(students)').fetchall()]
        want = ['id','telegram_id','full_name','phone','level','xp','total_xp',
                'streak','is_paid','placement_done','placement_score','stage',
                'missions_completed','mock_exam_score','registered_at','last_active']
        select = [c for c in want if c in cols] or ['*']
        rows = [dict(r) for r in conn.execute(
            'SELECT ' + ', '.join(select) + ' FROM students ORDER BY id DESC'
        ).fetchall()]
        conn.close()
        return jsonify({'students': rows, 'total': len(rows)})
    except Exception as e:
        return jsonify({'error': str(e), 'students': []}), 200


@app.route('/api/admin/grading-rules', methods=['GET'])
def api_grading_rules_get():
    try:
        import sqlite3, os as _os
        db_path = _os.environ.get('DB_PATH',
            _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'academy.db'))
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE IF NOT EXISTS essay_grading_rules ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "topic TEXT NOT NULL,"
            "target_keywords TEXT DEFAULT '[]',"
            "academic_connectors TEXT DEFAULT '[]',"
            "forbidden_words TEXT DEFAULT '[]',"
            "points_per_keyword INTEGER DEFAULT 2,"
            "points_per_connector INTEGER DEFAULT 3,"
            "penalty_per_forbidden INTEGER DEFAULT 1,"
            "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.commit()
        rows = [dict(r) for r in conn.execute(
            'SELECT * FROM essay_grading_rules ORDER BY id DESC'
        ).fetchall()]
        conn.close()
        return jsonify({'rules': rows, 'total': len(rows)})
    except Exception as e:
        return jsonify({'error': str(e), 'rules': []}), 200


@app.route('/api/admin/grading-rules', methods=['POST'])
def api_grading_rules_post():
    try:
        import sqlite3, os as _os, json as _json
        db_path = _os.environ.get('DB_PATH',
            _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'academy.db'))
        data = request.get_json() or {}
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO essay_grading_rules "
            "(topic, target_keywords, academic_connectors, forbidden_words,"
            " points_per_keyword, points_per_connector, penalty_per_forbidden)"
            " VALUES (?,?,?,?,?,?,?)",
            (data.get('topic', ''),
             _json.dumps(data.get('target_keywords', [])),
             _json.dumps(data.get('academic_connectors', [])),
             _json.dumps(data.get('forbidden_words', [])),
             data.get('points_per_keyword', 2),
             data.get('points_per_connector', 3),
             data.get('penalty_per_forbidden', 1))
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 200


@app.route('/api/admin/grading-rules/<int:rule_id>', methods=['DELETE'])
def api_grading_rules_delete(rule_id):
    try:
        import sqlite3, os as _os
        db_path = _os.environ.get('DB_PATH',
            _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'academy.db'))
        conn = sqlite3.connect(db_path)
        conn.execute('DELETE FROM essay_grading_rules WHERE id=?', (rule_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 200


@app.route('/api/student/<int:student_id>')
def api_student(student_id):
    try:
        import sqlite3, os as _os
        db = _os.environ.get('DB_PATH',
            _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'academy.db'))
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cols = [r[1] for r in conn.execute('PRAGMA table_info(students)').fetchall()]
        id_col = 'telegram_id' if 'telegram_id' in cols else 'id'
        s = conn.execute(
            f'SELECT * FROM students WHERE {id_col}=?', (str(student_id),)
        ).fetchone()
        if not s:
            conn.close()
            return jsonify({'error': 'not found'}), 404
        s = dict(s)
        skills = conn.execute(
            'SELECT * FROM user_skills_progress WHERE telegram_id=?',
            (str(student_id),)
        ).fetchone()
        s['skills'] = dict(skills) if skills else {}
        conn.close()
        return jsonify(s)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lessons')
def api_lessons():
    try:
        import sqlite3, os as _os
        db = _os.environ.get('DB_PATH',
            _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'academy.db'))
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            'SELECT id,title,skill_type,stage,order_num,xp_reward,description '
            'FROM lessons WHERE is_active=1 ORDER BY stage,order_num'
        ).fetchall()
        conn.close()
        return jsonify({'lessons': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'error': str(e), 'lessons': []}), 200


@app.route('/api/leaderboard')
def api_leaderboard():
    try:
        import sqlite3, os as _os
        db = _os.environ.get('DB_PATH',
            _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'academy.db'))
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            'SELECT telegram_id, full_name, username, xp '
            'FROM students ORDER BY xp DESC LIMIT 20'
        ).fetchall()
        conn.close()
        return jsonify({'leaderboard': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'error': str(e), 'leaderboard': []}), 200


@app.route('/api/user/graduation-status')
def api_graduation():
    try:
        import sqlite3, os as _os
        from flask import request as _req
        sid = _req.args.get('student_id')
        if not sid:
            return jsonify({'eligible': False, 'checks': []})
        db = _os.environ.get('DB_PATH',
            _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'academy.db'))
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        s = conn.execute(
            'SELECT * FROM students WHERE telegram_id=?', (str(sid),)
        ).fetchone()
        settings = {r[0]: r[1] for r in conn.execute(
            'SELECT key, value FROM system_settings'
        ).fetchall()}
        conn.close()
        if not s:
            return jsonify({'eligible': False, 'checks': []})
        s = dict(s)
        req_score    = int(settings.get('required_score', 59))
        req_xp       = int(settings.get('graduation_xp', 500))
        req_missions = int(settings.get('graduation_missions', 10))
        req_streak   = int(settings.get('graduation_streak', 3))
        mock_thresh  = req_score + 10
        checks = [
            {
                'message': f'اشتراك مدفوع ✅' if s.get('is_paid') else 'اشتراك مدفوع مطلوب',
                'passed': bool(s.get('is_paid'))
            },
            {
                'message': f'XP: {s.get("xp",0)} / {req_xp}',
                'passed': (s.get('xp', 0) >= req_xp)
            },
            {
                'message': f'المهام: {s.get("missions_completed",0)} / {req_missions}',
                'passed': (s.get('missions_completed', 0) >= req_missions)
            },
            {
                'message': f'Streak: {s.get("streak",0)} / {req_streak} أيام',
                'passed': (s.get('streak', 0) >= req_streak)
            },
            {
                'message': f'Mock Exam: {s.get("mock_exam_score",0)}% / {mock_thresh}%',
                'passed': (s.get('mock_exam_score', 0) >= mock_thresh)
            },
        ]
        eligible = all(c['passed'] for c in checks)
        return jsonify({'eligible': eligible, 'checks': checks,
                        'required_score': req_score})
    except Exception as e:
        return jsonify({'error': str(e), 'eligible': False, 'checks': []}), 200


@app.route('/student')
def student_dashboard():
    from flask import render_template, request as _req
    sid = _req.args.get('student_id', '')
    return render_template('student_dashboard.html', student_id=sid)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
