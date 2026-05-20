import os, json
from datetime import datetime, timedelta

BASE = r'C:\yamen_academy'
DB_PATH = r'C:\yamen_academy\data\academy.db'

# ============================================================
# SM-2 ALGORITHM — Pure Python Implementation
# ============================================================
SM2_CODE = '''
def sm2(quality, repetitions, previous_ef, previous_interval):
    """SuperMemo-2 algorithm. Returns (interval, repetitions, ease_factor)."""
    if quality >= 3:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(previous_interval * previous_ef)
        repetitions += 1
        ef = previous_ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if ef < 1.3:
            ef = 1.3
    else:
        repetitions = 0
        interval = 1
        ef = previous_ef  # no change on failure
    return interval, repetitions, ef

def quality_from_answer(correct: bool, time_taken_seconds: float = 4.0) -> int:
    """Map correctness + speed → SM-2 quality 0-5."""
    if not correct:
        return 1
    if time_taken_seconds <= 2:
        return 5  # perfect + fast
    elif time_taken_seconds <= 5:
        return 4  # correct with slight hesitation
    else:
        return 3  # correct but slow
'''
# ============================================================
# DATABASE.PY — Full Yamen Academy Schema
# ============================================================
DATABASE_PY = r'''
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
'''

# ============================================================
# HANDLERS/__INIT__.PY
# ============================================================
INIT_PY = r'''
from aiogram import Dispatcher

def register_all(dp: Dispatcher):
    from .start import router as r0; dp.include_router(r0)
    from .student import router as r1; dp.include_router(r1)
    from .subscriptions import router as r2; dp.include_router(r2)
    from .placement_test import router as r3; dp.include_router(r3)
    from .courses import router as r4; dp.include_router(r4)
    from .admin import router as r5; dp.include_router(r5)
    from .spelling import router as r6; dp.include_router(r6)
    from .daily_challenge import router as r7; dp.include_router(r7)
    from .speaking import router as r8; dp.include_router(r8)
    from .writing import router as r9; dp.include_router(r9)
'''

