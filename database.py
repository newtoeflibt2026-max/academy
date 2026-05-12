import sqlite3, os, logging
logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "academy.db")

def init_db():
    """Create database directory and tables if not exist."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            level TEXT DEFAULT 'A1',
            xp INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            last_active TEXT,
            joined_at TEXT DEFAULT (datetime('now','localtime')),
            is_banned INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            level TEXT,
            image_url TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            order_index INTEGER DEFAULT 0,
            type TEXT DEFAULT 'reading',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER,
            question_text TEXT NOT NULL,
            options TEXT,
            correct_answer TEXT,
            type TEXT DEFAULT 'multiple_choice',
            FOREIGN KEY (lesson_id) REFERENCES lessons(id)
        );
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            lesson_id INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            FOREIGN KEY (student_id) REFERENCES students(telegram_id),
            FOREIGN KEY (lesson_id) REFERENCES lessons(id)
        );
        CREATE TABLE IF NOT EXISTS spelling_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            difficulty TEXT DEFAULT 'easy',
            course_id INTEGER,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
        CREATE TABLE IF NOT EXISTS daily_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_date TEXT NOT NULL,
            challenge_data TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS writing_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            prompt TEXT,
            submission TEXT,
            feedback TEXT,
            score INTEGER,
            submitted_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (student_id) REFERENCES students(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS speaking_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            prompt TEXT,
            audio_url TEXT,
            feedback TEXT,
            score INTEGER,
            submitted_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (student_id) REFERENCES students(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            amount REAL,
            currency TEXT DEFAULT 'USD',
            status TEXT DEFAULT 'pending',
            payment_date TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (student_id) REFERENCES students(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

def get_db_connection():
    """Get database connection with WAL mode, timeout, and normal sync."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=60000;")
    conn.execute("PRAGMA cache_size=-8000;")
    return conn
