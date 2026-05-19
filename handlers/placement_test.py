# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database_v2 import add_xp
import sqlite3, os

router = Router(name="placement_test")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "academy.db")


def get_placement_questions():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM placement_questions WHERE is_active=1 ORDER BY RANDOM() LIMIT 20"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_placement_questions error: {e}")
        return []


def save_placement_result(user_id, score, ok, total):
    try:
        level = "advanced" if score >= 70 else "intermediate" if score >= 50 else "beginner"
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        # تحقق من الاعمدة الموجودة
        cols = [r[1] for r in conn.execute("PRAGMA table_info(students)").fetchall()]

        if "placement_done" in cols and "placement_score" in cols:
            conn.execute(
                "UPDATE students SET placement_done=1, placement_score=?, level=? WHERE telegram_id=?",
                (score, level, str(user_id))
)

        else:
            conn.execute(
                "UPDATE students SET level=? WHERE telegram_id=?",
                (level, str(user_id))
)

        conn.commit()
        conn.close()
        return level
    except Exception as e:
        print(f"save_placement_result error: {e}")
        return "beginner"


def q_keyboard(index):
    kb = InlineKeyboardBuilder()
    kb.button(text="🅰 A", callback_data=f"ans:{index}:A")
    kb.button(text="🅱 B", callback_data=f"ans:{index}:B")
    kb.button(text="🅲 C", callback_data=f"ans:{index}:C")
    kb.button(text="🅳 D", callback_data=f"ans:{index}:D")
    kb.adjust(2)
    return kb.as_markup()


def q_text(q, index, total):
    filled = "█" * (index + 1)
    empty = "░" * (total - index - 1)
    pct = round((index + 1) / total * 100)
    return (
        f"🔬 <b>امتحان تحديد المستوى</b>\n"
        f"<code>[{filled}{empty}] {pct}%</code>\n"
        f"السؤال <b>{index + 1}</b> من <b>{total}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{q.get('question_text', '')}\n\n"
        f"🅰 {q.get('option_a', '')}\n"
        f"🅱 {q.get('option_b', '')}\n"
        f"🅲 {q.get('option_c', '')}\n"
        f"🅳 {q.get('option_d', '')}"
    )


@router.callback_query(F.data == "start_placement")
async def on_start_placement(cb: CallbackQuery, state: FSMContext):
    questions = get_placement_questions()
    if not questions:
        await cb.answer(
            "⚠️ لا توجد أسئلة في امتحان المستوى!\nتواصل مع الأدمن لإضافة الأسئلة.",
            show_alert=True
        )
        return
    await state.clear()
    await state.update_data(qs=questions, idx=0, ok=0)
    try:
        await cb.message.edit_text(
            q_text(questions[0], 0, len(questions)),
            reply_markup=q_keyboard(0),
            parse_mode="HTML"
        )
    except Exception:
        await cb.message.answer(
            q_text(questions[0], 0, len(questions)),
            reply_markup=q_keyboard(0),
            parse_mode="HTML"
        )
    await cb.answer()


@router.callback_query(F.data.startswith("ans:"))
async def on_answer(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    if len(parts) != 3:
        await cb.answer()
        return

    _, idx_str, choice = parts
    idx = int(idx_str)
    data = await state.get_data()
    questions = data.get("qs")

    if not questions:
        kb = InlineKeyboardBuilder()
        kb.button(text="🔬 ابدأ الامتحان", callback_data="start_placement")
        await cb.message.edit_text(
            "⚠️ انتهت الجلسة. اضغط لإعادة البدء:",
            reply_markup=kb.as_markup()
        )
        await cb.answer()
        return

    ok = data.get("ok", 0)
    total = len(questions)

    if idx >= total:
        await cb.answer()
        return

    correct = questions[idx].get("correct_option", "A")
    is_ok = (choice == correct)
    if is_ok:
        ok += 1

    feedback = "✅ صحيح!" if is_ok else f"❌ الإجابة: {correct}"
    next_idx = idx + 1

    if next_idx >= total:
        score = round(ok / total * 100, 1)
        user_id = cb.from_user.id
        level = save_placement_result(user_id, score, ok, total)
        add_xp(user_id, 50, "general", "placement_test")

        level_ar = {
            "beginner": "مبتدئ 🔵",
            "intermediate": "متوسط 🟡",
            "advanced": "متقدم 🟢"
        }.get(level, "مبتدئ 🔵")

        level_msg = {
            "beginner": "ستبدأ من دورة التأسيس الشاملة 📚",
            "intermediate": "ستنطلق مباشرة في TOEFL 🚀",
            "advanced": "مستواك ممتاز! ستبدأ من المراحل المتقدمة 🌟"
        }.get(level, "")

        stars = "⭐" * (1 if level == "beginner" else 2 if level == "intermediate" else 3)

        kb = InlineKeyboardBuilder()
        kb.button(text="📚 ابدأ دروسك", callback_data="menu_lessons")
        kb.button(text="🏠 الرئيسية", callback_data="menu_main")
        kb.adjust(1)

        await state.clear()
        await cb.message.edit_text(
            f"🎉 <b>انتهى الامتحان!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ صحيح: <b>{ok}/{total}</b>\n"
            f"📊 النتيجة: <b>{score}%</b>\n"
            f"🎓 مستواك: <b>{level_ar}</b> {stars}\n\n"
            f"💡 {level_msg}\n"
            f"🎁 ربحت <b>50 XP</b>!",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
        await cb.answer("🎉 انتهى!")
        return

    await state.update_data(idx=next_idx, ok=ok)
    next_q = questions[next_idx]

    try:
        await cb.message.edit_text(
            f"{feedback}\n\n" + q_text(next_q, next_idx, total),
            reply_markup=q_keyboard(next_idx),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await cb.answer(feedback[:30])
