# -*- coding: utf-8 -*-
"""
Yamen Academy - Central DB Module (v2 - Production Ready)
- Single source of truth for DB_PATH (env > Railway volume > local)
- Bridges legacy bot_database.py functions
- Provides safe connection helpers + integrity guard
"""
import os
import sqlite3

# ========== Unified DB path resolver ==========
def _resolve_db_path():
    """Single source of truth for DB path. Priority:
       1. DB_PATH env var (if set and absolute path that exists OR parent exists)
       2. /app/data/academy.db  (Railway volume)
       3. <project_dir>/academy.db  (local dev)
    """
    env_path = os.environ.get("DB_PATH", "").strip()
    # Reject local Windows paths leaking to Linux env
    if env_path and not env_path.startswith(("C:", "D:", "E:")):
        try:
            parent = os.path.dirname(env_path) or "."
            if os.path.isdir(parent) or os.path.exists(env_path):
                print(f"[db._resolve] using DB_PATH env: {env_path}")
                return env_path
        except Exception:
            pass
    if os.path.isdir("/app/data"):
        p = "/app/data/academy.db"
        print(f"[db._resolve] using Railway volume: {p}")
        return p
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")
    print(f"[db._resolve] using local dev path: {p}")
    return p


DB_PATH = _resolve_db_path()
# Export to environment so every other module sees the same path
os.environ["DB_PATH"] = DB_PATH


# ========== Re-export ALL legacy functions from bot_database ==========
from bot_database import (
    get_db,
    init_db,
    init_bot_db,
    create_student,
    get_student,
    update_student,
    get_all_students,
    get_all_students_db,
    search_students,
    activate_paid,
    deactivate_paid,
    get_students_count,
    add_xp,
    get_skills_progress,
    update_streak,
    get_setting,
    set_setting,
    get_all_settings,
    check_graduation,
    get_daily_missions,
    add_daily_mission,
    complete_mission,
    get_grading_rules,
    grade_essay,
    get_phase_settings,
    update_phase_settings,
    get_questions,
    add_question,
    delete_question,
    get_payments,
    add_payment,
    verify_payment,
    get_leaderboard,
    approve_payment,
    get_all_payments,
    create_payment,
)


# ========== Central safe connection helper ==========
def get_connection(row_factory=True):
    """Safe SQLite connection (WAL, 30s timeout, FK on, normal sync)."""
    conn = sqlite3.connect(
        DB_PATH, timeout=30.0, isolation_level=None, check_same_thread=False,
    )
    if row_factory:
        conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    except Exception as e:
        print(f"[db.get_connection] PRAGMA warn: {e}")
    return conn


# ========== Startup integrity guard ==========
REQUIRED_TABLES = [
    "students", "lessons", "stages", "stage_exam_questions",
    "lesson_questions", "lesson_practice_texts", "mini_lessons",
]


def verify_integrity():
    print(f"[db.verify] Using DB: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"[db.verify] FATAL: DB file does not exist: {DB_PATH}")
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        existing = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        missing = [t for t in REQUIRED_TABLES if t not in existing]
        if missing:
            print(f"[db.verify] FATAL: Missing required tables: {missing}")
            return False
        print(f"[db.verify] OK - all {len(REQUIRED_TABLES)} required tables present")
        return True
    except Exception as e:
        print(f"[db.verify] FATAL: {e}")
        return False


# ========== Student ID normalization (single policy) ==========
def normalize_student_id(raw):
    """Convert any incoming student_id/user_id/telegram_id to a single canonical string.
       Use this everywhere instead of mixing user_id vs telegram_id."""
    if raw is None:
        return ""
    s = str(raw).strip()
    return s


def find_student_row(conn, raw_id):
    """Look up a student by either user_id OR telegram_id (unified)."""
    sid = normalize_student_id(raw_id)
    if not sid:
        return None
    try:
        row = conn.execute(
            "SELECT * FROM students WHERE CAST(user_id AS TEXT)=? OR telegram_id=?",
            (sid, sid)
        ).fetchone()
        return row
    except Exception:
        return None
