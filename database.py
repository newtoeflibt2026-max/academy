import sqlite3, os, threading, json
from datetime import datetime, timedelta

DB_PATH = r"C:\yamen_academy\data\academy.db"
_local = threading.local()

def get_conn():
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn

def _safe_exec(sql, params=()):
    conn = get_conn()
    cur = conn.execute(sql, params)
    conn.commit()
    return cur

def dict_row(row):
    if row is None: return None
    return dict(row)

def dict_rows(rows):
    return [dict(r) for r in rows] if rows else []

# ─── SM-2 Algorithm (inline for zero-dependency) ───
def sm2(quality, repetitions, previous_ef, previous_interval):
    if quality >= 3:
        if repetitions == 0:       interval = 1
        elif repetitions == 1:     interval = 6
        else:                      interval = round(previous_interval * previous_ef)
        repetitions += 1
        ef = previous_ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if ef < 1.3: ef = 1.3
    else:
        repetitions = 0; interval = 1; ef = previous_ef
    return interval, repetitions, ef

def quality_from_answer(correct: bool, time_taken: float = 4.0) -> int:
    if not correct:  return 1
    if time_taken <= 2: return 5
    if time_taken <= 5: return 4
    return 3

# ─── SCHEMA ───

def get_courses_by_level(level):
    cur = _safe_exec('SELECT * FROM courses WHERE level=? ORDER BY id', (level,))
    return dict_rows(cur.fetchall())


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



# --- Writing Submissions Table ---
def ensure_writing_tables():
    """Create tables for writing & speaking if not exist."""
    _safe_exec("""
        CREATE TABLE IF NOT EXISTS writing_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_type TEXT NOT NULL DEFAULT 'task2',
            prompt TEXT,
            essay_text TEXT NOT NULL,
            word_count INTEGER DEFAULT 0,
            band_score REAL,
            task_response REAL,
            coherence_cohesion REAL,
            lexical_resource REAL,
            grammatical_range REAL,
            feedback_ar TEXT,
            corrections_json TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES students(user_id)
        )
    """)
    _safe_exec("""
        CREATE TABLE IF NOT EXISTS speaking_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prompt TEXT,
            transcript_text TEXT,
            audio_duration_sec REAL DEFAULT 0,
            band_score REAL,
            fluency REAL,
            pronunciation REAL,
            lexical_resource REAL,
            grammatical_range REAL,
            feedback_ar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES students(user_id)
        )
    """)
    print("✅ writing_submissions + speaking_sessions tables ready")

def save_writing_submission(user_id, task_type, prompt, essay_text,
                            band_score, task_response, coherence_cohesion,
                            lexical_resource, grammatical_range, feedback_ar, corrections_json):
    cur = _safe_exec(
        """INSERT INTO writing_submissions
           (user_id, task_type, prompt, essay_text, word_count, band_score,
            task_response, coherence_cohesion, lexical_resource, grammatical_range,
            feedback_ar, corrections_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, task_type, prompt, essay_text, len(essay_text.split()),
         band_score, task_response, coherence_cohesion, lexical_resource,
         grammatical_range, feedback_ar, corrections_json)
    )
    return cur.lastrowid

def save_speaking_session(user_id, prompt, transcript_text, duration,
                          band_score, fluency, pronunciation,
                          lexical_resource, grammatical_range, feedback_ar):
    cur = _safe_exec(
        """INSERT INTO speaking_sessions
           (user_id, prompt, transcript_text, audio_duration_sec,
            band_score, fluency, pronunciation, lexical_resource,
            grammatical_range, feedback_ar)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, prompt, transcript_text, duration,
         band_score, fluency, pronunciation, lexical_resource,
         grammatical_range, feedback_ar)
    )
    return cur.lastrowid

def get_writing_history(user_id, limit=10):
    cur = _safe_exec(
        "SELECT * FROM writing_submissions WHERE user_id=? ORDER BY submitted_at DESC LIMIT ?",
        (user_id, limit)
    )
    return dict_rows(cur.fetchall())

