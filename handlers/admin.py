# -*- coding: utf-8 -*-
"""
handlers/admin.py — لوحة تحكم الأدمن من البوت
يكتفي بإرسال رابط لوحة التحكم. الموافقة/الرفض على المدفوعات
يتعامل معها handlers/payments.py مباشرة.
"""
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import settings

router = Router(name="admin")


@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """يرسل رابط لوحة التحكم للأدمن فقط."""
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("⛔ هذا الأمر متاح للأدمن فقط.")
        return

    # استخرج رابط لوحة التحكم من settings
    panel_url = settings.WEBHOOK_HOST.rstrip("/") + "/"

    kb = InlineKeyboardBuilder()
    kb.button(text="🌐 فتح لوحة التحكم", url=panel_url)
    kb.button(text="👥 إدارة الطلاب", url=panel_url + "#students")
    kb.button(text="💳 المدفوعات", url=panel_url + "#payments")
    kb.button(text="📚 الدروس والأسئلة", url=panel_url + "#lessons")
    kb.adjust(1, 2, 1)

    await message.answer(
        f"👑 <b>لوحة تحكم الأدمن</b>\n\n"
        f"مرحباً {message.from_user.full_name} 👋\n\n"
        f"🌐 الرابط: <code>{panel_url}</code>\n\n"
        f"اضغط الزر أدناه لفتح اللوحة:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )


@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """إحصائيات سريعة في البوت — للأدمن فقط."""
    if message.from_user.id not in settings.ADMIN_IDS:
        return

    import sqlite3
    try:
        conn = sqlite3.connect(settings.DB_PATH)
        cur  = conn.cursor()
        s_total = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        s_paid  = cur.execute("SELECT COUNT(*) FROM students WHERE is_paid=1").fetchone()[0]
        p_pend  = cur.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
        lessons = cur.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
        quests  = cur.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        conn.close()
    except Exception as e:
        await message.answer(f"❌ خطأ: {e}")
        return

    await message.answer(
        f"📊 <b>إحصائيات سريعة</b>\n\n"
        f"👥 الطلاب: <b>{s_total}</b>\n"
        f"💰 المدفوعين: <b>{s_paid}</b>\n"
        f"⏳ مدفوعات بانتظار: <b>{p_pend}</b>\n"
        f"📚 الدروس: <b>{lessons}</b>\n"
        f"❓ الأسئلة: <b>{quests}</b>",
        parse_mode="HTML"
    )