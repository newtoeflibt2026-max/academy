# database.py - Yamen Academy LMS (with safe_migrate)
import sqlite3, logging, os
from datetime import datetime, timedelta

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "academy.db")

def get_db_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute("PRAGMA cache_size=-8000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.row_factory = sqlite3.Row
    return conn

def safe_migrate():
    """Add missing columns safely — never fails if column exists."""
    conn = get_db_connection()
    c = conn.cursor()

    # Helper: check if column exists via PRAGMA table_info
    def column_exists(table, column):
        cols = [row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()]
        return column in cols

    def add_column(table, column, col_type, default="1"):
        if not column_exists(table, column):
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}")
                logging.info(f"✅ Added column {table}.{column} ({col_type}) DEFAULT {default}")
            except Exception as e:
                logging.warning(f"⚠️ Skipped {table}.{column}: {e}")
        else:
            logging.info(f"⏭️ Column {table}.{column} already exists.")

    # ========== ALL MISSING COLUMNS ==========
    add_column("courses",     "is_active",      "INTEGER", "1")
    add_column("courses",     "skill_type",     "TEXT",    "'speaking'")
    add_column("courses",     "time_limit",     "INTEGER", "45")
    add_column("courses",     "target_score",   "INTEGER", "59")
    add_column("courses",     "template_module","TEXT",    "''")
    add_column("courses",     "is_vip",         "INTEGER", "0")

    add_column("lessons",     "is_active",      "INTEGER", "1")
    add_column("lessons",     "skill_type",     "TEXT",    "'speaking'")

    add_column("students",    "is_active",      "INTEGER", "1")
    add_column("students",    "last_active",    "TIMESTAMP", "CURRENT_TIMESTAMP")
    add_column("students",    "xp",             "INTEGER", "0")
    add_column("students",    "level",          "INTEGER", "1")

    add_column("questions",   "skill_type",     "TEXT",    "'speaking'")
    add_column("questions",   "is_active",      "INTEGER", "1")

    add_column("progress",    "is_active",      "INTEGER", "1")

    add_column("spelling_words","is_active","INTEGER","1")
    add_column("daily_challenges","is_active","INTEGER","1")
    add_column("writing_submissions","is_active","INTEGER","1")
    add_column("speaking_submissions","is_active","INTEGER","1")

    add_column("vault_items", "is_active",      "INTEGER", "1")
    add_column("vault_items", "category",       "TEXT",    "'speaking'")

    add_column("error_bank",  "is_active",      "INTEGER", "1")

    conn.close()
    logging.info("✅ safe_migrate() completed — all columns verified.")

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
            is_active INTEGER DEFAULT 1,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, level TEXT DEFAULT 'beginner',
            price REAL DEFAULT 0, duration_days INTEGER DEFAULT 30,
            is_vip INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1,
            skill_type TEXT DEFAULT 'speaking', time_limit INTEGER DEFAULT 45,
            target_score INTEGER DEFAULT 59, template_module TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER,
            title TEXT, content TEXT, order_num INTEGER,
            is_active INTEGER DEFAULT 1, skill_type TEXT DEFAULT 'speaking',
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, lesson_id INTEGER,
            question_text TEXT, correct_answer TEXT,
            skill_type TEXT DEFAULT 'speaking', is_active INTEGER DEFAULT 1,
            FOREIGN KEY (lesson_id) REFERENCES lessons(id)
        );
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, course_id INTEGER, lesson_id INTEGER,
            completed INTEGER DEFAULT 0, score REAL DEFAULT 0,
            attempts INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1,
            last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS error_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, question_id INTEGER,
            course_id INTEGER, skill_type TEXT,
            wrong_answer TEXT, correct_streak INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            next_review_date TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS daily_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, skill_type TEXT, challenge_date DATE,
            completed INTEGER DEFAULT 0, score INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, action TEXT, details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS vault_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, content TEXT, category TEXT DEFAULT 'speaking',
            unlock_level INTEGER DEFAULT 1, is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            plan_name TEXT, amount REAL, status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            plan_name TEXT, days INTEGER,
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, end_date TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS spelling_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT,
            difficulty INTEGER DEFAULT 1, is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS writing_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            prompt TEXT, submission TEXT, score REAL, feedback TEXT,
            is_active INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS speaking_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            prompt TEXT, audio_path TEXT, score REAL, feedback TEXT,
            is_active INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.close()
    logging.info("✅ Database tables created.")

    # Now add any missing columns to EXISTING tables
    safe_migrate()

# ============================
# ERROR BANK LOGIC
# ============================
def add_to_error_bank(user_id, question_id, course_id, skill_type, wrong_answer):
    conn = get_db_connection()
    try:
        next_review = datetime.now() + timedelta(days=2)
        conn.execute("INSERT INTO error_bank (user_id,question_id,course_id,skill_type,wrong_answer,next_review_date) VALUES (?,?,?,?,?,?)",
                     (user_id, question_id, course_id, skill_type, wrong_answer, next_review.isoformat()))
        conn.commit()
    finally: conn.close()

