from aiogram import Router, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    get_due_reviews, get_or_create_review, update_review,
    add_to_error_bank, get_error_bank, mark_error_mastered,
    quality_from_answer, get_student_level, get_spelling_words, add_xp,
    get_all_spelling_words
)
import time as _time
import asyncio

router = Router()

class SpellState(StatesGroup):
    answering = State()

@router.callback_query(F.data == "spelling_practice")
async def start_spelling(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    level = get_student_level(uid) or "A1"
    due = get_due_reviews(uid, limit=10)
    if not due:
        # No due reviews — get new words
        new_words = get_spelling_words(level, 5)
        if not new_words:
            await callback.message.edit_text("📚 لا توجد كلمات متاحة حالياً للمستوى الحالي. سيتم إضافتها قريباً!")
            await callback.answer()
            return
        for w in new_words:
            get_or_create_review(uid, w['id'])
        due = get_due_reviews(uid, limit=10)
    if not due:
        await callback.message.edit_text("🎉 لقد أنهيت جميع مراجعاتك! عد لاحقاً للمراجعة حسب الجدول الزمني.")
        await callback.answer()
        return
    await state.update_data(due=due, idx=0, correct=0, errors=0, start_time=_time.time())
    await send_spell_q(callback.message, state, 0)

async def send_spell_q(msg, state, idx):
    data = await state.get_data()
    due = data.get("due", [])
    if idx >= len(due):
        await finish_spelling(msg, state)
        return
    word = due[idx]
    await state.set_state(SpellState.answering)
    await state.update_data(idx=idx, current_word=word, q_start=_time.time())
    await msg.edit_text(
        f"✍️ *تهجئة الكلمة*\n\nاكتب الكلمة التي تعني:\n\n"
        f"📖 *{word['definition']}*\n\n"
        f"مثال: _{word['example_sentence']}_\n\n"
        f"(/skip للتخطي)",
        parse_mode="Markdown"
    )

@router.message(SpellState.answering)
async def handle_spell(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current = data.get("current_word")
    if not current:
        return
    uid = message.from_user.id
    answer = message.text.strip().lower()

    if answer == '/skip':
        await message.answer(f"⏭️ الكلمة الصحيحة: *{current['word']}*", parse_mode="Markdown")
        update_review(uid, current['word_id'], 2, 10)
        add_to_error_bank(uid, current['word_id'], "skipped")
        await state.update_data(errors=data.get('errors', 0) + 1)
        await send_spell_q(message, state, data['idx'] + 1)
        return

    correct_word = current['word'].lower()
    elapsed = _time.time() - data.get('q_start', _time.time())

    if answer == correct_word:
        q = quality_from_answer(True, elapsed)
        update_review(uid, current['word_id'], q, elapsed)
        await state.update_data(correct=data.get('correct', 0) + 1)
        await message.answer(f"✅ صحيح! *{current['word']}* ⚡", parse_mode="Markdown")
    else:
        update_review(uid, current['word_id'], 1, elapsed)
        add_to_error_bank(uid, current['word_id'], answer)
        await state.update_data(errors=data.get('errors', 0) + 1)
        await message.answer(
            f"❌ خطأ! كتبت: _{answer}_\n✅ الصحيح: *{current['word']}*",
            parse_mode="Markdown"
        )

    await asyncio.sleep(0.5)
    await send_spell_q(message, state, data['idx'] + 1)

async def finish_spelling(msg, state):
    data = await state.get_data()
    correct = data.get('correct', 0)
    errors = data.get('errors', 0)
    total = correct + errors
    xp = correct * 5
    uid = msg.chat.id
    if xp > 0:
        add_xp(uid, xp, 'spelling_practice')
    await msg.answer(
        f"📊 *نتيجة التهجئة*\n\n"
        f"✅ صحيح: {correct}\n❌ أخطاء: {errors}\n"
        f"⭐ XP: +{xp}\n\n"
        f"🔁 الكلمات الخاطئة دخلت *بنك الأخطاء* وستراجع لاحقاً.",
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "error_bank_review")
async def review_error_bank(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    errors = get_error_bank(uid, limit=8)
    if not errors:
        await callback.message.edit_text("🎉 لا توجد أخطاء في بنك الأخطاء! أنت تتقن التهجئة.")
        await callback.answer()
        return
    await state.update_data(eb=errors, idx=0, eb_correct=0, eb_errors=0)
    await send_eb_q(callback.message, state, 0)

async def send_eb_q(msg, state, idx):
    data = await state.get_data()
    eb = data.get("eb", [])
    if idx >= len(eb):
        correct = data.get('eb_correct', 0)
        total = len(eb)
        uid = msg.chat.id
        xp = correct * 8
        if xp > 0:
            add_xp(uid, xp, 'error_bank_review')
        await msg.edit_text(
            f"📊 *نتيجة مراجعة بنك الأخطاء*\n\n"
            f"✅ صحيح: {correct}\n❌ أخطاء: {total - correct}\n"
            f"⭐ XP: +{xp}\n\n"
            f"الكلمات المتقنة خرجت من بنك الأخطاء 🔓",
            parse_mode="Markdown"
        )
        return
    error = eb[idx]
    await state.update_data(eb_idx=idx)
    await state.set_state(SpellState.answering)
    await msg.edit_text(
        f"🔁 *مراجعة بنك الأخطاء*\n\n"
        f"آخر خطأ كتبته: _{error['misspelled_as']}_\n\n"
        f"📖 اكتب الكلمة: *{error['definition']}*\n"
        f"(الكلمة: {error['word']})",
        parse_mode="Markdown"
    )
