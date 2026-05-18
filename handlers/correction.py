# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.states import CorrectionStates
from utils.ai_corrector import correct_writing, correct_speaking

router = Router(name="correction")

def back_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 الرئيسية", callback_data="menu:main")
    return kb.as_markup()

@router.callback_query(F.data == "menu:correction")
async def correction_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text="✍️ تصحيح Writing", callback_data="corr:writing")
    kb.button(text="🎤 تصحيح Speaking", callback_data="corr:speaking")
    kb.button(text="🏠 رجوع", callback_data="menu:main")
    kb.adjust(1)
    await cb.message.edit_text(
        "🤖 <b>التصحيح الذكي بالذكاء الاصطناعي</b>\n\n"
        "اختر نوع المهارة التي تريد تصحيحها:",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data == "corr:writing")
async def ask_writing(cb: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ إلغاء", callback_data="menu:correction")
    await cb.message.edit_text(
        "✍️ <b>تصحيح Writing</b>\n\n"
        "أرسل نص المقال (Essay) الآن:\n\n"
        "<i>مثال: Some people think that... Discuss both views.</i>",
        reply_markup=kb.as_markup()
    )
    await state.set_state(CorrectionStates.waiting_for_essay)
    await cb.answer()

@router.message(CorrectionStates.waiting_for_essay)
async def handle_writing(message: Message, state: FSMContext):
    text = message.text or ""
    if len(text) < 50:
        await message.answer("⚠️ النص قصير جداً. أرسل على الأقل 50 كلمة.")
        return
    await message.answer("⏳ <b>جاري التصحيح بالذكاء الاصطناعي...</b>")
    try:
        result = await correct_writing(text)
        await message.answer(
            f"📝 <b>نتيجة التصحيح:</b>\n\n{result}",
            reply_markup=back_kb()
        )
    except Exception as e:
        await message.answer(f"❌ خطأ: {e}", reply_markup=back_kb())
    await state.clear()

@router.callback_query(F.data == "corr:speaking")
async def ask_speaking(cb: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ إلغاء", callback_data="menu:correction")
    await cb.message.edit_text(
        "🎤 <b>تصحيح Speaking</b>\n\n"
        "أرسل نص إجابتك على سؤال Speaking:\n\n"
        "<i>مثال: Describe a place you visited recently...</i>",
        reply_markup=kb.as_markup()
    )
    await state.set_state(CorrectionStates.waiting_for_speaking)
    await cb.answer()

@router.message(CorrectionStates.waiting_for_speaking)
async def handle_speaking(message: Message, state: FSMContext):
    text = message.text or ""
    if len(text) < 20:
        await message.answer("⚠️ النص قصير جداً. أرسل على الأقل 20 كلمة.")
        return
    await message.answer("⏳ <b>جاري التصحيح...</b>")
    try:
        result = await correct_speaking(text)
        await message.answer(
            f"🎤 <b>نتيجة تقييم Speaking:</b>\n\n{result}",
            reply_markup=back_kb()
        )
    except Exception as e:
        await message.answer(f"❌ خطأ: {e}", reply_markup=back_kb())
    await state.clear()
