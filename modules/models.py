"""
models.py — تعريف جميع جداول قاعدة البيانات (Skills, Lessons, Users)
هذا الملف مسؤول فقط عن الـ Schema، لا يحوي منطق أعمال.
"""
import os, sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "data", "yamen_academy.db")

def get_db():
    """يعيد اتصال SQLite آمن مع row_factory"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    """إنشاء / تحديث جميع الجداول"""
    conn = get_db()
    c = conn.cursor()

    c.executescript('''
        -- ═══ المستخدمون ═══
        CREATE TABLE IF NOT EXISTS students (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT, first_name TEXT, last_name TEXT,
            xp INTEGER DEFAULT 0, level INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1,
            last_active DATETIME, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ المهارات اليومية — حرة بالكامل ═══
        CREATE TABLE IF NOT EXISTS daily_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            skill_type TEXT NOT NULL,
            task_type TEXT DEFAULT 'text',
            icon TEXT DEFAULT '📝',
            time_limit INTEGER DEFAULT 45,
            target_score REAL DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            telegram_link TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ مواد المكتبة ═══
        CREATE TABLE IF NOT EXISTS library_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            item_type TEXT DEFAULT 'pdf',
            url TEXT, telegram_link TEXT,
            icon TEXT DEFAULT '📄',
            category TEXT DEFAULT 'general',
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ الأسئلة ═══
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id INTEGER REFERENCES daily_skills(id) ON DELETE SET NULL,
            title TEXT, question_text TEXT NOT NULL,
            skill_type TEXT NOT NULL,
            options TEXT, correct_answer TEXT,
            audio_url TEXT, image_url TEXT,
            points INTEGER DEFAULT 10,
            time_limit INTEGER DEFAULT 45,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ بنك الأخطاء ═══
        CREATE TABLE IF NOT EXISTS error_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            skill_type TEXT,
            correct_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id)
        );

        -- ═══ جلسات الامتحان ═══
        CREATE TABLE IF NOT EXISTS exam_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            section TEXT NOT NULL,
            total_questions INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            xp_earned INTEGER DEFAULT 0,
            completed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ التسجيلات الصوتية ═══
        CREATE TABLE IF NOT EXISTS audio_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_id INTEGER,
            filename TEXT NOT NULL,
            transcription TEXT,
            ai_score REAL,
            ai_feedback TEXT,
            duration_seconds REAL DEFAULT 0,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ الإجابات الكتابية ═══
        CREATE TABLE IF NOT EXISTS writing_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_id INTEGER,
            essay_text TEXT NOT NULL,
            ai_score REAL,
            ai_feedback TEXT,
            word_count INTEGER DEFAULT 0,
            grammar_issues INTEGER DEFAULT 0,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ إعدادات AI ═══
        CREATE TABLE IF NOT EXISTS ai_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT,
            description TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ نشاط المستخدم ═══
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            xp_change INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # ═══ القيم الافتراضية ═══
    defaults = [
        ("min_speaking_score",   "2.5", "الحد الأدنى للمحادثة"),
        ("min_writing_score",    "3.0", "الحد الأدنى للكتابة"),
        ("accent_tolerance",     "medium", "تسامح اللكنة"),
        ("grammar_weight",       "0.6", "وزن القواعد"),
        ("fluency_weight",       "0.4", "وزن الطلاقة"),
        ("max_recording_seconds","120", "الحد الأقصى للتسجيل"),
    ]
    for key, val, desc in defaults:
        c.execute("INSERT OR IGNORE INTO ai_config (config_key, config_value, description) VALUES (?,?,?)",
                  (key, val, desc))

    conn.commit()
    conn.close()
    print("✅ models.py — 10 جداول مُهيأة")

# ═══ دوال مساعدة ═══
def query_db(query, args=(), one=False):
    conn = get_db()
    try:
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        conn.commit()
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(f"❌ models.query_db: {e}")
        return None
    finally:
        conn.close()

def execute_db(query, args=()):
    conn = get_db()
    try:
        conn.execute(query, args)
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ models.execute_db: {e}")
        return False
    finally:
        conn.close()
