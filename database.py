import sqlite3, os, logging
logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "academy.db")

_initialized = False

def init_db():
    global _initialized
    if _initialized:
        return
    os.makedirs(DB_DIR, exist_ok=True)
    conn = get_db_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE, username TEXT, first_name TEXT, last_name TEXT, level TEXT DEFAULT 'A1', xp INTEGER DEFAULT 0, streak INTEGER DEFAULT 0, last_active TEXT, joined_at TEXT DEFAULT (datetime('now','localtime')), is_banned INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, level TEXT, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS lessons (id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, title TEXT, content TEXT, order_index INTEGER DEFAULT 0, type TEXT DEFAULT 'reading');
        CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY AUTOINCREMENT, lesson_id INTEGER, question_text TEXT, options TEXT, correct_answer TEXT, type TEXT DEFAULT 'multiple_choice');
        CREATE TABLE IF NOT EXISTS progress (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, lesson_id INTEGER, score INTEGER DEFAULT 0, completed INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS spelling_words (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT, difficulty TEXT DEFAULT 'easy');
        CREATE TABLE IF NOT EXISTS daily_challenges (id INTEGER PRIMARY KEY AUTOINCREMENT, challenge_date TEXT, challenge_data TEXT);
        CREATE TABLE IF NOT EXISTS writing_submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, prompt TEXT, submission TEXT, feedback TEXT, score INTEGER);
        CREATE TABLE IF NOT EXISTS speaking_submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, prompt TEXT, audio_url TEXT, feedback TEXT, score INTEGER);
        CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, amount REAL, status TEXT DEFAULT 'pending');
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
    """)
    conn.close()
    _initialized = True
    logger.info("Database initialized")

def get_db_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute("PRAGMA cache_size=-8000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    return conn

# ====================== صلاحيات المستخدمين ======================

def update_user_role(telegram_id, role):
    """تحديث صلاحية المستخدم (admin/student)"""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (f"role_{telegram_id}", role))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"update_user_role error: {e}")
        return False
    finally:
        conn.close()

def get_user(telegram_id):
    """استعلام عن معلومات المستخدم"""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = ?", (f"role_{telegram_id}",))
        row = c.fetchone()
        return {"role": row[0]} if row else {"role": "student"}
    except:
        return {"role": "student"}
    finally:
        conn.close()
