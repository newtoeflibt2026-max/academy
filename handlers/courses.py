from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    get_student, has_active_subscription, get_courses_by_level,
    get_lessons_by_course, get_lesson, get_quiz_by_lesson_id,
    get_quiz_questions, add_quiz_attempt, _safe_exec, dict_rows
)
import json

router = Router()

@router.callback_query(F.data == "my_courses")
async def my_courses(cb: types.CallbackQuery):
    student = get_student(cb.from_user.id)
    if not student:
        await cb.message.edit_text("Register first /start"); await cb.answer(); return
    if not has_active_subscription(cb.from_user.id):
        await cb.message.edit_text("Need active subscription"); await cb.answer(); return
    courses = get_courses_by_level(student.get('level', 'A1'))
    if not courses:
        await cb.message.edit_text("No courses yet"); await cb.answer(); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{c['name']} ({c['level']})", callback_data=f"course_{c['id']}")]
        for c in courses
    ] + [[InlineKeyboardButton(text="Back", callback_data="student_menu")]])
    await cb.message.edit_text("My Courses:", reply_markup=kb); await cb.answer()

@router.callback_query(F.data.startswith("course_"))
async def course_lessons(cb: types.CallbackQuery):
    cid = int(cb.data.split("_")[1])
    lessons = get_lessons_by_course(cid)
    if not lessons:
        await cb.message.edit_text("No lessons"); await cb.answer(); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{l['title']}", callback_data=f"lesson_{l['id']}")]
        for l in lessons
    ] + [[InlineKeyboardButton(text="Back", callback_data="my_courses")]])
    await cb.message.edit_text("Lessons:", reply_markup=kb); await cb.answer()

@router.callback_query(F.data.startswith("lesson_"))
async def view_lesson(cb: types.CallbackQuery):
    lid = int(cb.data.split("_")[1])
    lesson = get_lesson(lid)
    if not lesson:
        await cb.answer("Not found", show_alert=True); return
    
    text = f"{lesson['title']}\n\n{lesson.get('content','')}"
    mt = lesson.get('media_type')
    mfid = lesson.get('media_file_id')
    
    buttons = []
    quiz = get_quiz_by_lesson_id(lid)
    if quiz:
        buttons.append([InlineKeyboardButton(text="Take Quiz", callback_data=f"take_quiz_{quiz['id']}")])
    if lesson.get('action_type') and lesson.get('action_label'):
        buttons.append([InlineKeyboardButton(text=lesson['action_label'], callback_data=f"action_{lesson['action_type']}_{lid}")])
    
    row = _safe_exec("SELECT value FROM group_settings WHERE key='discussion_group'").fetchone()
    glink = row[0] if row else "https://t.me/+2NkF901AApcyODk0"
    buttons.append([InlineKeyboardButton(text="Discuss in Group", url=glink)])
    buttons.append([InlineKeyboardButton(text="Back", callback_data="my_courses")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        if mt and mfid:
            if mt in ('audio', 'voice'):
                await cb.message.answer_audio(mfid, caption=text, reply_markup=kb)
            elif mt == 'video':
                await cb.message.answer_video(mfid, caption=text, reply_markup=kb)
            elif mt == 'video_note':
                await cb.message.answer_video_note(mfid)
                await cb.message.answer(text, reply_markup=kb)
            elif mt == 'document':
                await cb.message.answer_document(mfid, caption=text, reply_markup=kb)
            elif mt == 'photo':
                await cb.message.answer_photo(mfid, caption=text, reply_markup=kb)
            else:
                await cb.message.edit_text(text, reply_markup=kb)
            await cb.message.delete()
        else:
            await cb.message.edit_text(text, reply_markup=kb)
    except Exception as e:
        await cb.message.edit_text(f"{text}\n\n[Media unavailable: {e}]", reply_markup=kb)
    
    await cb.answer()

@router.callback_query(F.data.startswith("take_quiz_"))
async def take_quiz(cb: types.CallbackQuery):
    qid = int(cb.data.split("_")[2])
    questions = get_quiz_questions(qid)
    if not questions:
        await cb.message.edit_text("No questions", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Back", callback_data="my_courses")]]
        )); await cb.answer(); return
    await show_q(cb.message, questions, 0, qid, 0)
    await cb.answer()

async def show_q(msg, questions, idx, quiz_id, score):
    if idx >= len(questions):
        await msg.edit_text(f"Quiz done! Score: {score}/{len(questions)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Back", callback_data="my_courses")]
            ]))
        return
    q = questions[idx]
    if q.get('question_type') == 'mcq':
        opts = json.loads(q.get('options','[]'))
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=f"qzans_{quiz_id}_{idx}_{score}_{i}_{q['correct_answer']}")]
            for i, opt in enumerate(opts)
        ])
        await msg.edit_text(f"Q{idx+1}/{len(questions)}: {q['question_text']}", reply_markup=kb)
    else:
        await msg.edit_text(f"Q{idx+1}: Spell: {q['question_text']}")

@router.callback_query(F.data.startswith("qzans_"))
async def quiz_answer(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    quiz_id = int(parts[1]); q_idx = int(parts[2]); score = int(parts[3]); chosen = int(parts[4]); correct = parts[5]
    questions = get_quiz_questions(quiz_id)
    opts = json.loads(questions[q_idx].get('options','[]'))
    if opts[chosen] == correct:
        score += 1; await cb.answer("Correct!")
    else:
        await cb.answer(f"Wrong! Answer: {correct}")
    await show_q(cb.message, questions, q_idx+1, quiz_id, score)

@router.callback_query(F.data.startswith("action_"))
async def handle_action(cb: types.CallbackQuery):
    at = cb.data.split("_")[1]
    if at == 'speaking': await cb.message.edit_text("Send voice note...")
    elif at == 'writing': await cb.message.edit_text("Send text to correct...")
    await cb.answer()
