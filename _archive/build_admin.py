import os

base = r'C:\yamen_academy'
path = os.path.join(base, 'handlers', 'admin.py')

code = """from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    get_stats, get_pending_payments, update_payment_status, get_payment, add_subscription,
    get_all_lessons, add_lesson, get_all_spelling_words, add_spelling_word,
    get_all_placement_questions, add_placement_question,
    get_all_lesson_quizzes, add_lesson_quiz, add_quiz_question,
    _safe_exec, dict_rows
)

router = Router()
ADMIN_IDS = {469136626}

def is_admin(uid):
    return uid in ADMIN_IDS

class AddLesson(StatesGroup):
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_level = State()
    waiting_for_media = State()
    waiting_for_action = State()

class AddSpelling(StatesGroup):
    waiting_for_word = State()

class AddPlaceQ(StatesGroup):
    waiting_for_data = State()

class AddQuiz(StatesGroup):
    waiting_for_info = State()
    waiting_for_questions = State()

class AddPlan(StatesGroup):
    waiting_for_data = State()

# ========== PANEL ==========
@router.message(Command("admin"))
async def panel(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return await msg.answer("Blocked")
    s = get_stats()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Lessons", callback_data="ac")],
        [InlineKeyboardButton(text="Plans", callback_data="ap")],
        [InlineKeyboardButton(text="Payments", callback_data="apa")],
        [InlineKeyboardButton(text="Words", callback_data="as")],
        [InlineKeyboardButton(text="Place Q", callback_data="apq")],
        [InlineKeyboardButton(text="Quizzes", callback_data="aq")],
    ])
    await msg.answer(f"Admin | St:{s['total_students']} Act:{s['active_subs']} Pend:{s['pending_payments']}", reply_markup=kb)

@router.callback_query(F.data == "ac")
async def ac(cb: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Add", callback_data="al")],
        [InlineKeyboardButton(text="Back", callback_data="bk")],
    ])
    await cb.message.edit_text("Content", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "al")
async def al(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddLesson.waiting_for_title)
    await cb.message.edit_text("Title?")
    await cb.answer()

@router.message(AddLesson.waiting_for_title)
async def lt(msg: types.Message, state: FSMContext):
    await state.update_data(title=msg.text)
    await state.set_state(AddLesson.waiting_for_content)
    await msg.answer("Content?")

@router.message(AddLesson.waiting_for_content)
async def lc(msg: types.Message, state: FSMContext):
    await state.update_data(content=msg.text)
    await state.set_state(AddLesson.waiting_for_level)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="A1", callback_data="lv_A1"), InlineKeyboardButton(text="A2", callback_data="lv_A2")],
        [InlineKeyboardButton(text="B1", callback_data="lv_B1"), InlineKeyboardButton(text="B2", callback_data="lv_B2")],
        [InlineKeyboardButton(text="C1", callback_data="lv_C1")],
    ])
    await msg.answer("Level?", reply_markup=kb)

@router.callback_query(F.data.startswith("lv_"))
async def ll(cb: types.CallbackQuery, state: FSMContext):
    lv = cb.data.split("_")[1]
    m = {"A1":1,"A2":2,"B1":3,"B2":4,"C1":5}
    await state.update_data(level=lv, course_id=m.get(lv,1))
    await state.set_state(AddLesson.waiting_for_media)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Photo", callback_data="md_photo"), InlineKeyboardButton(text="Audio", callback_data="md_audio")],
        [InlineKeyboardButton(text="Video", callback_data="md_video"), InlineKeyboardButton(text="Skip", callback_data="md_skip")],
    ])
    await cb.message.edit_text("Media?", reply_markup=kb)
    await cb.answer()

@router.callback_query(AddLesson.waiting_for_media, F.data.startswith("md_"))
async def lm(cb: types.CallbackQuery, state: FSMContext):
    mt = cb.data.split("_")[1]
    if mt == "skip":
        await state.update_data(media_type=None, media_file_id=None)
        await state.set_state(AddLesson.waiting_for_action)
        await _act(cb.message)
    else:
        await state.update_data(media_type=mt)
        await cb.message.edit_text("Send file")
    await cb.answer()

@router.message(AddLesson.waiting_for_media)
async def rm(msg: types.Message, state: FSMContext):
    d = await state.get_data()
    mt = d.get('media_type')
    fid = None
    if mt == 'photo' and msg.photo: fid = msg.photo[-1].file_id
    elif mt in ('audio','voice') and msg.audio: fid = msg.audio.file_id
    elif mt == 'video' and msg.video: fid = msg.video.file_id
    if fid: await state.update_data(media_file_id=fid)
    await state.set_state(AddLesson.waiting_for_action)
    await _act(msg)

async def _act(msg):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Speaking", callback_data="at_speaking"), InlineKeyboardButton(text="Writing", callback_data="at_writing")],
        [InlineKeyboardButton(text="None", callback_data="at_none")],
    ])
    await msg.answer("Action?", reply_markup=kb)

@router.callback_query(AddLesson.waiting_for_action, F.data.startswith("at_"))
async def la(cb: types.CallbackQuery, state: FSMContext):
    a = cb.data.split("_")[1]
    lb = None
    if a == 'speaking': lb = 'Speak'
    elif a == 'writing': lb = 'Correct'
    at = a if a != 'none' else None
    await state.update_data(action_type=at, action_label=lb)
    d = await state.get_data()
    add_lesson(d['title'], d['content'], d['course_id'],
               media_type=d.get('media_type'), media_file_id=d.get('media_file_id'),
               action_type=d.get('action_type'), action_label=d.get('action_label'))
    await state.clear()
    await cb.message.edit_text("Done")
    await cb.answer()

# ========== PLANS ==========
@router.callback_query(F.data == "ap")
async def ap(cb: types.CallbackQuery):
    pl = dict_rows(_safe_exec("SELECT * FROM subscription_plans ORDER BY price").fetchall())
    rows = [[InlineKeyboardButton(text="Add", callback_data="adp")]]
    for p in pl:
        rows.append([InlineKeyboardButton(text="X " + p['name'], callback_data="dp_" + str(p['id']))])
    rows.append([InlineKeyboardButton(text="Back", callback_data="bk")])
    await cb.message.edit_text("Plans", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await cb.answer()

@router.callback_query(F.data == "adp")
async def adp(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddPlan.waiting_for_data)
    await cb.message.edit_text("name|key|price|days")
    await cb.answer()

@router.message(AddPlan.waiting_for_data)
async def sp(msg: types.Message, state: FSMContext):
    p = msg.text.split("|")
    _safe_exec("INSERT OR REPLACE INTO subscription_plans(name,key,price,days) VALUES(?,?,?,?)",
               (p[0].strip(), p[1].strip(), float(p[2].strip()), int(p[3].strip())))
    await state.clear()
    await msg.answer("OK")

@router.callback_query(F.data.startswith("dp_"))
async def dp(cb: types.CallbackQuery):
    _safe_exec("DELETE FROM subscription_plans WHERE id=?", (int(cb.data.split("_")[1]),))
    await cb.message.edit_text("Deleted")
    await cb.answer()

# ========== WORDS ==========
@router.callback_query(F.data == "as")
async def aw(cb: types.CallbackQuery):
    w = get_all_spelling_words()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Add", callback_data="adw")],
        [InlineKeyboardButton(text="Back", callback_data="bk")],
    ])
    await cb.message.edit_text("Words: " + str(len(w)), reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "adw")
async def adw(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddSpelling.waiting_for_word)
    await cb.message.edit_text("word|def|level|cat|example")
    await cb.answer()

@router.message(AddSpelling.waiting_for_word)
async def sw(msg: types.Message, state: FSMContext):
    p = msg.text.split("|")
    add_spelling_word(p[0].strip(), p[1].strip() if len(p)>1 else "",
                      p[2].strip() if len(p)>2 else "A1",
                      p[3].strip() if len(p)>3 else "",
                      p[4].strip() if len(p)>4 else "")
    await state.clear()
    await msg.answer("OK")

# ========== PLACEMENT Q ==========
@router.callback_query(F.data == "apq")
async def apq(cb: types.CallbackQuery):
    q = get_all_placement_questions()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Add", callback_data="adpq")],
        [InlineKeyboardButton(text="Back", callback_data="bk")],
    ])
    await cb.message.edit_text("Questions: " + str(len(q)), reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "adpq")
async def adpq(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddPlaceQ.waiting_for_data)
    await cb.message.edit_text("q|A|B|C|D|idx|level")
    await cb.answer()

@router.message(AddPlaceQ.waiting_for_data)
async def spq(msg: types.Message, state: FSMContext):
    p = msg.text.split("|")
    add_placement_question(p[0].strip(), [p[i].strip() for i in range(1,5)],
                           int(p[5].strip()) if len(p)>5 else 0,
                           p[6].strip() if len(p)>6 else "A1")
    await state.clear()
    await msg.answer("OK")

# ========== QUIZZES ==========
@router.callback_query(F.data == "aq")
async def aq(cb: types.CallbackQuery):
    q = get_all_lesson_quizzes()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Add", callback_data="adq")],
        [InlineKeyboardButton(text="Back", callback_data="bk")],
    ])
    await cb.message.edit_text("Quizzes: " + str(len(q)), reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "adq")
async def adq(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddQuiz.waiting_for_info)
    await cb.message.edit_text("lesson_id|title|pass_score")
    await cb.answer()

@router.message(AddQuiz.waiting_for_info)
async def sqi(msg: types.Message, state: FSMContext):
    p = msg.text.split("|")
    qid = add_lesson_quiz(int(p[0].strip()), p[1].strip() if len(p)>1 else "Q",
                          int(p[2].strip()) if len(p)>2 else 60)
    await state.update_data(qid=qid)
    await state.set_state(AddQuiz.waiting_for_questions)
    await msg.answer("Send: q|A|B|C|D|idx. /done to finish")

@router.message(AddQuiz.waiting_for_questions)
async def sqq(msg: types.Message, state: FSMContext):
    if msg.text.strip() == "/done":
        await state.clear()
        return await msg.answer("Done")
    p = msg.text.split("|")
    d = await state.get_data()
    add_quiz_question(d['qid'], p[0].strip(), [p[i].strip() for i in range(1,5)],
                      int(p[5].strip()) if len(p)>5 else 0)
    await msg.answer("Next or /done")

# ========== PAYMENTS ==========
@router.callback_query(F.data == "apa")
async def apa(cb: types.CallbackQuery):
    pp = get_pending_payments()
    if not pp:
        await cb.message.edit_text("None"); await cb.answer(); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(p['user_id']), callback_data="app_" + str(p['id']))]
        for p in pp
    ])
    await cb.message.edit_text("Pending", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("app_"))
async def app(cb: types.CallbackQuery):
    pid = int(cb.data.split("_")[1])
    p = get_payment(pid)
    if not p: await cb.answer("?"); return
    update_payment_status(pid, "approved")
    add_subscription(p['user_id'], p['plan_name'], 30)
    await cb.message.edit_text("OK")
    await cb.answer()

@router.callback_query(F.data == "bk")
async def bk(cb: types.CallbackQuery):
    await panel(cb.message)
    await cb.answer()
"""

os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w', encoding='utf-8') as f:
    f.write(code)
print("DONE - admin.py written")
