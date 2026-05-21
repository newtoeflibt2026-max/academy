from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_student, get_leaderboard, get_error_bank
import sqlite3

router = Router()

DB_PATH = "academy.db"


def get_error_bank_count(user_id: int) -> int:
    """Count errors in student error bank."""
    try:
        errors = get_error_bank(user_id)
        return len(errors) if errors else 0
    except Exception:
        # Fallback: count directly from DB
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            n = cur.execute(
                "SELECT COUNT(*) FROM error_bank WHERE user_id = ?",
                (user_id,)
            ).fetchone()[0]
            conn.close()
            return n
        except Exception:
            return 0


def get_quiz_attempts(user_id: int) -> list:
    """Get list of lesson attempts for a user."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        rows = cur.execute(
            """SELECT id, lesson_id, score_percent, passed, finished_at
               FROM lesson_attempts
               WHERE telegram_id = ?
               ORDER BY finished_at DESC""",
            (str(user_id),)
        ).fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "lesson_id": r[1],
                "score": r[2],
                "passed": bool(r[3]),
                "finished_at": r[4],
            }
            for r in rows
        ]
    except Exception:
        return []


@router.callback_query(F.data == "my_progress")
async def my_progress(callback: types.CallbackQuery):
    uid = callback.from_user.id
    student = get_student(uid)
    if not student:
        await callback.answer("سجل أولاً", show_alert=True)
        return

    err_count = get_error_bank_count(uid)
    attempts = get_quiz_attempts(uid)
    passed_count = sum(1 for a in attempts if a["passed"])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="student_menu")],
    ])

    # Build leaderboard text safely
    try:
        lb = get_leaderboard(5) or []
        lb_lines = []
        for i, r in enumerate(lb):
            name = r.get("full_name") or r.get("name") or "طالب"
            xp = r.get("xp", 0)
            lb_lines.append(f"{i+1}. {name} — {xp}XP")
        lb_text = "\n".join(lb_lines) if lb_lines else "لا توجد بيانات بعد"
    except Exception:
        lb_text = "لا توجد بيانات بعد"

    await callback.message.edit_text(
        f"📊 *تقدم {student.get('full_name','الطالب')}*\n\n"
        f"🎯 المستوى: *{student.get('level','?')}*\n"
        f"⭐ XP: *{student.get('xp',0)}*\n"
        f"📝 أخطاء في البنك: *{err_count}*\n"
        f"🧪 محاولات الكويزات: *{len(attempts)}*\n"
        f"✅ كويزات ناجحة: *{passed_count}*\n\n"
        f"🏆 *أفضل 5 طلاب:*\n{lb_text}",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()