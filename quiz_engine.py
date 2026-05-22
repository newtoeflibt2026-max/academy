# -*- coding: utf-8 -*-
"""
quiz_engine.py — Wave 5.4-A
يضيف: خلط ترتيب الأسئلة + خلط الخيارات + إخفاء الإجابة عند الخطأ.
"""
import sqlite3
import json
import logging
import random
from datetime import datetime
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Dynamic DB path (Railway volume / local fallback)
import os as _os_dbpath
_RAILWAY_DB = "/app/data/academy.db"
_LOCAL_DB = _os_dbpath.path.join(_os_dbpath.path.dirname(_os_dbpath.path.abspath(__file__)), "academy.db")
DB_PATH = _RAILWAY_DB if _os_dbpath.path.exists("/app/data") else _LOCAL_DB
PASS_THRESHOLD = 0.6  # 2 من 3 = نجاح

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_required_streak(target_score: int) -> int:
    """يحدد عدد الإجابات المتتالية المطلوبة حسب هدف الطالب."""
    if not target_score:
        return 3
    if target_score < 60:
        return 3
    elif target_score < 80:
        return 4
    else:
        return 5

def get_student_target(telegram_id: str) -> int:
    """يجلب target_score للطالب."""
    conn = _db()
    try:
        row = conn.execute(
            "SELECT target_score FROM students WHERE telegram_id = ?",
            (str(telegram_id),)
        ).fetchone()
        return int(row["target_score"]) if row and row["target_score"] else 69
    finally:
        conn.close()

# ============================================
# 1) جلب أسئلة الكويز مع خلط
# ============================================
def get_lesson_quiz(lesson_id: int, shuffle: bool = True) -> List[Dict]:
    """يرجع قائمة أسئلة الدرس. إذا shuffle=True يخلط ترتيب الأسئلة والخيارات."""
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
                # خلط الخيارات: نأخذ القيم ونعيد توزيعها على A/B/C/D
                original_correct_text = original_options.get(q["correct_answer"], "")
                values = list(original_options.values())
                random.shuffle(values)
                new_keys = ["A", "B", "C", "D"][:len(values)]
                new_options = dict(zip(new_keys, values))
                # العثور على الموقع الجديد للإجابة الصحيحة
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

# ============================================
# 2) فحص إجابة باستخدام correct_answer المُمرَّر
# ============================================
def check_answer_dynamic(correct_answer: str, user_answer: str) -> bool:
    """فحص بسيط — يستخدم القيمة المُمررة (بعد الخلط)."""
    return (user_answer or "").strip().upper() == (correct_answer or "").strip().upper()

def check_answer(question_id: int, user_answer: str) -> Tuple[bool, str, str]:
    """نسخة قديمة للتوافق — تستخدم القيمة في DB (بدون خلط)."""
    conn = _db()
    try:
        row = conn.execute(
            "SELECT correct_answer, explanation FROM lesson_questions WHERE id = ?",
            (question_id,)
        ).fetchone()
        if not row:
            return False, "", "Question not found"
        correct = (row["correct_answer"] or "").strip().upper()
        user = (user_answer or "").strip().upper()
        return (user == correct, row["correct_answer"], row["explanation"] or "")
    finally:
        conn.close()

# ============================================
# 3) بدء محاولة كويز
# ============================================
def start_quiz_attempt(telegram_id: str, lesson_id: int) -> int:
    conn = _db()
    try:
        cur = conn.execute("""
            INSERT INTO lesson_attempts
                (telegram_id, lesson_id, started_at, correct_count, total_questions, passed)
            VALUES (?, ?, CURRENT_TIMESTAMP, 0, 0, 0)
        """, (str(telegram_id), lesson_id))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

# ============================================
# 4) إنهاء محاولة كويز
# ============================================
def finish_quiz_attempt(attempt_id: int, correct: int, total: int,
                        answers: List[Dict]) -> Tuple[bool, float]:
    if total <= 0:
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
              json.dumps(answers, ensure_ascii=False), attempt_id))
        conn.commit()
        return (passed == 1, score)
    finally:
        conn.close()

