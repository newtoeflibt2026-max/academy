# -*- coding: utf-8 -*-
import os

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")

ROUTES = '''
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
'''

with open(APP, 'r', encoding='utf-8') as f:
    content = f.read()

marker = "if __name__ == '__main__':"
if marker not in content:
    marker = 'if __name__ == "__main__":'

added = []
for route_check, route_code in [
    ('/api/student/', ROUTES),
]:
    if route_check not in content:
        content = content.replace(marker, ROUTES + '\n' + marker)
        added.append(route_check)
        break

if added:
    with open(APP, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Routes added:', added)
else:
    print('Routes already exist')
