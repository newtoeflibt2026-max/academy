import os, sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "data", "yamen_academy.db")

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # ═══ الجداول الأساسية ═══
    c.executescript('''
        CREATE TABLE IF NOT EXISTS students (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT, first_name TEXT, last_name TEXT,
            xp INTEGER DEFAULT 0, level INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1,
            last_active TEXT, created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, skill_type TEXT,
            time_limit INTEGER DEFAULT 45, target_score INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1, icon TEXT DEFAULT '📚',
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, type TEXT DEFAULT 'video',
            url TEXT NOT NULL, course_id INTEGER DEFAULT 1,
            skill_type TEXT DEFAULT 'reading',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, question_text TEXT,
            skill_type TEXT NOT NULL, options TEXT,
            correct_answer TEXT, points INTEGER DEFAULT 10,
            time_limit INTEGER DEFAULT 45,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS error_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            skill_type TEXT, correct_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, question_id)
        );
        
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_type TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            total_time INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, skill_type)
        );

        -- ═══ جداول التوفل الجديدة ═══
        CREATE TABLE IF NOT EXISTS daily_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, skill_type TEXT NOT NULL,
            icon TEXT DEFAULT '📝', time_limit INTEGER DEFAULT 45,
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS skill_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id INTEGER REFERENCES daily_skills(id),
            question_text TEXT NOT NULL,
            options TEXT, correct_answer TEXT,
            audio_url TEXT, image_url TEXT,
            is_active INTEGER DEFAULT 1
        );
        
        CREATE TABLE IF NOT EXISTS library_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, type TEXT NOT NULL,
            url TEXT NOT NULL, telegram_link TEXT,
            icon TEXT DEFAULT '📄', category TEXT DEFAULT 'general',
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS exam_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, section TEXT NOT NULL,
            total_questions INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0, xp_earned INTEGER DEFAULT 0,
            completed_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS speaking_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, question_id INTEGER,
            audio_url TEXT, transcript TEXT,
            ai_score REAL, ai_feedback TEXT,
            submitted_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS writing_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, question_id INTEGER,
            essay_text TEXT, ai_score REAL, ai_feedback TEXT,
            word_count INTEGER DEFAULT 0,
            submitted_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS ai_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT,
            description TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        );
    ''')
    
    # إعدادات AI الافتراضية
    c.execute("INSERT OR IGNORE INTO ai_config (config_key, config_value, description) VALUES ('min_speaking_score', '2.5', 'الحد الأدنى لتقييم المحادثة')")
    c.execute("INSERT OR IGNORE INTO ai_config (config_key, config_value, description) VALUES ('min_writing_score', '3.0', 'الحد الأدنى لتقييم الكتابة')")
    c.execute("INSERT OR IGNORE INTO ai_config (config_key, config_value, description) VALUES ('accent_tolerance', 'medium', 'تسامح اللكنة (low/medium/high)')")
    c.execute("INSERT OR IGNORE INTO ai_config (config_key, config_value, description) VALUES ('grammar_weight', '0.6', 'وزن القواعد في التقييم')")
    c.execute("INSERT OR IGNORE INTO ai_config (config_key, config_value, description) VALUES ('fluency_weight', '0.4', 'وزن الطلاقة في التقييم')")
    
    conn.commit()
    conn.close()
    print("✅ Database initialized — TOEFL-ready schema")

if __name__ == "__main__":
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    init_db()
