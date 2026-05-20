import os

BASE = r'C:\yamen_academy'

# ============================================================
# Fix 1: subscriptions.py — fix \$ escape warnings
# ============================================================
subs_content = '''from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import add_payment, _safe_exec, dict_rows

router = Router()

def get_plans():
    cur = _safe_exec("SELECT * FROM subscription_plans WHERE active=1 ORDER BY price")
    return dict_rows(cur.fetchall())

@router.callback_query(F.data == "menu_subscribe")
async def menu_subscribe(callback: types.CallbackQuery):
    plans = get_plans()
    if not plans:
        await callback.message.edit_text("\\u26a0\\ufe0f \\u0644\\u0627 \\u062a\\u0648\\u062c\\u062f \\u062e\\u0637\\u0637 \\u0645\\u062a\\u0627\\u062d\\u0629 \\u062d\\u0627\\u0644\\u064a\\u0627\\u064b.")
        await callback.answer()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p['name']} \\u2014 {p['price']}$", callback_data=f"plan_{p['key']}")]
        for p in plans
    ] + [[InlineKeyboardButton(text="\\U0001f519 \\u0631\\u062c\\u0648\\u0639", callback_data="student_menu")]])
    await callback.message.edit_text("\\U0001f48e *\\u062e\\u0637\\u0637 \\u0627\\u0644\\u0627\\u0634\\u062a\\u0631\\u0627\\u0643*\\n\\u0627\\u062e\\u062a\\u0631 \\u062e\\u0637\\u062a\\u0643:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("plan_"))
async def show_plan(callback: types.CallbackQuery):
    key = callback.data.split("_")[1]
    plans = get_plans()
    plan = next((p for p in plans if p['key'] == key), None)
    if not plan:
        await callback.answer("\\u274c \\u062e\\u0637\\u0629 \\u063a\\u064a\\u0631 \\u0645\\u0648\\u062c\\u0648\\u062f\\u0629", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\\U0001f4f8 \\u0625\\u0631\\u0633\\u0627\\u0644 \\u0625\\u064a\\u0635\\u0627\\u0644 \\u0627\\u0644\\u062f\\u0641\\u0639", callback_data=f"pay_{key}")],
        [InlineKeyboardButton(text="\\U0001f519 \\u0631\\u062c\\u0648\\u0639", callback_data="menu_subscribe")],
    ])
    await callback.message.edit_text(
        f"*{plan['name']}* \\u2014 {plan['price']}$ \\u0644\\u0645\\u062f\\u0629 {plan['days']} \\u064a\\u0648\\u0645\\n\\n"
        "\\u0644\\u0644\\u0627\\u0634\\u062a\\u0631\\u0627\\u0643:\\n1\\ufe0f\\u20e3 \\u062d\\u0648\\u0651\\u0644 \\u0627\\u0644\\u0645\\u0628\\u0644\\u063a\\n2\\ufe0f\\u20e3 \\u0623\\u0631\\u0633\\u0644 \\u0635\\u0648\\u0631\\u0629 \\u0627\\u0644\\u0625\\u064a\\u0635\\u0627\\u0644 \\u0647\\u0646\\u0627",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pay_"))
async def request_receipt(callback: types.CallbackQuery):
    key = callback.data.split("_")[1]
    plans = get_plans()
    plan = next((p for p in plans if p['key'] == key), None)
    await callback.message.edit_text(
        f"\\U0001f4f8 \\u0623\\u0631\\u0633\\u0644 \\u0635\\u0648\\u0631\\u0629 \\u0625\\u064a\\u0635\\u0627\\u0644 \\u0627\\u0644\\u062f\\u0641\\u0639 \\u0627\\u0644\\u0622\\u0646\\n\\u0627\\u0644\\u062e\\u0637\\u0629: *{plan['name']}* \\u2014 {plan['price']}$",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(F.photo)
async def handle_receipt_photo(message: types.Message):
    file_id = message.photo[-1].file_id
    add_payment(message.from_user.id, 'subscription', 0, file_id)
    await message.answer("\\u2705 \\u062a\\u0645 \\u0627\\u0633\\u062a\\u0644\\u0627\\u0645 \\u0627\\u0644\\u0625\\u064a\\u0635\\u0627\\u0644! \\u0633\\u064a\\u0631\\u0627\\u062c\\u0639\\u0647 \\u0627\\u0644\\u0623\\u062f\\u0645\\u0646 \\u0642\\u0631\\u064a\\u0628\\u0627\\u064b.")
'''

