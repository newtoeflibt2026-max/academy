import os

BASE = r"C:\yamen_academy"

admin_code = """from aiogram import Router, F, types
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
import json

router = Router()
ADMIN_IDS = {469136626, 5572314718}

def is_admin(uid): return uid in ADMIN_IDS

class AddLesson(StatesGroup):
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_level = State()
    waiting_for_media = State()
    waiting_for_action = State()

class AddSpelling(StatesGroup):
    waiting_for_data = State()

class AddPlaceQ(StatesGroup):
    waiting_for_data = State()

class AddQuiz(StatesGroup):
    waiting_for_lesson = State()
    waiting_for_questions = State()

class AddPlan(StatesGroup):
    waiting_for_data = State()

class ImportData(StatesGroup):
    waiting_for_file = State()

class GroupLink(StatesGroup):
    waiting_for_link = State()

def extract_file_id(msg):
    if msg.audio: return ('audio', msg.audio.file_id)
    if msg.voice: return ('voice', msg.voice.file_id)
    if msg.video: return ('video', msg.video.file_id)
    if msg.video_note: return ('video_note', msg.video_note.file_id)
    if msg.photo: return ('photo', msg.photo[-1].file_id)
    if msg.document:
        mime = msg.document.mime_type or ''
        if 'audio' in mime: return ('audio', msg.document.file_id)
        if 'video' in mime: return ('video', msg.document.file_id)
        return ('document', msg.document.file_id)
    if msg.animation: return ('animation', msg.animation.file_id)
    if msg.sticker: return ('sticker', msg.sticker.file_id)
    return (None, None)

@router.message(Command("admin"))
async def panel(msg: types.Message):
    if not is_admin(msg.from_user.id): return await msg.answer("Blocked")
    s = get_stats()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Content", callback_data="admin_content")],
        [InlineKeyboardButton(text="Plans", callback_data="admin_plans")],
        [InlineKeyboardButton(text="Payments", callback_data="admin_payments")],
        [InlineKeyboardButton(text="Words", callback_data="admin_spelling")],
        [InlineKeyboardButton(text="Placement Q", callback_data="admin_placement")],
        [InlineKeyboardButton(text="Quizzes", callback_data="admin_quizzes")],
        [InlineKeyboardButton(text="Import", callback_data="admin_import")],
        [InlineKeyboardButton(text="Group Link", callback_data="admin_group")],
    ])
    await msg.answer(f"Admin | St:{s['total_students']} Act:{s['active_subs']} Pend:{s['pending_payments']}", reply_markup=kb)

@router.callback_query(F.data == "admin_back")
async def admin_back(cb: types.CallbackQuery):
    s = get_stats()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Content", callback_data="admin_content")],
        [InlineKeyboardButton(text="Plans", callback_data="admin_plans")],
        [InlineKeyboardButton(text="Payments", callback_data="admin_payments")],
        [InlineKeyboardButton(text="Words", callback_data="admin_spelling")],
        [InlineKeyboardButton(text="Placement Q", callback_data="admin_placement")],
        [InlineKeyboardButton(text="Quizzes", callback_data="admin_quizzes")],
        [InlineKeyboardButton(text="Import", callback_data="admin_import")],
        [InlineKeyboardButton(text="Group Link", callback_data="admin_group")],
    ])
    await cb.message.edit_text(f"Admin | St:{s['total_students']} Act:{s['active_subs']} Pend:{s['pending_payments']}", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "admin_content")
async def admin_content(cb: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Add Lesson", callback_data="add_lesson")],
        [InlineKeyboardButton(text="List Lessons", callback_data="list_lessons")],
        [InlineKeyboardButton(text="Back", callback_data="admin_back")],
    ])
    await cb.message.edit_text("Content", reply_markup=kb); await cb.answer()

@router.callback_query(F.data == "add_lesson")
async def add_lesson_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddLesson.waiting_for_title)
    await cb.message.edit_text("Title?"); await cb.answer()

@router.message(AddLesson.waiting_for_title)
async def add_lesson_title(msg: types.Message, state: FSMContext):
    await state.update_data(title=msg.text)
    await state.set_state(AddLesson.waiting_for_content)
    await msg.answer("Content?")

@router.message(AddLesson.waiting_for_content)
async def add_lesson_content(msg: types.Message, state: FSMContext):
    await state.update_data(content=msg.text)
    await state.set_state(AddLesson.waiting_for_level)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="A1", callback_data="lvl_A1"), InlineKeyboardButton(text="A2", callback_data="lvl_A2")],
        [InlineKeyboardButton(text="B1", callback_data="lvl_B1"), InlineKeyboardButton(text="B2", callback_data="lvl_B2")],
        [InlineKeyboardButton(text="C1", callback_data="lvl_C1")],
    ])
    await msg.answer("Level?", reply_markup=kb)

@router.callback_query(F.data.startswith("lvl_"))
async def add_lesson_level(cb: types.CallbackQuery, state: FSMContext):
    lv = cb.data.split("_")[1]
    m = {"A1":1,"A2":2,"B1":3,"B2":4,"C1":5}
    await state.update_data(level=lv, course_id=m.get(lv,1))
    await state.set_state(AddLesson.waiting_for_media)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Photo", callback_data="media_photo"), InlineKeyboardButton(text="Audio", callback_data="media_audio")],
        [InlineKeyboardButton(text="Voice", callback_data="media_voice"), InlineKeyboardButton(text="Video", callback_data="media_video")],
        [InlineKeyboardButton(text="Document", callback_data="media_document"), InlineKeyboardButton(text="Skip", callback_data="media_skip")],
    ])
    await cb.message.edit_text("Media?\\nSend file, or choose type then send:", reply_markup=kb); await cb.answer()

@router.callback_query(AddLesson.waiting_for_media, F.data.startswith("media_"))
async def add_lesson_media(cb: types.CallbackQuery, state: FSMContext):
    mt = cb.data.split("_")[1]
    if mt == "skip":
        await state.update_data(media_type=None, media_file_id=None)
        await state.set_state(AddLesson.waiting_for_action)
        await _ask_action(cb.message)
    else:
        await state.update_data(media_type=mt)
        await cb.message.edit_text(f"Send {mt} file now (forward from channel or upload)")
    await cb.answer()

@router.message(AddLesson.waiting_for_media)
async def receive_media(msg: types.Message, state: FSMContext):
    d = await state.get_data()
    preferred_type = d.get('media_type')
    
    # Try to detect actual file type
    actual_type, fid = extract_file_id(msg)
    
    if fid:
        final_type = preferred_type if preferred_type and preferred_type != 'document' else actual_type
        await state.update_data(media_file_id=fid, media_type=final_type)
        await state.set_state(AddLesson.waiting_for_action)
        await msg.answer(f"Got {final_type}! file_id: {fid[:20]}...")
        await _ask_action(msg)
    else:
        await msg.answer("No media found. Forward a message with audio/photo/video, or upload a file. /cancel to abort.")

async def _ask_action(msg):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Speaking", callback_data="act_speaking"), InlineKeyboardButton(text="Writing", callback_data="act_writing")],
        [InlineKeyboardButton(text="None", callback_data="act_none")],
    ])
    await msg.answer("Action?", reply_markup=kb)

@router.callback_query(AddLesson.waiting_for_action, F.data.startswith("act_"))
async def add_lesson_action(cb: types.CallbackQuery, state: FSMContext):
    a = cb.data.split("_")[1]
    lb = {'speaking':'Speak','writing':'Correct'}.get(a)
    at = a if a != 'none' else None
    await state.update_data(action_type=at, action_label=lb)
    d = await state.get_data()
    add_lesson(d['title'], d['content'], d['course_id'],
               media_type=d.get('media_type'), media_file_id=d.get('media_file_id'),
               action_type=d.get('action_type'), action_label=d.get('action_label'))
    await state.clear()
    await cb.message.edit_text("Done"); await cb.answer()

# Plans
@router.callback_query(F.data == "admin_plans")
async def admin_plans(cb: types.CallbackQuery):
    pl = dict_rows(_safe_exec("SELECT * FROM subscription_plans ORDER BY price").fetchall())
    rows = [[InlineKeyboardButton(text="Add", callback_data="add_plan")]]
    for p in pl:
        rows.append([InlineKeyboardButton(text="X "+p['name'], callback_data="dp_"+str(p['id']))])
    rows.append([InlineKeyboardButton(text="Back", callback_data="admin_back")])
    await cb.message.edit_text("Plans", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)); await cb.answer()

@router.callback_query(F.data == "add_plan")
async def add_plan_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddPlan.waiting_for_data)
    await cb.message.edit_text("name|key|price|days"); await cb.answer()

@router.message(AddPlan.waiting_for_data)
async def add_plan_save(msg: types.Message, state: FSMContext):
    p = msg.text.split("|")
    _safe_exec("INSERT OR REPLACE INTO subscription_plans(name,key,price,days) VALUES(?,?,?,?)",
               (p[0].strip(), p[1].strip(), float(p[2].strip()), int(p[3].strip())))
    await state.clear(); await msg.answer("OK")

@router.callback_query(F.data.startswith("dp_"))
async def del_plan(cb: types.CallbackQuery):
    _safe_exec("DELETE FROM subscription_plans WHERE id=?", (int(cb.data.split("_")[1]),))
    await cb.message.edit_text("Deleted"); await cb.answer()

# Words
@router.callback_query(F.data == "admin_spelling")
async def admin_spelling(cb: types.CallbackQuery):
    w = get_all_spelling_words()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Add", callback_data="add_word")],
        [InlineKeyboardButton(text="Back", callback_data="admin_back")],
    ])
    await cb.message.edit_text(f"Words: {len(w)}", reply_markup=kb); await cb.answer()

@router.callback_query(F.data == "add_word")
async def add_word_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddSpelling.waiting_for_data)
    await cb.message.edit_text("word|def|level|cat|example"); await cb.answer()

@router.message(AddSpelling.waiting_for_data)
async def add_word_save(msg: types.Message, state: FSMContext):
    p = msg.text.split("|")
    add_spelling_word(p[0].strip(), p[1].strip() if len(p)>1 else "",
                      p[2].strip() if len(p)>2 else "A1",
                      p[3].strip() if len(p)>3 else "general",
                      p[4].strip() if len(p)>4 else "")
    await state.clear(); await msg.answer("OK")

# Placement
@router.callback_query(F.data == "admin_placement")
async def admin_placement(cb: types.CallbackQuery):
    q = get_all_placement_questions()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Add MCQ", callback_data="add_place_mcq")],
        [InlineKeyboardButton(text="Add Spelling", callback_data="add_place_spell")],
        [InlineKeyboardButton(text="Back", callback_data="admin_back")],
    ])
    await cb.message.edit_text(f"Questions: {len(q)}", reply_markup=kb); await cb.answer()

@router.callback_query(F.data == "add_place_mcq")
async def add_place_mcq(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddPlaceQ.waiting_for_data)
    await state.update_data(qtype="mcq")
    await cb.message.edit_text("question|opt1|opt2|opt3|opt4|correct|level"); await cb.answer()

@router.callback_query(F.data == "add_place_spell")
async def add_place_spell(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddPlaceQ.waiting_for_data)
    await state.update_data(qtype="spelling")
    await cb.message.edit_text("word|level|hint"); await cb.answer()

@router.message(AddPlaceQ.waiting_for_data)
async def add_place_save(msg: types.Message, state: FSMContext):
    d = await state.get_data(); qtype = d.get("qtype","mcq"); p = msg.text.split("|")
    if qtype == "mcq":
        add_placement_question(p[0].strip(), p[6].strip(), qtype,
                              options=json.dumps([x.strip() for x in p[1:5]]),
                              correct_answer=p[5].strip())
    elif qtype == "spelling":
        add_placement_question(p[0].strip(), p[1].strip(), qtype,
                              correct_answer=p[0].strip(),
                              hint=p[2].strip() if len(p)>2 else "")
    await state.clear(); await msg.answer("OK")

# Quizzes
@router.callback_query(F.data == "admin_quizzes")
async def admin_quizzes(cb: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Add Quiz", callback_data="add_quiz")],
        [InlineKeyboardButton(text="Back", callback_data="admin_back")],
    ])
    await cb.message.edit_text("Quizzes", reply_markup=kb); await cb.answer()

@router.callback_query(F.data == "add_quiz")
async def add_quiz_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddQuiz.waiting_for_lesson)
    lessons = get_all_lessons()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=l['title'], callback_data=f"ql_{l['id']}")]
        for l in lessons[:20]
    ] + [[InlineKeyboardButton(text="Back", callback_data="admin_quizzes")]])
    await cb.message.edit_text("Pick lesson:", reply_markup=kb); await cb.answer()

@router.callback_query(F.data.startswith("ql_"))
async def add_quiz_lesson(cb: types.CallbackQuery, state: FSMContext):
    lid = int(cb.data.split("_")[1])
    qid = add_lesson_quiz(lid)
    await state.update_data(quiz_id=qid)
    await state.set_state(AddQuiz.waiting_for_questions)
    await cb.message.edit_text("Quiz created. Send questions. /done to finish"); await cb.answer()

@router.message(AddQuiz.waiting_for_questions)
async def add_quiz_q(msg: types.Message, state: FSMContext):
    if msg.text == "/done":
        await state.clear(); await msg.answer("Done"); return
    d = await state.get_data(); qid = d['quiz_id']
    for line in msg.text.split("\\n"):
        if not line.strip(): continue
        if line.upper().startswith("SPELL|"):
            p = [x.strip() for x in line.split("|")]
            add_quiz_question(qid, p[1], "spelling", options="", correct_answer=p[1], level=p[2] if len(p)>2 else "A1")
        else:
            p = [x.strip() for x in line.split("|")]
            add_quiz_question(qid, p[0], "mcq", options=json.dumps(p[1:5]), correct_answer=p[5])
    await msg.answer("Added")

# Payments
@router.callback_query(F.data == "admin_payments")
async def admin_payments(cb: types.CallbackQuery):
    pending = get_pending_payments()
    if not pending:
        await cb.message.edit_text("No pending", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back", callback_data="admin_back")]
        ])); await cb.answer(); return
    text = "Pending:\\n" + "\\n".join([f"#{p['id']} uid:{p['user_id']}" for p in pending[:10]])
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Back", callback_data="admin_back")]
    ])); await cb.answer()

# Import
@router.callback_query(F.data == "admin_import")
async def admin_import(cb: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="JSON", callback_data="imp_json")],
        [InlineKeyboardButton(text="CSV", callback_data="imp_csv")],
        [InlineKeyboardButton(text="TXT", callback_data="imp_txt")],
        [InlineKeyboardButton(text="Back", callback_data="admin_back")],
    ])
    await cb.message.edit_text("Import", reply_markup=kb); await cb.answer()

@router.callback_query(F.data.startswith("imp_"))
async def import_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(ImportData.waiting_for_file)
    await state.update_data(import_type=cb.data.split("_")[1])
    await cb.message.edit_text("Send file"); await cb.answer()

@router.message(ImportData.waiting_for_file, F.document)
async def import_file(msg: types.Message, state: FSMContext):
    d = await state.get_data(); itype = d.get("import_type")
    file = await msg.bot.get_file(msg.document.file_id)
    data = await msg.bot.download_file(file.file_path)
    content = data.read().decode('utf-8')
    count = 0
    if itype == "json":
        for item in json.loads(content):
            add_spelling_word(item.get("word",""), item.get("def",""), item.get("level","A1")); count += 1
    elif itype == "csv":
        import csv, io
        for row in csv.reader(io.StringIO(content)):
            if row and row[0].strip():
                add_spelling_word(row[0].strip(), row[1].strip() if len(row)>1 else "", row[2].strip() if len(row)>2 else "A1")
                count += 1
    elif itype == "txt":
        for line in content.strip().split("\\n"):
            if line.strip():
                add_spelling_word(line.strip(), "", "A1")
                count += 1
    await state.clear(); await msg.answer(f"Imported {count} items")

# Group Link
@router.callback_query(F.data == "admin_group")
async def admin_group(cb: types.CallbackQuery):
    row = _safe_exec("SELECT value FROM group_settings WHERE key='discussion_group'").fetchone()
    link = row[0] if row else "https://t.me/+2NkF901AApcyODk0"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Change", callback_data="chg_group")],
        [InlineKeyboardButton(text="Back", callback_data="admin_back")],
    ])
    await cb.message.edit_text(f"Group: {link}", reply_markup=kb); await cb.answer()

@router.callback_query(F.data == "chg_group")
async def chg_group_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(GroupLink.waiting_for_link)
    await cb.message.edit_text("New link:"); await cb.answer()

@router.message(GroupLink.waiting_for_link)
async def chg_group_save(msg: types.Message, state: FSMContext):
    _safe_exec("INSERT OR REPLACE INTO group_settings(key,value) VALUES('discussion_group',?)", (msg.text.strip(),))
    await state.clear(); await msg.answer("Updated")

@router.callback_query(F.data == "list_lessons")
async def list_lessons(cb: types.CallbackQuery):
    lessons = get_all_lessons()
    text = "Lessons:\\n" + "\\n".join([f"#{l['id']} {l['title']} ({l.get('media_type','none')})" for l in lessons[:30]])
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Back", callback_data="admin_content")]
    ])); await cb.answer()
"""

admin_path = os.path.join(BASE, "handlers", "admin.py")
with open(admin_path, "w", encoding="utf-8") as f:
    f.write(admin_code)
print("admin.py FIXED - extract_file_id handles forwarded messages + all types")
print("\\nRestart bot: python main.py")
