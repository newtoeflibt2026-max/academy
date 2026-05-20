import sqlite3
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def _safe_add_columns(conn):
    c = conn.cursor()
    schema = {
        "students": [
            ("phone", "TEXT"),
            ("is_paid", "INTEGER DEFAULT 0"),
            ("tasks_completed", "INTEGER DEFAULT 0"),
            ("completed_lessons", "TEXT"),
            ("mock_score", "REAL DEFAULT 0"),
            ("current_phase", "INTEGER DEFAULT 1"),
            ("streak", "INTEGER DEFAULT 0"),
            ("last_activity", "TEXT"),
            ("is_active", "INTEGER DEFAULT 1"),
            ("level", "TEXT DEFAULT beginner"),
            ("xp", "INTEGER DEFAULT 0"),
        ],
        "system_settings": [
            ("description", "TEXT"),
            ("updated_at", "TEXT"),
        ],
        "phase_settings": [
            ("phase_number", "INTEGER"),
            ("phase_name", "TEXT"),
            ("min_xp", "INTEGER DEFAULT 0"),
            ("min_streak", "INTEGER DEFAULT 0"),
            ("min_quiz_score", "REAL DEFAULT 0"),
            ("min_attendance_days", "INTEGER DEFAULT 0"),
            ("description", "TEXT"),
            ("updated_at", "TEXT"),
        ],
    }
    for table, cols in schema.items():
        try:
            c.execute("PRAGMA table_info(" + table + ")")
            existing = [row[1] for row in c.fetchall()]
            for col_name, col_def in cols:
                if col_name not in existing:
                    try:
                        c.execute("ALTER TABLE " + table + " ADD COLUMN " + col_name + " " + col_def)
                    except Exception:
                        pass
        except Exception:
            pass
    conn.commit()

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        full_name TEXT,
        phone TEXT,
        level TEXT DEFAULT 'beginner',
        xp INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0,
        tasks_completed INTEGER DEFAULT 0,
        completed_lessons TEXT,
        is_paid INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        last_activity TEXT,
        joined_at TEXT DEFAULT (datetime('now')),
        mock_score REAL DEFAULT 0,
        current_phase INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_skills_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        reading_xp INTEGER DEFAULT 0,
        listening_xp INTEGER DEFAULT 0,
        speaking_xp INTEGER DEFAULT 0,
        writing_xp INTEGER DEFAULT 0,
        grammar_xp INTEGER DEFAULT 0,
        vocabulary_xp INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER,
        question_text TEXT NOT NULL,
        question_type TEXT DEFAULT 'mcq',
        options TEXT,
        correct_answer TEXT,
        explanation TEXT,
        skill TEXT DEFAULT 'reading',
        difficulty TEXT DEFAULT 'medium',
        media_url TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        skill TEXT DEFAULT 'reading',
        phase INTEGER DEFAULT 1,
        order_num INTEGER DEFAULT 0,
        content TEXT,
        media_url TEXT,
        xp_reward INTEGER DEFAULT 10,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS daily_missions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        mission_type TEXT DEFAULT 'reading',
        xp_reward INTEGER DEFAULT 20,
        target_date TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_missions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mission_id INTEGER NOT NULL,
        completed INTEGER DEFAULT 0,
        completed_at TEXT,
        UNIQUE(user_id, mission_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS essay_grading_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        skill TEXT DEFAULT 'writing',
        vocab_keywords TEXT DEFAULT '[]',
        connector_keywords TEXT DEFAULT '[]',
        forbidden_words TEXT DEFAULT '[]',
        vocab_points REAL DEFAULT 2.0,
        connector_points REAL DEFAULT 3.0,
        forbidden_penalty REAL DEFAULT 1.0,
        max_score REAL DEFAULT 100.0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS writing_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        topic TEXT,
        content TEXT,
        score REAL DEFAULT 0,
        feedback TEXT,
        graded_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS phase_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase_number INTEGER UNIQUE NOT NULL,
        phase_name TEXT,
        min_xp INTEGER DEFAULT 0,
        min_streak INTEGER DEFAULT 0,
        min_quiz_score REAL DEFAULT 0,
        min_attendance_days INTEGER DEFAULT 0,
        description TEXT,
        updated_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS system_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT NOT NULL,
        description TEXT,
        updated_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL DEFAULT 0,
        currency TEXT DEFAULT 'IQD',
        plan TEXT DEFAULT 'basic',
        status TEXT DEFAULT 'pending',
        payment_method TEXT,
        receipt_url TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        verified_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS xp_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        xp_amount INTEGER NOT NULL,
        reason TEXT,
        skill TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS error_bank (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id INTEGER,
        error_type TEXT,
        wrong_answer TEXT,
        correct_answer TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS mock_exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        score REAL DEFAULT 0,
        reading_score REAL DEFAULT 0,
        listening_score REAL DEFAULT 0,
        speaking_score REAL DEFAULT 0,
        writing_score REAL DEFAULT 0,
        duration_minutes INTEGER DEFAULT 0,
        completed_at TEXT DEFAULT (datetime('now'))
    )""")

    conn.commit()
    _safe_add_columns(conn)

    defaults = [
        ("graduation_min_xp", "500", "الحد الادنى من XP للتخرج"),
        ("graduation_min_tasks", "10", "عدد المهام اليومية المطلوبة"),
        ("graduation_min_streak", "3", "الحد الادنى للـ streak"),
        ("graduation_min_mock_score", "69", "الحد الادنى لنتيجة Mock Exam"),
        ("graduation_mock_bonus", "10", "نقاط اضافية فوق required_score"),
        ("subscription_price", "25000", "سعر الاشتراك بالدينار"),
        ("subscription_currency", "IQD", "العملة"),
        ("bot_welcome_message", "مرحبا بك في اكاديمية يامن للتوفل", "رسالة الترحيب"),
        ("paid_required_message", "هذه الميزة للمشتركين فقط تواصل مع الادمن", "رسالة المدفوع"),
    ]
    for key, value, desc in defaults:
        try:
            c.execute("INSERT OR IGNORE INTO system_settings (key,value,description) VALUES (?,?,?)",
                      (key, value, desc))
        except Exception:
            pass

    phases = [
        (1, "المبتدئ", 0, 0, 0, 0, "المرحلة الاولى"),
        (2, "المتوسط", 200, 2, 60, 7, "المرحلة الثانية"),
        (3, "المتقدم", 500, 5, 75, 14, "المرحلة الثالثة"),
    ]
    for p in phases:
        try:
            c.execute("INSERT OR IGNORE INTO phase_settings (phase_number,phase_name,min_xp,min_streak,min_quiz_score,min_attendance_days,description) VALUES (?,?,?,?,?,?,?)", p)
        except Exception:
            pass

    conn.commit()
    conn.close()

# ─── Students ──────────────────────────────────────────────────────────────────

def create_student(user_id, username=None, full_name=None, phone=None):
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO students (user_id,username,full_name,phone,last_activity) VALUES (?,?,?,?,?)",
            (user_id, username, full_name, phone, datetime.now().isoformat())
        )
        conn.execute("INSERT OR IGNORE INTO user_skills_progress (user_id) VALUES (?)", (user_id,))
        conn.commit()
    finally:
        conn.close()

def get_student(user_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM students WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_student(user_id, **kwargs):
    if not kwargs:
        return
    conn = get_db()
    try:
        sets = ", ".join(k + "=?" for k in kwargs)
        vals = list(kwargs.values()) + [user_id]
        conn.execute("UPDATE students SET " + sets + " WHERE user_id=?", vals)
        conn.commit()
    finally:
        conn.close()

def get_all_students(limit=200, offset=0):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM students ORDER BY joined_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def search_students(query):
    conn = get_db()
    try:
        q = "%" + query + "%"
        rows = conn.execute(
            "SELECT * FROM students WHERE username LIKE ? OR full_name LIKE ? OR phone LIKE ? OR CAST(user_id AS TEXT) LIKE ?",
            (q, q, q, q)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def activate_paid(user_id):
    conn = get_db()
    try:
        conn.execute("UPDATE students SET is_paid=1 WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()

def deactivate_paid(user_id):
    conn = get_db()
    try:
        conn.execute("UPDATE students SET is_paid=0 WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()

def get_students_count():
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as total, SUM(is_paid) as paid, SUM(is_active) as active FROM students"
        ).fetchone()
        return dict(row) if row else {"total": 0, "paid": 0, "active": 0}
    finally:
        conn.close()

# ─── XP & Skills ───────────────────────────────────────────────────────────────

def add_xp(user_id, amount, skill=None, reason=None):
    conn = get_db()
    try:
        conn.execute("UPDATE students SET xp=xp+? WHERE user_id=?", (amount, user_id))
        allowed = ["reading_xp","listening_xp","speaking_xp","writing_xp","grammar_xp","vocabulary_xp"]
        if skill and (skill + "_xp") in allowed:
            conn.execute(
                "UPDATE user_skills_progress SET " + skill + "_xp=" + skill + "_xp+? WHERE user_id=?",
                (amount, user_id)
            )
        conn.execute(
            "INSERT INTO xp_log (user_id,xp_amount,reason,skill) VALUES (?,?,?,?)",
            (user_id, amount, reason, skill)
        )
        conn.commit()
    finally:
        conn.close()

def get_skills_progress(user_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM user_skills_progress WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            conn.execute("INSERT OR IGNORE INTO user_skills_progress (user_id) VALUES (?)", (user_id,))
            conn.commit()
            row = conn.execute("SELECT * FROM user_skills_progress WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()

def update_streak(user_id):
    conn = get_db()
    try:
        s = conn.execute("SELECT last_activity, streak FROM students WHERE user_id=?", (user_id,)).fetchone()
        if not s:
            return 0
        today = date.today().isoformat()
        last = s["last_activity"][:10] if s["last_activity"] else None
        streak = s["streak"] or 0
        if last == today:
            pass
        elif last and (date.today() - date.fromisoformat(last)).days == 1:
            streak += 1
        else:
            streak = 1
        conn.execute(
            "UPDATE students SET streak=?, last_activity=? WHERE user_id=?",
            (streak, datetime.now().isoformat(), user_id)
        )
        conn.commit()
        return streak
    finally:
        conn.close()

# ─── Settings ──────────────────────────────────────────────────────────────────

def get_setting(key, default=None):
    conn = get_db()
    try:
        row = conn.execute("SELECT value FROM system_settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()

def set_setting(key, value):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO system_settings (key,value,updated_at) VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, datetime.now().isoformat())
        )
        conn.commit()
    finally:
        conn.close()

def get_all_settings():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM system_settings ORDER BY key").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

# ─── Graduation ────────────────────────────────────────────────────────────────

def check_graduation(user_id):
    student = get_student(user_id)
    if not student:
        return {"eligible": False, "reason": "الطالب غير موجود", "checks": []}

    checks = []
    eligible = True

    if not student.get("is_paid"):
        eligible = False
        checks.append({"check": "is_paid", "passed": False, "message": "الحساب غير مفعل - تواصل مع الادمن"})
    else:
        checks.append({"check": "is_paid", "passed": True, "message": "الحساب مفعل"})

    min_xp = int(get_setting("graduation_min_xp", 500))
    xp = student.get("xp", 0)
    if xp < min_xp:
        eligible = False
        checks.append({"check": "xp", "passed": False, "message": "XP: " + str(xp) + "/" + str(min_xp)})
    else:
        checks.append({"check": "xp", "passed": True, "message": "XP: " + str(xp) + "/" + str(min_xp)})

    min_tasks = int(get_setting("graduation_min_tasks", 10))
    tasks = student.get("tasks_completed", 0)
    if tasks < min_tasks:
        eligible = False
        checks.append({"check": "tasks", "passed": False, "message": "المهام: " + str(tasks) + "/" + str(min_tasks)})
    else:
        checks.append({"check": "tasks", "passed": True, "message": "المهام: " + str(tasks) + "/" + str(min_tasks)})

    min_streak = int(get_setting("graduation_min_streak", 3))
    streak = student.get("streak", 0)
    if streak < min_streak:
        eligible = False
        checks.append({"check": "streak", "passed": False, "message": "Streak: " + str(streak) + "/" + str(min_streak)})
    else:
        checks.append({"check": "streak", "passed": True, "message": "Streak: " + str(streak) + "/" + str(min_streak)})

    required = int(get_setting("graduation_min_mock_score", 59))
    bonus = int(get_setting("graduation_mock_bonus", 10))
    needed = required + bonus
    mock = student.get("mock_score", 0)
    if mock < needed:
        eligible = False
        checks.append({"check": "mock", "passed": False, "message": "Mock Exam: " + str(mock) + "/" + str(needed)})
    else:
        checks.append({"check": "mock", "passed": True, "message": "Mock Exam: " + str(mock) + "/" + str(needed)})

    return {"eligible": eligible, "checks": checks, "student": student}

# ─── Daily Missions ────────────────────────────────────────────────────────────

def get_daily_missions(target_date=None):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM daily_missions WHERE is_active=1 ORDER BY id DESC LIMIT 10"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def add_daily_mission(title, description, mission_type, xp_reward, target_date=None):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO daily_missions (title,description,mission_type,xp_reward,target_date) VALUES (?,?,?,?,?)",
            (title, description, mission_type, xp_reward, target_date)
        )
        conn.commit()
    finally:
        conn.close()

def complete_mission(user_id, mission_id):
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT completed FROM user_missions WHERE user_id=? AND mission_id=?",
            (user_id, mission_id)
        ).fetchone()
        if existing and existing["completed"]:
            return False
        conn.execute(
            "INSERT INTO user_missions (user_id,mission_id,completed,completed_at) VALUES (?,?,1,?) ON CONFLICT(user_id,mission_id) DO UPDATE SET completed=1,completed_at=excluded.completed_at",
            (user_id, mission_id, datetime.now().isoformat())
        )
        conn.execute("UPDATE students SET tasks_completed=tasks_completed+1 WHERE user_id=?", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()

# ─── Grading ───────────────────────────────────────────────────────────────────

def get_grading_rules(skill=None):
    conn = get_db()
    try:
        if skill:
            rows = conn.execute(
                "SELECT * FROM essay_grading_rules WHERE skill=? AND is_active=1", (skill,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM essay_grading_rules WHERE is_active=1 ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def grade_essay(user_id, topic, essay_text):
    import json
    conn = get_db()
    try:
        rule = conn.execute(
            "SELECT * FROM essay_grading_rules WHERE topic=? AND is_active=1", (topic,)
        ).fetchone()
        if not rule:
            return {"score": 0, "feedback": "لا توجد معايير تصحيح لهذا الموضوع", "details": []}
        rule = dict(rule)
        text_lower = essay_text.lower()
        score = 0
        details = []
        max_score = rule.get("max_score", 100)
        vocab_kw = json.loads(rule.get("vocab_keywords", "[]"))
        connector_kw = json.loads(rule.get("connector_keywords", "[]"))
        forbidden_kw = json.loads(rule.get("forbidden_words", "[]"))
        matched_v = [w for w in vocab_kw if w.lower() in text_lower]
        vpts = len(matched_v) * rule.get("vocab_points", 2)
        score += vpts
        details.append("Vocab: " + str(len(matched_v)) + "/" + str(len(vocab_kw)) + " (+" + str(vpts) + ")")
        matched_c = [w for w in connector_kw if w.lower() in text_lower]
        cpts = len(matched_c) * rule.get("connector_points", 3)
        score += cpts
        details.append("Connectors: " + str(len(matched_c)) + "/" + str(len(connector_kw)) + " (+" + str(cpts) + ")")
        matched_f = [w for w in forbidden_kw if w.lower() in text_lower]
        penalty = len(matched_f) * rule.get("forbidden_penalty", 1)
        score -= penalty
        if matched_f:
            details.append("محظور: " + ", ".join(matched_f) + " (-" + str(penalty) + ")")
        score = max(0, min(score, max_score))
        pct = round((score / max_score) * 100, 1) if max_score > 0 else 0
        feedback = "\n".join(details) + "\nالنتيجة: " + str(score) + "/" + str(max_score) + " (" + str(pct) + "%)"
        conn.execute(
            "INSERT INTO writing_submissions (user_id,topic,content,score,feedback) VALUES (?,?,?,?,?)",
            (user_id, topic, essay_text, pct, feedback)
        )
        conn.commit()
        return {"score": pct, "raw_score": score, "max_score": max_score, "feedback": feedback, "details": details}
    finally:
        conn.close()

# ─── Phase Settings ────────────────────────────────────────────────────────────

def get_phase_settings():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM phase_settings ORDER BY phase_number").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def update_phase_settings(phase_number, **kwargs):
    if not kwargs:
        return
    conn = get_db()
    try:
        kwargs["updated_at"] = datetime.now().isoformat()
        sets = ", ".join(k + "=?" for k in kwargs)
        vals = list(kwargs.values()) + [phase_number]
        conn.execute("UPDATE phase_settings SET " + sets + " WHERE phase_number=?", vals)
        conn.commit()
    finally:
        conn.close()

# ─── Questions ─────────────────────────────────────────────────────────────────

def get_questions(skill=None, limit=200):
    conn = get_db()
    try:
        if skill:
            rows = conn.execute(
                "SELECT * FROM questions WHERE skill=? ORDER BY id DESC LIMIT ?", (skill, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM questions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def add_question(question_text, skill, question_type="mcq", options=None, correct_answer=None, explanation=None, lesson_id=None):
    import json
    conn = get_db()
    try:
        opts = json.dumps(options, ensure_ascii=False) if isinstance(options, list) else options
        conn.execute(
            "INSERT INTO questions (question_text,skill,question_type,options,correct_answer,explanation,lesson_id) VALUES (?,?,?,?,?,?,?)",
            (question_text, skill, question_type, opts, correct_answer, explanation, lesson_id)
        )
        conn.commit()
    finally:
        conn.close()

def delete_question(question_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM questions WHERE id=?", (question_id,))
        conn.commit()
    finally:
        conn.close()

# ─── Payments ──────────────────────────────────────────────────────────────────

def get_payments(limit=100):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT p.*, s.username, s.full_name
            FROM payments p LEFT JOIN students s ON p.user_id=s.user_id
            ORDER BY p.created_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def add_payment(user_id, amount, plan="basic", status="pending", notes=None):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO payments (user_id,amount,plan,status,notes) VALUES (?,?,?,?,?)",
            (user_id, amount, plan, status, notes)
        )
        conn.commit()
    finally:
        conn.close()

def verify_payment(payment_id):
    conn = get_db()
    try:
        payment = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
        if payment:
            conn.execute(
                "UPDATE payments SET status='verified', verified_at=? WHERE id=?",
                (datetime.now().isoformat(), payment_id)
            )
            conn.execute("UPDATE students SET is_paid=1 WHERE user_id=?", (payment["user_id"],))
            conn.commit()
            return True
        return False
    finally:
        conn.close()

# ─── Leaderboard ───────────────────────────────────────────────────────────────

def get_leaderboard(limit=10):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT user_id,username,full_name,xp,streak,level FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

get_leaderboard_data = get_leaderboard

# ─── Auto init ─────────────────────────────────────────────────────────────────
try:
    init_db()
except Exception as _init_err:
    import logging
    logging.getLogger(__name__).warning("init_db warning: " + str(_init_err))

# alias for backward compatibility
init_bot_db = init_db

# alias
create_payment = add_payment

# aliases for all handlers
approve_payment = verify_payment
get_all_payments = get_payments
create_payment = add_payment
init_bot_db = init_db

# ── unified db alias ──
from db import init_bot_db, get_db, create_student, get_student, update_student, activate_paid, deactivate_paid, get_setting, set_setting, get_all_students_db
