# -*- coding: utf-8 -*-
import sqlite3
import os
from datetime import datetime, timedelta
from loguru import logger

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_bot_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id     TEXT UNIQUE NOT NULL,
        name            TEXT DEFAULT 'طالب',
        username        TEXT,
        target_band     REAL DEFAULT 6.5,
        current_band    REAL DEFAULT 0,
        path_type       TEXT DEFAULT 'toefl',
        days_left       INTEGER DEFAULT 90,
        xp              INTEGER DEFAULT 0,
        streak_days     INTEGER DEFAULT 0,
        last_active     DATE,
        is_active       INTEGER DEFAULT 0,
        subscription_type TEXT DEFAULT 'free',
        package_end     DATE,
        current_stage   INTEGER DEFAULT 1,
        placement_done  INTEGER DEFAULT 0,
        level           TEXT DEFAULT 'beginner',
        actual_exam_date DATE,
        free_week       INTEGER DEFAULT 1,
        review_submitted INTEGER DEFAULT 0,
        post_submitted  INTEGER DEFAULT 0,
        required_score  INTEGER DEFAULT 59,
        mock_exam_score INTEGER DEFAULT 0,
        is_graduated    INTEGER DEFAULT 0,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS subscriptions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT NOT NULL,
        user_id     TEXT,
        plan_key    TEXT,
        plan_name   TEXT,
        start_date  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_date    TIMESTAMP,
        is_active   INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS payments (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id     TEXT NOT NULL,
        plan_key        TEXT,
        plan_name       TEXT,
        amount          REAL DEFAULT 0,
        status          TEXT DEFAULT 'pending',
        receipt_photo_id TEXT,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS student_error_bank (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id     TEXT NOT NULL,
        question_id     INTEGER,
        error_count     INTEGER DEFAULT 1,
        last_attempted  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS book_codes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        code        TEXT UNIQUE NOT NULL,
        duration_days INTEGER DEFAULT 90,
        is_used     INTEGER DEFAULT 0,
        used_by     TEXT,
        used_at     TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS xp_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT NOT NULL,
        amount      INTEGER,
        reason      TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()
    logger.info("DB ready")

# ── STUDENTS ──────────────────────────────────────────────────────────────

def get_student(telegram_id):
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM students WHERE telegram_id=? LIMIT 1",
            (str(telegram_id),)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"get_student: {e}")
        return None

async def async_get_student(telegram_id):
    return get_student(telegram_id)

def create_student(telegram_id, name, target_band=6.5,
                   path_type="toefl", days_left=90, username=None):
    try:
        conn = get_db()
        conn.execute(
            """INSERT OR IGNORE INTO students
               (telegram_id, name, username, target_band, path_type, days_left,
                is_active, xp, streak_days, last_active)
               VALUES (?,?,?,?,?,?,0,0,0,date('now'))""",
            (str(telegram_id), name, username, target_band, path_type, days_left)
        )
        conn.commit()
        conn.close()
        return get_student(telegram_id)
    except Exception as e:
        logger.error(f"create_student: {e}")
        return None

def update_student_xp(telegram_id, amount, reason=""):
    try:
        conn = get_db()
        conn.execute(
            "UPDATE students SET xp = MAX(0, xp + ?) WHERE telegram_id=?",
            (amount, str(telegram_id))
        )
        conn.execute(
            "INSERT INTO xp_log (telegram_id, amount, reason) VALUES (?,?,?)",
            (str(telegram_id), amount, reason)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"update_xp: {e}")

def update_streak(telegram_id):
    try:
        conn = get_db()
        student = conn.execute(
            "SELECT last_active, streak_days FROM students WHERE telegram_id=?",
            (str(telegram_id),)
        ).fetchone()
        if student:
            last = student["last_active"]
            today = datetime.now().date().isoformat()
            yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
            if last == yesterday:
                new_streak = (student["streak_days"] or 0) + 1
            elif last == today:
                new_streak = student["streak_days"] or 1
            else:
                new_streak = 1
            conn.execute(
                "UPDATE students SET streak_days=?, last_active=? WHERE telegram_id=?",
                (new_streak, today, str(telegram_id))
            )
            conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"update_streak: {e}")

# ── SUBSCRIPTIONS ─────────────────────────────────────────────────────────

def get_subscription(telegram_id):
    try:
        conn = get_db()
        row = conn.execute(
            """SELECT * FROM subscriptions
               WHERE telegram_id=? AND is_active=1
               ORDER BY end_date DESC LIMIT 1""",
            (str(telegram_id),)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"get_subscription: {e}")
        return None

