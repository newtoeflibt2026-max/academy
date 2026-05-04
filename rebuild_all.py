"""
Yamen Academy – Full Rebuild
Rebuilds: api_server.py, handlers/writing.py, handlers/speaking.py
"""

import os

BASE = r"C:\yamen_academy"
HANDLERS = os.path.join(BASE, "handlers")
os.makedirs(HANDLERS, exist_ok=True)

API_KEYS = {
    "writing": [
        "AIzaSyDkAuMCa9rBQGiFkqxIauUCL7eXQyP2aHw",
        "AIzaSyDGRbeskDR64jlDFkC5UzSdfleMp_sUwKc",
        "AIzaSyDFU5MAO20Hssq6SWS-F0TGGint3IZHcTU",
    ],
    "speaking": [
        "AIzaSyCBFNExYp5-9yFjHFrnaqUS-yZn_YqigSY",
        "AIzaSyAXGja3hvzIo2SyTTQcuKBNa-yHZghHu8M",
        "AIzaSyBWj39r49ORhKEpoDLhk6bpPiJLGrmohW0",
    ],
    "default": "AIzaSyBfu0gQwsBOqh6dzTVBaOcFByEzjJ9unxM",
}

MODEL = "gemini-2.5-flash"

# =====================================================
# 1. api_server.py
# =====================================================
API_SERVER = '''"""
Yamen Academy – Flask API Server
"""
import os, json, sqlite3, asyncio, aiohttp, base64, random
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="webapp", static_url_path="")
CORS(app)

DB = "data/academy.db"
os.makedirs("data", exist_ok=True)

WRITING_KEYS = %(writing_keys)s
SPEAKING_KEYS = %(speaking_keys)s
MODEL = "%(model)s"

# ── DB Helpers ──
def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def query(sql, params=()):
    return get_conn().execute(sql, params).fetchall()

def execute(sql, params=()):
    conn = get_conn()
    conn.execute(sql, params)
    conn.commit()
    conn.close()

def dict_rows(rows):
    return [dict(r) for r in rows]

# ── Health ──
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

# ── Student ──
@app.route("/api/me")
def me():
    uid = request.args.get("user_id")
    if not uid: return jsonify({"error": "user_id required"}), 400
    row = query("SELECT * FROM students WHERE user_id=?", (uid,))
    return jsonify(dict(row[0]) if row else {"error": "not found"})

# ── Courses ──
@app.route("/api/courses")
def courses():
    uid = request.args.get("user_id")
    level = request.args.get("level", "")
    if level:
        rows = query("SELECT * FROM courses WHERE level=? ORDER BY id", (level,))
    else:
        rows = query("SELECT * FROM courses ORDER BY id")
    return jsonify(dict_rows(rows))

# ── Lessons ──
@app.route("/api/lessons")
def lessons():
    cid = request.args.get("course_id")
    rows = query("SELECT * FROM lessons WHERE course_id=? ORDER BY id", (cid,))
    return jsonify(dict_rows(rows))

# ── AI Writing ──
@app.route("/api/writing/evaluate", methods=["POST"])
def evaluate_writing():
    data = request.get_json(force=True)
    essay = data.get("essay", "")
    task_type = data.get("task_type", "task2")
    prompt = data.get("prompt", "")
    user_id = data.get("user_id")

    if len(essay.split()) < 150:
        return jsonify({"error": "Essay too short"}), 400

    key = random.choice(WRITING_KEYS)
    system = """You are an IELTS examiner. Score this essay on:
Task Achievement, Coherence & Cohesion, Lexical Resource, Grammatical Range & Accuracy.
Reply ONLY in JSON: {"overall":6.5,"task_response":6,"coherence_cohesion":7,"lexical_resource":6.5,"grammatical_range":6.5,"feedback_ar":"detailed Arabic feedback","corrections":[]}"""

    url = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent?key=" + key
    body = {"contents":[{"parts":[{"text":system},{"text":"Task: "+task_type+"\\nPrompt: "+prompt+"\\nESSAY:\\n\\n"+essay}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":2048}}

    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = json.loads(resp.read())["candidates"][0]["content"]["parts"][0]["text"]
            raw = raw.strip().lstrip("```json").rstrip("```").strip()
            result = json.loads(raw)
            result.setdefault("overall", 6.0)
            result.setdefault("feedback_ar", "تم التقييم.")
            if user_id:
                execute("""INSERT INTO writing_submissions
                    (user_id,task_type,prompt,essay_text,word_count,band_score,task_response,coherence_cohesion,lexical_resource,grammatical_range,feedback_ar,corrections_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (int(user_id), task_type, prompt, essay, len(essay.split()),
                     result["overall"], result.get("task_response",6), result.get("coherence_cohesion",6),
                     result.get("lexical_resource",6), result.get("grammatical_range",6),
                     result["feedback_ar"], json.dumps(result.get("corrections",[]))))
            return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── AI Speaking ──
@app.route("/api/speaking/evaluate", methods=["POST"])
def evaluate_speaking():
    data = request.get_json(force=True)
    audio_b64 = data.get("audio_base64", "")
    prompt = data.get("prompt", "")
    part = data.get("part", "part1")
    duration = data.get("duration", 30)
    user_id = data.get("user_id")

    key = random.choice(SPEAKING_KEYS)
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent?key=" + key
    body = {"contents":[{"parts":[{"text":"IELTS Speaking "+part+". Prompt: "+prompt+". Duration: "+str(duration)+"s. Score on Fluency, Pronunciation, Lexical Resource, Grammar. Reply JSON: {\\"overall\\":6.5,\\"fluency\\":6,\\"pronunciation\\":7,\\"lexical_resource\\":6.5,\\"grammatical_range\\":6,\\"feedback_ar\\":\\"...\\",\\"transcript\\":\\"...\\"}"},{"inline_data":{"mime_type":"audio/ogg","data":audio_b64}}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":2048}}

    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = json.loads(resp.read())["candidates"][0]["content"]["parts"][0]["text"]
            raw = raw.strip().lstrip("```json").rstrip("```").strip()
            result = json.loads(raw)
            result.setdefault("overall", 6.0)
            result.setdefault("feedback_ar", "تم التقييم.")
            if user_id:
                execute("""INSERT INTO speaking_sessions
                    (user_id,prompt,transcript_text,audio_duration_sec,band_score,fluency,pronunciation,lexical_resource,grammatical_range,feedback_ar)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (int(user_id), prompt, result.get("transcript",""), duration,
                     result["overall"], result.get("fluency",6), result.get("pronunciation",6),
                     result.get("lexical_resource",6), result.get("grammatical_range",6),
                     result["feedback_ar"]))
            return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Admin ──
@app.route("/api/admin/stats")
def admin_stats():
    students = query("SELECT COUNT(*) as n FROM students")[0]["n"]
    active = query("SELECT COUNT(*) as n FROM subscriptions WHERE active=1")[0]["n"]
    pending = query("SELECT COUNT(*) as n FROM payments WHERE status='pending'")[0]["n"]
    return jsonify({"students": students, "active_subs": active, "pending_payments": pending})

@app.route("/api/admin/payments")
def admin_payments():
    rows = query("SELECT * FROM payments ORDER BY created_at DESC LIMIT 50")
    return jsonify(dict_rows(rows))

@app.route("/api/admin/approve", methods=["POST"])
def admin_approve():
    data = request.get_json(force=True)
    pid = data["payment_id"]
    execute("UPDATE payments SET status='approved' WHERE id=?", (pid,))
    p = query("SELECT * FROM payments WHERE id=?", (pid,))
    if p:
        p = dict(p[0])
        execute("INSERT INTO subscriptions (user_id,plan_name,course_id,start_date,end_date,active) VALUES (?,?,?,date('now'),date('now','+30 days'),1)",
                (p["user_id"], p.get("plan_name","default"), p.get("course_id",1)))
    return jsonify({"ok": True})

@app.route("/api/admin/reject", methods=["POST"])
def admin_reject():
    data = request.get_json(force=True)
    execute("UPDATE payments SET status='rejected' WHERE id=?", (data["payment_id"],))
    return jsonify({"ok": True})

# ── Static ──
@app.route("/")
def index():
    return send_from_directory("webapp", "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory("webapp", filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
''' % {"writing_keys": repr(API_KEYS["writing"]), "speaking_keys": repr(API_KEYS["speaking"]), "model": MODEL}

