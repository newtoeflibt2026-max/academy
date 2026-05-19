# -*- coding: utf-8 -*-
"""
patch_app.py - يضيف المسارات الناقصة لـ app.py
"""
import os

APP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")

STUDENTS_ROUTE = '''
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
'''

GRADING_ROUTE = '''
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
'''

SW_ROUTE = '''
@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')
'''

with open(APP_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

marker = "if __name__ == '__main__':"
marker2 = 'if __name__ == "__main__":'

insert_marker = marker if marker in content else marker2

changed = False

if '/api/admin/students' not in content:
    content = content.replace(insert_marker, STUDENTS_ROUTE + '\n' + insert_marker)
    print("added /api/admin/students route")
    changed = True
else:
    print("/api/admin/students already exists")

if '/api/admin/grading-rules' not in content:
    content = content.replace(insert_marker, GRADING_ROUTE + '\n' + insert_marker)
    print("added /api/admin/grading-rules routes")
    changed = True
else:
    print("/api/admin/grading-rules already exists")

if '/sw.js' not in content:
    content = content.replace(insert_marker, SW_ROUTE + '\n' + insert_marker)
    print("added /sw.js route")
    changed = True
else:
    print("/sw.js already exists")

if changed:
    with open(APP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print("app.py updated!")
else:
    print("no changes needed")
