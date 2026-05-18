# -*- coding: utf-8 -*-
from __future__ import annotations
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from bot_database import get_student, create_student, get_subscription
from utils.states import RegistrationStates
from config import settings

router = Router(name="start")


def build_main_menu(is_active=False, student_id=None):
    kb = InlineKeyboardBuilder()
    if is_active and student_id:
        kb.button(
            text="🚀 افتح لوحة التحكم",
            web_app=WebAppInfo(url=f"{settings.WEBHOOK_HOST}?student_id={student_id}")
        )
        kb.button(text="📚 دروسي",         callback_data="menu:lessons")
        kb.button(text="✍️ تصحيح ذكي",    callback_data="menu:correction")
        kb.button(text="👤 ملفي",          callback_data="menu:profile")
        kb.adjust(1, 2, 1)
    else:
        kb.button(text="💎 اشترك الآن",           callback_data="menu:subscribe")
        kb.button(text="🔬 تحديد المستوى مجاني", callback_data="start_placement")
        kb.button(text="👤 ملفي الشخصي",         callback_data="menu:profile")
        kb.adjust(1)
    return kb.as_markup()


def build_path_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎓 Academic", callback_data="reg:path:academic")
    kb.button(text="🌍 General",  callback_data="reg:path:general")
    kb.adjust(2)
    return kb.as_markup()


def build_band_keyboard():
    kb = InlineKeyboardBuilder()
    for b in [5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]:
        kb.button(text=f"Band {b}", callback_data=f"reg:band:{b}")
    kb.adjust(3)
    return kb.as_markup()


# ── /start ────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    student = await get_student(user_id)

    if student:
        sub = await get_subscription(user_id)
        is_active = bool(student.get("is_active")) or sub is not None
        status = "✅ مشترك" if is_active else "🔒 غير مشترك"
        await message.answer(
            f"🏠 <b>مرحباً {student['name']}!</b>\n\n"
            f"🎯 هدفك: <b>Band {student.get('target_band','—')}</b>\n"
            f"💳 الاشتراك: <b>{status}</b>\n\n"
            "اختر من القائمة 👇",
            reply_markup=build_main_menu(is_active, user_id)
        )
    else:
        await message.answer(
            "👋 <b>أهلاً بك في أكاديمية يامن!</b>\n\n"
            "🎯 سنساعدك على رفع درجتك في IELTS\n\n"
            "📝 <b>أرسل اسمك الكامل للبدء:</b>"
        )
        await state.set_state(RegistrationStates.waiting_for_name)


# ── تسجيل الاسم ───────────────────────────────────────────────
@router.message(RegistrationStates.waiting_for_name)
async def reg_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if len(name) < 2 or len(name) > 60:
        await message.answer("⚠️ الاسم يجب بين 2 و60 حرف. حاول مجدداً:")
        return
    await state.update_data(name=name)
    await message.answer(
        f"✅ أهلاً <b>{name}</b>!\n\n📌 <b>اختر نوع اختبار IELTS:</b>",
        reply_markup=build_path_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_for_path)


# ── تسجيل المسار ──────────────────────────────────────────────
@router.callback_query(RegistrationStates.waiting_for_path, F.data.startswith("reg:path:"))
async def reg_path(cb: CallbackQuery, state: FSMContext):
    path = cb.data.split(":")[2]
    await state.update_data(path_type=path)
    label = "🎓 Academic" if path == "academic" else "🌍 General"
    await cb.message.edit_text(
        f"✅ المسار: <b>{label}</b>\n\n🎯 <b>ما الـ Band المستهدف؟</b>",
        reply_markup=build_band_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_for_target_band)
    await cb.answer()


