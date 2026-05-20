# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database_v2 import add_xp
import sqlite3, os, logging, json

logger = logging.getLogger(__name__)
router = Router(name="lessons")

DB_PATH = r"C:\Users\nelt2\yamen_academy\academy.db"

SKILL_EMOJI = {
    "reading":    "📖",
    "listening":  "🎧",
    "speaking":   "🗣️",
    "writing":    "✍️",
    "grammar":    "📝",
    "vocabulary": "📚",
}


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.callback_query(F.data == "menu_lessons")
async def show_lessons(cb: CallbackQuery):
    await cb.answer()
    try:
        conn = db()
        rows = conn.execute(
            "SELECT id, title, skill_type, stage, xp_reward "
            "FROM lessons WHERE is_active=1 "
            "ORDER BY stage, order_num"
        ).fetchall()
        conn.close()
        lessons = [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"show_lessons: {e}")
        lessons = []

    if not lessons:
        kb = InlineKeyboardBuilder()
        kb.button(text="🏠 الرئيسية", callback_data="menu_main")
        await cb.message.answer(
            "📚 <b>الدروس</b>\n\nلا توجد دروس متاحة حالياً.\nسيتم إضافة المحتوى قريباً! 🚀",
            reply_markup=kb.as_markup(), parse_mode="HTML"
        )
        return

    # تجميع حسب المرحلة
    stages = {}
    for l in lessons:
        s = l.get("stage", 1)
        stages.setdefault(s, []).append(l)

    kb = InlineKeyboardBuilder()
    for stage_num in sorted(stages.keys()):
        stage_lessons = stages[stage_num]
        kb.button(
            text=f"━━ المرحلة {stage_num} ━━",
            callback_data=f"stage_info:{stage_num}"
        )
        for l in stage_lessons:
            emoji = SKILL_EMOJI.get(l.get("skill_type", ""), "📌")
            kb.button(
                text=f"{emoji} {l['title']}",
                callback_data=f"lesson:{l['id']}"
            )
    kb.button(text="🏠 الرئيسية", callback_data="menu_main")
    kb.adjust(1)

    await cb.message.answer(
        f"📚 <b>الدروس المتاحة</b> ({len(lessons)} درس)\n\nاختر درساً للبدء:",
        reply_markup=kb.as_markup(), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("stage_info:"))
async def stage_info(cb: CallbackQuery):
    await cb.answer(f"المرحلة {cb.data.split(':')[1]}", show_alert=False)


@router.callback_query(F.data.startswith("lesson:"))
async def show_lesson(cb: CallbackQuery):
    await cb.answer()
    lid = int(cb.data.split(":")[1])

    try:
        conn = db()
        lesson = conn.execute(
            "SELECT * FROM lessons WHERE id=?", (lid,)
        ).fetchone()
        conn.close()
        lesson = dict(lesson) if lesson else None
    except Exception as e:
        logger.error(f"show_lesson: {e}")
        lesson = None

    if not lesson:
        await cb.message.answer("❌ الدرس غير موجود")
        return

    emoji = SKILL_EMOJI.get(lesson.get("skill_type", ""), "📌")
    content = (
        lesson.get("description") or
        lesson.get("content") or
        "لا يوجد محتوى بعد"
    )

    text = (
        f"{emoji} <b>{lesson['title']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{content}\n\n"
    )

    vocab = lesson.get("vocabulary", "")
    if vocab and vocab.strip():
        text += f"📝 <b>المفردات الأساسية:</b>\n<code>{vocab}</code>\n\n"

    grammar = lesson.get("grammar_rule", "")
    if grammar and grammar.strip():
        text += f"📐 <b>القاعدة النحوية:</b>\n{grammar}\n\n"

    text += f"━━━━━━━━━━━━━━━━━━\n🎁 إتمام الدرس = <b>{lesson.get('xp_reward', 20)} XP</b>"

    # تحقق من وجود كويز
    quiz_json = lesson.get("quiz_json", "[]")
    has_quiz = False
    try:
        quiz = json.loads(quiz_json) if quiz_json else []
        has_quiz = len(quiz) > 0
    except Exception:
        pass

    kb = InlineKeyboardBuilder()
    if has_quiz:
        kb.button(
            text="✏️ اختبر نفسك",
            callback_data=f"lesson_quiz:{lid}:0"
        )
    kb.button(text="✅ أتممت الدرس", callback_data=f"complete:{lid}")
    kb.button(text="🔙 قائمة الدروس", callback_data="menu_lessons")
    kb.adjust(1)

    await cb.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("complete:"))
