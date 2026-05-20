# -*- coding: utf-8 -*-
"""
قاعدة البيانات الموحدة - ملف واحد للبوت والويب
"""
import sqlite3, os, json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_bot_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT DEFAULT "",
        full_name TEXT DEFAULT "",
        phone TEXT DEFAULT "",
        level TEXT DEFAULT "beginner",
        xp INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0,
        tasks_completed INTEGER DEFAULT 0,
        mock_score REAL DEFAULT 0,
        current_phase INTEGER DEFAULT 1,
        is_paid INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        placement_done INTEGER DEFAULT 0,
        placement_score REAL DEFAULT 0,
        completed_lessons TEXT DEFAULT "[]",
        joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_active TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL,
        option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
        correct_option TEXT DEFAULT "a",
        skill TEXT DEFAULT "grammar",
        difficulty TEXT DEFAULT "medium",
        explanation TEXT DEFAULT "",
        timer_seconds INTEGER DEFAULT 30,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS placement_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL,
        option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
        correct_option TEXT DEFAULT "a",
        skill TEXT DEFAULT "grammar",
        difficulty TEXT DEFAULT "medium",
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        title_ar TEXT DEFAULT "",
        description TEXT DEFAULT "",
        skill TEXT DEFAULT "reading",
        phase INTEGER DEFAULT 1,
        order_num INTEGER DEFAULT 0,
        content TEXT DEFAULT "",
        media_url TEXT DEFAULT "",
        xp_reward INTEGER DEFAULT 10,
        timer_minutes INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS daily_missions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT DEFAULT "",
        mission_type TEXT DEFAULT "quiz",
        target_count INTEGER DEFAULT 1,
        xp_reward INTEGER DEFAULT 20,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS user_missions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        mission_id INTEGER,
        progress INTEGER DEFAULT 0,
        completed INTEGER DEFAULT 0,
        date TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        plan_id INTEGER DEFAULT 1,
        amount REAL DEFAULT 25000,
        currency TEXT DEFAULT "IQD",
        status TEXT DEFAULT "pending",
        proof_file TEXT DEFAULT "",
        notes TEXT DEFAULT "",
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        verified_at TEXT DEFAULT ""
    );

    CREATE TABLE IF NOT EXISTS subscription_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT DEFAULT "",
        name_ar TEXT NOT NULL,
        price REAL DEFAULT 25000,
        currency TEXT DEFAULT "IQD",
        duration_days INTEGER DEFAULT 30,
        description TEXT DEFAULT "",
        features TEXT DEFAULT "[]",
        is_active INTEGER DEFAULT 1,
        is_featured INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS system_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT DEFAULT "",
        description TEXT DEFAULT "",
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS phase_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase_number INTEGER UNIQUE,
        phase_name TEXT DEFAULT "",
        min_xp INTEGER DEFAULT 0,
        min_streak INTEGER DEFAULT 0,
        min_quiz_score REAL DEFAULT 0,
        min_attendance_days INTEGER DEFAULT 0,
        description TEXT DEFAULT "",
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS broadcasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT DEFAULT "",
        message TEXT NOT NULL,
        target TEXT DEFAULT "all",
        target_user_id INTEGER DEFAULT 0,
        sent_count INTEGER DEFAULT 0,
        status TEXT DEFAULT "pending",
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        sent_at TEXT DEFAULT ""
    );

    CREATE TABLE IF NOT EXISTS student_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT DEFAULT "",
        full_name TEXT DEFAULT "",
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        replied INTEGER DEFAULT 0,
        reply_text TEXT DEFAULT "",
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS xp_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        reason TEXT DEFAULT "",
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS mock_exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        score REAL DEFAULT 0,
        answers TEXT DEFAULT "{}",
        duration_minutes INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS writing_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        text TEXT NOT NULL,
        score REAL DEFAULT 0,
        feedback TEXT DEFAULT "",
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Default settings
    defaults = [
        ("graduation_min_xp", "500", "الحد الأدنى من نقاط XP للتخرج"),
        ("graduation_min_tasks", "50", "الحد الأدنى من المهام للتخرج"),
        ("graduation_min_streak", "7", "الحد الأدنى من أيام الـ Streak للتخرج"),
        ("graduation_min_mock_score", "70", "الحد الأدنى من درجة الاختبار للتخرج"),
        ("subscription_price", "25000", "سعر الاشتراك"),
        ("subscription_currency", "IQD", "عملة الاشتراك"),
        ("admin_telegram_id", "", "معرف تلغرام الأدمن"),
        ("question_timer_seconds", "30", "وقت كل سؤال بالثواني"),
        ("exam_timer_minutes", "60", "وقت الامتحان الكامل بالدقائق"),
        ("bot_welcome_message", "مرحباً بك في أكاديمية يامن للتوفل!", "رسالة الترحيب"),
        ("paid_required_message", "هذه الميزة للمشتركين فقط. اضغط للاشتراك.", "رسالة الميزات المدفوعة"),
    ]
    for key, value, desc in defaults:
        c.execute("INSERT OR IGNORE INTO system_settings (key,value,description) VALUES (?,?,?)",
                  (key, value, desc))

    # Default phases
    phases = [
        (1, "المبتدئ", 0, 0, 0, 0, "المرحلة الأولى للمبتدئين"),
        (2, "المتوسط", 200, 2, 60, 7, "المرحلة الثانية للمتوسطين"),
        (3, "المتقدم", 500, 5, 75, 14, "المرحلة الثالثة للمتقدمين"),
    ]
    for p in phases:
        c.execute("""INSERT OR IGNORE INTO phase_settings
            (phase_number,phase_name,min_xp,min_streak,min_quiz_score,min_attendance_days,description)
            VALUES (?,?,?,?,?,?,?)""", p)

    # Default plans
    plans = [
        ("basic", "الباقة الأساسية", 25000, 30, "اشتراك شهري أساسي", '["امتحانات يومية","متابعة التقدم"]', 1, 0),
        ("standard", "الباقة المميزة", 45000, 60, "اشتراك شهرين مميز", '["كل مزايا الأساسية","تصحيح المقالات","امتحان mock"]', 1, 1),
        ("premium", "الباقة الكاملة", 75000, 90, "اشتراك ثلاثة أشهر كامل", '["كل المزايا","دعم شخصي","شهادة إتمام"]', 1, 0),
    ]
    for p in plans:
        c.execute("""INSERT OR IGNORE INTO subscription_plans
            (name,name_ar,price,duration_days,description,features,is_active,is_featured)
            VALUES (?,?,?,?,?,?,?,?)""", p)

    conn.commit()
    conn.close()
    print("✅ Database initialized")

