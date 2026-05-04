"""
AI Speaking Coach – IELTS Voice Analysis (Gemini)
"""

import json, asyncio, random, base64
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
from database import _safe_exec

router = Router()

KEYS = ['AIzaSyCBFNExYp5-9yFjHFrnaqUS-yZn_YqigSY', 'AIzaSyAXGja3hvzIo2SyTTQcuKBNa-yHZghHu8M', 'AIzaSyBWj39r49ORhKEpoDLhk6bpPiJLGrmohW0']
MODEL = "gemini-2.5-flash"

PART1 = [
    "Tell me about your hometown.",
    "Do you work or study? Describe your routine.",
    "What music do you like? Why?",
]

PART2 = [
    "Describe a memorable trip. Where, how, what, why memorable.",
    "Describe a useful skill you learned. What, how, why, how it helped.",
]

class SF(StatesGroup):
    waiting = State()

def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗣 Part 1 — Questions", callback_data="s1")],
        [InlineKeyboardButton(text="🎤 Part 2 — Cue Card", callback_data="s2")],
        [InlineKeyboardButton(text="📊 History", callback_data="sh")],
    ])

@router.message(F.text.in_(["🎙️ Speaking","🎙️ تحدث","🎙️ Speaking Coach"]))
async def start(msg: Message, state: FSMContext):
    await msg.answer("🎙️ *IELTS Speaking Coach*\nChoose:", reply_markup=menu(), parse_mode="Markdown")

@router.callback_query(F.data=="s1")
async def p1(cb: CallbackQuery, state: FSMContext):
    q = random.choice(PART1)
    await state.update_data(part="part1", prompt=q)
    await state.set_state(SF.waiting)
    await cb.message.edit_text("🗣 *Part 1*\n\n"+q+"\n\n🎙️ Record 30-60s voice note and send.", parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data=="s2")
async def p2(cb: CallbackQuery, state: FSMContext):
    q = random.choice(PART2)
    await state.update_data(part="part2", prompt=q)
    await state.set_state(SF.waiting)
    await cb.message.edit_text("🎤 *Part 2*\n\n"+q+"\n\n🎙️ Speak 1-2 min. Send voice note.", parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data=="sh")
async def hist(cb: CallbackQuery):
    rows = _safe_exec("SELECT * FROM speaking_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT 5", (cb.from_user.id,)).fetchall()
    if not rows:
        await cb.message.edit_text("No history.", reply_markup=menu())
    else:
        out = ["📊 *Speaking History:*\n"]
        for r in rows:
            r = dict(r)
            out.append("Band *"+str(r.get("band_score","?"))+"* | "+str(r.get("created_at","")[:10]))
        await cb.message.edit_text("\n".join(out), parse_mode="Markdown", reply_markup=menu())
    await cb.answer()

@router.message(SF.waiting, F.voice)
async def evaluate(msg: Message, state: FSMContext):
    voice = msg.voice
    dur = voice.duration
    data = await state.get_data()
    prompt = data.get("prompt","")
    part = data.get("part","part1")

    status = await msg.answer("🎧 Analyzing your speech...")

    # Download voice
    f = await msg.bot.get_file(voice.file_id)
    b = await msg.bot.download_file(f.file_path)
    audio_b64 = base64.b64encode(b.read()).decode()

    key = random.choice(KEYS)
    system = "IELTS Speaking "+part+". Prompt: "+prompt+". Duration: "+str(dur)+"s. Score Fluency, Pronunciation, Lexical Resource, Grammar. Reply ONLY JSON: {\"overall\":6.5,\"fluency\":6,\"pronunciation\":7,\"lexical_resource\":6.5,\"grammatical_range\":6,\"feedback_ar\":\"...\",\"transcript\":\"...\"}"

    try:
        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"+MODEL+":generateContent?key="+key,
                json={"contents":[{"parts":[{"text":system},{"inline_data":{"mime_type":"audio/ogg","data":audio_b64}}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":2048}}
            ) as r:
                raw = (await r.json())["candidates"][0]["content"]["parts"][0]["text"]
                raw = raw.strip().lstrip("```json").rstrip("```").strip()
                res = json.loads(raw)
                res.setdefault("overall",6.0)
                res.setdefault("feedback_ar","Done.")
                res.setdefault("transcript","")

        _safe_exec("""INSERT INTO speaking_sessions
            (user_id,prompt,transcript_text,audio_duration_sec,band_score,fluency,pronunciation,lexical_resource,grammatical_range,feedback_ar)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (msg.from_user.id, prompt, res["transcript"], dur,
             res["overall"], res.get("fluency",6), res.get("pronunciation",6),
             res.get("lexical_resource",6), res.get("grammatical_range",6),
             res["feedback_ar"]))

        emoji = {9:"🏆",8:"🥇",7:"✅",6:"📘"}.get(res["overall"],"📕")
        out = f"{emoji} *Band: {res['overall']}*\n\n"
        out += f"FC: *{res.get('fluency','?')}* | P: *{res.get('pronunciation','?')}*\n"
        out += f"LR: *{res.get('lexical_resource','?')}* | GRA: *{res.get('grammatical_range','?')}*\n\n"
        out += f"📝 {res['feedback_ar']}"
        await status.edit_text(out, parse_mode="Markdown")
    except Exception as e:
        await status.edit_text(f"❌ Error: {e}")
    finally:
        await state.clear()

@router.message(SF.waiting)
async def no_voice(msg: Message):
    await msg.answer("🎙️ Send a *voice message*, not text.", parse_mode="Markdown")

print("✅ speaking.py ready")