async def complete_lesson(cb: CallbackQuery):
    await cb.answer()
    lid = int(cb.data.split(":")[1])
    user_id = str(cb.from_user.id)

    try:
        conn = db()
        row = conn.execute(
            "SELECT xp_reward, skill_type, title FROM lessons WHERE id=?", (lid,)
        ).fetchone()
        conn.close()
        xp_reward  = row["xp_reward"] if row else 20
        skill_type = row["skill_type"] if row else "general"
        title      = row["title"] if row else "الدرس"
    except Exception as e:
        logger.error(f"complete: {e}")
        xp_reward  = 20
        skill_type = "general"
        title      = "الدرس"

    try:
        add_xp(user_id, xp_reward, skill_type, f"lesson_{lid}")
    except Exception as e:
        logger.warning(f"add_xp: {e}")

    # تحديث missions_completed
    try:
        conn = db()
        cols = [r[1] for r in conn.execute(
            "PRAGMA table_info(students)"
        ).fetchall()]
        if "missions_completed" in cols:
            conn.execute(
                "UPDATE students SET missions_completed = missions_completed + 1 "
                "WHERE telegram_id=?",
                (user_id,)
            )
            conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"missions_completed update: {e}")

    kb = InlineKeyboardBuilder()
    kb.button(text="📚 دروس أخرى",    callback_data="menu_lessons")
    kb.button(text="🏠 الرئيسية",     callback_data="menu_main")
    kb.adjust(1)

    await cb.message.answer(
        f"🎉 <b>أحسنت!</b> أتممت درس:\n<b>{title}</b>\n\n"
        f"🎁 ربحت <b>{xp_reward} XP</b>!\n"
        f"استمر في التعلم يومياً 🔥",
        reply_markup=kb.as_markup(), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("lesson_quiz:"))
async def lesson_quiz(cb: CallbackQuery):
    await cb.answer()
    parts = cb.data.split(":")
    lid   = int(parts[1])
    q_idx = int(parts[2])

    try:
        conn = db()
        row = conn.execute(
            "SELECT quiz_json, title FROM lessons WHERE id=?", (lid,)
        ).fetchone()
        conn.close()
        quiz  = json.loads(row["quiz_json"] or "[]") if row else []
        title = row["title"] if row else ""
    except Exception as e:
        logger.error(f"lesson_quiz: {e}")
        quiz  = []
        title = ""

    if not quiz or q_idx >= len(quiz):
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ أتممت الدرس", callback_data=f"complete:{lid}")
        await cb.message.answer(
            "✅ انتهى الكويز!\nاضغط لإتمام الدرس والحصول على XP:",
            reply_markup=kb.as_markup()
        )
        return

    q = quiz[q_idx]
    kb = InlineKeyboardBuilder()
    for opt in q.get("options", []):
        kb.button(
            text=opt,
            callback_data=f"quiz_ans:{lid}:{q_idx}:{opt[:20]}"
        )
    kb.adjust(1)

    await cb.message.answer(
        f"❓ <b>سؤال {q_idx+1}/{len(quiz)}</b>\n\n{q.get('question', '')}",
        reply_markup=kb.as_markup(), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("quiz_ans:"))
async def quiz_answer(cb: CallbackQuery):
    parts   = cb.data.split(":")
    lid     = int(parts[1])
    q_idx   = int(parts[2])
    answer  = parts[3]

    try:
        conn = db()
        row  = conn.execute(
            "SELECT quiz_json FROM lessons WHERE id=?", (lid,)
        ).fetchone()
        conn.close()
        quiz = json.loads(row["quiz_json"] or "[]") if row else []
    except Exception:
        quiz = []

    if q_idx < len(quiz):
        correct = quiz[q_idx].get("correct", "")
        is_ok   = answer.strip() == correct.strip()
        feedback = "✅ صحيح!" if is_ok else f"❌ الإجابة الصحيحة: {correct}"
        if is_ok:
            try:
                add_xp(str(cb.from_user.id), 5, "general", f"quiz_{lid}_{q_idx}")
            except Exception:
                pass
    else:
        feedback = ""

    next_idx = q_idx + 1
    await cb.answer(feedback[:30])

    kb = InlineKeyboardBuilder()
    kb.button(
        text="السؤال التالي ▶️" if next_idx < len(quiz) else "✅ إنهاء الكويز",
        callback_data=f"lesson_quiz:{lid}:{next_idx}"
    )
    await cb.message.answer(
        f"{feedback}\n\nاضغط للمتابعة:",
        reply_markup=kb.as_markup()
    )