def activate_subscription(telegram_id, plan_key, plan_name, days):
    try:
        conn = get_db()
        end_date = (datetime.now() + timedelta(days=days)).isoformat()
        conn.execute(
            "UPDATE subscriptions SET is_active=0 WHERE telegram_id=?",
            (str(telegram_id),)
        )
        conn.execute(
            """INSERT INTO subscriptions
               (telegram_id, plan_key, plan_name, end_date, is_active)
               VALUES (?,?,?,?,1)""",
            (str(telegram_id), plan_key, plan_name, end_date)
        )
        conn.execute(
            """UPDATE students SET is_active=1, subscription_type=?,
               package_end=? WHERE telegram_id=?""",
            (plan_key, end_date, str(telegram_id))
        )
        conn.commit()
        conn.close()
        logger.info(f"Activated {plan_key} for {telegram_id} until {end_date}")
    except Exception as e:
        logger.error(f"activate_subscription: {e}")

# ── PAYMENTS ──────────────────────────────────────────────────────────────

def create_payment(telegram_id, plan_key, plan_name, amount, receipt_photo_id):
    try:
        conn = get_db()
        conn.execute(
            """INSERT INTO payments
               (telegram_id, plan_key, plan_name, amount, status, receipt_photo_id)
               VALUES (?,?,?,?,'pending',?)""",
            (str(telegram_id), plan_key, plan_name, amount, receipt_photo_id)
        )
        pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()
        return pid
    except Exception as e:
        logger.error(f"create_payment: {e}")
        return None

def approve_payment(payment_id, plan_key, plan_name, telegram_id, days):
    try:
        conn = get_db()
        conn.execute(
            "UPDATE payments SET status='approved' WHERE id=?",
            (payment_id,)
        )
        conn.commit()
        conn.close()
        activate_subscription(telegram_id, plan_key, plan_name, days)
    except Exception as e:
        logger.error(f"approve_payment: {e}")

# ── ERROR BANK ────────────────────────────────────────────────────────────

def add_error(telegram_id, question_id):
    try:
        conn = get_db()
        existing = conn.execute(
            "SELECT id, error_count FROM student_error_bank WHERE telegram_id=? AND question_id=?",
            (str(telegram_id), question_id)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE student_error_bank SET error_count=error_count+1, last_attempted=CURRENT_TIMESTAMP WHERE id=?",
                (existing["id"],)
            )
        else:
            conn.execute(
                "INSERT INTO student_error_bank (telegram_id, question_id) VALUES (?,?)",
                (str(telegram_id), question_id)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"add_error: {e}")

def get_review_questions(telegram_id, limit=3):
    try:
        conn = get_db()
        rows = conn.execute(
            """SELECT question_id FROM student_error_bank
               WHERE telegram_id=?
               ORDER BY error_count DESC, last_attempted ASC
               LIMIT ?""",
            (str(telegram_id), limit)
        ).fetchall()
        conn.close()
        return [r["question_id"] for r in rows]
    except Exception as e:
        logger.error(f"get_review_questions: {e}")
        return []

# ── BOOK CODES ────────────────────────────────────────────────────────────

def activate_book_code(telegram_id, code):
    try:
        conn = get_db()
        book = conn.execute(
            "SELECT * FROM book_codes WHERE code=? AND is_used=0",
            (code.upper(),)
        ).fetchone()
        if not book:
            conn.close()
            return False, "الكود غير صحيح أو مستخدم مسبقاً"
        days = book["duration_days"]
        conn.execute(
            "UPDATE book_codes SET is_used=1, used_by=?, used_at=CURRENT_TIMESTAMP WHERE code=?",
            (str(telegram_id), code.upper())
        )
        conn.commit()
        conn.close()
        activate_subscription(telegram_id, "book_premium", "كتاب يامن المميز", days)
        return True, f"تم تفعيل الكود! مدة الاشتراك: {days} يوم"
    except Exception as e:
        logger.error(f"activate_book_code: {e}")
        return False, "خطأ في النظام"

# ── LEADERBOARD ───────────────────────────────────────────────────────────

def get_leaderboard(limit=10):
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT telegram_id, name, xp, streak_days FROM students ORDER BY xp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"get_leaderboard: {e}")
        return []

def get_student_rank(telegram_id):
    try:
        conn = get_db()
        student = conn.execute(
            "SELECT xp FROM students WHERE telegram_id=?",
            (str(telegram_id),)
        ).fetchone()
        if not student:
            conn.close()
            return None, None
        rank = conn.execute(
            "SELECT COUNT(*)+1 as rank FROM students WHERE xp > ?",
            (student["xp"],)
        ).fetchone()["rank"]
        conn.close()
        return rank, student["xp"]
    except Exception as e:
        logger.error(f"get_student_rank: {e}")
        return None, None
