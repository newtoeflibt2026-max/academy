path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

new_block = """

# ============================================================
# ADMIN CRUD + PLACEMENT ENGINE (v40 - Clean Injection)
# ============================================================
import sqlite3
def _db():
    c = sqlite3.connect('data/yamen_academy.db')
    c.row_factory = sqlite3.Row
    return c

@app.route('/api/admin/content/create', methods=['POST'])
def _admin_new_lesson():
    try:
        r = create_lesson_from_admin(request.get_json(force=True))
        return jsonify(r)
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@app.route('/api/admin/content/update', methods=['POST'])
def _admin_edit_lesson():
    try:
        r = update_lesson_from_admin(request.get_json(force=True))
        return jsonify(r)
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@app.route('/api/admin/content/delete', methods=['POST'])
def _admin_del_lesson():
    try:
        r = delete_lesson_from_admin(request.get_json(force=True).get('lesson_id'))
        return jsonify(r)
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@app.route('/api/admin/questions')
def _admin_qlist():
    conn = _db()
    rows = conn.execute('SELECT * FROM questions ORDER BY skill,id').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/questions/add', methods=['POST'])
def _admin_qadd():
    d = request.get_json(force=True)
    conn = _db()
    conn.execute(
        'INSERT INTO questions(skill,question,option_a,option_b,option_c,option_d,correct_answer,difficulty) VALUES(?,?,?,?,?,?,?,?)',
        [d['skill'], d['question'], d['option_a'], d['option_b'], d['option_c'], d['option_d'],
         d['correct_answer'].strip().upper(), d.get('difficulty','beginner')]
    )
    conn.commit()
    nid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    return jsonify({'status':'ok','id':nid}), 201

@app.route('/api/admin/questions/edit/<int:qid>', methods=['POST'])
def _admin_qedit(qid):
    d = request.get_json(force=True)
    sets, vals = [], []
    for k in ['skill','question','option_a','option_b','option_c','option_d','correct_answer','difficulty']:
        if k in d:
            sets.append(k + '=?')
            vals.append(d[k])
    if not sets:
        return jsonify({'error':'No fields'}), 400
    sets.append('updated_at=datetime("now","localtime")')
    vals.append(qid)
    conn = _db()
    conn.execute('UPDATE questions SET ' + ','.join(sets) + ' WHERE id=?', vals)
    conn.commit()
    conn.close()
    return jsonify({'status':'ok'})

@app.route('/api/admin/questions/delete/<int:qid>', methods=['POST'])
def _admin_qdel(qid):
    conn = _db()
    conn.execute('DELETE FROM questions WHERE id=?', (qid,))
    conn.commit()
    conn.close()
    return jsonify({'status':'ok'})

@app.route('/api/placement/questions')
def _placement_qs():
    conn = _db()
    rows = conn.execute('SELECT id,skill,question,option_a,option_b,option_c,option_d,difficulty FROM questions ORDER BY RANDOM()').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/placement/submit', methods=['POST'])
def _placement_submit():
    d = request.get_json(force=True)
    sid = d.get('student_id', session.get('student_id', 1))
    ans = d.get('answers', [])
    if not ans:
        return jsonify({'error':'No answers'}), 400
    total = len(ans)
    correct = 0
    conn = _db()
    for a in ans:
        row = conn.execute('SELECT correct_answer FROM questions WHERE id=?', (a.get('question_id'),)).fetchone()
        if row and row['correct_answer'].strip().upper() == a.get('answer','').strip().upper():
            correct += 1
    pct = round((correct / total) * 100, 1) if total else 0
    if pct < 50:
        band, level, label, path = 'A1-A2', 'beginner', 'Weak', 'foundations'
    elif pct <= 75:
        band, level, label, path = 'B1-B2', 'intermediate', 'Intermediate', 'core'
    else:
        band, level, label, path = 'C1-C2', 'advanced', 'Advanced', 'mastery'
    conn.execute('INSERT INTO placement_results(student_id,band,level,path,score_pct) VALUES(?,?,?,?,?)', (sid,band,level,path,pct))
    try:
        conn.execute('UPDATE users SET level=? WHERE id=?', (level, sid))
    except:
        pass
    conn.commit()
    conn.close()
    session['student_id'] = sid
    session['placement_level'] = level
    return jsonify({'status':'ok','score':pct,'correct':correct,'total':total,'band':band,'level':level,'label':label,'path':path})

"""

# Find if __name__ and inject before it
needle = "if __name__ =="
pos = code.find(needle)
if pos == -1:
    print("ERROR: if __name__ not found!")
    exit()

code = code[:pos] + new_block + "\n" + code[pos:]

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print("DONE: Routes injected into app.py successfully!")
