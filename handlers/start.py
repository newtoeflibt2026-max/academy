# -*- coding: utf-8 -*-
from aiogram import types, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database_v2 import (
    create_student, get_student, update_streak,
    get_skills_progress, check_graduation,
    get_setting, get_daily_missions, get_leaderboard
)
import logging

logger = logging.getLogger(__name__)
router = Router(name="start")

def get_main_keyboard(is_paid: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📚 الدروس", callback_data="menu_lessons"),
            InlineKeyboardButton(text="🎯 المهام اليومية", callback_data="menu_missions"),
        ],
        [
            InlineKeyboardButton(text="📊 تقدمي", callback_data="menu_progress"),
            InlineKeyboardButton(text="🏆 المتصدرون", callback_data="menu_leaderboard"),
        ],
        [
            InlineKeyboardButton(text="✍️ تدريب الكتابة", callback_data="menu_writing"),
            InlineKeyboardButton(text="🎧 تدريب الاستماع", callback_data="menu_listening"),
        ],
        [
            InlineKeyboardButton(text="🔬 امتحان تحديد المستوى", callback_data="start_placement"),
        ],
    ]
    if is_paid:
        buttons.append([InlineKeyboardButton(text="📝 Mock Exam", callback_data="menu_mock")])
        buttons.append([InlineKeyboardButton(text="🎓 التخرج", callback_data="menu_graduation")])
    else:
        buttons.append([InlineKeyboardButton(text="🔒 Mock Exam (مدفوع)", callback_data="locked_feature")])
    buttons.append([InlineKeyboardButton(text="⚙️ الإعدادات", callback_data="menu_settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""

    create_student(user_id, username=username, full_name=full_name)
    student = get_student(user_id)
    streak = update_streak(user_id)

    welcome_msg = get_setting("bot_welcome_message", "مرحباً بك في أكاديمية يامن للتوفل! 🎓")
    is_paid = bool(student.get("is_paid", 0)) if student else False
    xp = student.get("xp", 0) if student else 0
    level = student.get("level", "beginner") if student else "beginner"
    placement_done = student.get("placement_done", 0) if student else 0

    level_ar = {"beginner": "مبتدئ 🔵", "intermediate": "متوسط 🟡", "advanced": "متقدم 🟢"}.get(level, level)

    text = (
        f"{welcome_msg}\n\n"
        f"👤 {full_name}\n"
        f"⭐ XP: {xp} | 🔥 Streak: {streak} أيام | 📈 {level_ar}\n"
    )
    if is_paid:
        text += "✅ حساب مفعّل\n"
    else:
        text += "⚠️ حساب غير مفعّل — بعض الميزات مقفلة\n"

    if not placement_done:
        text += "\n💡 <b>ننصحك بإجراء امتحان تحديد المستوى أولاً!</b>"

    text += "\n\nاختر من القائمة:"

    await message.answer(text, reply_markup=get_main_keyboard(is_paid), parse_mode="HTML")


@router.message(Command("progress"))
async def cmd_progress(message: types.Message):
    user_id = message.from_user.id
    student = get_student(user_id)
    if not student:
        await message.answer("❌ سجّل أولاً بـ /start")
        return
    skills = get_skills_progress(user_id)
    text = (
        f"📊 <b>تقدمك في الأكاديمية</b>\n\n"
        f"⭐ إجمالي XP: {student.get('xp', 0)}\n"
        f"🔥 Streak: {student.get('streak', 0)} أيام\n"
        f"✅ مهام مكتملة: {student.get('tasks_completed', 0)}\n\n"
        f"<b>المهارات:</b>\n"
        f"📖 القراءة: {skills.get('reading_xp', 0)} XP\n"
        f"🎧 الاستماع: {skills.get('listening_xp', 0)} XP\n"
        f"🗣️ التحدث: {skills.get('speaking_xp', 0)} XP\n"
        f"✍️ الكتابة: {skills.get('writing_xp', 0)} XP\n"
        f"📝 القواعد: {skills.get('grammar_xp', 0)} XP\n"
        f"📚 المفردات: {skills.get('vocabulary_xp', 0)} XP\n"
    )
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "locked_feature")
async def callback_locked(callback: types.CallbackQuery):
    msg = get_setting("paid_required_message", "⚠️ هذه الميزة للمشتركين فقط. تواصل مع الأدمن.")
    await callback.answer(msg, show_alert=True)


@router.callback_query(F.data == "menu_graduation")
async def callback_graduation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    student = get_student(user_id)
    if not student or not student.get("is_paid"):
        msg = get_setting("paid_required_message", "⚠️ هذه الميزة للمشتركين فقط.")
        await callback.answer(msg, show_alert=True)
        return
    result = check_graduation(user_id)
    checks_text = "\n".join(c["message"] for c in result.get("checks", []))
    if result.get("eligible"):
        text = f"🎓 <b>أهلاً بك في التخرج!</b>\n\n{checks_text}\n\n✅ أنت مؤهل للتخرج! تواصل مع الأدمن."
    else:
        text = f"🎓 <b>شروط التخرج:</b>\n\n{checks_text}\n\n❌ لم تستوفِ جميع الشروط بعد."
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_progress")
async def callback_progress(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_progress(callback.message)


@router.callback_query(F.data == "menu_leaderboard")
async def callback_leaderboard(callback: types.CallbackQuery):
    await callback.answer()
    leaders = get_leaderboard(10)
    if not leaders:
        await callback.message.answer("📊 لا توجد بيانات بعد")
        return
    text = "🏆 <b>المتصدرون:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    for i, s in enumerate(leaders):
        name = s.get("full_name") or s.get("username") or f"مجهول_{s['user_id']}"
        text += f"{medals[i]} {name} — {s.get('xp', 0)} XP\n"
    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "menu_missions")
async def callback_missions(callback: types.CallbackQuery):
    await callback.answer()
    from datetime import date
    today = date.today().isoformat()
    missions = get_daily_missions(today)
    if not missions:
        missions = get_daily_missions()
    if not missions:
        await callback.message.answer("📋 لا توجد مهام يومية اليوم")
        return
    text = "🎯 <b>المهام اليومية:</b>\n\n"
    for m in missions[:5]:
        text += f"• {m['title']} (+{m.get('xp_reward', 0)} XP)\n  {m.get('description', '')}\n\n"
    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "menu_settings")
async def callback_settings(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    student = get_student(user_id)
    if not student:
        await callback.message.answer("❌ سجّل أولاً بـ /start")
        return
    text = (
        f"⚙️ <b>إعداداتك</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 الاسم: {student.get('full_name', '—')}\n"
        f"📱 الهاتف: {student.get('phone', 'غير مسجل')}\n"
        f"💳 النوع: {'مدفوع ✅' if student.get('is_paid') else 'مجاني ⚠️'}\n\n"
        f"للتواصل مع الدعم أو الاشتراك: @YamenAdmin"
    )
    await callback.message.answer(text, parse_mode="HTML")
