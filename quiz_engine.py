# -*- coding: utf-8 -*-
"""
quiz_engine.py — v2 production-ready
- Unified DB path (delegates to db.py resolver)
- Safer error handling (never raises 500 on optional features)
- Defensive normalisation of inputs
"""
import sqlite3
import json
import logging
import random
import os as _os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# ========== Unified DB path resolver (matches db.py) ==========
def _resolve_db_path():
    env_path = _os.environ.get("DB_PATH", "").strip()
    if env_path:
        return env_path
    if _os.path.isdir("/app/data"):
        return "/app/data/academy.db"
    return _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "academy.db")


DB_PATH = _resolve_db_path()
PASS_THRESHOLD = 0.6  # 60% = نجاح


def _db():
    """Safe SQLite connection (WAL, busy_timeout)."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
    except Exception:
        pass
    return conn


# ========== Streak / target ==========
def get_required_streak(target_score: int) -> int:
    if not target_score:
        return 3
    if target_score < 60:
        return 3
    elif target_score < 80:
        return 4
    else:
        return 5


def get_student_target(telegram_id) -> int:
    """يجلب target_score للطالب (مع تطبيع id)."""
    sid = str(telegram_id) if telegram_id is not None else ""
    if not sid or sid in ("0", "999", "12345") or not sid.isdigit():  # RECORD_MISTAKE_GUARD
        return 69
    conn = _db()
    try:
        row = conn.execute(
            "SELECT target_score FROM students WHERE CAST(user_id AS TEXT)=? OR telegram_id=?",
            (sid, sid)
        ).fetchone()
        if row and row["target_score"]:
            try:
                return int(row["target_score"])
            except Exception:
                return 69
        return 69
    except Exception as e:
        logger.warning(f"get_student_target error: {e}")
        return 69
    finally:
        conn.close()


# ========== Get quiz with shuffling ==========
def get_lesson_quiz(lesson_id: int, shuffle: bool = True) -> List[Dict]:
    conn = _db()
    try:
        rows = conn.execute("""
            SELECT id, q_id, q_type, question, options_json,
                   correct_answer, explanation, tip, timer_seconds, order_num
            FROM lesson_questions
            WHERE lesson_id = ?
            ORDER BY RANDOM()
            LIMIT 8
        """, (lesson_id,)).fetchall()

        questions = []
        for r in rows:
            q = dict(r)
            try:
                original_options = json.loads(q["options_json"]) if q["options_json"] else {}
            except Exception:
                original_options = {}

            if shuffle and original_options:
                original_correct_text = original_options.get(q["correct_answer"], "")
                values = list(original_options.values())
                random.shuffle(values)
                new_keys = ["A", "B", "C", "D"][:len(values)]
                new_options = dict(zip(new_keys, values))
                new_correct = next(
                    (k for k, v in new_options.items() if v == original_correct_text),
                    q["correct_answer"]
                )
                q["options"] = new_options
                q["correct_answer"] = new_correct
            else:
                q["options"] = original_options
            questions.append(q)

        if shuffle:
            random.shuffle(questions)
        return questions
    finally:
        conn.close()


def check_answer_dynamic(correct_answer: str, user_answer: str) -> bool:
    return (user_answer or "").strip().upper() == (correct_answer or "").strip().upper()


def check_answer(question_id, user_answer) -> Tuple[bool, str, str]:
    """Defensive check_answer - never raises."""
    try:
        qid = int(question_id)
    except Exception:
        return False, "", "Invalid question_id"
    user = (str(user_answer) if user_answer is not None else "").strip().upper()
    conn = _db()
    try:
        row = conn.execute(
            "SELECT correct_answer, explanation FROM lesson_questions WHERE id = ?",
            (qid,)
        ).fetchone()
        if not row:
            return False, "", "Question not found"
        correct = (row["correct_answer"] or "").strip().upper()
        return (user == correct, row["correct_answer"] or "", row["explanation"] or "")
    except Exception as e:
        logger.warning(f"check_answer error: {e}")
        return False, "", ""
    finally:
        conn.close()


# ========== Attempts ==========
def start_quiz_attempt(telegram_id, lesson_id: int) -> int:
    sid = str(telegram_id)
    conn = _db()
    try:
        cur = conn.execute("""
            INSERT INTO lesson_attempts
                (telegram_id, lesson_id, started_at, correct_count, total_questions, passed)
            VALUES (?, ?, CURRENT_TIMESTAMP, 0, 0, 0)
        """, (sid, int(lesson_id)))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def finish_quiz_attempt(attempt_id, correct: int, total: int,
                        answers: List[Dict]) -> Tuple[bool, float]:
    if not attempt_id or total <= 0:
        return False, 0.0
    score = (correct / total) * 100
    passed = 1 if (correct / total) >= PASS_THRESHOLD else 0
    conn = _db()
    try:
        conn.execute("""
            UPDATE lesson_attempts
            SET finished_at = CURRENT_TIMESTAMP,
                correct_count = ?, total_questions = ?, passed = ?,
                score_percent = ?, answers_json = ?
            WHERE id = ?
        """, (correct, total, passed, score,
              json.dumps(answers, ensure_ascii=False), int(attempt_id)))
        conn.commit()
        return (passed == 1, score)
    finally:
        conn.close()


# ========== Mistakes (defensive) ==========
def record_mistake(telegram_id, question_id: int, wrong_answer: str,
                   correct_answer: str = "") -> None:
    sid = str(telegram_id) if telegram_id is not None else ""
    if not sid:
        return
    conn = _db()
    try:
        existing = conn.execute("""
            SELECT id FROM student_error_bank
            WHERE telegram_id = ? AND question_id = ?
        """, (sid, int(question_id))).fetchone()
        if existing:
            conn.execute("""
                UPDATE student_error_bank
                SET error_count = error_count + 1, last_attempted = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (existing["id"],))
        else:
            conn.execute("""
                INSERT INTO student_error_bank
                    (telegram_id, question_id, error_count, last_attempted)
                VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            """, (sid, int(question_id)))
        # error_bank is best-effort
        try:
            uid_int = int(sid) if sid.isdigit() else 0
            _dup = conn.execute(
                "SELECT id FROM error_bank WHERE user_id=? AND question_id=? AND wrong_answer=? AND COALESCE(is_mastered,0)=0",
                (uid_int, int(question_id), wrong_answer or "")
            ).fetchone()
            if not _dup:  # تجنّب التكرار
                conn.execute("""
                    INSERT INTO error_bank
                        (user_id, question_id, error_type, wrong_answer, correct_answer)
                    VALUES (?, ?, 'quiz', ?, ?)
                """, (uid_int, int(question_id), wrong_answer or "", correct_answer or ""))
        except Exception as e:
            logger.warning(f"error_bank insert skipped: {e}")
        conn.commit()
    except Exception as e:
        logger.warning(f"record_mistake error: {e}")
    finally:
        conn.close()


