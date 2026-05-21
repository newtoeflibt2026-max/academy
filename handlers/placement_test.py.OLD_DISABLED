# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database_v2 import add_xp
import sqlite3, os, logging

logger = logging.getLogger(__name__)
router = Router(name="placement_test")

DB_PATH = r"C:\Users\nelt2\yamen_academy\academy.db"


def get_questions():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM placement_questions "
            "WHERE is_active=1 ORDER BY RANDOM() LIMIT 20"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"get_questions: {e}")
        return []


def save_result(telegram_id, score):
    try:
        level = (
            "advanced"     if score >= 70 else
            "intermediate" if score >= 50 else
            "beginner"
        )
        conn = sqlite3.connect(DB_PATH)
        cols = [r[1] for r in conn.execute(
            "PRAGMA table_info(students)"
        ).fetchall()]

        updates = ["level=?"]
        params  = [level]

        if "placement_done" in cols:
            updates.append("placement_done=1")
        if "placement_score" in cols:
            updates.append("placement_score=?")
            params.append(score)

        params.append(str(telegram_id))

        # جرب telegram_id أولاً ثم user_id
        for col in ("telegram_id", "user_id"):
            if col in cols:
                conn.execute(
                    "UPDATE students SET " + ", ".join(updates) +
                    " WHERE " + col + "=?",
                    params
                )
                if conn.total_changes > 0:
                    break

        conn.commit()
        conn.close()
        return level
    except Exception as e:
        logger.error(f"save_result: {e}")
        return "beginner"


def build_kb(index):
    kb = InlineKeyboardBuilder()
    kb.button(text="A", callback_data=f"pl:{index}:A")
    kb.button(text="B", callback_data=f"pl:{index}:B")
    kb.button(text="C", callback_data=f"pl:{index}:C")
    kb.button(text="D", callback_data=f"pl:{index}:D")
    kb.adjust(4)
    return kb.as_markup()


def build_text(q, index, total):
    done  = "█" * (index + 1)
    empty = "░" * (total - index - 1)
    pct   = round((index + 1) / total * 100)
    return (
        f"🔬 <b>امتحان تحديد المستوى</b>\n"
        f"<code>[{done}{empty}] {pct}%</code>\n"
        f"السؤال <b>{index+1}</b> من <b>{total}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{q['question_text']}</b>\n\n"
        f"🇦 {q['option_a']}\n"
        f"🇧 {q['option_b']}\n"
        f"🇨 {q['option_c']}\n"
        f"🇩 {q['option_d']}"
    )


def build_result_text(ok, total, score, level):
    level_ar = {
        "beginner":     "مبتدئ 🔵",
        "intermediate": "متوسط 🟡",
        "advanced":     "متقدم 🟢",
    }.get(level, "مبتدئ 🔵")

    level_msg = {
        "beginner":     "ستبدأ من دورة التأسيس الشاملة 📚",
        "intermediate": "ستنطلق مباشرة في مسار TOEFL 🚀",
        "advanced":     "مستواك ممتاز! المراحل المتقدمة تنتظرك 🌟",
    }.get(level, "")

    bar_full  = "█" * round(score / 10)
    bar_empty = "░" * (10 - round(score / 10))

    return (
        f"🎉 <b>انتهى الامتحان!</b>\n\n"
        f"<code>[{bar_full}{bar_empty}] {score}%</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ إجابات صحيحة: <b>{ok} / {total}</b>\n"
        f"📊 النتيجة: <b>{score}%</b>\n"
        f"🎓 مستواك: <b>{level_ar}</b>\n\n"
        f"💡 {level_msg}\n\n"
        f"🎁 ربحت <b>50 XP</b>!"
    )


# ── بدء الامتحان ─────────────────────────────────────────
async def start_placement(cb: CallbackQuery, state: FSMContext):
    questions = get_questions()
    if not questions:
        await cb.answer(
            "⚠️ لا توجد أسئلة. تواصل مع الأدمن.",
            show_alert=True
        )
        return

    await state.clear()
    await state.update_data(qs=questions, idx=0, ok=0)

    text = build_text(questions[0], 0, len(questions))
    kb   = build_kb(0)

    try:
        await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await cb.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "start_placement")
async def on_start_placement(cb: CallbackQuery, state: FSMContext):
    await start_placement(cb, state)


# ── معالجة الإجابة ───────────────────────────────────────
@router.callback_query(F.data.startswith("pl:"))
async def on_answer(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    if len(parts) != 3:
        await cb.answer()
        return

    idx    = int(parts[1])
    choice = parts[2]

    data      = await state.get_data()
    questions = data.get("qs")
    ok        = data.get("ok", 0)

    # ── الجلسة منتهية ──
    if not questions:
        kb = InlineKeyboardBuilder()
        kb.button(text="🔬 ابدأ من جديد", callback_data="start_placement")
        try:
            await cb.message.edit_text(
                "⚠️ انتهت الجلسة. اضغط لإعادة البدء:",
                reply_markup=kb.as_markup()
            )
        except Exception:
            await cb.message.answer(
                "⚠️ انتهت الجلسة. اضغط لإعادة البدء:",
                reply_markup=kb.as_markup()
            )
        await cb.answer()
        return

    total = len(questions)

    if idx >= total:
        await cb.answer()
        return

    # ── هل الإجابة صحيحة؟ ──
    correct = questions[idx].get("correct_option", "A")
    is_ok   = (choice == correct)
    if is_ok:
        ok += 1

    next_idx = idx + 1

    # ── آخر سؤال → اعرض النتيجة ──
    if next_idx >= total:
        score = round(ok / total * 100, 1)
        level = save_result(cb.from_user.id, score)

        try:
            add_xp(cb.from_user.id, 50, "placement_test")
        except Exception as e:
            logger.warning(f"add_xp: {e}")

        kb = InlineKeyboardBuilder()
        kb.button(text="📚 ابدأ دروسك الآن",   callback_data="menu_lessons")
        kb.button(text="💳 الباقات",             callback_data="menu_subscriptions")
        kb.button(text="🏠 القائمة الرئيسية",   callback_data="menu_main")
        kb.adjust(1)

        await state.clear()

        result_text = build_result_text(ok, total, score, level)

        try:
            await cb.message.edit_text(
                result_text,
                reply_markup=kb.as_markup(),
                parse_mode="HTML"
            )
        except Exception:
            await cb.message.answer(
                result_text,
                reply_markup=kb.as_markup(),
                parse_mode="HTML"
            )
        await cb.answer("🎉 انتهى الامتحان!")
        return

    # ── السؤال التالي ──
    await state.update_data(idx=next_idx, ok=ok)
    next_q = questions[next_idx]

    # الـ feedback بدون ذكر الإجابة الصحيحة
    feedback = "✅" if is_ok else "❌"

    new_text = f"{feedback}\n\n" + build_text(next_q, next_idx, total)
    new_kb   = build_kb(next_idx)

    try:
        await cb.message.edit_text(
            new_text,
            reply_markup=new_kb,
            parse_mode="HTML"
        )
    except Exception:
        await cb.message.answer(
            new_text,
            reply_markup=new_kb,
            parse_mode="HTML"
        )
    await cb.answer(feedback)
