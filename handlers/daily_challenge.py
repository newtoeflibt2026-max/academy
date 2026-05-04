from aiogram import Router, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_today_challenge, add_xp
import asyncio

router = Router()

class ChallengeState(StatesGroup):
    waiting = State()

@router.callback_query(F.data == "daily_challenge")
async def daily_challenge(callback: types.CallbackQuery, state: FSMContext):
    challenge = get_today_challenge()
    if not challenge:
        await callback.message.edit_text("📭 لا يوجد تحدي اليوم. عد غداً!")
        await callback.answer(); return
    uid = callback.from_user.id
    xp = challenge['xp_reward']
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏱️ ابدأ التحدي!", callback_data="start_challenge")],
    ])
    await callback.message.edit_text(
        f"⚡ *تحدي اليوم*\n\n{challenge['question']}\n\n"
        f"🏆 المكافأة: *+{xp} XP*\nالوقت: 60 ثانية",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "start_challenge")
async def start_challenge(callback: types.CallbackQuery, state: FSMContext):
    challenge = get_today_challenge()
    if not challenge:
        await callback.answer("لا يوجد تحدي"); return
    await state.update_data(answer=challenge['answer'], xp=challenge['xp_reward'], cid=challenge['id'], start=True)
    await state.set_state(ChallengeState.waiting)
    await callback.message.edit_text(
        "⏱️ *60 ثانية!*\nاكتب إجابتك الآن:\n\n"
        "/cancel للإلغاء",
        parse_mode="Markdown"
    )
    await callback.answer()
    # Timer: auto-cancel after 60s
    await asyncio.sleep(60)
    current = await state.get_state()
    if current == "ChallengeState:waiting":
        await state.clear()
        try:
            await callback.message.edit_text("⏰ انتهى الوقت! حاول غداً.")
        except Exception:
            pass

@router.message(ChallengeState.waiting)
async def handle_challenge(message: types.Message, state: FSMContext):
    if message.text and message.text.strip() == '/cancel':
        await state.clear()
        await message.answer("🚫 ألغي التحدي.")
        return
    data = await state.get_data()
    await state.clear()
    correct = data['answer'].lower().strip()
    user_ans = message.text.strip().lower() if message.text else ''
    if user_ans == correct:
        add_xp(message.from_user.id, data['xp'], 'daily_challenge')
        await message.answer(f"✅ إجابة صحيحة! +{data['xp']} XP 🏆")
    else:
        await message.answer(f"❌ خطأ! الإجابة الصحيحة: *{data['answer']}*", parse_mode="Markdown")
