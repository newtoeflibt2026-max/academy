# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, WebAppInfo
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database_v2 import (
    get_student, create_student, get_subscription,
    check_graduation, get_skills_progress, get_setting
)
from utils.states import RegistrationStates
from config import settings

router = Router(name="start")

def main_menu_kb(is_paid=False, student_id=None):
    kb = InlineKeyboardBuilder()
    base_url = settings.WEBHOOK_HOST.rstrip("/")
    toefl_active = get_setting("toefl_active", "1") == "1"

    if toefl_active:
        if is_paid and student_id:
            kb.button(
                text="🚀 لوحة التحكم",
                web_app=WebAppInfo(
                    url=f"{base_url}/student?student_id={student_id}"
                )
            )
        kb.button(text="📚 دروسي اليومية", callback_data="menu:lessons")
        kb.button(text="🔬 اختبار تحديد المستوى", callback_data="start_placement")
        kb.button(text="✍️ تصحيح ذكي", callback_data="menu:correction")
        kb.button(text="🏆 لوحة الصدارة", callback_data="menu:leaderboard")
        kb.button(text="💎 الباقات والاشتراك", callback_data="menu:subscribe")
        kb.button(text="👤 ملفي الشخصي", callback_data="menu:profile")
    else:
        kb.button(text="🔒 TOEFL — قريباً", callback_data="coming_soon")

    kb.button(text="🔒 IELTS — قريباً", callback_data="coming_soon")
    kb.adjust(1)
    return kb.as_markup()

def path_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎓 TOEFL iBT الدولي", callback_data="reg:path:toefl")
    kb.button(text="🔒 IELTS — قريباً", callback_data="coming_soon")
    kb.adjust(1)
    return kb.as_markup()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = str(message.from_user.id)
    student = get_student(user_id)

    if student:
        sub = get_subscription(user_id)
        is_paid = bool(student.get("is_paid")) or sub is not None
        status = "✅ مشترك مدفوع" if is_paid else "🆓 مجاني"
        level_map = {
            "beginner": "مبتدئ",
            "intermediate": "متوسط",
            "advanced": "متقدم"
        }
        level = level_map.get(student.get("level", "beginner"), "مبتدئ")
        await message.answer(
            f"🏠 <b>مرحباً {student['name']}!</b>\n\n"
            f"🎯 المستوى: <b>{level}</b>\n"
            f"⭐ XP: <b>{student.get('xp', 0)}</b>\n"
            f"🔥 Streak: <b>{student.get('streak_days', 0)} يوم</b>\n"
            f"💳 الاشتراك: <b>{status}</b>\n\n"
            "اختر من القائمة 👇",
            reply_markup=main_menu_kb(is_paid, user_id)
        )
    else:
        await message.answer(
            "👋 <b>أهلاً بك في أكاديمية يامن!</b>\n\n"
            "🎓 منصتك الذكية للوصول لـ TOEFL iBT\n\n"
            "📝 <b>أرسل اسمك الكامل للبدء:</b>"
        )
        await state.set_state(RegistrationStates.waiting_for_name)

@router.message(RegistrationStates.waiting_for_name)
async def reg_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if len(name) < 2 or len(name) > 60:
        await message.answer("⚠️ الاسم يجب أن يكون بين 2 و60 حرف:")
        return
    await state.update_data(name=name)
    await message.answer(
        f"✅ أهلاً <b>{name}</b>!\n\n🎓 <b>اختر مسارك:</b>",
        reply_markup=path_kb()
    )
    await state.set_state(RegistrationStates.waiting_for_path)

@router.callback_query(RegistrationStates.waiting_for_path,
                       F.data.startswith("reg:path:"))
async def reg_path(cb: CallbackQuery, state: FSMContext):
    path = cb.data.split(":")[2]
    data = await state.get_data()
    user_id = str(cb.from_user.id)
    student = create_student(
        telegram_id=user_id,
        name=data["name"],
        username=cb.from_user.username,
        path_type=path
    )
    await state.clear()
    await cb.message.edit_text(
        f"🎉 <b>تم تسجيلك في أكاديمية يامن!</b>\n\n"
        f"👤 الاسم: <b>{data['name']}</b>\n"
        f"🎓 المسار: <b>TOEFL iBT</b>\n\n"
        "ابدأ باختبار تحديد مستواك 👇",
        reply_markup=main_menu_kb(False, user_id)
    )
    await cb.answer("✅ تم التسجيل!")

