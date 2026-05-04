import logging, traceback, os, tempfile
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import settings

logger = logging.getLogger(__name__)
router = Router()

class ListeningState(StatesGroup):
    waiting_answer = State()

KB_BACK_LISTENING = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔙 رجوع للقائمة", callback_data="back_to_menu")]
])

LISTENING_EXERCISES = [
    {
        "title": "🎧 محادثة في المطار",
        "audio_id": None,  # سيتم رفعه لاحقاً
        "question": "What is the passenger's final destination?",
        "options": ["A) London", "B) New York", "C) Dubai", "D) Paris"],
        "correct": 1,
    },
    {
        "title": "🎧 حجز فندق",
        "audio_id": None,
        "question": "How many nights will the guest stay?",
        "options": ["A) 2 nights", "B) 3 nights", "C) 4 nights", "D) 5 nights"],
        "correct": 2,
    },
    {
        "title": "🎧 محاضرة جامعية",
        "audio_id": None,
        "question": "What is the main topic of the lecture?",
        "options": ["A) Climate change", "B) Renewable energy", "C) Ocean pollution", "D) Wildlife conservation"],
        "correct": 1,
    },
]

@router.message(F.text == "🎧 تدريب الاستماع")
async def show_listening_menu(msg: types.Message):
    kb = InlineKeyboardBuilder()
    for i, ex in enumerate(LISTENING_EXERCISES):
        kb.row(InlineKeyboardButton(text=ex["title"], callback_data=f"listen_{i}"))
    kb.row(InlineKeyboardButton(text="🔙 رجوع", callback_data="back_to_menu"))
    
    await msg.answer(
        "🎧 *قسم الاستماع*\n\n"
        "اختر تمريناً للبدء:\n"
        "• استمع للمقطع الصوتي\n"
        "• أجب عن السؤال\n"
        "• احصل على تقييم فوري",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )

@router.callback_query(F.data.startswith("listen_"))
async def start_listening(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    idx = int(callback.data.split("_")[1])
    ex = LISTENING_EXERCISES[idx]
    
    await callback.answer()
    await callback.message.answer(
        f"🎧 *{ex['title']}*\n\n"
        f"📌 *السؤال:* {ex['question']}\n\n"
        "استمع للمقطع ثم اختر الإجابة الصحيحة.\n\n"
        "⚠️ ملاحظة: المقاطع الصوتية سيتم رفعها من قبل الأدمن.",
        parse_mode="Markdown"
    )
    
    if ex["audio_id"]:
        await bot.send_voice(callback.from_user.id, ex["audio_id"])
    
    # Show options
    kb = InlineKeyboardBuilder()
    for i, opt in enumerate(ex["options"]):
        kb.row(InlineKeyboardButton(text=opt, callback_data=f"answer_{idx}_{i}"))
    kb.row(InlineKeyboardButton(text="🔙 رجوع", callback_data="back_to_menu"))
    
    await callback.message.answer("📝 اختر إجابتك:", reply_markup=kb.as_markup())
    await state.set_state(ListeningState.waiting_answer)

@router.callback_query(F.data.startswith("answer_"), ListeningState.waiting_answer)
async def check_listening_answer(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    ex_idx = int(parts[1])
    answer_idx = int(parts[2])
    ex = LISTENING_EXERCISES[ex_idx]
    
    await callback.answer()
    
    if answer_idx == ex["correct"]:
        await callback.message.edit_text(
            f"✅ *إجابة صحيحة!*\n\n"
            f"أحسنت! إجابتك صحيحة.",
            parse_mode="Markdown",
            reply_markup=KB_BACK_LISTENING
        )
    else:
        await callback.message.edit_text(
            f"❌ *إجابة خاطئة*\n\n"
            f"الإجابة الصحيحة: {ex['options'][ex['correct']]}\n"
            f"حاول مرة أخرى في تمرين جديد!",
            parse_mode="Markdown",
            reply_markup=KB_BACK_LISTENING
        )
    await state.clear()