# ========== Result messages ==========
def get_quiz_result_message_ar(correct: int, total: int, passed: bool) -> str:
    score = round((correct / total) * 100) if total > 0 else 0
    if passed:
        return (
            f"🎉 مبروك! نجحت في الكويز\n\n"
            f"📊 نتيجتك: {correct}/{total} ({score}%)\n"
            f"✅ تم فتح الدرس التالي\n"
            f"⏰ القفل اليومي: 24 ساعة (باقة مجانية)\n\n"
            f"💪 استمر في التقدم!"
        )
    return (
        f"📝 لم تجتز الكويز هذه المرة\n\n"
        f"📊 نتيجتك: {correct}/{total} ({score}%)\n"
        f"🎯 الحد الأدنى: 60% للنجاح\n\n"
        f"💡 راجع الدرس وحاول مرة أخرى."
    )


# ========== Cooldown system ==========
COOLDOWN_SCHEDULE = {1: 5, 2: 15, 3: 60, 4: 240, 5: 1440}  # minutes
MOTIVATION_MESSAGES = {
    1: "حاول مرة أخرى بعد 5 دقائق 💪",
    2: "خذ نفساً عميقاً وعد بعد ربع ساعة 🧠",
    3: "راجع الدرس بعد ساعة وستنجح إن شاء الله 📖",
    4: "خذ استراحة 4 ساعات، الراحة جزء من النجاح ☕",
    5: "عد غداً بطاقة جديدة 🌅",
}