@router.callback_query(F.data == "coming_soon")
async def coming_soon(cb: CallbackQuery):
    await cb.answer("🔒 هذا المسار سيفتح قريباً!", show_alert=True)

@router.callback_query(F.data == "menu:main")
async def cb_main(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = str(cb.from_user.id)
    student = get_student(user_id)
    if not student:
        await cb.message.edit_text("⚠️ أرسل /start للتسجيل.")
        await cb.answer()
        return
    sub = get_subscription(user_id)
    is_paid = bool(student.get("is_paid")) or sub is not None
    await cb.message.edit_text(
        f"🏠 <b>القائمة الرئيسية</b>\n\n"
        f"👤 {student['name']} | ⭐ {student.get('xp',0)} XP",
        reply_markup=main_menu_kb(is_paid, user_id)
    )
    await cb.answer()

@router.callback_query(F.data == "menu:profile")
async def cb_profile(cb: CallbackQuery):
    user_id = str(cb.from_user.id)
    student = get_student(user_id)
    if not student:
        await cb.answer("أرسل /start أولاً", show_alert=True)
        return
    skills = get_skills_progress(user_id)
    sub = get_subscription(user_id)
    is_paid = bool(student.get("is_paid")) or sub is not None
    sub_text = f"✅ مدفوع حتى {sub['end_date'][:10]}" if sub else \
               ("✅ مفعّل" if is_paid else "🔒 مجاني")
    can_grad, grad_msg = check_graduation(user_id)
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 اشترك", callback_data="menu:subscribe")
    kb.button(text="🏠 رجوع", callback_data="menu:main")
    kb.adjust(2)
    await cb.message.edit_text(
        f"👤 <b>ملفك الشخصي</b>\n\n"
        f"📛 {student['name']}\n"
        f"🆔 <code>{user_id}</code>\n"
        f"🎓 المستوى: {student.get('level','beginner')}\n"
        f"⭐ XP: <b>{student.get('xp',0)}</b>\n"
        f"🔥 Streak: <b>{student.get('streak_days',0)} يوم</b>\n"
        f"✅ مهام: <b>{student.get('tasks_completed',0)}</b>\n"
        f"💳 {sub_text}\n\n"
        f"<b>📊 تقدم المهارات:</b>\n"
        f"📖 Reading: {skills.get('reading_xp',0)} XP\n"
        f"🎧 Listening: {skills.get('listening_xp',0)} XP\n"
        f"🎤 Speaking: {skills.get('speaking_xp',0)} XP\n"
        f"✍️ Writing: {skills.get('writing_xp',0)} XP\n\n"
        f"🎓 بوابة التخرج: {'✅ مؤهل' if can_grad else '🔒 لم تكتمل الشروط'}",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data == "menu:leaderboard")
async def cb_leaderboard(cb: CallbackQuery):
    from database_v2 import get_leaderboard_data, get_student_rank
    board = get_leaderboard_data(10)
    user_id = str(cb.from_user.id)
    rank, xp = get_student_rank(user_id)
    text = "🏆 <b>لوحة الصدارة</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, s in enumerate(board):
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} {s['name']} — {s['xp']} XP\n"
    if rank:
        text += f"\n📍 مرتبتك: <b>#{rank}</b> ({xp} XP)"
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 رجوع", callback_data="menu:main")
    await cb.message.edit_text(text, reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data == "menu:subscribe")
async def cb_subscribe(cb: CallbackQuery):
    from handlers.subscriptions import show_plans
    await show_plans(cb)

@router.callback_query(F.data.in_({"menu:lessons", "menu:correction",
                                    "start_placement"}))
async def cb_feature(cb: CallbackQuery):
    user_id = str(cb.from_user.id)
    student = get_student(user_id)
    if not student:
        await cb.answer("أرسل /start أولاً", show_alert=True)
        return
    if cb.data == "start_placement":
        from handlers.placement_test import start_placement
        start_placement(cb)
    elif cb.data == "menu:lessons":
        from handlers.lessons import show_lessons
        await show_lessons(cb)
    elif cb.data == "menu:correction":
        from handlers.correction import correction_menu
        await correction_menu(cb, None)
    await cb.answer()
