from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database import upsert_student, get_student, get_error_bank_count, get_student_level, has_active_subscription

router = Router()

class RegState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

# ─── /start ───
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    student = get_student(uid)
    if student and student.get("full_name"):
        await show_main_menu(message, uid)
        return
    await state.set_state(RegState.waiting_for_name)
    await message.answer("\U0001f44b \u0623\u0647\u0644\u0627\u064b \u0628\u0643 \u0641\u064a *\u0623\u0643\u0627\u062f\u064a\u0645\u064a\u0629 \u064a\u0627\u0645\u0646*!\n\n\u0645\u0646 \u0641\u0636\u0644\u0643\u060c \u0623\u0631\u0633\u0644 \u0627\u0633\u0645\u0643 \u0627\u0644\u0643\u0627\u0645\u0644:", parse_mode="Markdown")

@router.message(RegState.waiting_for_name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(RegState.waiting_for_phone)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="\U0001f4f1 \u0645\u0634\u0627\u0631\u0643\u0629 \u0627\u0644\u0631\u0642\u0645", request_contact=True)]],
                             resize_keyboard=True, one_time_keyboard=True)
    await message.answer("\U0001f4f1 \u0623\u0631\u0633\u0644 \u0631\u0642\u0645 \u0647\u0627\u062a\u0641\u0643 \u0623\u0648 \u0627\u0636\u063a\u0637 \u0627\u0644\u0632\u0631:", reply_markup=kb)

@router.message(RegState.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    phone = message.contact.phone_number if message.contact else message.text.strip()
    upsert_student(message.from_user.id, data["name"], phone)
    await state.clear()
    await message.answer(f"\u2705 \u062a\u0645 \u0627\u0644\u062a\u0633\u062c\u064a\u0644! \u0645\u0631\u062d\u0628\u0627\u064b {data['name']} \U0001f389", reply_markup=types.ReplyKeyboardRemove())
    await show_main_menu(message, message.from_user.id)

# ─── SMART MAIN MENU ───
async def show_main_menu(message: types.Message, uid: int):
    student = get_student(uid)
    has_placement = student and student.get("placement_done")
    has_sub = has_active_subscription(uid)
    level = student.get("level") if student else None

    kb_rows = []

    # ═══ BEFORE PLACEMENT TEST ═══
    if not has_placement:
        kb_rows.append([InlineKeyboardButton(text="\U0001f4dd \u0627\u0645\u062a\u062d\u0627\u0646 \u0627\u0644\u0645\u0633\u062a\u0648\u0649", callback_data="placement_test")])
        # show subscribe only before placement if they want
        kb_rows.append([InlineKeyboardButton(text="\U0001f4b2 \u0627\u0634\u062a\u0631\u0643 \u0627\u0644\u0622\u0646", callback_data="menu_subscribe")])
    # ═══ AFTER PLACEMENT, BEFORE SUBSCRIPTION ═══
    elif not has_sub:
        kb_rows.append([InlineKeyboardButton(text="\U0001f4b2 \u0627\u0634\u062a\u0631\u0643 \u0627\u0644\u0622\u0646 \u0644\u0644\u0645\u062a\u0627\u0628\u0639\u0629", callback_data="menu_subscribe")])
        kb_rows.append([InlineKeyboardButton(text="\U0001f4ca \u0646\u062a\u064a\u062c\u062a\u064a", callback_data="my_progress")])
    # ═══ FULLY ACTIVATED ═══
    else:
        kb_rows.append([InlineKeyboardButton(text="\U0001f4da \u062f\u0648\u0631\u0627\u062a\u064a", callback_data="my_courses")])
        kb_rows.append([
            InlineKeyboardButton(text="\u270d\ufe0f \u062a\u062f\u0631\u064a\u0628 \u0627\u0644\u062a\u0647\u062c\u0626\u0629", callback_data="spelling_practice"),
            InlineKeyboardButton(text="\U0001f501 \u0628\u0646\u0643 \u0627\u0644\u0623\u062e\u0637\u0627\u0621", callback_data="error_bank_review"),
        ])
        kb_rows.append([InlineKeyboardButton(text="\u26a1 \u062a\u062d\u062f\u064a \u0666\u0660 \u062b\u0627\u0646\u064a\u0629", callback_data="daily_challenge")])
        kb_rows.append([InlineKeyboardButton(text="\U0001f4ca \u062a\u0642\u062f\u0645\u064a", callback_data="my_progress")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    
    # status line
    if not has_placement:
        status = "\U0001f538 \u0645\u0631\u062d\u0628\u0627\u064b \u0628\u0643! \u0627\u0628\u062f\u0623 \u0628\u0627\u062e\u062a\u0628\u0627\u0631 \u0627\u0644\u0645\u0633\u062a\u0648\u0649 \u0644\u062a\u062d\u062f\u064a\u062f \u0645\u0633\u062a\u0648\u0627\u0643."
    elif not has_sub:
        status = f"\U0001f7e2 \u062a\u0645 \u062a\u062d\u062f\u064a\u062f \u0645\u0633\u062a\u0648\u0627\u0643: *{level}*\n\U0001f512 \u0627\u0634\u062a\u0631\u0643 \u0644\u0644\u0648\u0635\u0648\u0644 \u0644\u0644\u062f\u0631\u0648\u0633."
    else:
        status = f"\u2728 \u0645\u0633\u062a\u0648\u0627\u0643: *{level}* | \u0623\u0647\u0644\u0627\u064b \u0628\u0639\u0648\u062f\u062a\u0643!"

    await message.answer(f"\U0001f3e0 *\u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0631\u0626\u064a\u0633\u064a\u0629*\n_{status}_", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "student_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await show_main_menu(callback.message, callback.from_user.id)
    await callback.answer()



# ── Writing & Speaking quick access ──
@router.message(F.text.in_(["✍️ تقييم كتابة", "✍️ Writing Correction"]))
async def quick_writing(msg: Message, state: FSMContext):
    from .writing import writing_start
    await writing_start(msg, state)

@router.message(F.text.in_(["🎙️ تحدث", "🎙️ Speaking Coach"]))
async def quick_speaking(msg: Message, state: FSMContext):
    from .speaking import speaking_start
    await speaking_start(msg, state)
