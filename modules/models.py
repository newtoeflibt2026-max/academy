import sqlite3, os, time
from config import DATABASE_PATH, ADMIN_IDS

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def query_db(query, args=(), one=False):
    conn = get_db()
    cur = conn.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    conn = get_db()
    cur = conn.execute(query, args)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def init_db():
    conn = get_db()
    c = conn.cursor()
    # ---------- 17 tables ----------
    c.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            telegram_id   INTEGER PRIMARY KEY,
            name          TEXT DEFAULT '',
            username      TEXT DEFAULT '',
            xp            INTEGER DEFAULT 0,
            level         INTEGER DEFAULT 1,
            streak        INTEGER DEFAULT 0,
            course_id     INTEGER,
            is_active     INTEGER DEFAULT 1,
            registered_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS courses (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT NOT NULL,
            description   TEXT,
            is_active     INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS placement_questions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            option_a      TEXT,
            option_b      TEXT,
            option_c      TEXT,
            option_d      TEXT,
            correct_answer TEXT NOT NULL,
            difficulty    TEXT DEFAULT 'medium',
            is_active     INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS placement_results (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            score         INTEGER,
            total         INTEGER,
            level         TEXT,
            completed_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (student_id) REFERENCES students(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS billing_plans (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            price_monthly REAL DEFAULT 0,
            features      TEXT,
            is_active     INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            plan_id       INTEGER NOT NULL,
            status        TEXT DEFAULT 'active',
            started_at    TEXT DEFAULT (datetime('now')),
            expires_at    TEXT,
            FOREIGN KEY (student_id) REFERENCES students(telegram_id),
            FOREIGN KEY (plan_id) REFERENCES billing_plans(id)
        );
        CREATE TABLE IF NOT EXISTS daily_skills (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT NOT NULL,
            skill_type    TEXT DEFAULT 'text',
            task_type     TEXT DEFAULT 'mcq',
            icon          TEXT DEFAULT 'fa-star',
            time_limit    INTEGER DEFAULT 45,
            telegram_link TEXT,
            is_active     INTEGER DEFAULT 1,
            sort_order    INTEGER DEFAULT 0,
            created_at    TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS library_items (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT NOT NULL,
            item_type     TEXT DEFAULT 'pdf',
            file_path     TEXT,
            external_url  TEXT,
            course_id     INTEGER,
            is_active     INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS questions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id      INTEGER,
            question_text TEXT NOT NULL,
            option_a      TEXT,
            option_b      TEXT,
            option_c      TEXT,
            option_d      TEXT,
            correct_answer TEXT NOT NULL,
            is_active     INTEGER DEFAULT 1,
            FOREIGN KEY (skill_id) REFERENCES daily_skills(id)
        );
        CREATE TABLE IF NOT EXISTS error_bank (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            question_id   INTEGER,
            skill_type    TEXT,
            is_corrected  INTEGER DEFAULT 0,
            created_at    TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (student_id) REFERENCES students(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS exam_sessions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            exam_type     TEXT DEFAULT 'full',
            score         INTEGER,
            total         INTEGER,
            status        TEXT DEFAULT 'in_progress',
            started_at    TEXT DEFAULT (datetime('now')),
            completed_at  TEXT,
            FOREIGN KEY (student_id) REFERENCES students(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS audio_submissions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            skill_id      INTEGER,
            file_path     TEXT,
            transcript    TEXT,
            ai_score      REAL,
            ai_feedback   TEXT,
            submitted_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (student_id) REFERENCES students(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS writing_submissions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            skill_id      INTEGER,
            content       TEXT,
            ai_score      REAL,
            ai_feedback   TEXT,
            submitted_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (student_id) REFERENCES students(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS ai_config (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key    TEXT UNIQUE NOT NULL,
            config_value  TEXT
        );
        CREATE TABLE IF NOT EXISTS activity_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER,
            action        TEXT,
            details       TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS student_skills (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            skill_id      INTEGER NOT NULL,
            progress      REAL DEFAULT 0,
            FOREIGN KEY (student_id) REFERENCES students(telegram_id),
            FOREIGN KEY (skill_id) REFERENCES daily_skills(id)
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            title         TEXT,
            message       TEXT,
            is_read       INTEGER DEFAULT 0,
            created_at    TEXT DEFAULT (datetime('now'))
        );
    """)
    # --- Insert defaults if empty ---
    existing = c.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    if existing == 0:
        c.execute("INSERT INTO courses (title, description) VALUES (?,?)",
            ("International TOEFL Course", "Complete TOEFL preparation course"))
    existing = c.execute("SELECT COUNT(*) FROM billing_plans").fetchone()[0]
    if existing == 0:
        c.executescript("""
            INSERT INTO billing_plans (name, price_monthly, features) VALUES ('Free', 0, 'Limited skills,Basic library');
            INSERT INTO billing_plans (name, price_monthly, features) VALUES ('Silver', 9.99, 'All skills,Weekly AI review');
            INSERT INTO billing_plans (name, price_monthly, features) VALUES ('Gold', 19.99, 'Daily AI review,Live sessions');
            INSERT INTO billing_plans (name, price_monthly, features) VALUES ('Diamond', 49.99, 'Personal trainer,Priority support');
        """)
    existing = c.execute("SELECT COUNT(*) FROM ai_config").fetchone()[0]
    if existing == 0:
        c.executescript("""
            INSERT INTO ai_config (config_key, config_value) VALUES ('min_speaking_score', '2.5');
            INSERT INTO ai_config (config_key, config_value) VALUES ('min_writing_score', '3.0');
            INSERT INTO ai_config (config_key, config_value) VALUES ('accent_tolerance', 'medium');
            INSERT INTO ai_config (config_key, config_value) VALUES ('grammar_weight', '0.6');
            INSERT INTO ai_config (config_key, config_value) VALUES ('fluency_weight', '0.4');
            INSERT INTO ai_config (config_key, config_value) VALUES ('max_recording_seconds', '120');
        """)
    existing = c.execute("SELECT COUNT(*) FROM placement_questions").fetchone()[0]
    if existing == 0:
        c.executescript("""
            INSERT INTO placement_questions (question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty)
            VALUES ('What is the synonym of "happy"?', 'Sad', 'Angry', 'Joyful', 'Tired', 'C', 'easy');
            INSERT INTO placement_questions (question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty)
            VALUES ('Choose the correct sentence:', 'He go to school', 'He goes to school', 'He going to school', 'He gone to school', 'B', 'easy');
            INSERT INTO placement_questions (question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty)
            VALUES ('"She ___ a book every night." Fill in the blank:', 'read', 'reads', 'reading', 'is read', 'B', 'medium');
            INSERT INTO placement_questions (question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty)
            VALUES ('What does "ubiquitous" mean?', 'Rare', 'Everywhere', 'Underground', 'Unique', 'B', 'medium');
            INSERT INTO placement_questions (question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty)
            VALUES ('Which word is a noun?', 'Quickly', 'Beautiful', 'Happiness', 'Running', 'C', 'easy');
            INSERT INTO placement_questions (question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty)
            VALUES ('"If I ___ you, I would study more."', 'am', 'was', 'were', 'be', 'C', 'hard');
            INSERT INTO placement_questions (question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty)
            VALUES ('The study of word origins is called:', 'Phonetics', 'Etymology', 'Syntax', 'Morphology', 'B', 'hard');
            INSERT INTO placement_questions (question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty)
            VALUES ('"Neither the teacher nor the students ___ happy."', 'is', 'are', 'was', 'be', 'B', 'medium');
            INSERT INTO placement_questions (question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty)
            VALUES ('What is the past participle of "swim"?', 'Swam', 'Swum', 'Swimmed', 'Swimming', 'B', 'easy');
            INSERT INTO placement_questions (question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty)
            VALUES ('"I have been studying ___ three hours."', 'since', 'for', 'during', 'while', 'B', 'medium');
        """)
    # Ensure admin students exist
    for aid in ADMIN_IDS:
        c.execute("INSERT OR IGNORE INTO students (telegram_id, name, username, xp, level) VALUES (?,?,?,?,?)",
            (aid, f"Admin {aid}", f"admin_{aid}", 9999, 99))
    conn.commit()
    conn.close()
    print("[DB] init_db() — all 17 tables ready + defaults inserted.")

# Run init
init_db()
