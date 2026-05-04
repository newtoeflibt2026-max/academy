from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_student, get_leaderboard, get_error_bank_count, get_quiz_attempts

router = Router()

@router.callback_query(F.data == "my_progress")
async def my_progress(callback: types.CallbackQuery):
    uid = callback.from_user.id
    student = get_student(uid)
    if not student:
        await callback.answer("سجل أولاً", show_alert=True); return
    err_count = get_error_bank_count(uid)
    attempts = get_quiz_attempts(uid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="student_menu")],
    ])
    await callback.message.edit_text(
        f"📊 *تقدم {student.get('full_name','الطالب')}*\n\n"
        f"🎯 المستوى: *{student.get('level','?')}*\n"
        f"⭐ XP: *{student.get('xp',0)}*\n"
        f"📝 أخطاء في البنك: *{err_count}*\n"
        f"🧪 اختبارات مكتملة: *{len(attempts)}*\n\n"
        f"🏆 *أفضل 5 طلاب:*\n" +
        "\n".join([f"{i+1}. {r['full_name']} — {r['xp']}XP"
                   for i,r in enumerate(get_leaderboard(5))]),
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()
