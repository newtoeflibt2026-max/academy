import os

base = r'C:\yamen_academy'

# ==================== database.py ====================
database_py = '''import sqlite3, os, threading
from config import settings

_local = threading.local()
DB_PATH = getattr(settings, 'DB_PATH', 'data/academy.db')

def get_conn():
    if not hasattr(_local, 'conn') or _local.conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
        _local.conn.row_factory = sqlite3.Row
    return _local.conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            user_id INTEGER PRIMARY KEY, full_name TEXT, username TEXT DEFAULT '',
            level TEXT DEFAULT '', placement_done INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1, xp INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, level TEXT,
            price REAL, duration_days INTEGER, is_vip INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, title TEXT,
            content TEXT, properties TEXT DEFAULT '', order_num INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            media_type TEXT DEFAULT '', media_file_id TEXT DEFAULT '',
            action_type TEXT DEFAULT '', action_label TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan_name TEXT,
            course_id INTEGER,
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, end_date TIMESTAMP,
            is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan_name TEXT,
            amount REAL, status TEXT DEFAULT 'pending', receipt_file_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS admin_settings (
            key TEXT PRIMARY KEY, value TEXT
        );
        CREATE TABLE IF NOT EXISTS xp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
            reason TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS daily_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, options TEXT,
            correct_idx INTEGER, sent_at TIMESTAMP, is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS challenge_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, challenge_id INTEGER, user_id INTEGER,
            answer_idx INTEGER, is_correct INTEGER, response_time_sec REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS vault_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT,
            unlock_level TEXT, is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, feature TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

def _safe_fetchone(query, params=()):
    try: return get_conn().execute(query, params).fetchone()
    except Exception as e:
        try: get_conn().execute("INSERT OR IGNORE INTO errors_log (error,ctx) VALUES (?,?)", (str(e), query))
        except: pass
        return None

def _safe_fetchall(query, params=()):
    try: return get_conn().execute(query, params).fetchall()
    except Exception as e:
        try: get_conn().execute("INSERT OR IGNORE INTO errors_log (error,ctx) VALUES (?,?)", (str(e), query))
        except: pass
        return []

def _safe_exec(query, params=()):
    try:
        get_conn().execute(query, params)
        get_conn().commit()
    except Exception as e:
        try: get_conn().execute("INSERT OR IGNORE INTO errors_log (error,ctx) VALUES (?,?)", (str(e), query))
        except: pass
        raise e

# ---- Student ----
def add_student(user_id, full_name, username=''):
    _safe_exec("INSERT OR IGNORE INTO students (user_id, full_name, username) VALUES (?,?,?)",
               (user_id, full_name, username))

def upsert_student(user_id, full_name, username=''):
    add_student(user_id, full_name, username)

def get_student(user_id):
    return _safe_fetchone("SELECT * FROM students WHERE user_id=?", (user_id,))

def get_all_students():
    return _safe_fetchall("SELECT * FROM students ORDER BY created_at DESC")

def set_placement_done(user_id, level):
    _safe_exec("UPDATE students SET placement_done=1, level=? WHERE user_id=?", (level, user_id))

def toggle_student_active(user_id):
    row = _safe_fetchone("SELECT is_active FROM students WHERE user_id=?", (user_id,))
    if row: _safe_exec("UPDATE students SET is_active=? WHERE user_id=?", (0 if row["is_active"] else 1, user_id))

def add_xp(user_id, amount, reason=''):
    _safe_exec("UPDATE students SET xp = xp + ? WHERE user_id=?", (amount, user_id))
    _safe_exec("INSERT INTO xp_log (user_id, amount, reason) VALUES (?,?,?)", (user_id, amount, reason))

def get_leaderboard(limit=10):
    return _safe_fetchall("SELECT full_name, xp FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT ?", (limit,))

# ---- Lessons ----
def add_lesson(title, content, course_id=1, order_num=0, properties='',
               media_type='', media_file_id='', action_type='', action_label=''):
    _safe_exec(
        "INSERT INTO lessons (title, content, properties, course_id, order_num, media_type, media_file_id, action_type, action_label) VALUES (?,?,?,?,?,?,?,?,?)",
        (title, content, properties, course_id, order_num, media_type, media_file_id, action_type, action_label)
    )

def get_all_lessons():
    return _safe_fetchall("SELECT * FROM lessons ORDER BY order_num")

# ---- Payments ----
def get_pending_payments():
    return _safe_fetchall("SELECT * FROM payments WHERE status='pending'")

def update_payment_status(pid, status):
    _safe_exec("UPDATE payments SET status=? WHERE id=?", (status, pid))

def add_payment(user_id, plan_name, amount, receipt_file_id):
    _safe_exec("INSERT INTO payments (user_id, plan_name, amount, receipt_file_id) VALUES (?,?,?,?)",
               (user_id, plan_name, amount, receipt_file_id))

# ---- Subscriptions ----
def add_subscription(user_id, plan_name, duration_days=30, course_id=None):
    import datetime
    end = (datetime.datetime.now() + datetime.timedelta(days=duration_days)).strftime('%Y-%m-%d %H:%M:%S')
    _safe_exec("INSERT INTO subscriptions (user_id, plan_name, course_id, end_date) VALUES (?,?,?,?)",
               (user_id, plan_name, course_id, end))

# ---- Stats ----
def get_stats():
    conn = get_conn()
    total = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    active = conn.execute('SELECT COUNT(*) FROM students WHERE is_active=1').fetchone()[0]
    try:
        paying = conn.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
    except:
        paying = 0
    return {
        "total_students": total,
        "active_students": active,
        "pending_payments": paying,
    }
'''

with open(os.path.join(base, 'database.py'), 'w', encoding='utf-8') as f:
    f.write(database_py)
print('✅ database.py written')