# =====================================================
# 2. handlers/writing.py
# =====================================================
WRITING = '''"""
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

KEYS = %(keys)s
MODEL = "%(model)s"

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
    await msg.answer("✍️ *IELTS Writing Engine*\\nChoose task type:", reply_markup=menu(), parse_mode="Markdown")

@router.callback_query(F.data=="w2")
async def t2(cb: CallbackQuery, state: FSMContext):
    p = random.choice(TASK2)
    await state.update_data(task="task2", prompt=p)
    await state.set_state(WF.waiting)
    await cb.message.edit_text("📝 *Task 2*\\n\\n"+p+"\\n\\nWrite 250+ words. Send as one message.", parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data=="w1")
async def t1(cb: CallbackQuery, state: FSMContext):
    p = random.choice(TASK1)
    await state.update_data(task="task1", prompt=p)
    await state.set_state(WF.waiting)
    await cb.message.edit_text("📊 *Task 1*\\n\\n"+p+"\\n\\nWrite 150+ words.", parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data=="wh")
async def hist(cb: CallbackQuery):
    rows = _safe_exec("SELECT * FROM writing_submissions WHERE user_id=? ORDER BY submitted_at DESC LIMIT 5", (cb.from_user.id,)).fetchall()
    if not rows:
        await cb.message.edit_text("No history yet.", reply_markup=menu())
    else:
        lines = ["📈 *Your Writing History:*\\n"]
        for r in rows:
            r = dict(r)
            lines.append("Band *"+str(r.get("band_score","?"))+"* | "+str(r.get("submitted_at","")[:10]))
        await cb.message.edit_text("\\n".join(lines), parse_mode="Markdown", reply_markup=menu())
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
                json={"contents":[{"parts":[{"text":system},{"text":"Task: "+task_type+"\\nPrompt: "+prompt+"\\nESSAY:\\n\\n"+essay}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":2048}}
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
        out = f"{emoji} *Band: {res['overall']}*\\n\\n"
        out += f"TA: *{res.get('task_response','?')}* | CC: *{res.get('coherence_cohesion','?')}*\\n"
        out += f"LR: *{res.get('lexical_resource','?')}* | GRA: *{res.get('grammatical_range','?')}*\\n\\n"
        out += f"📝 {res['feedback_ar']}\\n\\nWords: {wc}"
        await status.edit_text(out, parse_mode="Markdown")
    except Exception as e:
        await status.edit_text(f"❌ Error: {e}")
    finally:
        await state.clear()

print("✅ writing.py ready")
''' % {"keys": repr(API_KEYS["writing"]), "model": MODEL}