# ─── Student helpers ─────────────────────────────────────────────────────────
def create_student(telegram_id, username="", full_name=""):
    conn = get_db()
    try:
        conn.execute("""INSERT OR IGNORE INTO students
            (telegram_id, username, full_name) VALUES (?,?,?)""",
            (telegram_id, username, full_name))
        conn.commit()
    finally:
        conn.close()

def get_student(telegram_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM students WHERE telegram_id=?", (telegram_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_student(telegram_id, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [telegram_id]
    conn = get_db()
    try:
        conn.execute(f"UPDATE students SET {fields} WHERE telegram_id=?", values)
        conn.commit()
    finally:
        conn.close()

def add_xp(telegram_id, amount, reason=""):
    conn = get_db()
    try:
        conn.execute("UPDATE students SET xp=xp+? WHERE telegram_id=?", (amount, telegram_id))
        conn.execute("INSERT INTO xp_log (user_id,amount,reason) VALUES (?,?,?)",
                     (telegram_id, amount, reason))
        conn.commit()
    finally:
        conn.close()

def activate_paid(telegram_id):
    update_student(telegram_id, is_paid=1)

def deactivate_paid(telegram_id):
    update_student(telegram_id, is_paid=0)

def get_all_students_db():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM students ORDER BY xp DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_setting(key, default=""):
    conn = get_db()
    try:
        row = conn.execute("SELECT value FROM system_settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default
    finally:
        conn.close()

def set_setting(key, value):
    conn = get_db()
    try:
        conn.execute("""INSERT INTO system_settings (key,value,updated_at)
            VALUES (?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
            (key, value))
        conn.commit()
    finally:
        conn.close()

# Aliases for backward compatibility
init_db = init_bot_db