# ============================================================
# HANDLERS/PLACEMENT_TEST.PY — DB-driven, prevents repeats
# ============================================================
PLACEMENT_TEST_PY = r'''
from aiogram import Router, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_student, set_student_level, set_placement_done, get_placement_questions

router = Router()
TOTAL_PER_LEVEL = {0: (0,3,"A1"), 1:(4,6,"A2"), 2:(7,8,"B1"), 3:(9,9,"B2"), 4:(10,10,"C1")}

def get_pathway(score):
    if score <= 3:   return "A1", "مبتدئ 🔸"
    elif score <= 6:  return "A2", "تحت المتوسط 🟠"
    elif score <= 8:  return "B1", "متوسط 🟡"
    elif score <= 9:  return "B2", "فوق المتوسط 🟢"
    return "C1", "متقدم 🔴"

class PlaceState(StatesGroup):
    q = State()

@router.callback_query(F.data == "placement_test")
async def start_test(callback: types.CallbackQuery, state: FSMContext):
    student = get_student(callback.from_user.id)
    if student and student["placement_done"]:
        await callback.message.edit_text(
            "✅ *لقد أتممت اختبار تحديد المستوى مسبقاً* ✅\n\n"
            "تم تحديد مستواك بالفعل، يمكنك الآن:\n"
            "📚 تصفح *دوراتي* للبدء بالتعلم\n"
            "🎯 المشاركة في *تحدي الـ60 ثانية*\n\n"
            "بالتوفيق في رحلتك التعليمية! 🌟",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    questions = get_placement_questions(10)
    if len(questions) < 10:
        await callback.message.edit_text("⚠️ لم يتم إعداد أسئلة كافية بعد. يرجى التواصل مع الأدمن.")
        await callback.answer()
        return
    await state.update_data(score=0, idx=0, questions=questions)
    await state.set_state(PlaceState.q)
    await send_q(callback.message, state, 0)

async def send_q(msg, state, idx):
    data = await state.get_data()
    questions = data.get("questions", [])
    if idx >= len(questions):
        await finish_test(msg, state)
        return
    q = questions[idx]
    opts = [q['option_a'], q['option_b'], q['option_c'], q['option_d']]
    btns = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{chr(0x2460+i)} {o}", callback_data=f"pq_{idx}_{i}")]
        for i, o in enumerate(opts)
    ])
    await msg.edit_text(
        f"📝 *سؤال {idx+1} من {len(questions)}*\n\n_{q['question']}_",
        reply_markup=btns, parse_mode="Markdown"
    )

@router.callback_query(PlaceState.q, F.data.startswith("pq_"))
async def handle_place(callback: types.CallbackQuery, state: FSMContext):
    _, idx_s, choice_s = callback.data.split("_")
    idx, choice = int(idx_s), int(choice_s)
    data = await state.get_data()
    questions = data["questions"]
    correct = questions[idx]["correct_option"]
    score = data.get("score", 0)
    if choice == correct:
        score += 1
    await state.update_data(score=score)
    await send_q(callback.message, state, idx + 1)
    await callback.answer()

async def finish_test(msg, state):
    data = await state.get_data()
    score = data.get("score", 0)
    total = len(data.get("questions", []))
    level, label = get_pathway(score)
    uid = msg.chat.id
    set_student_level(uid, level)
    set_placement_done(uid)
    await msg.edit_text(
        f"🎉 *اكتمل اختبار تحديد المستوى!*\n\n"
        f"📊 نتيجتك: *{score}/{total}*\n"
        f"🎯 مستواك: *{label} ({level})*\n\n"
        f"📚 تفضل بزيارة *دوراتي* للبدء بالدروس!\n"
        f"⚡ جرّب *تحدي الـ60 ثانية* لاختبار سرعتك!",
        parse_mode="Markdown"
    )
'''