# ============================================
# 5) تسجيل خطأ
# ============================================
def record_mistake(telegram_id: str, question_id: int, wrong_answer: str,
                   correct_answer: str = "") -> None:
    conn = _db()
    try:
        existing = conn.execute("""
            SELECT id FROM student_error_bank
            WHERE telegram_id = ? AND question_id = ?
        """, (str(telegram_id), question_id)).fetchone()
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
            """, (str(telegram_id), question_id))
        try:
            conn.execute("""
                INSERT INTO error_bank
                    (user_id, question_id, error_type, wrong_answer, correct_answer)
                VALUES (?, ?, 'quiz', ?, ?)
            """, (int(telegram_id) if str(telegram_id).isdigit() else 0,
                  question_id, wrong_answer, correct_answer))
        except Exception as e:
            logger.warning(f"error_bank insert skipped: {e}")
        conn.commit()
    finally:
        conn.close()

# ============================================
# 6) رسالة نتيجة الكويز
# ============================================
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
    else:
        return (
            f"📝 لم تجتز الكويز هذه المرة\n\n"
            f"📊 نتيجتك: {correct}/{total} ({score}%)\n"
            f"🎯 الحد الأدنى: إجابتان صحيحتان من ثلاث\n\n"
            f"💡 راجع الدرس وفكّر في كل سؤال — ستحصل على مجموعة أسئلة مرتبة بشكل مختلف!"
        )

# ============================================
# 7) إحصائيات الطالب
# ============================================
def get_student_lesson_stats(telegram_id: str, lesson_id: int) -> Dict:
    conn = _db()
    try:
        rows = conn.execute("""
            SELECT correct_count, total_questions, passed, score_percent, finished_at
            FROM lesson_attempts
            WHERE telegram_id = ? AND lesson_id = ? AND finished_at IS NOT NULL
            ORDER BY id DESC
        """, (str(telegram_id), lesson_id)).fetchall()
        if not rows:
            return {"attempts": 0, "passed": False, "best_score": 0.0, "last_attempt": None}
        return {
            "attempts": len(rows),
            "passed": any(r["passed"] for r in rows),
            "best_score": max(r["score_percent"] or 0 for r in rows),
            "last_attempt": rows[0]["finished_at"],
        }
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    tid = sys.argv[1] if len(sys.argv) > 1 else "5572314718"
    lesson_id = int(sys.argv[2]) if len(sys.argv) > 2 else 31

    print(f"\n=== Quiz Engine Test (with shuffling) ===")
    print(f"Student: {tid} | Lesson: {lesson_id}\n")

    for run in range(2):
        print(f"\n--- Run #{run+1} (questions reshuffled) ---")
        questions = get_lesson_quiz(lesson_id, shuffle=True)
        for i, q in enumerate(questions, 1):
            print(f"  Q{i} [{q['q_id']}]: correct={q['correct_answer']}")
            for k, v in q['options'].items():
                marker = " ← correct" if k == q['correct_answer'] else ""
                print(f"     {k}) {v[:40]}{marker}")

# ============================================
# 8) نظام العودة المتدرجة (Smart Cooldown)
# ============================================
from datetime import timedelta

# جدول الانتظار: محاولة → دقائق
COOLDOWN_SCHEDULE = {
    1: 15,      # المحاولة 2 بعد 15 دقيقة
    2: 45,      # المحاولة 3 بعد 45 دقيقة
    3: 120,     # المحاولة 4 بعد 2 ساعة
    4: 240,     # المحاولة 5 بعد 4 ساعات
    5: 1440,    # المحاولة 6+ بعد 24 ساعة
}

MOTIVATION_MESSAGES = {
    1: "💪 مجرد بداية! استرح وارجع للدرس",
    2: "🌱 المعرفة تنمو بالصبر والمراجعة",
    3: "🎯 أنت قريب جداً، استمر بثقة",
    4: "🏆 المثابرون يصلون لأهدافهم",
    5: "⭐ كل محاولة تقربك من الإتقان",
}

def get_cooldown_status(telegram_id: str, lesson_id: int) -> Dict:
    """يرجع: {in_cooldown, seconds_left, failed_attempts, motivation}"""
    conn = _db()
    try:
        row = conn.execute("""
            SELECT failed_attempts, next_attempt_at
            FROM quiz_attempts_cooldown
            WHERE telegram_id = ? AND lesson_id = ?
        """, (str(telegram_id), lesson_id)).fetchone()
        if not row or not row["next_attempt_at"]:
            return {"in_cooldown": False, "seconds_left": 0,
                    "failed_attempts": 0, "motivation": ""}
        try:
            next_at = datetime.fromisoformat(row["next_attempt_at"])
        except Exception:
            next_at = datetime.strptime(row["next_attempt_at"], "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        if now >= next_at:
            return {"in_cooldown": False, "seconds_left": 0,
                    "failed_attempts": row["failed_attempts"], "motivation": ""}
        seconds_left = int((next_at - now).total_seconds())
        attempt_num = min(row["failed_attempts"], 5)
        motivation = MOTIVATION_MESSAGES.get(attempt_num, MOTIVATION_MESSAGES[5])
        return {
            "in_cooldown": True,
            "seconds_left": seconds_left,
            "failed_attempts": row["failed_attempts"],
            "motivation": motivation,
        }
    finally:
        conn.close()

def register_failed_attempt(telegram_id: str, lesson_id: int) -> Dict:
    """يسجل رسوب ويحسب وقت المحاولة القادمة. يرجع معلومات الانتظار."""
    conn = _db()
    try:
        row = conn.execute("""
            SELECT failed_attempts FROM quiz_attempts_cooldown
            WHERE telegram_id = ? AND lesson_id = ?
        """, (str(telegram_id), lesson_id)).fetchone()

        current_fails = row["failed_attempts"] if row else 0
        new_fails = current_fails + 1
        # جدول الانتظار: استخدم new_fails للحصول على المدة
        wait_minutes = COOLDOWN_SCHEDULE.get(min(new_fails, 5), 1440)
        next_at = datetime.now() + timedelta(minutes=wait_minutes)
        next_at_str = next_at.strftime("%Y-%m-%d %H:%M:%S")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if row:
            conn.execute("""
                UPDATE quiz_attempts_cooldown
                SET failed_attempts = ?, next_attempt_at = ?, last_failed_at = ?
                WHERE telegram_id = ? AND lesson_id = ?
            """, (new_fails, next_at_str, now_str, str(telegram_id), lesson_id))
        else:
            conn.execute("""
                INSERT INTO quiz_attempts_cooldown
                (telegram_id, lesson_id, failed_attempts, next_attempt_at, last_failed_at)
                VALUES (?, ?, ?, ?, ?)
            """, (str(telegram_id), lesson_id, new_fails, next_at_str, now_str))
        conn.commit()

        motivation = MOTIVATION_MESSAGES.get(min(new_fails, 5), MOTIVATION_MESSAGES[5])
        return {
            "wait_minutes": wait_minutes,
            "wait_seconds": wait_minutes * 60,
            "next_attempt_at": next_at_str,
            "failed_attempts": new_fails,
            "motivation": motivation,
        }
    finally:
        conn.close()

def clear_cooldown(telegram_id: str, lesson_id: int) -> None:
    """عند النجاح، نمسح الـ cooldown."""
    conn = _db()
    try:
        conn.execute("""
            DELETE FROM quiz_attempts_cooldown
            WHERE telegram_id = ? AND lesson_id = ?
        """, (str(telegram_id), lesson_id))
        conn.commit()
    finally:
        conn.close()

def format_cooldown_time(seconds: int) -> str:
    """يحول الثواني إلى نص عربي مفهوم."""
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