# ── تسجيل Band ────────────────────────────────────────────────
@router.callback_query(RegistrationStates.waiting_for_target_band, F.data.startswith("reg:band:"))
async def reg_band(cb: CallbackQuery, state: FSMContext):
    band = float(cb.data.split(":")[2])
    await state.update_data(target_band=band)
    kb = InlineKeyboardBuilder()
    for label, val in [("⚡ أقل من 30 يوم", "20"), ("📆 30-90 يوم", "60"), ("📚 أكثر من 90 يوم", "120")]:
        kb.button(text=label, callback_data=f"reg:days:{val}")
    kb.adjust(1)
    await cb.message.edit_text(
        f"✅ هدفك: <b>Band {band}</b>\n\n⏳ <b>كم يوماً لديك قبل الامتحان؟</b>",
        reply_markup=kb.as_markup()
    )
    await state.set_state(RegistrationStates.waiting_for_days)
    await cb.answer()


# ── إنهاء التسجيل ─────────────────────────────────────────────
@router.callback_query(RegistrationStates.waiting_for_days, F.data.startswith("reg:days:"))
async def reg_days(cb: CallbackQuery, state: FSMContext):
    days = int(cb.data.split(":")[2])
    data = await state.get_data()
    user_id = cb.from_user.id
    student = await create_student(
        telegram_id=user_id,
        name=data["name"],
        target_band=data.get("target_band", 6.5),
        path_type=data.get("path_type", "academic"),
        days_left=days
    )
    await state.clear()
    await cb.message.edit_text(
        f"🎉 <b>تم تسجيلك بنجاح!</b>\n\n"
        f"👤 الاسم: <b>{data['name']}</b>\n"
        f"🎯 الهدف: <b>Band {data.get('target_band', 6.5)}</b>\n"
        f"⏳ الأيام: <b>{days} يوم</b>\n\n"
        "ابدأ باختبار المستوى أو اشترك الآن 👇",
        reply_markup=build_main_menu(False, user_id)
    )
    await cb.answer("✅ تم التسجيل!")


# ── القائمة الرئيسية ──────────────────────────────────────────
@router.callback_query(F.data == "menu:main")
async def cb_main(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = cb.from_user.id
    student = await get_student(user_id)
    if not student:
        await cb.message.edit_text("⚠️ أرسل /start للتسجيل.")
        await cb.answer()
        return
    sub = await get_subscription(user_id)
    is_active = bool(student.get("is_active")) or sub is not None
    status = "✅ مشترك" if is_active else "🔒 غير مشترك"
    try:
        await cb.message.edit_text(
            f"🏠 <b>مرحباً {student['name']}!</b>\n\n"
            f"💳 الاشتراك: <b>{status}</b>\n\n"
            "اختر من القائمة 👇",
            reply_markup=build_main_menu(is_active, user_id)
        )
    except Exception:
        pass
    await cb.answer()


# ── التحقق من الاشتراك في القناة (Force Sub) ─────────────────
@router.callback_query(F.data == "force_sub_check")
async def cb_force_sub_check(cb: CallbackQuery):
    """يُشغَّل عندما يضغط المستخدم «تحققت من الاشتراك»"""
    from middlewares.force_sub import check_all_channels
    user_id = cb.from_user.id
    subscribed = await check_all_channels(cb.bot, user_id)
    if subscribed:
        # مشترك → أكمل كـ /start عادي
        student = await get_student(user_id)
        if student:
            sub = await get_subscription(user_id)
            is_active = bool(student.get("is_active")) or sub is not None
            await cb.message.edit_text(
                f"✅ <b>شكراً على الاشتراك!</b>\n\n"
                f"أهلاً <b>{student['name']}</b>!\n\n"
                "اختر من القائمة 👇",
                reply_markup=build_main_menu(is_active, user_id)
            )
        else:
            await cb.message.edit_text(
                "✅ <b>تم التحقق!</b>\n\n📝 <b>أرسل اسمك الكامل للتسجيل:</b>"
            )
        await cb.answer("✅ تم التحقق!")
    else:
        await cb.answer(
            "⛔ لم يتم الاشتراك بعد! اشترك في القناة أولاً.",
            show_alert=True
        )