with open(os.path.join(BASE, 'handlers', 'subscriptions.py'), 'w', encoding='utf-8') as f:
    f.write(subs_content.strip() + '\n')
print('1/2: subscriptions.py FIXED')

# ============================================================
# Fix 2: admin.py — rebuild clean with plans section
# ============================================================
admin_content = r'''
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    get_stats, get_pending_payments, update_payment_status, get_payment, add_subscription,
    get_all_lessons, add_lesson, get_all_spelling_words, add_spelling_word, delete_spelling_word,
    get_all_placement_questions, add_placement_question, delete_placement_question,
    get_all_lesson_quizzes, delete_lesson_quiz, add_lesson_quiz, add_quiz_question,
    get_quiz_questions, _safe_exec, dict_rows
)

router = Router()
ADMIN_IDS = {469136626}

def is_admin(user_id):
    return user_id in ADMIN_IDS

class AddLesson(StatesGroup):
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_level = State()
    waiting_for_media = State()
    waiting_for_action = State()

class AddSpelling(StatesGroup):
    waiting_for_word = State()

class AddPlaceQ(StatesGroup):
    waiting_for_question = State()

class AddQuiz(StatesGroup):
    waiting_for_lesson_id = State()
    waiting_for_question = State()

class AddPlan(StatesGroup):
    waiting_for_plan = State()

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("\u26d4 \u063a\u064a\u0631 \u0645\u0635\u0631\u062d")
        return
    stats = get_stats()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f4da \u0627\u0644\u0645\u062d\u062a\u0648\u0649 \u0648\u0627\u0644\u062f\u0631\u0648\u0633", callback_data="admin_content")],
        [InlineKeyboardButton(text="\U0001f465 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645\u064a\u0646", callback_data="admin_users")],
        [InlineKeyboardButton(text="\U0001f48e \u062e\u0637\u0637 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643", callback_data="admin_plans")],
        [InlineKeyboardButton(text="\U0001f4b3 \u0627\u0644\u0645\u062f\u0641\u0648\u0639\u0627\u062a", callback_data="admin_payments")],
        [InlineKeyboardButton(text="\u270d\ufe0f \u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0643\u0644\u0645\u0627\u062a", callback_data="admin_spelling")],
        [InlineKeyboardButton(text="\U0001f4dd \u0625\u062f\u0627\u0631\u0629 \u0623\u0633\u0626\u0644\u0629 \u0627\u0644\u0645\u0633\u062a\u0648\u0649", callback_data="admin_placement")],
        [InlineKeyboardButton(text="\U0001f9ea \u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0627\u062e\u062a\u0628\u0627\u0631\u0627\u062a", callback_data="admin_quizzes")],
    ])
    await message.answer(
        f"\U0001f6e1\ufe0f *\u0644\u0648\u062d\u0629 \u0627\u0644\u0623\u062f\u0645\u0646*\n\n"
        f"\U0001f465 \u0627\u0644\u0637\u0644\u0627\u0628: {stats['total_students']}\n"
        f"\u2705 \u0627\u0644\u0646\u0634\u0637\u0627\u0621: {stats['active_subs']}\n"
        f"\U0001f4b3 \u0645\u0639\u0644\u0642\u0629: {stats['pending_payments']}",
        reply_markup=kb, parse_mode="Markdown"
    )

# ─── CONTENT ───
@router.callback_query(F.data == "admin_content")
async def admin_content(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u2795 \u0625\u0636\u0627\u0641\u0629 \u062f\u0631\u0633 \u062c\u062f\u064a\u062f", callback_data="add_lesson")],
        [InlineKeyboardButton(text="\U0001f4cb \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u062f\u0631\u0648\u0633", callback_data="list_lessons")],
        [InlineKeyboardButton(text="\U0001f519 \u0631\u062c\u0648\u0639", callback_data="admin_back")],
    ])
    await callback.message.edit_text("\U0001f4da *\u0642\u0633\u0645 \u0627\u0644\u0645\u062d\u062a\u0648\u0649*", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "add_lesson")
async def add_lesson_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddLesson.waiting_for_title)
    await callback.message.edit_text("\U0001f4dd \u0623\u0631\u0633\u0644 \u0639\u0646\u0648\u0627\u0646 \u0627\u0644\u062f\u0631\u0633:")
    await callback.answer()

@router.message(AddLesson.waiting_for_title)
async def add_lesson_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddLesson.waiting_for_content)
    await message.answer("\U0001f4c4 \u0623\u0631\u0633\u0644 \u0645\u062d\u062a\u0648\u0649 \u0627\u0644\u062f\u0631\u0633:")

@router.message(AddLesson.waiting_for_content)
async def add_lesson_content(message: types.Message, state: FSMContext):
    await state.update_data(content=message.text)
    await state.set_state(AddLesson.waiting_for_level)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="A1 \U0001f538", callback_data="lvl_A1"),
         InlineKeyboardButton(text="A2 \U0001f7e0", callback_data="lvl_A2")],
        [InlineKeyboardButton(text="B1 \U0001f7e1", callback_data="lvl_B1"),
         InlineKeyboardButton(text="B2 \U0001f7e2", callback_data="lvl_B2")],
        [InlineKeyboardButton(text="C1 \U0001f534", callback_data="lvl_C1")],
    ])
    await message.answer("\U0001f3af \u0627\u062e\u062a\u0631 \u0627\u0644\u0645\u0633\u062a\u0648\u0649:", reply_markup=kb)

@router.callback_query(F.data.startswith("lvl_"))
async def add_lesson_level(callback: types.CallbackQuery, state: FSMContext):
    level = callback.data.split("_")[1]
    cinfo = {"A1":1,"A2":2,"B1":3,"B2":4,"C1":5}
    await state.update_data(level=level, course_id=cinfo.get(level,1))
    await state.set_state(AddLesson.waiting_for_media)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f5bc\ufe0f \u0635\u0648\u0631\u0629", callback_data="media_photo"),
         InlineKeyboardButton(text="\U0001f3b5 \u0635\u0648\u062a", callback_data="media_audio")],
        [InlineKeyboardButton(text="\U0001f3ac \u0641\u064a\u062f\u064a\u0648", callback_data="media_video"),
         InlineKeyboardButton(text="\u23ed\ufe0f \u062a\u062e\u0637\u064a", callback_data="media_skip")],
    ])
    await callback.message.edit_text("\u0647\u0644 \u062a\u0631\u064a\u062f \u0625\u0636\u0627\u0641\u0629 \u0648\u0633\u0627\u0626\u0637\u061f", reply_markup=kb)
    await callback.answer()

@router.callback_query(AddLesson.waiting_for_media, F.data.startswith("media_"))
async def add_lesson_media(callback: types.CallbackQuery, state: FSMContext):
    mt = callback.data.split("_")[1]
    if mt == "skip":
        await state.update_data(media_type=None, media_file_id=None)
        await state.set_state(AddLesson.waiting_for_action)
        await _ask_action(callback.message)
    else:
        await state.update_data(media_type=mt)
        await callback.message.edit_text("\U0001f4ce \u0623\u0631\u0633\u0644 \u0627\u0644\u0645\u0644\u0641 \u0627\u0644\u0622\u0646:")
    await callback.answer()

@router.message(AddLesson.waiting_for_media)
async def receive_media(message: types.Message, state: FSMContext):
    data = await state.get_data()
    mt = data.get('media_type')
    file_id = None
    if mt == 'photo' and message.photo:
        file_id = message.photo[-1].file_id
    elif mt in ('audio','voice') and message.audio:
        file_id = message.audio.file_id
    elif mt == 'video' and message.video:
        file_id = message.video.file_id
    if file_id:
        await state.update_data(media_file_id=file_id)
    await state.set_state(AddLesson.waiting_for_action)
    await _ask_action(message)

async def _ask_action(msg):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f3a4 \u062a\u062d\u062f\u062b", callback_data="act_speaking"),
         InlineKeyboardButton(text="\u270d\ufe0f \u062a\u0635\u062d\u064a\u062d", callback_data="act_writing")],
        [InlineKeyboardButton(text="\u23ed\ufe0f \u0628\u062f\u0648\u0646", callback_data="act_none")],
    ])
    await msg.answer("\u0647\u0644 \u062a\u0631\u064a\u062f \u0625\u0636\u0627\u0641\u0629 \u0632\u0631 \u062a\u0641\u0627\u0639\u0644\u064a\u061f", reply_markup=kb)

@router.callback_query(AddLesson.waiting_for_action, F.data.startswith("act_"))
async def add_lesson_action(callback: types.CallbackQuery, state: FSMContext):
    act = callback.data.split("_")[1]
    await state.update_data(
        action_type=act if act != 'none' else None,
        action_label='\U0001f3a4 \u062a\u062d\u062f\u062b' if act=='speaking' else '\u270d\ufe0f \u0635\u062d\u062d \u0643\u062a\u0627\u0628\u062a\u064a' if act=='writing' else None
    )
    data = await state.get_data()
    add_lesson(data['title'], data['content'], data['course_id'],
               media_type=data.get('media_type'), media_file_id=data.get('media_file_id'),
               action_type=data.get('action_type'), action_label=data.get('action_label'))
    await state.clear()
    await callback.message.edit_text("\u2705 \u062a\u0645\u062a \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u062f\u0631\u0633 \u0628\u0646\u062c\u0627\u062d")
    await callback.answer()

# ─── SUBSCRIPTION PLANS MANAGEMENT ───
@router.callback_query(F.data == "admin_plans")
async def admin_plans(callback: types.CallbackQuery):
    plans = dict_rows(_safe_exec("SELECT * FROM subscription_plans ORDER BY price").fetchall())
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u2795 \u0625\u0636\u0627\u0641\u0629 \u062e\u0637\u0629", callback_data="add_plan")],
        *([[InlineKeyboardButton(
            text=f"\u274c {p['name']} \\u2014 {p['price']}$",
            callback_data=f"delplan_{p['id']}"
        )] for p in plans]),
        [InlineKeyboardButton(text="\U0001f519 \u0631\u062c\u0648\u0639", callback_data="admin_back")],
    ])
    await callback.message.edit_text(
        f"\U0001f48e *\u062e\u0637\u0637 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643* ({len(plans)} \u062e\u0637\u0629)",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "add_plan")
async def add_plan_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddPlan.waiting_for_plan)
    await callback.message.edit_text(
        "\u0623\u0631\u0633\u0644 \u0627\u0644\u062e\u0637\u0629 \u0628\u0647\u0630\u0627 \u0627\u0644\u0634\u0643\u0644:\\n" +
        "
ame|key|price|days\\n\\n" +
        "\u0645\u062b\u0627\u0644: \u0634\u0647\u0631|1month|10|30",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AddPlan.waiting_for_plan)
async def add_plan_save(message: types.Message, state: FSMContext):
    parts = message.text.split("|")
    name, key = parts[0].strip(), parts[1].strip()
    price, days = float(parts[2].strip()), int(parts[3].strip())
    _safe_exec("INSERT OR REPLACE INTO subscription_plans(name,key,price,days) VALUES(?,?,?,?)",
               (name, key, price, days))
    await state.clear()
    await message.answer(f"\u2705 \u0623\u0636\u064a\u0641\u062a \u0627\u0644\u062e\u0637\u0629: *{name}* \\u2014 {price}$ / {days} \u064a\u0648\u0645", parse_mode="Markdown")

@router.callback_query(F.data.startswith("delplan_"))
async def del_plan(callback: types.CallbackQuery):
    pid = int(callback.data.split("_")[1])
    _safe_exec("DELETE FROM subscription_plans WHERE id=?", (pid,))
    await callback.message.edit_text("\u2705 \u062d\u0630\u0641\u062a \u0627\u0644\u062e\u0637\u0629.")
    await callback.answer()

# ─── SPELLING MANAGEMENT ───
@router.callback_query(F.data == "admin_spelling")
async def admin_spelling(callback: types.CallbackQuery):
    words = get_all_spelling_words()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u2795 \u0625\u0636\u0627\u0641\u0629 \u0643\u0644\u0645\u0629", callback_data="add_spell")],
        [InlineKeyboardButton(text="\U0001f519 \u0631\u062c\u0648\u0639", callback_data="admin_back")],
    ])
    await callback.message.edit_text(
        f"\u270d\ufe0f *\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0643\u0644\u0645\u0627\u062a* ({len(words)} \u0643\u0644\u0645\u0629)",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "add_spell")
async def add_spell_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddSpelling.waiting_for_word)
    await callback.message.edit_text("\u0623\u0631\u0633\u0644 \u0627\u0644\u0643\u0644\u0645\u0629 \u0628\u0647\u0630\u0627 \u0627\u0644\u0634\u0643\u0644:\\nword|definition|level|category|example", parse_mode="Markdown")
    await callback.answer()

@router.message(AddSpelling.waiting_for_word)
async def add_spell_save(message: types.Message, state: FSMContext):
    parts = message.text.split("|")
    word = parts[0].strip()
    definition = parts[1].strip() if len(parts)>1 else ''
    level = parts[2].strip() if len(parts)>2 else 'A1'
    category = parts[3].strip() if len(parts)>3 else ''
    example = parts[4].strip() if len(parts)>4 else ''
    add_spelling_word(word, definition, level, category, example)
    await state.clear()
    await message.answer(f"\u2705 \u0623\u0636\u064a\u0641\u062a: *{word}*", parse_mode="Markdown")

# ─── PLACEMENT QUESTIONS MANAGEMENT ───
@router.callback_query(F.data == "admin_placement")
async def admin_placement(callback: types.CallbackQuery):
    qs = get_all_placement_questions()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u2795 \u0625\u0636\u0627\u0641\u0629 \u0633\u0624\u0627\u0644", callback_data="add_placeq")],
        [InlineKeyboardButton(text="\U0001f519 \u0631\u062c\u0648\u0639", callback_data="admin_back")],
    ])
    await callback.message.edit_text(
        f"\U0001f4dd *\u0623\u0633\u0626\u0644\u0629 \u062a\u062d\u062f\u064a\u062f \u0627\u0644\u0645\u0633\u062a\u0648\u0649* ({len(qs)} \u0633\u0624\u0627\u0644)",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "add_placeq")
async def add_placeq_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddPlaceQ.waiting_for_question)
    await callback.message.edit_text("\u0623\u0631\u0633\u0644 \u0627\u0644\u0633\u0624\u0627\u0644 + \u0627\u0644\u062e\u064a\u0627\u0631\u0627\u062a:\\nquestion|A|B|C|D|correct_index|level", parse_mode="Markdown")
    await callback.answer()

@router.message(AddPlaceQ.waiting_for_question)
async def add_placeq_save(message: types.Message, state: FSMContext):
    parts = message.text.split("|")
    question = parts[0].strip()
    opts = [parts[i].strip() for i in range(1,5)]
    correct = int(parts[5].strip()) if len(parts)>5 else 0
    level = parts[6].strip() if len(parts)>6 else 'A1'
    add_placement_question(question, opts, correct, level)
    await state.clear()
    await message.answer(f"\u2705 \u0623\u0636\u064a\u0641 \u0627\u0644\u0633\u0624\u0627\u0644: {question[:40]}...")

# ─── QUIZZES MANAGEMENT ───
@router.callback_query(F.data == "admin_quizzes")
async def admin_quizzes(callback: types.CallbackQuery):
    quizzes = get_all_lesson_quizzes()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u2795 \u0625\u0646\u0634\u0627\u0621 \u0627\u062e\u062a\u0628\u0627\u0631", callback_data="add_quiz")],
        [InlineKeyboardButton(text="\U0001f519 \u0631\u062c\u0648\u0639", callback_data="admin_back")],
    ])
    await callback.message.edit_text(
        f"\U0001f9ea *\u0627\u0644\u0627\u062e\u062a\u0628\u0627\u0631\u0627\u062a* ({len(quizzes)} \u0627\u062e\u062a\u0628\u0627\u0631)",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "add_quiz")
async def add_quiz_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddQuiz.waiting_for_lesson_id)
    await callback.message.edit_text("\u0623\u0631\u0633\u0644 lesson_id|title|pass_score:\\n\u0645\u062b\u0627\u0644: 1|Quiz 1|60", parse_mode="Markdown")
    await callback.answer()

@router.message(AddQuiz.waiting_for_lesson_id)
async def add_quiz_info(message: types.Message, state: FSMContext):
    parts = message.text.split("|")
    lesson_id = int(parts[0].strip())
    title = parts[1].strip() if len(parts)>1 else 'Quiz'
    pass_score = int(parts[2].strip()) if len(parts)>2 else 60
    quiz_id = add_lesson_quiz(lesson_id, title, pass_score)
    await state.update_data(quiz_id=quiz_id, lesson_id=lesson_id)
    await state.set_state(AddQuiz.waiting_for_question)
    await message.answer(
        f"\u2705 \u062a\u0645 \u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u0627\u062e\u062a\u0628\u0627\u0631 (ID={quiz_id})\\n" +
        "\u0627\u0644\u0622\u0646 \u0623\u0631\u0633\u0644 \u0627\u0644\u0623\u0633\u0626\u0644\u0629:\\n" +
        "question|A|B|C|D|correct_index\\n\u0623\u0631\u0633\u0644 /done \u0644\u0644\u0627\u0646\u062a\u0647\u0627\u0621"
    )

@router.message(AddQuiz.waiting_for_question)
async def add_quiz_q(message: types.Message, state: FSMContext):
    if message.text.strip() == '/done':
        data = await state.get_data()
        await state.clear()
        await message.answer(f"\u2705 \u0627\u0646\u062a\u0647\u0649 \u0627\u062e\u062a\u0628\u0627\u0631 \u0627\u0644\u062f\u0631\u0633 {data.get('lesson_id')}")
        return
    parts = message.text.split("|")
    question = parts[0].strip()
    opts = [parts[i].strip() for i in range(1,5)]
    correct = int(parts[5].strip()) if len(parts)>5 else 0
    data = await state.get_data()
    add_quiz_question(data['quiz_id'], question, opts, correct)
    await message.answer("\u2705 \u0623\u0636\u064a\u0641 \u0627\u0644\u0633\u0624\u0627\u0644. \u0623\u0631\u0633\u0644 \u0627\u0644\u062a\u0627\u0644\u064a \u0623\u0648 /done")

# ─── PAYMENTS ───
@router.callback_query(F.data == "admin_payments")
async def admin_payments(callback: types.CallbackQuery):
    payments = get_pending_payments()
    if not payments:
        await callback.message.edit_text("\U0001f4b3 \u0644\u0627 \u062a\u0648\u062c\u062f \u0645\u062f\u0641\u0648\u0639\u0627\u062a \u0645\u0639\u0644\u0642\u0629")
        await callback.answer(); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"\U0001f4b0 {p['user_id']} - {p['plan_name']}",
                              callback_data=f"approve_{p['id']}")]
        for p in payments
    ])
    await callback.message.edit_text("\U0001f4b3 *\u0645\u062f\u0641\u0648\u0639\u0627\u062a \u0645\u0639\u0644\u0642\u0629*", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    pid = int(callback.data.split("_")[1])
    payment = get_payment(pid)
    if not payment:
        await callback.answer("\u274c \u063a\u064a\u0631 \u0645\u0648\u062c\u0648\u062f", show_alert=True); return
    update_payment_status(pid, 'approved')
    add_subscription(payment['user_id'], payment['plan_name'], 30)
    await callback.message.edit_text("\u2705 \u062a\u0645 \u0627\u0644\u062a\u0641\u0639\u064a\u0644 \u0648\u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643")
    await callback.answer()

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    await admin_panel(callback.message)
    await callback.answer()
'''

with open(os.path.join(BASE, 'handlers', 'admin.py'), 'w', encoding='utf-8') as f:
    f.write(admin_content.strip() + '\n')
print('2/2: admin.py REBUILT clean with plans section')

print('\n========== DONE ==========')