# ============================================================
# HANDLERS/SPELLING.PY — SRS + Error Bank + Spelling Quiz
# ============================================================
SPELLING_PY = r'''
from aiogram import Router, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    get_due_reviews, get_or_create_review, update_review,
    add_to_error_bank, get_error_bank, mark_error_mastered,
    quality_from_answer, get_student_level, get_spelling_words, add_xp,
    get_all_spelling_words
)
import time as _time
import asyncio

router = Router()

class SpellState(StatesGroup):
    answering = State()

@router.callback_query(F.data == "spelling_practice")
async def start_spelling(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    level = get_student_level(uid) or "A1"
    due = get_due_reviews(uid, limit=10)
    if not due:
        # No due reviews — get new words
        new_words = get_spelling_words(level, 5)
        if not new_words:
            await callback.message.edit_text("📚 لا توجد كلمات متاحة حالياً للمستوى الحالي. سيتم إضافتها قريباً!")
            await callback.answer()
            return
        for w in new_words:
            get_or_create_review(uid, w['id'])
        due = get_due_reviews(uid, limit=10)
    if not due:
        await callback.message.edit_text("🎉 لقد أنهيت جميع مراجعاتك! عد لاحقاً للمراجعة حسب الجدول الزمني.")
        await callback.answer()
        return
    await state.update_data(due=due, idx=0, correct=0, errors=0, start_time=_time.time())
    await send_spell_q(callback.message, state, 0)

async def send_spell_q(msg, state, idx):
    data = await state.get_data()
    due = data.get("due", [])
    if idx >= len(due):
        await finish_spelling(msg, state)
        return
    word = due[idx]
    await state.set_state(SpellState.answering)
    await state.update_data(idx=idx, current_word=word, q_start=_time.time())
    await msg.edit_text(
        f"✍️ *تهجئة الكلمة*\n\nاكتب الكلمة التي تعني:\n\n"
        f"📖 *{word['definition']}*\n\n"
        f"مثال: _{word['example_sentence']}_\n\n"
        f"(/skip للتخطي)",
        parse_mode="Markdown"
    )

@router.message(SpellState.answering)
async def handle_spell(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current = data.get("current_word")
    if not current:
        return
    uid = message.from_user.id
    answer = message.text.strip().lower()

    if answer == '/skip':
        await message.answer(f"⏭️ الكلمة الصحيحة: *{current['word']}*", parse_mode="Markdown")
        update_review(uid, current['word_id'], 2, 10)
        add_to_error_bank(uid, current['word_id'], "skipped")
        await state.update_data(errors=data.get('errors', 0) + 1)
        await send_spell_q(message, state, data['idx'] + 1)
        return

    correct_word = current['word'].lower()
    elapsed = _time.time() - data.get('q_start', _time.time())

    if answer == correct_word:
        q = quality_from_answer(True, elapsed)
        update_review(uid, current['word_id'], q, elapsed)
        await state.update_data(correct=data.get('correct', 0) + 1)
        await message.answer(f"✅ صحيح! *{current['word']}* ⚡", parse_mode="Markdown")
    else:
        update_review(uid, current['word_id'], 1, elapsed)
        add_to_error_bank(uid, current['word_id'], answer)
        await state.update_data(errors=data.get('errors', 0) + 1)
        await message.answer(
            f"❌ خطأ! كتبت: _{answer}_\n✅ الصحيح: *{current['word']}*",
            parse_mode="Markdown"
        )

    await asyncio.sleep(0.5)
    await send_spell_q(message, state, data['idx'] + 1)

async def finish_spelling(msg, state):
    data = await state.get_data()
    correct = data.get('correct', 0)
    errors = data.get('errors', 0)
    total = correct + errors
    xp = correct * 5
    uid = msg.chat.id
    if xp > 0:
        add_xp(uid, xp, 'spelling_practice')
    await msg.answer(
        f"📊 *نتيجة التهجئة*\n\n"
        f"✅ صحيح: {correct}\n❌ أخطاء: {errors}\n"
        f"⭐ XP: +{xp}\n\n"
        f"🔁 الكلمات الخاطئة دخلت *بنك الأخطاء* وستراجع لاحقاً.",
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "error_bank_review")
async def review_error_bank(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    errors = get_error_bank(uid, limit=8)
    if not errors:
        await callback.message.edit_text("🎉 لا توجد أخطاء في بنك الأخطاء! أنت تتقن التهجئة.")
        await callback.answer()
        return
    await state.update_data(eb=errors, idx=0, eb_correct=0, eb_errors=0)
    await send_eb_q(callback.message, state, 0)

async def send_eb_q(msg, state, idx):
    data = await state.get_data()
    eb = data.get("eb", [])
    if idx >= len(eb):
        correct = data.get('eb_correct', 0)
        total = len(eb)
        uid = msg.chat.id
        xp = correct * 8
        if xp > 0:
            add_xp(uid, xp, 'error_bank_review')
        await msg.edit_text(
            f"📊 *نتيجة مراجعة بنك الأخطاء*\n\n"
            f"✅ صحيح: {correct}\n❌ أخطاء: {total - correct}\n"
            f"⭐ XP: +{xp}\n\n"
            f"الكلمات المتقنة خرجت من بنك الأخطاء 🔓",
            parse_mode="Markdown"
        )
        return
    error = eb[idx]
    await state.update_data(eb_idx=idx)
    await state.set_state(SpellState.answering)
    await msg.edit_text(
        f"🔁 *مراجعة بنك الأخطاء*\n\n"
        f"آخر خطأ كتبته: _{error['misspelled_as']}_\n\n"
        f"📖 اكتب الكلمة: *{error['definition']}*\n"
        f"(الكلمة: {error['word']})",
        parse_mode="Markdown"
    )
'''