def register_failed_attempt(telegram_id, lesson_id: int) -> Dict:
    sid = str(telegram_id)
    conn = _db()
    try:
        row = conn.execute("""
            SELECT failed_attempts FROM quiz_attempts_cooldown
            WHERE telegram_id = ? AND lesson_id = ?
        """, (sid, int(lesson_id))).fetchone()
        current_fails = row["failed_attempts"] if row else 0
        new_fails = current_fails + 1
        wait_minutes = COOLDOWN_SCHEDULE.get(min(new_fails, 5), 1440)
        next_at = datetime.now() + timedelta(minutes=wait_minutes)
        next_at_str = next_at.strftime("%Y-%m-%d %H:%M:%S")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if row:
            conn.execute("""
                UPDATE quiz_attempts_cooldown
                SET failed_attempts = ?, next_attempt_at = ?, last_failed_at = ?
                WHERE telegram_id = ? AND lesson_id = ?
            """, (new_fails, next_at_str, now_str, sid, int(lesson_id)))
        else:
            conn.execute("""
                INSERT INTO quiz_attempts_cooldown
                (telegram_id, lesson_id, failed_attempts, next_attempt_at, last_failed_at)
                VALUES (?, ?, ?, ?, ?)
            """, (sid, int(lesson_id), new_fails, next_at_str, now_str))
        conn.commit()
        return {
            "wait_minutes": wait_minutes,
            "wait_seconds": wait_minutes * 60,
            "next_attempt_at": next_at_str,
            "failed_attempts": new_fails,
            "motivation": MOTIVATION_MESSAGES.get(min(new_fails, 5), MOTIVATION_MESSAGES[5]),
        }
    except Exception as e:
        logger.warning(f"register_failed_attempt error: {e}")
        return {"wait_minutes": 5, "wait_seconds": 300, "motivation": ""}
    finally:
        conn.close()


def clear_cooldown(telegram_id, lesson_id: int) -> None:
    sid = str(telegram_id)
    conn = _db()
    try:
        conn.execute("""
            DELETE FROM quiz_attempts_cooldown
            WHERE telegram_id = ? AND lesson_id = ?
        """, (sid, int(lesson_id)))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def format_cooldown_time(seconds: int) -> str:
    if seconds <= 0:
        return "الآن"
    if seconds < 60:
        return f"{seconds} ثانية"
    minutes = seconds // 60
    if minutes < 60:
        secs = seconds % 60
        return f"{minutes} دقيقة و{secs} ثانية" if secs else f"{minutes} دقيقة"
    hours = minutes // 60
    mins = minutes % 60
    if hours < 24:
        return f"{hours} ساعة و{mins} دقيقة" if mins else f"{hours} ساعة"
    days = hours // 24
    hrs = hours % 24
    return f"{days} يوم و{hrs} ساعة" if hrs else f"{days} يوم"


def get_student_lesson_stats(telegram_id, lesson_id):
    """Stub: returns simple stats dict for a student/lesson."""
    try:
        import sqlite3, os
        db = os.environ.get("DB_PATH", "academy.db")
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM lesson_attempts WHERE telegram_id=? AND lesson_id=?",
                    (str(telegram_id), lesson_id))
        attempts = cur.fetchone()[0] or 0
        con.close()
        return {"attempts": attempts, "best_score": 0, "passed": False}
    except Exception as e:
        return {"attempts": 0, "best_score": 0, "passed": False, "error": str(e)}

