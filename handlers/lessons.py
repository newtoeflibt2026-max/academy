# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import sqlite3

router = Router(name="lessons")

DB = r'C:\Users\nelt2\yamen_academy\academy.db'

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

@router.callback_query(F.data == "menu:lessons")
async def show_lessons(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        conn = get_conn()
        lessons = conn.execute(
            "SELECT * FROM lessons ORDER BY order_num LIMIT 10"
        ).fetchall()
        conn.close()
    except Exception:
        lessons = []

    kb = InlineKeyboardBuilder()
    if lessons:
        for lesson in lessons:
            title = lesson['title'] if 'title' in lesson.keys() else f"درس {lesson['id']}"
            kb.button(text=f"📖 {title}", callback_data=f"lesson:{lesson['id']}")
        kb.adjust(1)
    else:
        kb.button(text="🔒 لا توجد دروس متاحة بعد", callback_data="menu:main")

    kb.button(text="🏠 الرئيسية", callback_data="menu:main")
    kb.adjust(1)

    await cb.message.edit_text(
        "📚 <b>الدروس المتاحة</b>\n\nاختر الدرس الذي تريد البدء به:",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data.startswith("lesson:"))
async def open_lesson(cb: CallbackQuery, state: FSMContext):
    lesson_id = cb.data.split(":")[1]
    try:
        conn = get_conn()
        lesson = conn.execute("SELECT * FROM lessons WHERE id=?", (lesson_id,)).fetchone()
        conn.close()
    except Exception:
        lesson = None

    kb = InlineKeyboardBuilder()
    kb.button(text="📋 الدروس", callback_data="menu:lessons")
    kb.button(text="🏠 الرئيسية", callback_data="menu:main")
    kb.adjust(2)

    if lesson:
        title = lesson['title'] if 'title' in lesson.keys() else "درس"
        content = lesson['content'] if 'content' in lesson.keys() else "لا يوجد محتوى بعد."
        await cb.message.edit_text(
            f"📖 <b>{title}</b>\n\n{content}",
            reply_markup=kb.as_markup()
        )
    else:
        await cb.message.edit_text(
            "❌ الدرس غير موجود.",
            reply_markup=kb.as_markup()
        )
    await cb.answer()
