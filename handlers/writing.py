"""
AI Writing Engine – IELTS Essay Correction (Gemini)
"""

import json, asyncio, random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
from database import _safe_exec

router = Router()

KEYS = ['AIzaSyDkAuMCa9rBQGiFkqxIauUCL7eXQyP2aHw', 'AIzaSyDGRbeskDR64jlDFkC5UzSdfleMp_sUwKc', 'AIzaSyDFU5MAO20Hssq6SWS-F0TGGint3IZHcTU']
MODEL = "gemini-2.5-flash"

TASK2 = [
    "Some people believe that unpaid community service should be compulsory in schools. Agree/Disagree?",
    "Many countries face a 'throwaway society'. Causes and problems?",
    "Should governments spend more on railways than roads? Discuss.",
]

TASK1 = [
    "The graph shows average monthly temperatures in 3 cities. Summarize.",
    "The chart shows internet use by age group (2005-2020). Summarize.",
]

class WF(StatesGroup):
    waiting = State()

def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Task 2 — Essay", callback_data="w2")],
        [InlineKeyboardButton(text="📊 Task 1 — Graph", callback_data="w1")],
        [InlineKeyboardButton(text="📈 My History", callback_data="wh")],
    ])

@router.message(F.text.in_(["✍️ Writing","✍️ تقييم كتابة"]))
async def start(msg: Message, state: FSMContext):
    await msg.answer("✍️ *IELTS Writing Engine*\nChoose task type:", reply_markup=menu(), parse_mode="Markdown")

@router.callback_query(F.data=="w2")
async def t2(cb: CallbackQuery, state: FSMContext):
    p = random.choice(TASK2)
    await state.update_data(task="task2", prompt=p)
    await state.set_state(WF.waiting)
    await cb.message.edit_text("📝 *Task 2*\n\n"+p+"\n\nWrite 250+ words. Send as one message.", parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data=="w1")
async def t1(cb: CallbackQuery, state: FSMContext):
    p = random.choice(TASK1)
    await state.update_data(task="task1", prompt=p)
    await state.set_state(WF.waiting)
    await cb.message.edit_text("📊 *Task 1*\n\n"+p+"\n\nWrite 150+ words.", parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data=="wh")
async def hist(cb: CallbackQuery):
    rows = _safe_exec("SELECT * FROM writing_submissions WHERE user_id=? ORDER BY submitted_at DESC LIMIT 5", (cb.from_user.id,)).fetchall()
    if not rows:
        await cb.message.edit_text("No history yet.", reply_markup=menu())
    else:
        lines = ["📈 *Your Writing History:*\n"]
        for r in rows:
            r = dict(r)
            lines.append("Band *"+str(r.get("band_score","?"))+"* | "+str(r.get("submitted_at","")[:10]))
        await cb.message.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=menu())
    await cb.answer()

@router.message(WF.waiting)
async def evaluate(msg: Message, state: FSMContext):
    essay = msg.text.strip()
    data = await state.get_data()
    task_type = data.get("task","task2")
    prompt = data.get("prompt","")
    wc = len(essay.split())
    needed = 250 if task_type=="task2" else 150
    if wc < needed:
        await msg.answer(f"Too short ({wc} words, need {needed}). Expand and resend.")
        return

    status = await msg.answer("🔍 Analyzing...")
    key = random.choice(KEYS)
    system = """IELTS examiner. Score: Task Achievement, Coherence & Cohesion, Lexical Resource, Grammatical Range.
Reply ONLY JSON: {"overall":6.5,"task_response":6,"coherence_cohesion":7,"lexical_resource":6.5,"grammatical_range":6.5,"feedback_ar":"Arabic feedback"}"""

    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"+MODEL+":generateContent?key="+key,
                json={"contents":[{"parts":[{"text":system},{"text":"Task: "+task_type+"\nPrompt: "+prompt+"\nESSAY:\n\n"+essay}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":2048}}
            ) as r:
                raw = (await r.json())["candidates"][0]["content"]["parts"][0]["text"]
                raw = raw.strip().lstrip("```json").rstrip("```").strip()
                res = json.loads(raw)
                res.setdefault("overall",6.0)
                res.setdefault("feedback_ar","Done.")

        _safe_exec("""INSERT INTO writing_submissions
            (user_id,task_type,prompt,essay_text,word_count,band_score,task_response,coherence_cohesion,lexical_resource,grammatical_range,feedback_ar,corrections_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (msg.from_user.id, task_type, prompt, essay, wc,
             res["overall"], res.get("task_response",6), res.get("coherence_cohesion",6),
             res.get("lexical_resource",6), res.get("grammatical_range",6),
             res["feedback_ar"], "[]"))

        emoji = {9:"🏆",8:"🥇",7:"✅",6:"📘"}.get(res["overall"],"📕")
        out = f"{emoji} *Band: {res['overall']}*\n\n"
        out += f"TA: *{res.get('task_response','?')}* | CC: *{res.get('coherence_cohesion','?')}*\n"
        out += f"LR: *{res.get('lexical_resource','?')}* | GRA: *{res.get('grammatical_range','?')}*\n\n"
        out += f"📝 {res['feedback_ar']}\n\nWords: {wc}"
        await status.edit_text(out, parse_mode="Markdown")
    except Exception as e:
        await status.edit_text(f"❌ Error: {e}")
    finally:
        await state.clear()

print("✅ writing.py ready")