# ============================================================
# HANDLERS/COURSES.PY — with post-lesson quiz
# ============================================================
COURSES_PY = r'''
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    get_student, has_active_subscription, get_all_lessons,
    get_lesson, get_lesson_quiz, get_quiz_questions
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

router = Router()

COURSE_INFO = {
    "A1": {"name": "🔸 مبتدئ A1", "course_id": 1},
    "A2": {"name": "🟠 تحت المتوسط A2", "course_id": 2},
    "B1": {"name": "🟡 متوسط B1", "course_id": 3},
    "B2": {"name": "🟢 فوق المتوسط B2", "course_id": 4},
    "C1": {"name": "🔴 متقدم C1", "course_id": 5},
}

class QuizState(StatesGroup):
    answering = State()

@router.callback_query(F.data == "my_courses")
async def my_courses(callback: types.CallbackQuery):
    uid = callback.from_user.id
    student = get_student(uid)
    if not student:
        await callback.message.edit_text("⚠️ لم يتم تسجيلك بعد. استخدم /start أولاً.")
        await callback.answer(); return
    if not student["placement_done"]:
        await callback.message.edit_text("📋 *يجب إكمال اختبار تحديد المستوى أولاً*", parse_mode="Markdown")
        await callback.answer(); return
    if not has_active_subscription(uid):
        await callback.message.edit_text("🔒 *لا يوجد اشتراك نشط*\nيرجى الاشتراك للمتابعة.", parse_mode="Markdown")
        await callback.answer(); return
    level = student["level"] or "A1"
    cinfo = COURSE_INFO.get(level, COURSE_INFO["A1"])
    lessons = get_all_lessons(cinfo["course_id"])
    if not lessons:
        await callback.message.edit_text(f"📚 *{cinfo['name']}*\n\nℹ️ لا توجد دروس بعد.", parse_mode="Markdown")
        await callback.answer(); return
    kb = []
    for les in lessons:
        kb.append([InlineKeyboardButton(text=les["title"], callback_data=f"view_lesson_{les['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="student_menu")])
    await callback.message.edit_text(
        f"📚 *{cinfo['name']}*\nاختر الدرس:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("view_lesson_"))
async def view_lesson(callback: types.CallbackQuery):
    lesson_id = int(callback.data.split("_")[-1])
    les = get_lesson(lesson_id)
    if not les:
        await callback.answer("❌ الدرس غير موجود", show_alert=True); return
    # send media if exists
    mt, mfid = les.get("media_type"), les.get("media_file_id")
    if mt and mfid:
        send_map = {"photo": callback.message.answer_photo, "audio": callback.message.answer_audio,
                    "voice": callback.message.answer_voice, "video": callback.message.answer_video}
        sender = send_map.get(mt)
        if sender:
            try:
                await sender(mfid, caption=les["content"] or les["title"])
                await callback.message.delete()
            except Exception:
                pass  # fall through
            else:
                await callback.answer(); return
    # inline buttons: quiz + action + back
    inline = []
    quiz = get_lesson_quiz(lesson_id)
    if quiz:
        inline.append([InlineKeyboardButton(text="📝 اختبار الدرس", callback_data=f"start_quiz_{lesson_id}")])
    atype, alabel = les.get("action_type"), les.get("action_label")
    if atype and alabel:
        cb = f"speaking_{lesson_id}" if atype == "speaking" else f"writing_{lesson_id}"
        inline.append([InlineKeyboardButton(text=alabel, callback_data=cb)])
    inline.append([InlineKeyboardButton(text="🔙 دوراتي", callback_data="my_courses")])
    txt = les["content"] or les["title"]
    try:
        await callback.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=inline))
    except Exception:
        await callback.message.answer(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=inline))
        await callback.message.delete()
    await callback.answer()

# ─── QUIZ HANDLER ───
@router.callback_query(F.data.startswith("start_quiz_"))
async def start_quiz(callback: types.CallbackQuery, state: FSMContext):
    lesson_id = int(callback.data.split("_")[-1])
    quiz = get_lesson_quiz(lesson_id)
    if not quiz:
        await callback.answer("⚠️ لا يوجد اختبار لهذا الدرس", show_alert=True); return
    questions = get_quiz_questions(quiz['id'])
    if not questions:
        await callback.answer("⚠️ لا توجد أسئلة في هذا الاختبار", show_alert=True); return
    await state.update_data(quiz_id=quiz['id'], qs=questions, score=0, q_idx=0,
                            pass_score=quiz['pass_score'])
    await state.set_state(QuizState.answering)
    await send_quiz_q(callback.message, state, 0)

async def send_quiz_q(msg, state, idx):
    data = await state.get_data()
    qs = data['qs']
    if idx >= len(qs):
        await finish_quiz(msg, state); return
    q = qs[idx]
    opts = [q['option_a'], q['option_b'], q['option_c'], q['option_d']]
    btns = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{chr(0x2460+i)} {o}", callback_data=f"qz_{idx}_{i}")]
        for i, o in enumerate(opts)
    ])
    await state.update_data(q_idx=idx)
    await msg.edit_text(f"📝 *اختبار الدرس — سؤال {idx+1}/{len(qs)}*\n\n_{q['question']}_",
                        reply_markup=btns, parse_mode="Markdown")

@router.callback_query(QuizState.answering, F.data.startswith("qz_"))
async def handle_quiz(callback: types.CallbackQuery, state: FSMContext):
    _, idx_s, choice_s = callback.data.split("_")
    idx, choice = int(idx_s), int(choice_s)
    data = await state.get_data()
    qs = data['qs']
    correct = qs[idx]['correct_option']
    score = data.get('score', 0)
    if choice == correct:
        score += 1
    await state.update_data(score=score)
    await send_quiz_q(callback.message, state, idx + 1)
    await callback.answer()

async def finish_quiz(msg, state):
    data = await state.get_data()
    score = data['score']
    total = len(data['qs'])
    passed = (score / total * 100) >= data['pass_score']
    xp = score * 10 if passed else score * 3
    # save attempt
    from database import record_quiz_attempt, add_xp
    uid = msg.chat.id
    record_quiz_attempt(uid, data['quiz_id'], score, total, int(passed), xp)
    add_xp(uid, xp, 'lesson_quiz')
    status = "✅ اجتزت الاختبار!" if passed else "❌ لم تجتز، حاول مرة أخرى."
    await msg.edit_text(
        f"📊 *نتيجة الاختبار*\n\n{status}\n"
        f"نقاط: {score}/{total} ({score/total*100:.0f}%)\n⭐ XP: +{xp}",
        parse_mode="Markdown"
    )
'''

