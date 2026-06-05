# -*- coding: utf-8 -*-
"""
Lightweight compatibility layer for legacy bot_database imports.
This file makes the patched package self-contained and keeps the
student/miniapp launch flow working against the existing academy.db.
"""
import json
import os
import sqlite3
from datetime import datetime


# DB_PATH centralized in db.py (single source of truth)
def _resolve_db_path():
    env_path = os.environ.get("DB_PATH", "").strip()
    if env_path and not env_path.startswith(("C:", "D:", "E:")):
        return env_path
    if os.path.isdir("/app/data"):
        return "/app/data/academy.db"
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")

DB_PATH = _resolve_db_path()
os.environ["DB_PATH"] = DB_PATH
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA foreign_keys=ON;")
    except Exception:
        pass
    return conn


def get_connection():
    return get_db()


def _student_where():
    return "CAST(user_id AS TEXT)=? OR telegram_id=?"


def _norm_sid(student_id):
    if student_id is None:
        return ""
    return str(student_id).strip()


def init_db():
    conn = get_db()
    conn.close()
    return True


def init_bot_db():
    return init_db()


def create_student(user_id, full_name=None, username="", level="beginner", telegram_id=None, **extra):
    sid = _norm_sid(telegram_id or user_id)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO students
        (user_id, telegram_id, full_name, username, level, is_active, created_at, name)
        VALUES (?, ?, COALESCE(?, full_name), ?, ?, 1, COALESCE((SELECT created_at FROM students WHERE user_id=?), CURRENT_TIMESTAMP), COALESCE(?, 'طالب'))
        """,
        (int(user_id), sid, full_name, username or "", level or "beginner", int(user_id), full_name or "طالب"),
    )
    conn.commit()
    row = cur.execute("SELECT * FROM students WHERE user_id=?", (int(user_id),)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_student(student_id):
    sid = _norm_sid(student_id)
    if not sid:
        return None
    conn = get_db()
    row = conn.execute(f"SELECT * FROM students WHERE {_student_where()} LIMIT 1", (sid, sid)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_student(student_id, **fields):
    sid = _norm_sid(student_id)
    if not sid or not fields:
        return False
    allowed = []
    values = []
    for key, value in fields.items():
        allowed.append(f"{key}=?")
        values.append(value)
    values.extend([sid, sid])
    conn = get_db()
    conn.execute(f"UPDATE students SET {', '.join(allowed)} WHERE {_student_where()}", values)
    conn.commit()
    conn.close()
    return True


def get_all_students():
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM students ORDER BY user_id DESC").fetchall()]
    conn.close()
    return rows


def get_all_students_db():
    return get_all_students()


def search_students(query):
    q = f"%{query or ''}%"
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM students WHERE full_name LIKE ? OR name LIKE ? OR username LIKE ? OR telegram_id LIKE ? ORDER BY user_id DESC",
        (q, q, q, q),
    ).fetchall()]
    conn.close()
    return rows


def activate_paid(student_id):
    sid = _norm_sid(student_id)
    conn = get_db()
    conn.execute(f"UPDATE students SET is_paid=1, subscription_type='paid' WHERE {_student_where()}", (sid, sid))
    conn.commit()
    conn.close()
    return True


def deactivate_paid(student_id):
    sid = _norm_sid(student_id)
    conn = get_db()
    conn.execute(f"UPDATE students SET is_paid=0, subscription_type='free' WHERE {_student_where()}", (sid, sid))
    # تعطيل أي اشتراك نشط
    try:
        conn.execute("UPDATE subscriptions SET is_active=0 WHERE user_id=? OR telegram_id=?", (sid, str(sid)))
    except Exception as e:
        print(f"[deactivate_paid] subscriptions update error: {e}")
    conn.commit()
    conn.close()
    return True



def get_students_count():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    conn.close()
    return count


def add_xp(student_id, amount, reason=""):
    sid = _norm_sid(student_id)
    amt = int(amount or 0)
    conn = get_db()
    conn.execute(
        f"UPDATE students SET xp=COALESCE(xp,0)+?, total_xp=COALESCE(total_xp,0)+? WHERE {_student_where()}",
        (amt, amt, sid, sid),
    )
    try:
        uid = int(sid) if sid.isdigit() else 0
        conn.execute("INSERT INTO xp_log (user_id, amount, reason, created_at) VALUES (?, ?, ?, datetime('now'))", (uid, amt, reason or 'xp'))
    except Exception:
        pass
    conn.commit()
    conn.close()
    return True


def get_skills_progress(student_id):
    sid = _norm_sid(student_id)
    conn = get_db()
    cur = conn.cursor()
    totals = {}
    for row in cur.execute("SELECT COALESCE(skill, skill_type, 'general') AS skill, COUNT(*) AS c FROM lessons WHERE COALESCE(is_active,1)=1 GROUP BY 1"):
        totals[row['skill']] = row['c']
    done = {}
    for row in cur.execute(
        """
        SELECT COALESCE(l.skill, l.skill_type, 'general') AS skill, COUNT(DISTINCT la.lesson_id) AS c
        FROM lesson_attempts la JOIN lessons l ON l.id=la.lesson_id
        WHERE la.telegram_id=? AND la.passed=1
        GROUP BY 1
        """,
        (sid,),
    ):
        done[row['skill']] = row['c']
    conn.close()
    out = {}
    for skill in sorted(set(totals) | set(done)):
        total = int(totals.get(skill, 0) or 0)
        completed = int(done.get(skill, 0) or 0)
        out[skill] = {
            'completed': completed,
            'total': total,
            'ratio': round(completed / total, 4) if total else 0,
        }
    return out


def update_streak(student_id):
    sid = _norm_sid(student_id)
    conn = get_db()
    conn.execute(f"UPDATE students SET streak=COALESCE(streak,0)+1, streak_days=COALESCE(streak_days,0)+1, last_activity=datetime('now') WHERE {_student_where()}", (sid, sid))
    conn.commit()
    conn.close()
    return True


def get_setting(key, default=None):
    conn = get_db()
    val = default
    for table in ("system_settings", "admin_settings"):
        try:
            row = conn.execute(f"SELECT value FROM {table} WHERE key=? LIMIT 1", (key,)).fetchone()
            if row:
                val = row[0]
                break
        except Exception:
            continue
    conn.close()
    return val


def set_setting(key, value):
    conn = get_db()
    saved = False
    for table in ("system_settings", "admin_settings"):
        try:
            conn.execute(f"INSERT INTO {table} (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
            saved = True
            break
        except Exception:
            continue
    conn.commit()
    conn.close()
    return saved


def get_all_settings():
    conn = get_db()
    for table in ("system_settings", "admin_settings"):
        try:
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table}").fetchall()]
            conn.close()
            return rows
        except Exception:
            continue
    conn.close()
    return []


def check_graduation(student_id):
    row = get_student(student_id) or {}
    score = float(row.get('graduation_score') or 0)
    threshold = int(row.get('personal_pass_score') or row.get('target_score') or 70)
    return {'graduated': score >= threshold, 'score': score, 'required': threshold}


def get_daily_missions(student_id=None):
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM daily_missions WHERE COALESCE(is_active,1)=1 ORDER BY id ASC").fetchall()]
    conn.close()
    return rows


def add_daily_mission(title, description, skill_type='general', xp_reward=10, mission_date=None, **extra):
    mission_date = mission_date or datetime.utcnow().date().isoformat()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO daily_missions (title, description, skill_type, xp_reward, mission_date, is_active, mission_type, target_count) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
        (title, description, skill_type, int(xp_reward or 10), mission_date, extra.get('mission_type', 'lesson'), int(extra.get('target_count', 1) or 1)),
    )
    conn.commit()
    mission_id = cur.lastrowid
    conn.close()
    return mission_id


def complete_mission(student_id, mission_id):
    sid = _norm_sid(student_id)
    conn = get_db()
    try:
        conn.execute("INSERT INTO user_missions (user_id, mission_id, completed_at) VALUES (?, ?, datetime('now'))", (sid, mission_id))
    except Exception:
        pass
    conn.commit()
    conn.close()
    return True


def get_grading_rules():
    conn = get_db()
    try:
        rows = [dict(r) for r in conn.execute("SELECT * FROM essay_grading_rules ORDER BY id").fetchall()]
    except Exception:
        rows = []
    conn.close()
    return rows


def grade_essay(text, *args, **kwargs):
    text = text or ""
    wc = len(text.split())
    score = min(5.5, max(1.0, 1.0 + wc / 80.0))
    return {
        'score': round(score, 1),
        'feedback': 'Automatic placeholder feedback. Replace with human/AI grading pipeline when available.',
        'word_count': wc,
    }


def get_phase_settings():
    conn = get_db()
    try:
        rows = [dict(r) for r in conn.execute("SELECT * FROM phase_settings ORDER BY phase_number").fetchall()]
    except Exception:
        rows = []
    conn.close()
    return rows


def update_phase_settings(phase_id, **fields):
    if not fields:
        return False
    conn = get_db()
    sets = []
    values = []
    for key, value in fields.items():
        sets.append(f"{key}=?")
        values.append(value)
    values.append(phase_id)
    conn.execute(f"UPDATE phase_settings SET {', '.join(sets)} WHERE id=?", values)
    conn.commit()
    conn.close()
    return True


def get_questions():
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM questions ORDER BY id DESC").fetchall()]
    conn.close()
    return rows


def add_question(question, answer=None, **extra):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO questions (question, answer) VALUES (?, ?)", (question, answer))
    conn.commit()
    qid = cur.lastrowid
    conn.close()
    return qid


def delete_question(qid):
    conn = get_db()
    conn.execute("DELETE FROM questions WHERE id=?", (qid,))
    conn.commit()
    conn.close()
    return True


def get_payments():
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM payments ORDER BY id DESC").fetchall()]
    conn.close()
    return rows


def add_payment(**fields):
    conn = get_db()
    cur = conn.cursor()
    keys = list(fields.keys())
    vals = [fields[k] for k in keys]
    cur.execute(f"INSERT INTO payments ({', '.join(keys)}) VALUES ({', '.join(['?'] * len(keys))})", vals)
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid


def verify_payment(payment_id):
    conn = get_db()
    conn.execute("UPDATE payments SET status='verified', verified_at=datetime('now') WHERE id=?", (payment_id,))
    conn.commit()
    conn.close()
    return True


def approve_payment(payment_id):
    conn = get_db()
    conn.execute("UPDATE payments SET status='approved', verified_at=datetime('now') WHERE id=?", (payment_id,))
    conn.commit()
    conn.close()
    return True


def create_payment(**fields):
    return add_payment(**fields)


def get_all_payments():
    return get_payments()


def get_leaderboard(limit=20):
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        "SELECT user_id, telegram_id, COALESCE(full_name, name, username, 'طالب') AS name, COALESCE(xp,total_xp,0) AS xp FROM students ORDER BY COALESCE(xp,total_xp,0) DESC, user_id ASC LIMIT ?",
        (int(limit or 20),),
    ).fetchall()]
    conn.close()
    return rows
