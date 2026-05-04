path = r'C:\yamen_academy\database.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

fns = """
def get_all_lessons():
    cur = _safe_exec('SELECT * FROM lessons ORDER BY id')
    return dict_rows(cur.fetchall())

def get_lessons_by_course(course_id):
    cur = _safe_exec('SELECT * FROM lessons WHERE course_id=? ORDER BY order_num', (course_id,))
    return dict_rows(cur.fetchall())

def get_lesson(lesson_id):
    cur = _safe_exec('SELECT * FROM lessons WHERE id=?', (lesson_id,))
    return dict_row(cur.fetchone())

def get_quiz_by_lesson_id(lesson_id):
    cur = _safe_exec('SELECT * FROM lesson_quizzes WHERE lesson_id=?', (lesson_id,))
    return dict_row(cur.fetchone())

def get_quiz_questions(quiz_id):
    cur = _safe_exec('SELECT * FROM quiz_questions WHERE quiz_id=? ORDER BY id', (quiz_id,))
    return dict_rows(cur.fetchall())

def add_quiz_attempt(user_id, quiz_id, answers, score):
    cur = _safe_exec('INSERT INTO quiz_attempts(user_id,quiz_id,answers,score) VALUES(?,?,?,?)',
         (user_id, quiz_id, str(answers), score))
    return cur.lastrowid

def get_stats():
    cur = _safe_exec('SELECT count(*) as c FROM students')
    total = cur.fetchone()[0]
    cur = _safe_exec('SELECT count(*) as c FROM subscriptions WHERE active=1')
    active = cur.fetchone()[0]
    cur = _safe_exec("SELECT count(*) as c FROM payments WHERE status='pending'")
    pending = cur.fetchone()[0]
    return {'total_students': total, 'active_subs': active, 'pending_payments': pending}

def get_pending_payments():
    cur = _safe_exec("SELECT * FROM payments WHERE status='pending' ORDER BY created_at DESC")
    return dict_rows(cur.fetchall())

def get_payment(pid):
    cur = _safe_exec('SELECT * FROM payments WHERE id=?', (pid,))
    return dict_row(cur.fetchone())

def update_payment_status(pid, status):
    _safe_exec('UPDATE payments SET status=? WHERE id=?', (status, pid))

def has_active_subscription(user_id):
    cur = _safe_exec('SELECT id FROM subscriptions WHERE user_id=? AND active=1', (user_id,))
    return cur.fetchone() is not None

def get_student(user_id):
    cur = _safe_exec('SELECT * FROM students WHERE user_id=?', (user_id,))
    return dict_row(cur.fetchone())

def get_all_spelling_words():
    cur = _safe_exec('SELECT * FROM spelling_words ORDER BY id')
    return dict_rows(cur.fetchall())

def add_spelling_word(word, definition, level, category, example):
    cur = _safe_exec('INSERT INTO spelling_words(word,definition,level,category,example) VALUES(?,?,?,?,?)',
         (word, definition, level, category, example))
    return cur.lastrowid

def get_all_placement_questions():
    cur = _safe_exec('SELECT * FROM placement_questions ORDER BY id')
    return dict_rows(cur.fetchall())

def add_placement_question(text, level, qtype, options='', correct_answer='', hint=''):
    cur = _safe_exec('INSERT INTO placement_questions(question_text,level,question_type,options,correct_answer,hint) VALUES(?,?,?,?,?,?)',
         (text, level, qtype, options, correct_answer, hint))
    return cur.lastrowid

def get_all_lesson_quizzes():
    cur = _safe_exec('SELECT * FROM lesson_quizzes ORDER BY id')
    return dict_rows(cur.fetchall())

def add_lesson_quiz(lesson_id):
    cur = _safe_exec('INSERT INTO lesson_quizzes(lesson_id) VALUES(?)', (lesson_id,))
    return cur.lastrowid

def add_lesson(title, content, course_id, media_type=None, media_file_id=None, action_type=None, action_label=None, order_num=0):
    cur = _safe_exec('INSERT INTO lessons(title,content,course_id,media_type,media_file_id,action_type,action_label,order_num) VALUES(?,?,?,?,?,?,?,?)',
         (title, content, course_id, media_type, media_file_id, action_type, action_label, order_num))
    return cur.lastrowid

def add_quiz_question(quiz_id, text, qtype, options='', correct_answer='', level='A1'):
    cur = _safe_exec('INSERT INTO quiz_questions(quiz_id,question_text,question_type,options,correct_answer,level) VALUES(?,?,?,?,?,?)',
         (quiz_id, text, qtype, options, correct_answer, level))
    return cur.lastrowid
"""

content = content.replace('def init_db():', fns + '\ndef init_db():')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done - all functions added')