# =====================================================
# 3. handlers/speaking.py
# =====================================================
SPEAKING = '''"""
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

KEYS = %(keys)s
MODEL = "%(model)s"

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
    await msg.answer("🎙️ *IELTS Speaking Coach*\\nChoose:", reply_markup=menu(), parse_mode="Markdown")

@router.callback_query(F.data=="s1")
async def p1(cb: CallbackQuery, state: FSMContext):
    q = random.choice(PART1)
    await state.update_data(part="part1", prompt=q)
    await state.set_state(SF.waiting)
    await cb.message.edit_text("🗣 *Part 1*\\n\\n"+q+"\\n\\n🎙️ Record 30-60s voice note and send.", parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data=="s2")
async def p2(cb: CallbackQuery, state: FSMContext):
    q = random.choice(PART2)
    await state.update_data(part="part2", prompt=q)
    await state.set_state(SF.waiting)
    await cb.message.edit_text("🎤 *Part 2*\\n\\n"+q+"\\n\\n🎙️ Speak 1-2 min. Send voice note.", parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data=="sh")
async def hist(cb: CallbackQuery):
    rows = _safe_exec("SELECT * FROM speaking_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT 5", (cb.from_user.id,)).fetchall()
    if not rows:
        await cb.message.edit_text("No history.", reply_markup=menu())
    else:
        out = ["📊 *Speaking History:*\\n"]
        for r in rows:
            r = dict(r)
            out.append("Band *"+str(r.get("band_score","?"))+"* | "+str(r.get("created_at","")[:10]))
        await cb.message.edit_text("\\n".join(out), parse_mode="Markdown", reply_markup=menu())
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
    system = "IELTS Speaking "+part+". Prompt: "+prompt+". Duration: "+str(dur)+"s. Score Fluency, Pronunciation, Lexical Resource, Grammar. Reply ONLY JSON: {\\"overall\\":6.5,\\"fluency\\":6,\\"pronunciation\\":7,\\"lexical_resource\\":6.5,\\"grammatical_range\\":6,\\"feedback_ar\\":\\"...\\",\\"transcript\\":\\"...\\"}"

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
        out = f"{emoji} *Band: {res['overall']}*\\n\\n"
        out += f"FC: *{res.get('fluency','?')}* | P: *{res.get('pronunciation','?')}*\\n"
        out += f"LR: *{res.get('lexical_resource','?')}* | GRA: *{res.get('grammatical_range','?')}*\\n\\n"
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
''' % {"keys": repr(API_KEYS["speaking"]), "model": MODEL}