def get_due_reviews(user_id):
    conn = get_db_connection()
    try:
        now = datetime.now().isoformat()
        rows = conn.execute("SELECT eb.*, q.question_text, q.correct_answer FROM error_bank eb JOIN questions q ON eb.question_id=q.id WHERE eb.user_id=? AND eb.next_review_date<=?",
                            (user_id, now)).fetchall()
        return [dict(r) for r in rows]
    finally: conn.close()

def record_correct_review(user_id, error_bank_id):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT correct_streak FROM error_bank WHERE id=?",(error_bank_id,)).fetchone()
        if row:
            streak = row[0] + 1
            if streak >= 2:
                conn.execute("DELETE FROM error_bank WHERE id=?",(error_bank_id,))
            else:
                next_review = datetime.now() + timedelta(days=2)
                conn.execute("UPDATE error_bank SET correct_streak=?, next_review_date=? WHERE id=?",
                             (streak, next_review.isoformat(), error_bank_id))
        conn.commit()
    finally: conn.close()

# ============================
# STUDENT ACTIVITY
# ============================
def log_activity(user_id, action, details=""):
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO activity_log (user_id,action,details) VALUES (?,?,?)",(user_id,action,details))
        conn.execute("UPDATE students SET last_active=CURRENT_TIMESTAMP WHERE user_id=?",(user_id,))
        conn.commit()
    finally: conn.close()

def get_absent_students(hours=48):
    conn = get_db_connection()
    try:
        cutoff = (datetime.now()-timedelta(hours=hours)).isoformat()
        return [dict(r) for r in conn.execute("SELECT user_id,first_name,last_active FROM students WHERE last_active<? AND is_active=1",(cutoff,)).fetchall()]
    finally: conn.close()

# ============================
# LEADERBOARD
# ============================
def get_leaderboard(limit=5):
    conn = get_db_connection()
    try:
        return [dict(r) for r in conn.execute("SELECT user_id,first_name,xp,level FROM students ORDER BY xp DESC LIMIT ?",(limit,)).fetchall()]
    finally: conn.close()

def add_xp(user_id, amount):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE students SET xp=xp+? WHERE user_id=?",(amount,user_id)); conn.commit()
    finally: conn.close()

# ============================
# SETTINGS
# ============================
def get_admin_setting(key, default=""):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone()
        return row[0] if row else default
    finally: conn.close()

def set_admin_setting(key, value):
    conn = get_db_connection()
    try:
        conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)",(key,str(value)))
        conn.commit()
    finally: conn.close()

# ============================
# STATS
# ============================
def get_stats():
    conn = get_db_connection()
    try:
        s = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        c = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
        a = conn.execute("SELECT COUNT(*) FROM students WHERE last_active>=date('now')").fetchone()[0]
        return {"students":s,"courses":c,"active_today":a}
    finally: conn.close()

def get_all_students():
    conn = get_db_connection()
    try:
        return conn.execute("SELECT * FROM students ORDER BY xp DESC").fetchall()
    finally: conn.close()

def toggle_student_active(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT is_active FROM students WHERE user_id=?",(user_id,)).fetchone()
        if row: conn.execute("UPDATE students SET is_active=? WHERE user_id=?",(0 if row[0] else 1, user_id))
        conn.commit()
    finally: conn.close()

def get_pending_payments():
    conn = get_db_connection()
    try:
        return conn.execute("SELECT * FROM payments WHERE status='pending' ORDER BY created_at DESC").fetchall()
    finally: conn.close()

def update_payment_status(pid, status):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE payments SET status=? WHERE id=?",(status,pid)); conn.commit()
    finally: conn.close()

def add_subscription(user_id, plan_name, days):
    conn = get_db_connection()
    try:
        end = (datetime.now()+timedelta(days=days)).isoformat()
        conn.execute("INSERT INTO subscriptions (user_id,plan_name,days,end_date) VALUES (?,?,?,?)",(user_id,plan_name,days,end))
        conn.commit()
    finally: conn.close()

def add_payment(user_id, plan_name, amount):
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO payments (user_id,plan_name,amount) VALUES (?,?,?)",(user_id,plan_name,amount))
        conn.commit()
    finally: conn.close()

def upsert_student(user_id, username="", first_name=""):
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO students (user_id,username,first_name) VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name,last_active=CURRENT_TIMESTAMP",
                     (user_id,username,first_name))
        conn.commit()
    finally: conn.close()

def update_user_role(telegram_id, role):
    conn = get_db_connection()
    try:
        conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)",(f"role_{telegram_id}",role))
        conn.commit()
    finally: conn.close()

def get_user(telegram_id):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key=?",(f"role_{telegram_id}",)).fetchone()
        return {"role":row[0]} if row else {"role":"student"}
    finally: conn.close()

get_conn = get_db_connection

if __name__ == "__main__":
    init_db()
    print("✅ Database initialized + migrated successfully.")
