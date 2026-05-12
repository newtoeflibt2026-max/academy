import sqlite3, os, logging
logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "academy.db")

def init_db():
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
    logger.info("Database initialized successfully")

def get_db_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=60000;")
    conn.execute("PRAGMA cache_size=-8000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    return conn