def get_speaking_history(user_id, limit=10):
    cur = _safe_exec(
        "SELECT * FROM speaking_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    return dict_rows(cur.fetchall())


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            user_id INTEGER PRIMARY KEY, full_name TEXT, phone TEXT,
            level TEXT, placement_done INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0, active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, level TEXT NOT NULL, description TEXT
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER, title TEXT NOT NULL, content TEXT,
            properties TEXT DEFAULT '', order_num INTEGER DEFAULT 0,
            is_locked INTEGER DEFAULT 0,
            media_type TEXT, media_file_id TEXT,
            action_type TEXT, action_label TEXT,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, plan_name TEXT,
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_date TIMESTAMP, active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES students(user_id)
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, plan_name TEXT, amount REAL,
            receipt_file_id TEXT DEFAULT '', status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES students(user_id)
        );
        CREATE TABLE IF NOT EXISTS admin_settings (
            key TEXT PRIMARY KEY, value TEXT
        );
        CREATE TABLE IF NOT EXISTS xp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, amount INTEGER, reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS daily_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE, question TEXT, answer TEXT,
            xp_reward INTEGER DEFAULT 50
        );
        CREATE TABLE IF NOT EXISTS challenge_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, challenge_id INTEGER,
            response TEXT, score REAL, feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS vault_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, item_type TEXT, content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, action TEXT, details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        -- ═══ NEW: SRS & SPELLING SYSTEM ═══
        CREATE TABLE IF NOT EXISTS spelling_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL, definition TEXT,
            level TEXT DEFAULT 'A1', category TEXT,
            example_sentence TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS word_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, word_id INTEGER,
            ef REAL DEFAULT 2.5, repetitions INTEGER DEFAULT 0,
            interval_days INTEGER DEFAULT 0,
            next_review DATE,
            error_count INTEGER DEFAULT 0,
            consecutive_correct INTEGER DEFAULT 0,
            last_quality INTEGER,
            last_reviewed TIMESTAMP,
            FOREIGN KEY (word_id) REFERENCES spelling_words(id),
            FOREIGN KEY (user_id) REFERENCES students(user_id),
            UNIQUE(user_id, word_id)
        );
        CREATE TABLE IF NOT EXISTS error_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, word_id INTEGER,
            misspelled_as TEXT,
            review_count INTEGER DEFAULT 0,
            mastered INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (word_id) REFERENCES spelling_words(id),
            FOREIGN KEY (user_id) REFERENCES students(user_id)
        );
        CREATE TABLE IF NOT EXISTS placement_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
            correct_option INTEGER,  -- 0-3
            level TEXT DEFAULT 'A1',
            order_num INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS lesson_quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER,
            title TEXT,
            pass_score INTEGER DEFAULT 60,
            FOREIGN KEY (lesson_id) REFERENCES lessons(id)
        );
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER,
            question TEXT NOT NULL,
            option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
            correct_option INTEGER,
            order_num INTEGER DEFAULT 0,
            FOREIGN KEY (quiz_id) REFERENCES lesson_quizzes(id)
        );
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, quiz_id INTEGER,
            score REAL, max_score REAL,
            passed INTEGER DEFAULT 0,
            xp_earned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (quiz_id) REFERENCES lesson_quizzes(id),
            FOREIGN KEY (user_id) REFERENCES students(user_id)
        );
    """)
    conn.commit()

# ─── STUDENT ───
def upsert_student(user_id, full_name=None, phone=None):
    s = get_student(user_id)
    if s:
        if full_name: _safe_exec("UPDATE students SET full_name=? WHERE user_id=?", (full_name, user_id))
        if phone: _safe_exec("UPDATE students SET phone=? WHERE user_id=?", (phone, user_id))
    else:
        _safe_exec("INSERT OR IGNORE INTO students(user_id,full_name,phone) VALUES(?,?,?)", (user_id, full_name, phone))

def get_student(user_id):
    cur = _safe_exec("SELECT * FROM students WHERE user_id=?", (user_id,))
    return dict_row(cur.fetchone())

def set_placement_done(user_id):
    _safe_exec("UPDATE students SET placement_done=1 WHERE user_id=?", (user_id,))

def set_student_level(user_id, level):
    _safe_exec("UPDATE students SET level=? WHERE user_id=?", (level, user_id))

def get_student_level(user_id):
    s = get_student(user_id)
    return s['level'] if s else None

# ─── XP ───
def add_xp(user_id, amount, reason=''):
    _safe_exec("UPDATE students SET xp = xp + ? WHERE user_id=?", (amount, user_id))
    _safe_exec("INSERT INTO xp_log(user_id,amount,reason) VALUES(?,?,?)", (user_id, amount, reason))

def get_leaderboard(limit=10):
    cur = _safe_exec("SELECT user_id, full_name, xp FROM students ORDER BY xp DESC LIMIT ?", (limit,))
    return dict_rows(cur.fetchall())

# ─── LESSONS ───
def add_lesson(title, content, course_id, order_num=0, properties='',
               media_type=None, media_file_id=None, action_type=None, action_label=None):
    _safe_exec("""INSERT INTO lessons (title,content,properties,course_id,order_num,
                 media_type,media_file_id,action_type,action_label)
                 VALUES(?,?,?,?,?,?,?,?,?)""",
               (title, content, properties, course_id, order_num,
                media_type, media_file_id, action_type, action_label))

def get_all_lessons(course_id=None):
    if course_id:
        cur = _safe_exec("SELECT * FROM lessons WHERE course_id=? ORDER BY order_num", (course_id,))
    else:
        cur = _safe_exec("SELECT * FROM lessons ORDER BY course_id, order_num")
    return dict_rows(cur.fetchall())

def get_lesson(lesson_id):
    cur = _safe_exec("SELECT * FROM lessons WHERE id=?", (lesson_id,))
    return dict_row(cur.fetchone())

# ─── PAYMENTS ───
def add_payment(user_id, plan_name, amount, receipt_file_id=''):
    _safe_exec("INSERT INTO payments(user_id,plan_name,amount,receipt_file_id) VALUES(?,?,?,?)",
               (user_id, plan_name, amount, receipt_file_id))

def get_pending_payments():
    cur = _safe_exec("SELECT * FROM payments WHERE status='pending' ORDER BY created_at")
    return dict_rows(cur.fetchall())

def update_payment_status(payment_id, status):
    _safe_exec("UPDATE payments SET status=? WHERE id=?", (status, payment_id))

def get_payment(payment_id):
    cur = _safe_exec("SELECT * FROM payments WHERE id=?", (payment_id,))
    return dict_row(cur.fetchone())

# ─── SUBSCRIPTIONS ───
def add_subscription(user_id, plan_name, days=30):
    end = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    _safe_exec("INSERT INTO subscriptions(user_id,plan_name,end_date) VALUES(?,?,?)",
               (user_id, plan_name, end))

def get_active_subscription(user_id):
    cur = _safe_exec("SELECT * FROM subscriptions WHERE user_id=? AND active=1 ORDER BY end_date DESC LIMIT 1", (user_id,))
    return dict_row(cur.fetchone())

def has_active_subscription(user_id):
    return get_active_subscription(user_id) is not None

# ─── STATS ───
def get_stats():
    total = _safe_exec("SELECT COUNT(*) as c FROM students").fetchone()['c']
    active = _safe_exec("SELECT COUNT(*) as c FROM subscriptions WHERE active=1").fetchone()['c']
    pending = _safe_exec("SELECT COUNT(*) as c FROM payments WHERE status='pending'").fetchone()['c']
    return {'total_students': total, 'active_subs': active, 'pending_payments': pending}

# ═══════════════════════════════════════════
# ⭐ NEW: SPELLING & SRS SYSTEM
# ═══════════════════════════════════════════

# ─── SPELLING WORDS ───
def add_spelling_word(word, definition='', level='A1', category='', example='', created_by=None):
    _safe_exec("""INSERT INTO spelling_words(word,definition,level,category,example_sentence,created_by)
                  VALUES(?,?,?,?,?,?)""",
               (word.strip().lower(), definition, level, category, example, created_by))

def get_spelling_words(level=None, limit=20):
    if level:
        cur = _safe_exec("SELECT * FROM spelling_words WHERE level=? ORDER BY RANDOM() LIMIT ?", (level, limit))
    else:
        cur = _safe_exec("SELECT * FROM spelling_words ORDER BY RANDOM() LIMIT ?", (limit,))
    return dict_rows(cur.fetchall())

def get_all_spelling_words():
    cur = _safe_exec("SELECT * FROM spelling_words ORDER BY level, word")
    return dict_rows(cur.fetchall())

def delete_spelling_word(word_id):
    _safe_exec("DELETE FROM spelling_words WHERE id=?", (word_id,))

def update_spelling_word(word_id, **kwargs):
    for k, v in kwargs.items():
        _safe_exec(f"UPDATE spelling_words SET {k}=? WHERE id=?", (v, word_id))

# ─── WORD REVIEWS (SRS) ───
def get_due_reviews(user_id, limit=10):
    cur = _safe_exec("""
        SELECT wr.*, sw.word, sw.definition, sw.example_sentence, sw.level
        FROM word_reviews wr
        JOIN spelling_words sw ON sw.id = wr.word_id
        WHERE wr.user_id = ? AND wr.next_review <= date('now')
        ORDER BY wr.next_review ASC
        LIMIT ?
    """, (user_id, limit))
    return dict_rows(cur.fetchall())

def get_or_create_review(user_id, word_id):
    existing = _safe_exec("SELECT * FROM word_reviews WHERE user_id=? AND word_id=?",
                          (user_id, word_id)).fetchone()
    if existing:
        return dict_row(existing)
    _safe_exec("""INSERT INTO word_reviews(user_id,word_id,ef,repetitions,interval_days,
                  next_review) VALUES(?,?,2.5,0,0,date('now'))""",
               (user_id, word_id))
    return dict_row(_safe_exec("SELECT * FROM word_reviews WHERE user_id=? AND word_id=?",
                               (user_id, word_id)).fetchone())

def update_review(user_id, word_id, quality, time_taken=4.0):
    """Record a review and update SM-2 scheduling."""
    if quality is None:
        quality = quality_from_answer(True, time_taken)
    row = _safe_exec("SELECT * FROM word_reviews WHERE user_id=? AND word_id=?",
                     (user_id, word_id)).fetchone()
    if not row:
        return None
    r = dict(row)
    interval, reps, ef = sm2(quality, r['repetitions'], r['ef'], r['interval_days'])
    next_review = (datetime.now() + timedelta(days=interval)).strftime('%Y-%m-%d')
    error_count = r['error_count']
    consecutive = r['consecutive_correct']
    if quality >= 3:
        consecutive += 1
    else:
        error_count += 1
        consecutive = 0
    _safe_exec("""UPDATE word_reviews SET ef=?, repetitions=?, interval_days=?,
                  next_review=?, error_count=?, consecutive_correct=?,
                  last_quality=?, last_reviewed=CURRENT_TIMESTAMP
                  WHERE user_id=? AND word_id=?""",
               (ef, reps, interval, next_review, error_count, consecutive,
                quality, user_id, word_id))
    return {'interval': interval, 'repetitions': reps, 'ef': ef, 'next_review': next_review}

# ─── ERROR BANK ───
def add_to_error_bank(user_id, word_id, misspelled_as=''):
    existing = _safe_exec("SELECT * FROM error_bank WHERE user_id=? AND word_id=? AND mastered=0",
                          (user_id, word_id)).fetchone()
    if existing:
        _safe_exec("UPDATE error_bank SET review_count=review_count+1, misspelled_as=? WHERE id=?",
                   (misspelled_as, existing['id']))
    else:
        _safe_exec("INSERT INTO error_bank(user_id,word_id,misspelled_as) VALUES(?,?,?)",
                   (user_id, word_id, misspelled_as))

def get_error_bank(user_id, limit=10):
    cur = _safe_exec("""
        SELECT eb.*, sw.word, sw.definition
        FROM error_bank eb
        JOIN spelling_words sw ON sw.id = eb.word_id
        WHERE eb.user_id=? AND eb.mastered=0
        ORDER BY eb.review_count DESC, eb.created_at DESC
        LIMIT ?
    """, (user_id, limit))
    return dict_rows(cur.fetchall())

def mark_error_mastered(error_id):
    _safe_exec("UPDATE error_bank SET mastered=1 WHERE id=?", (error_id,))

def get_error_bank_count(user_id):
    cur = _safe_exec("SELECT COUNT(*) as c FROM error_bank WHERE user_id=? AND mastered=0", (user_id,))
    return cur.fetchone()['c']

# ─── PLACEMENT QUESTIONS (DB-driven) ───
def add_placement_question(question, opts, correct_idx, level='A1', order=0):
    _safe_exec("""INSERT INTO placement_questions(question,option_a,option_b,option_c,option_d,
                  correct_option,level,order_num) VALUES(?,?,?,?,?,?,?,?)""",
               (question, opts[0], opts[1], opts[2], opts[3], correct_idx, level, order))

def get_placement_questions(limit=10):
    cur = _safe_exec("SELECT * FROM placement_questions ORDER BY order_num LIMIT ?", (limit,))
    return dict_rows(cur.fetchall())

def get_all_placement_questions():
    cur = _safe_exec("SELECT * FROM placement_questions ORDER BY order_num")
    return dict_rows(cur.fetchall())

def delete_placement_question(qid):
    _safe_exec("DELETE FROM placement_questions WHERE id=?", (qid,))

def update_placement_question(qid, **kwargs):
    for k, v in kwargs.items():
        _safe_exec(f"UPDATE placement_questions SET {k}=? WHERE id=?", (v, qid))

# ─── LESSON QUIZZES ───
def add_lesson_quiz(lesson_id, title='Quiz', pass_score=60):
    cur = _safe_exec("INSERT INTO lesson_quizzes(lesson_id,title,pass_score) VALUES(?,?,?)",
                     (lesson_id, title, pass_score))
    return cur.lastrowid

def get_lesson_quiz(lesson_id):
    cur = _safe_exec("SELECT * FROM lesson_quizzes WHERE lesson_id=? LIMIT 1", (lesson_id,))
    return dict_row(cur.fetchone())

def add_quiz_question(quiz_id, question, opts, correct_idx, order=0):
    _safe_exec("""INSERT INTO quiz_questions(quiz_id,question,option_a,option_b,option_c,option_d,
                  correct_option,order_num) VALUES(?,?,?,?,?,?,?,?)""",
               (quiz_id, question, opts[0], opts[1], opts[2], opts[3], correct_idx, order))

def get_quiz_questions(quiz_id):
    cur = _safe_exec("SELECT * FROM quiz_questions WHERE quiz_id=? ORDER BY order_num", (quiz_id,))
    return dict_rows(cur.fetchall())

def get_all_lesson_quizzes():
    cur = _safe_exec("SELECT * FROM lesson_quizzes")
    return dict_rows(cur.fetchall())

def delete_lesson_quiz(quiz_id):
    _safe_exec("DELETE FROM quiz_questions WHERE quiz_id=?", (quiz_id,))
    _safe_exec("DELETE FROM lesson_quizzes WHERE id=?", (quiz_id,))

# ─── QUIZ ATTEMPTS ───
def record_quiz_attempt(user_id, quiz_id, score, max_score, passed, xp_earned):
    _safe_exec("""INSERT INTO quiz_attempts(user_id,quiz_id,score,max_score,passed,xp_earned)
                  VALUES(?,?,?,?,?,?)""",
               (user_id, quiz_id, score, max_score, passed, xp_earned))

def get_quiz_attempts(user_id, quiz_id=None):
    if quiz_id:
        cur = _safe_exec("SELECT * FROM quiz_attempts WHERE user_id=? AND quiz_id=? ORDER BY created_at DESC",
                         (user_id, quiz_id))
    else:
        cur = _safe_exec("SELECT * FROM quiz_attempts WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    return dict_rows(cur.fetchall())

# ─── DAILY CHALLENGE ───
def get_today_challenge():
    today = datetime.now().strftime('%Y-%m-%d')
    cur = _safe_exec("SELECT * FROM daily_challenges WHERE date=?", (today,))
    return dict_row(cur.fetchone())

# ─── SEED DATA FOR FIRST RUN ───
def seed_spelling_words():
    # Only seed if table is empty
    count = _safe_exec("SELECT COUNT(*) as c FROM spelling_words").fetchone()['c']
    if count > 0:
        return
    words = [
        ("accommodate", "يستوعب / يوفر سكناً", "B1", "General", "Hotels must accommodate guests with disabilities."),
        ("necessary", "ضروري", "A2", "General", "Water is necessary for life."),
        ("separate", "يفصل", "A2", "General", "Please separate the white clothes from the colored ones."),
        ("definitely", "بالتأكيد", "A2", "General", "I will definitely come to your party."),
        ("environment", "بيئة", "B1", "Environment", "We must protect the environment."),
        ("government", "حكومة", "B1", "Politics", "The government passed a new law."),
        ("beginning", "بداية", "A2", "General", "The beginning of the story was exciting."),
        ("embarrass", "يُحرج", "B2", "Emotions", "Don't embarrass me in front of my friends."),
        ("successful", "ناجح", "B1", "Business", "She is a very successful entrepreneur."),
        ("maintenance", "صيانة", "B2", "Technical", "Regular maintenance keeps your car running well."),
        ("acknowledgment", "اعتراف / إقرار", "C1", "Academic", "He received acknowledgment for his work."),
        ("rhythm", "إيقاع", "B2", "Arts", "The rhythm of the music was captivating."),
        ("conscious", "واعٍ / مدرك", "B2", "Psychology", "Be conscious of your surroundings."),
        ("frequently", "بشكل متكرر", "B1", "General", "She frequently visits her grandmother."),
        ("immediately", "فوراً", "B1", "General", "Call me immediately if there is a problem."),
        ("pronunciation", "نطق", "B1", "Language", "Your pronunciation is improving every day."),
        ("opportunity", "فرصة", "B1", "Business", "This is a great opportunity for you."),
        ("recommend", "يوصي", "B1", "General", "I recommend this restaurant highly."),
        ("unfortunately", "للأسف", "B1", "General", "Unfortunately, the event was cancelled."),
        ("temperature", "درجة حرارة", "A2", "Science", "The temperature today is 30 degrees."),
    ]
    for w, definition, level, cat, example in words:
        add_spelling_word(w, definition, level, cat, example)
    print(f"✅ Seeded {len(words)} spelling words")

def seed_placement_questions():
    count = _safe_exec("SELECT COUNT(*) as c FROM placement_questions").fetchone()['c']
    if count > 0:
        return
    qs = [
        ("I ___ a student.", ["am","is","are","be"], 0, "A1", 1),
        ("She ___ to school every day.", ["go","goes","going","gone"], 1, "A1", 2),
        ("They ___ playing football now.", ["is","am","are","be"], 2, "A1", 3),
        ("He ___ a book yesterday.", ["read","reads","reading","is reading"], 0, "A2", 4),
        ("We have ___ finished our homework.", ["yet","already","still","just now"], 1, "A2", 5),
        ("There ___ many people at the party.", ["was","were","is","has"], 1, "A2", 6),
        ("This is the ___ movie I have ever seen.", ["good","better","best","well"], 2, "A2", 7),
        ("If I ___ rich, I would travel the world.", ["am","was","were","be"], 2, "B1", 8),
        ("The book ___ by Mark Twain.", ["wrote","was written","written","writing"], 1, "B1", 9),
        ("I look forward ___ from you soon.", ["hear","hearing","to hearing","to hear"], 2, "B1", 10),
    ]
    for q, opts, correct, level, order in qs:
        add_placement_question(q, opts, correct, level, order)
    print(f"✅ Seeded {len(qs)} placement questions")

if __name__ == '__main__':
    init_db()
    seed_spelling_words()
    seed_placement_questions()
    print('✅ Database initialized with all tables + seed data')