# ============================================================
# HANDLERS/ADMIN.PY — Extended: spelling mgmt + quiz mgmt + questions
# ============================================================
ADMIN_PY = r'''
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    get_stats, get_pending_payments, update_payment_status, get_payment, add_subscription,
    get_all_lessons, add_lesson, get_all_spelling_words, add_spelling_word, delete_spelling_word,
    get_all_placement_questions, add_placement_question, delete_placement_question,
    get_all_lesson_quizzes, delete_lesson_quiz, add_lesson_quiz, add_quiz_question,
    get_quiz_questions
)

router = Router()
ADMIN_IDS = {469136626}  # replace with real admin IDs

def is_admin(user_id):
    return user_id in ADMIN_IDS

class AddLesson(StatesGroup):
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_level = State()
    waiting_for_media = State()
    waiting_for_action = State()

class AddSpelling(StatesGroup):
    waiting_for_word = State()

class AddPlaceQ(StatesGroup):
    waiting_for_question = State()
    waiting_for_options = State()
    waiting_for_correct = State()
    waiting_for_level = State()

class AddQuiz(StatesGroup):
    waiting_for_lesson_id = State()
    waiting_for_title = State()
    waiting_for_pass = State()
    waiting_for_question = State()
    waiting_for_opts = State()
    waiting_for_correct = State()

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ غير مصرح")
        return
    stats = get_stats()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 المحتوى والدروس", callback_data="admin_content")],
        [InlineKeyboardButton(text="👥 المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton(text="💳 المدفوعات", callback_data="admin_payments")],
        [InlineKeyboardButton(text="✍️ إدارة الكلمات", callback_data="admin_spelling")],
        [InlineKeyboardButton(text="📝 إدارة أسئلة المستوى", callback_data="admin_placement")],
        [InlineKeyboardButton(text="🧪 إدارة الاختبارات", callback_data="admin_quizzes")],
    ])
    await message.answer(
        f"🛡️ *لوحة الأدمن*\n\n"
        f"👥 الطلاب: {stats['total_students']}\n"
        f"✅ النشطاء: {stats['active_subs']}\n"
        f"💳 معلقة: {stats['pending_payments']}",
        reply_markup=kb, parse_mode="Markdown"
    )

# ─── CONTENT ───
@router.callback_query(F.data == "admin_content")
async def admin_content(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ إضافة درس جديد", callback_data="add_lesson")],
        [InlineKeyboardButton(text="📋 قائمة الدروس", callback_data="list_lessons")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_back")],
    ])
    await callback.message.edit_text("📚 *قسم المحتوى*", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "add_lesson")
async def add_lesson_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddLesson.waiting_for_title)
    await callback.message.edit_text("📝 أرسل عنوان الدرس:")
    await callback.answer()

@router.message(AddLesson.waiting_for_title)
async def add_lesson_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddLesson.waiting_for_content)
    await message.answer("📄 أرسل محتوى الدرس:")

@router.message(AddLesson.waiting_for_content)
async def add_lesson_content(message: types.Message, state: FSMContext):
    await state.update_data(content=message.text)
    await state.set_state(AddLesson.waiting_for_level)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="A1 🔸", callback_data="lvl_A1"),
         InlineKeyboardButton(text="A2 🟠", callback_data="lvl_A2")],
        [InlineKeyboardButton(text="B1 🟡", callback_data="lvl_B1"),
         InlineKeyboardButton(text="B2 🟢", callback_data="lvl_B2")],
        [InlineKeyboardButton(text="C1 🔴", callback_data="lvl_C1")],
    ])
    await message.answer("🎯 اختر المستوى:", reply_markup=kb)

@router.callback_query(F.data.startswith("lvl_"))
async def add_lesson_level(callback: types.CallbackQuery, state: FSMContext):
    level = callback.data.split("_")[1]
    cinfo = {"A1":1,"A2":2,"B1":3,"B2":4,"C1":5}
    await state.update_data(level=level, course_id=cinfo.get(level,1))
    await state.set_state(AddLesson.waiting_for_media)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼️ صورة", callback_data="media_photo"),
         InlineKeyboardButton(text="🎵 صوت", callback_data="media_audio")],
        [InlineKeyboardButton(text="🎬 فيديو", callback_data="media_video"),
         InlineKeyboardButton(text="⏭️ تخطي", callback_data="media_skip")],
    ])
    await callback.message.edit_text("هل تريد إضافة وسائط؟", reply_markup=kb)
    await callback.answer()

@router.callback_query(AddLesson.waiting_for_media, F.data.startswith("media_"))
async def add_lesson_media(callback: types.CallbackQuery, state: FSMContext):
    mt = callback.data.split("_")[1]
    if mt == "skip":
        await state.update_data(media_type=None, media_file_id=None)
        await state.set_state(AddLesson.waiting_for_action)
        await _ask_action(callback.message)
    else:
        await state.update_data(media_type=mt)
        await callback.message.edit_text("📎 أرسل الملف الآن:")
    await callback.answer()

@router.message(AddLesson.waiting_for_media)
async def receive_media(message: types.Message, state: FSMContext):
    data = await state.get_data()
    mt = data.get('media_type')
    file_id = None
    if mt == 'photo' and message.photo:
        file_id = message.photo[-1].file_id
    elif mt in ('audio','voice') and message.audio:
        file_id = message.audio.file_id
    elif mt == 'video' and message.video:
        file_id = message.video.file_id
    if file_id:
        await state.update_data(media_file_id=file_id)
    await state.set_state(AddLesson.waiting_for_action)
    await _ask_action(message)

async def _ask_action(msg):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎤 تحدث", callback_data="act_speaking"),
         InlineKeyboardButton(text="✍️ تصحيح", callback_data="act_writing")],
        [InlineKeyboardButton(text="⏭️ بدون", callback_data="act_none")],
    ])
    await msg.answer("هل تريد إضافة زر تفاعلي؟", reply_markup=kb)

@router.callback_query(AddLesson.waiting_for_action, F.data.startswith("act_"))
async def add_lesson_action(callback: types.CallbackQuery, state: FSMContext):
    act = callback.data.split("_")[1]
    await state.update_data(action_type=act if act != 'none' else None,
                            action_label='🎤 تحدث' if act=='speaking' else '✍️ صحح كتابتي' if act=='writing' else None)
    data = await state.get_data()
    add_lesson(data['title'], data['content'], data['course_id'],
               media_type=data.get('media_type'), media_file_id=data.get('media_file_id'),
               action_type=data.get('action_type'), action_label=data.get('action_label'))
    await state.clear()
    await callback.message.edit_text("✅ تمت إضافة الدرس بنجاح")
    await callback.answer()

# ─── SPELLING MANAGEMENT ───
@router.callback_query(F.data == "admin_spelling")
async def admin_spelling(callback: types.CallbackQuery):
    words = get_all_spelling_words()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ إضافة كلمة", callback_data="add_spell")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_back")],
    ])
    await callback.message.edit_text(
        f"✍️ *إدارة الكلمات* ({len(words)} كلمة)",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "add_spell")
async def add_spell_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddSpelling.waiting_for_word)
    await callback.message.edit_text("أرسل الكلمة بهذا الشكل:\nword|definition|level|category|example", parse_mode="Markdown")
    await callback.answer()

@router.message(AddSpelling.waiting_for_word)
async def add_spell_save(message: types.Message, state: FSMContext):
    parts = message.text.split("|")
    word = parts[0].strip()
    definition = parts[1].strip() if len(parts)>1 else ''
    level = parts[2].strip() if len(parts)>2 else 'A1'
    category = parts[3].strip() if len(parts)>3 else ''
    example = parts[4].strip() if len(parts)>4 else ''
    add_spelling_word(word, definition, level, category, example)
    await state.clear()
    await message.answer(f"✅ أضيفت: *{word}*", parse_mode="Markdown")

# ─── PLACEMENT QUESTIONS MANAGEMENT ───
@router.callback_query(F.data == "admin_placement")
async def admin_placement(callback: types.CallbackQuery):
    qs = get_all_placement_questions()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ إضافة سؤال", callback_data="add_placeq")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_back")],
    ])
    await callback.message.edit_text(
        f"📝 *أسئلة تحديد المستوى* ({len(qs)} سؤال)",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "add_placeq")
async def add_placeq_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddPlaceQ.waiting_for_question)
    await callback.message.edit_text("أرسل السؤال + الخيارات:\nquestion|A|B|C|D|correct_index|level", parse_mode="Markdown")
    await callback.answer()

@router.message(AddPlaceQ.waiting_for_question)
async def add_placeq_save(message: types.Message, state: FSMContext):
    parts = message.text.split("|")
    question = parts[0].strip()
    opts = [parts[i].strip() for i in range(1,5)]
    correct = int(parts[5].strip()) if len(parts)>5 else 0
    level = parts[6].strip() if len(parts)>6 else 'A1'
    add_placement_question(question, opts, correct, level)
    await state.clear()
    await message.answer(f"✅ أضيف السؤال: {question[:40]}...")

# ─── QUIZZES MANAGEMENT ───
@router.callback_query(F.data == "admin_quizzes")
async def admin_quizzes(callback: types.CallbackQuery):
    quizzes = get_all_lesson_quizzes()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ إنشاء اختبار", callback_data="add_quiz")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_back")],
    ])
    await callback.message.edit_text(
        f"🧪 *الاختبارات* ({len(quizzes)} اختبار)",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "add_quiz")
async def add_quiz_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddQuiz.waiting_for_lesson_id)
    await callback.message.edit_text("أرسل lesson_id|title|pass_score:\nمثال: 1|Quiz 1|60", parse_mode="Markdown")
    await callback.answer()

@router.message(AddQuiz.waiting_for_lesson_id)
async def add_quiz_info(message: types.Message, state: FSMContext):
    parts = message.text.split("|")
    lesson_id = int(parts[0].strip())
    title = parts[1].strip() if len(parts)>1 else 'Quiz'
    pass_score = int(parts[2].strip()) if len(parts)>2 else 60
    quiz_id = add_lesson_quiz(lesson_id, title, pass_score)
    await state.update_data(quiz_id=quiz_id, lesson_id=lesson_id)
    await state.set_state(AddQuiz.waiting_for_question)
    await message.answer(
        f"✅ تم إنشاء الاختبار (ID={quiz_id})\nالآن أرسل الأسئلة:\n"
        f"question|A|B|C|D|correct_index\nأرسل /done للانتهاء"
    )

@router.message(AddQuiz.waiting_for_question)
async def add_quiz_q(message: types.Message, state: FSMContext):
    if message.text.strip() == '/done':
        data = await state.get_data()
        await state.clear()
        await message.answer(f"✅ انتهى اختبار الدرس {data.get('lesson_id')}")
        return
    parts = message.text.split("|")
    question = parts[0].strip()
    opts = [parts[i].strip() for i in range(1,5)]
    correct = int(parts[5].strip()) if len(parts)>5 else 0
    data = await state.get_data()
    add_quiz_question(data['quiz_id'], question, opts, correct)
    await message.answer(f"✅ أضيف السؤال. أرسل التالي أو /done")

# ─── PAYMENTS ───
@router.callback_query(F.data == "admin_payments")
async def admin_payments(callback: types.CallbackQuery):
    payments = get_pending_payments()
    if not payments:
        await callback.message.edit_text("💳 لا توجد مدفوعات معلقة")
        await callback.answer(); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💰 {p['user_id']} - {p['plan_name']}",
                              callback_data=f"approve_{p['id']}")]
        for p in payments
    ])
    await callback.message.edit_text("💳 *مدفوعات معلقة*", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    pid = int(callback.data.split("_")[1])
    payment = get_payment(pid)
    if not payment:
        await callback.answer("❌ غير موجود", show_alert=True); return
    update_payment_status(pid, 'approved')
    add_subscription(payment['user_id'], payment['plan_name'], 30)
    await callback.message.edit_text("✅ تم التفعيل وإنشاء الاشتراك")
    await callback.answer()

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    await admin_panel(callback.message)
    await callback.answer()
'''

# ============================================================
# WRITE ALL FILES
# ============================================================
files = {
    'database.py': DATABASE_PY,
    'handlers/__init__.py': INIT_PY,
    'handlers/placement_test.py': PLACEMENT_TEST_PY,
    'handlers/spelling.py': SPELLING_PY,
    'handlers/courses.py': COURSES_PY,
    'handlers/admin.py': ADMIN_PY,
}

for rel_path, content in files.items():
    full_path = os.path.join(BASE, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')
    print(f'✅ Written: {rel_path}')

print('\n========== ALL FILES BUILT ==========')
print('Now run: cd C:\\yamen_academy && python database.py  (to init DB)')
print('Then:    python main.py                 (to start bot)')
