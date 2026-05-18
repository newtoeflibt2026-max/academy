# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.states import PlacementStates
from database_v2 import add_xp
import sqlite3, os

router = Router(name="placement_test")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "academy.db")

def get_questions():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT * FROM placement_questions 
               WHERE is_active=1 ORDER BY RANDOM() LIMIT 20"""
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_questions error: {e}")
        return []

def save_result(telegram_id, score, correct, total):
    try:
        level = "advanced" if score >= 70 else \
                "intermediate" if score >= 50 else "beginner"
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """UPDATE students SET placement_done=1,
               placement_score=?, level=?
               WHERE telegram_id=?""",
            (score, level, str(telegram_id))
        )
        conn.commit()
        conn.close()
        return level
    except Exception as e:
        print(f"save_result error: {e}")
        return "beginner"

def build_question_kb(q_index, total):
    kb = InlineKeyboardBuilder()
    kb.button(text="🅐", callback_data=f"pla:{q_index}:A")
    kb.button(text="🅑", callback_data=f"pla:{q_index}:B")
    kb.button(text="🅒", callback_data=f"pla:{q_index}:C")
    kb.button(text="🅓", callback_data=f"pla:{q_index}:D")
    kb.adjust(4)
    return kb.as_markup()

def build_question_text(q, index, total, feedback=""):
    progress = "▓" * (index) + "░" * (total - index)
    return (
        f"🔬 <b>اختبار تحديد المستوى</b>\n"
        f"[{progress}]\n"
        f"📝 <b>السؤال {index + 1} من {total}</b>"
        f"{' ' + feedback if feedback else ''}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{q['question_text']}\n\n"
        f"🅐 {q['option_a']}\n"
        f"🅑 {q['option_b']}\n"
        f"🅒 {q['option_c']}\n"
        f"🅓 {q['option_d']}"
    )

async def start_placement(cb: CallbackQuery, state: FSMContext = None):
    questions = get_questions()
    if not questions:
        kb = InlineKeyboardBuilder()
        kb.button(text="🏠 رجوع", callback_data="menu:main")
        try:
            await cb.message.edit_text(
                "⚠️ لا توجد أسئلة بعد. تواصل مع الإدارة.",
                reply_markup=kb.as_markup()
            )
        except:
            await cb.message.answer(
                "⚠️ لا توجد أسئلة بعد.",
                reply_markup=kb.as_markup()
            )
        await cb.answer()
        return

    if state:
        await state.clear()
        await state.set_state(PlacementStates.answering)
        await state.update_data(
            questions=questions,
            current=0,
            correct=0
        )

    q = questions[0]
    text = build_question_text(q, 0, len(questions))
    try:
        await cb.message.edit_text(
            text, reply_markup=build_question_kb(0, len(questions))
        )
    except:
        await cb.message.answer(
            text, reply_markup=build_question_kb(0, len(questions))
        )
    await cb.answer()

@router.callback_query(F.data == "start_placement")
async def placement_start_cb(cb: CallbackQuery, state: FSMContext):
    await start_placement(cb, state)

@router.callback_query(F.data.startswith("pla:"))
async def placement_answer(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    q_index = int(parts[1])
    answer = parts[2]

    data = await state.get_data()
    questions = data.get("questions", [])
    correct_count = data.get("correct", 0)

        if not questions:
        # أعد تحميل الأسئلة تلقائياً
        questions = get_questions()
        if not questions:
            await cb.answer("❌ لا توجد أسئلة، تواصل مع الإدارة", show_alert=True)
            return
        await state.clear()
        await state.set_state(PlacementStates.answering)
        await state.update_data(questions=questions, current=0, correct=0)
        q_index = 0
        correct_count = 0
        current_q = questions[0]
        is_correct = answer == current_q.get("correct_option", "")
        if is_correct:
            correct_count += 1
        feedback = "✅" if is_correct else f"❌ الصحيح: {current_q.get('correct_option','')}"
        next_index = 1
        if next_index >= len(questions):
            pass
        else:
            await state.update_data(current=next_index, correct=correct_count)
            next_q = questions[next_index]
            text = build_question_text(next_q, next_index, len(questions), feedback)
            await cb.message.edit_text(text, reply_markup=build_question_kb(next_index, len(questions)))
            await cb.answer(feedback[:30])
            return


    if q_index >= len(questions):
        await cb.answer("انتهى الاختبار!")
        return

    current_q = questions[q_index]
    is_correct = answer == current_q.get("correct_option", "")
    if is_correct:
        correct_count += 1

    feedback = "✅" if is_correct else f"❌ الإجابة الصحيحة: {current_q.get('correct_option','')}"
    next_index = q_index + 1

    # ══ انتهى الاختبار ══
    if next_index >= len(questions):
        score = round((correct_count / len(questions)) * 100, 1)
        user_id = str(cb.from_user.id)
        level = save_result(user_id, score, correct_count, len(questions))
        add_xp(user_id, 50, "general", "placement test")

        level_map = {
            "beginner": ("مبتدئ 🔵", "ستبدأ من دورة التأسيس الشامل"),
            "intermediate": ("متوسط 🟡", "ستنطلق مباشرة في TOEFL"),
            "advanced": ("متقدم 🟢", "مستواك ممتاز! ستبدأ من المراحل المتقدمة")
        }
        lvl_name, msg = level_map.get(level, ("مبتدئ 🔵", ""))

        kb = InlineKeyboardBuilder()
        kb.button(text="📚 ابدأ دروسك", callback_data="menu:lessons")
        kb.button(text="🏠 الرئيسية", callback_data="menu:main")
        kb.adjust(1)

        await state.clear()
        await cb.message.edit_text(
            f"🎉 <b>انتهى اختبار تحديد المستوى!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ إجابات صحيحة: <b>{correct_count}/{len(questions)}</b>\n"
            f"📊 النتيجة: <b>{score}%</b>\n"
            f"🎓 مستواك: <b>{lvl_name}</b>\n\n"
            f"💡 {msg}\n\n"
            f"🎁 حصلت على <b>50 XP</b> مكافأة!",
            reply_markup=kb.as_markup()
        )
        await cb.answer("🎉 انتهى الاختبار!")
        return

    # ══ السؤال التالي ══
    await state.update_data(
        current=next_index,
        correct=correct_count
    )

    next_q = questions[next_index]
    text = build_question_text(next_q, next_index, len(questions), feedback)

    await cb.message.edit_text(
        text,
        reply_markup=build_question_kb(next_index, len(questions))
    )
    await cb.answer(feedback[:30])