# =====================================================
# WRITE ALL FILES
# =====================================================
files = {
    "api_server.py": API_SERVER,
    "handlers/writing.py": WRITING,
    "handlers/speaking.py": SPEAKING,
}

for rel, content in files.items():
    path = os.path.join(BASE, rel)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ {rel} — {len(content)} bytes")

# =====================================================
# ENSURE DB TABLES
# =====================================================
import sqlite3
conn = sqlite3.connect(os.path.join(BASE, "data/academy.db"))
conn.execute("""
    CREATE TABLE IF NOT EXISTS writing_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, task_type TEXT, prompt TEXT, essay_text TEXT,
        word_count INTEGER, band_score REAL, task_response REAL,
        coherence_cohesion REAL, lexical_resource REAL,
        grammatical_range REAL, feedback_ar TEXT, corrections_json TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.execute("""
    CREATE TABLE IF NOT EXISTS speaking_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, prompt TEXT, transcript_text TEXT,
        audio_duration_sec REAL, band_score REAL, fluency REAL,
        pronunciation REAL, lexical_resource REAL,
        grammatical_range REAL, feedback_ar TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()
conn.close()
print("✅ DB tables ensured")

# =====================================================
# REGISTER ROUTERS IN __init__.py
# =====================================================
init = os.path.join(HANDLERS, "__init__.py")
with open(init, "r", encoding="utf-8") as f:
    content = f.read()

for mod, var in [("writing", "r_write"), ("speaking", "r_speak")]:
    line = f"from .{mod} import router as {var}; dp.include_router({var})"
    if line not in content:
        content = content.rstrip() + "\n" + line + "\n"

with open(init, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ __init__.py routers registered")

# =====================================================
# DONE
# =====================================================
print("\n" + "="*50)
print("✅ REBUILD COMPLETE")
print("="*50)
print("\nRun:")
print("  cd C:\\yamen_academy")
print("  python main.py")
