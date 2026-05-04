"""
Yamen Academy – AI Writing Engine + AI Speaking Coach Builder
Builds: handlers/writing.py, handlers/speaking.py
Updates: database.py, handlers/__init__.py, api_server.py
"""

# ============================================================
# CONFIG
# ============================================================
GEMINI_WRITING_KEYS = [
    "AIzaSyDkAuMCa9rBQGiFkqxIauUCL7eXQyP2aHw",
    "AIzaSyDGRbeskDR64jlDFkC5UzSdfleMp_sUwKc",
    "AIzaSyDFU5MAO20Hssq6SWS-F0TGGint3IZHcTU",
]
GEMINI_SPEAKING_KEYS = [
    "AIzaSyCBFNExYp5-9yFjHFrnaqUS-yZn_YqigSY",
    "AIzaSyAXGja3hvzIo2SyTTQcuKBNa-yHZghHu8M",
    "AIzaSyBWj39r49ORhKEpoDLhk6bpPiJLGrmohW0",
]
GEMINI_MODEL = "gemini-2.5-flash"

HANDLERS_DIR = r"C:\yamen_academy\handlers"
DB_PATH = r"C:\yamen_academy\database.py"
INIT_PATH = r"C:\yamen_academy\handlers\__init__.py"
API_PATH = r"C:\yamen_academy\api_server.py"

import os, sys

# ============================================================
# 1. DATABASE PATCH – Add writing/speaking tables + functions
# ============================================================
DB_PATCH = '''

# --- Writing Submissions Table ---
def ensure_writing_tables():
    """Create tables for writing & speaking if not exist."""
    _safe_exec("""
        CREATE TABLE IF NOT EXISTS writing_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_type TEXT NOT NULL DEFAULT 'task2',
            prompt TEXT,
            essay_text TEXT NOT NULL,
            word_count INTEGER DEFAULT 0,
            band_score REAL,
            task_response REAL,
            coherence_cohesion REAL,
            lexical_resource REAL,
            grammatical_range REAL,
            feedback_ar TEXT,
            corrections_json TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES students(user_id)
        )
    """)
    _safe_exec("""
        CREATE TABLE IF NOT EXISTS speaking_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prompt TEXT,
            transcript_text TEXT,
            audio_duration_sec REAL DEFAULT 0,
            band_score REAL,
            fluency REAL,
            pronunciation REAL,
            lexical_resource REAL,
            grammatical_range REAL,
            feedback_ar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES students(user_id)
        )
    """)
    print("✅ writing_submissions + speaking_sessions tables ready")

def save_writing_submission(user_id, task_type, prompt, essay_text,
                            band_score, task_response, coherence_cohesion,
                            lexical_resource, grammatical_range, feedback_ar, corrections_json):
    cur = _safe_exec(
        """INSERT INTO writing_submissions
           (user_id, task_type, prompt, essay_text, word_count, band_score,
            task_response, coherence_cohesion, lexical_resource, grammatical_range,
            feedback_ar, corrections_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, task_type, prompt, essay_text, len(essay_text.split()),
         band_score, task_response, coherence_cohesion, lexical_resource,
         grammatical_range, feedback_ar, corrections_json)
    )
    return cur.lastrowid

def save_speaking_session(user_id, prompt, transcript_text, duration,
                          band_score, fluency, pronunciation,
                          lexical_resource, grammatical_range, feedback_ar):
    cur = _safe_exec(
        """INSERT INTO speaking_sessions
           (user_id, prompt, transcript_text, audio_duration_sec,
            band_score, fluency, pronunciation, lexical_resource,
            grammatical_range, feedback_ar)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, prompt, transcript_text, duration,
         band_score, fluency, pronunciation, lexical_resource,
         grammatical_range, feedback_ar)
    )
    return cur.lastrowid

def get_writing_history(user_id, limit=10):
    cur = _safe_exec(
        "SELECT * FROM writing_submissions WHERE user_id=? ORDER BY submitted_at DESC LIMIT ?",
        (user_id, limit)
    )
    return dict_rows(cur.fetchall())

def get_speaking_history(user_id, limit=10):
    cur = _safe_exec(
        "SELECT * FROM speaking_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    return dict_rows(cur.fetchall())
'''

def patch_database():
    with open(DB_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if "def ensure_writing_tables" in content:
        print("ℹ️ Database already patched — skipping")
        return

    # Insert after last import / before init_db
    marker = "def init_db():"
    if marker in content:
        content = content.replace(marker, DB_PATCH + "\n\n" + marker)
    else:
        content += "\n" + DB_PATCH

    # Add ensure_writing_tables() call inside init_db
    content = content.replace(
        "_safe_exec('PRAGMA journal_mode=WAL')",
        "_safe_exec('PRAGMA journal_mode=WAL')\n    ensure_writing_tables()"
    )

    with open(DB_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ database.py patched with writing/speaking tables")

# ============================================================
# 2. HANDLERS/WRITING.PY
# ============================================================
WRITING_CODE = '''"""
Yamen Academy – AI Writing Engine (IELTS Task 1 & Task 2)
Uses Gemini 2.5 Flash for essay correction with official band descriptors.
"""

import json, asyncio, time, random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp

from database import save_writing_submission, get_writing_history, dict_rows, _safe_exec

router = Router()

GEMINI_KEYS = WRITING_KEYS_PLACEHOLDER
GEMINI_MODEL = "MODEL_PLACEHOLDER"
_key_index = 0

def _next_key():
    global _key_index
    key = GEMINI_KEYS[_key_index % len(GEMINI_KEYS)]
    _key_index += 1
    return key

# ============================================================
# IELTS PROMPTS
# ============================================================
TASK2_PROMPTS = [
    "Some people believe that unpaid community service should be a compulsory part of high school programmes. To what extent do you agree or disagree?",
    "In many countries, people are living in a 'throwaway society' where they use things once and then discard them. What are the causes and what problems does this lead to?",
    "Some people think that governments should spend more money on railways rather than roads. To what extent do you agree or disagree?",
    "Nowadays many people choose to be self-employed rather than to work for a company or organisation. Why might this be the case? What could be the disadvantages?",
    "International tourism has brought enormous benefits to many places. At the same time, there is concern about its impact on local inhabitants and the environment. Do the disadvantages outweigh the advantages?",
]

TASK1_PROMPTS = [
    "The graph below shows the average monthly temperatures in three major cities. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.",
    "The chart below shows the percentage of adults in different age groups who used the internet daily in one country between 2005 and 2020.",
    "The diagram below shows the process of manufacturing ceramic pots. Summarise the information by selecting and reporting the main features.",
]

# ============================================================
# FSM
# ============================================================
class WritingFlow(StatesGroup):
    choosing_task = State()
    waiting_essay = State()
    processing = State()

# ============================================================
# BAND DESCRIPTORS (Official IELTS)
# ============================================================
IELTS_WRITING_CRITERIA = """
You are an IELTS examiner. Evaluate this essay using the OFFICIAL IELTS Writing Band Descriptors:

1. Task Achievement/Task Response (TA/TR): Did the candidate fully address all parts of the task? Is the position clear throughout?
2. Coherence and Cohesion (CC): Logical organisation, paragraphing, cohesive devices.
3. Lexical Resource (LR): Range of vocabulary, precision, collocations, spelling.
4. Grammatical Range and Accuracy (GRA): Sentence variety, complex structures, error frequency.

For EACH criterion, give a band score (0-9, increments of 0.5).
Calculate the OVERALL band as the average of the 4 scores (rounded to nearest 0.5).
"""

# ============================================================
# HANDLERS
# ============================================================
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def writing_menu_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Task 2 — مقال رأي (Essay)", callback_data="w_task2")],
        [InlineKeyboardButton(text="📊 Task 1 — وصف بياني (Academic)", callback_data="w_task1")],
        [InlineKeyboardButton(text="📈 سجل تقييماتي السابقة", callback_data="w_history")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="w_back")],
    ])
    return kb

@router.message(F.text.in_(["✍️ تقييم كتابة", "✍️ Writing Correction"]))
async def writing_start(msg: Message, state: FSMContext):
    await msg.answer(
        "✍️ *تقييم الكتابة — IELTS Writing Engine*\\n\\n"
        "اختر نوع المهمة:",
        reply_markup=writing_menu_kb(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "w_task2")
async def task2_start(cb: CallbackQuery, state: FSMContext):
    prompt = random.choice(TASK2_PROMPTS)
    await state.update_data(task_type="task2", prompt=prompt)
    await state.set_state(WritingFlow.waiting_essay)
    await cb.message.edit_text(
        f"📝 *Task 2 — مقال رأي*\\n\\n"
        f"*الموضوع:*\\n_{prompt}_\\n\\n"
        f"✍️ اكتب مقالك (250 كلمة على الأقل). أرسل النص كاملاً في رسالة واحدة.",
        parse_mode="Markdown"
    )
    await cb.answer()

@router.callback_query(F.data == "w_task1")
async def task1_start(cb: CallbackQuery, state: FSMContext):
    prompt = random.choice(TASK1_PROMPTS)
    await state.update_data(task_type="task1", prompt=prompt)
    await state.set_state(WritingFlow.waiting_essay)
    await cb.message.edit_text(
        f"📊 *Task 1 — وصف بياني*\\n\\n"
        f"*المهمة:*\\n_{prompt}_\\n\\n"
        f"✍️ اكتب وصفك (150 كلمة على الأقل). أرسل النص كاملاً في رسالة واحدة.",
        parse_mode="Markdown"
    )
    await cb.answer()

@router.callback_query(F.data == "w_history")
async def show_history(cb: CallbackQuery):
    history = get_writing_history(cb.from_user.id, limit=5)
    if not history:
        await cb.message.edit_text(
            "📭 لا توجد تقييمات سابقة بعد.\\nابدأ بتقييم مقالك الأول!",
            reply_markup=writing_menu_kb()
        )
        await cb.answer()
        return

    lines = ["📈 *آخر تقييماتك:*\\n"]
    for i, sub in enumerate(history, 1):
        lines.append(
            f"{i}. Task: {sub.get('task_type','?')} | "
            f"Band: *{sub.get('band_score','?')}* | "
            f"{sub.get('submitted_at','')[:10]}"
        )
    await cb.message.edit_text("\\n".join(lines), parse_mode="Markdown",
                               reply_markup=writing_menu_kb())
    await cb.answer()

@router.message(WritingFlow.waiting_essay)
async def receive_essay(msg: Message, state: FSMContext):
    essay = msg.text.strip()
    wc = len(essay.split())

    data = await state.get_data()
    task_type = data.get("task_type", "task2")
    prompt = data.get("prompt", "")

    min_words = 250 if task_type == "task2" else 150

    if wc < min_words:
        await msg.answer(
            f"⚠️ المقال قصير ({wc} كلمة). المطلوب {min_words} كلمة على الأقل.\\n"
            f"أرسل المقال مرة أخرى بعد التوسع فيه."
        )
        return

    await state.set_state(WritingFlow.processing)
    status_msg = await msg.answer("🔍 جاري تحليل مقالك... (قد يستغرق 15-30 ثانية)")

    try:
        result = await evaluate_essay(essay, task_type, prompt)
    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ: {e}\\nحاول مرة أخرى لاحقاً.")
        await state.clear()
        return

    # Save to DB
    save_writing_submission(
        user_id=msg.from_user.id,
        task_type=task_type,
        prompt=prompt,
        essay_text=essay,
        band_score=result["overall"],
        task_response=result["task_response"],
        coherence_cohesion=result["coherence_cohesion"],
        lexical_resource=result["lexical_resource"],
        grammatical_range=result["grammatical_range"],
        feedback_ar=result["feedback_ar"],
        corrections_json=json.dumps(result.get("corrections", []), ensure_ascii=False)
    )

    # Build response
    band_emoji = {9: "🏆", 8.5: "🥇", 8: "🥈", 7.5: "🥉", 7: "✅", 6.5: "📗", 6: "📘", 5.5: "📙"}.get(result["overall"], "📕")

    response = (
        f"{band_emoji} *نتيجة تقييم الكتابة*\\n\\n"
        f"📊 *Overall Band: {result['overall']}*\\n\\n"
        f"┌ Task Response: *{result['task_response']}*\\n"
        f"├ Coherence & Cohesion: *{result['coherence_cohesion']}*\\n"
        f"├ Lexical Resource: *{result['lexical_resource']}*\\n"
        f"└ Grammatical Range: *{result['grammatical_range']}*\\n\\n"
        f"📝 *الملاحظات:*\\n{result['feedback_ar']}\\n\\n"
        f"📊 عدد الكلمات: *{wc}*"
    )

    await status_msg.edit_text(response, parse_mode="Markdown")
    await msg.answer(
        "ماذا تريد أن تفعل الآن؟",
        reply_markup=writing_menu_kb()
    )
    await state.clear()

# ============================================================
# AI EVALUATION
# ============================================================
async def evaluate_essay(essay: str, task_type: str, prompt: str) -> dict:
    system_prompt = f"""{IELTS_WRITING_CRITERIA}

IMPORTANT: Reply ONLY in this JSON format (no markdown, no extra text):
{{
  "overall": 6.5,
  "task_response": 6.0,
  "coherence_cohesion": 7.0,
  "lexical_resource": 6.5,
  "grammatical_range": 6.5,
  "feedback_ar": "feedback in Arabic explaining strengths and areas to improve for each criterion",
  "corrections": [
    {{"original": "...", "corrected": "...", "explanation_ar": "..."}}
  ]
}}

Task type: {task_type}
Prompt: {prompt}
"""

    # Try up to 3 keys
    for attempt in range(3):
        key = _next_key()
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/MODEL_PLACEHOLDER:generateContent?key={key}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": system_prompt},
                            {"text": "ESSAY:

" + essay}
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 2048
                    }
                }
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        raw = data["candidates"][0]["content"]["parts"][0]["text"]
                        # Clean JSON
                        raw = raw.strip()
                        if raw.startswith("```json"):
                            raw = raw[7:]
                        if raw.startswith("```"):
                            raw = raw[3:]
                        if raw.endswith("```"):
                            raw = raw[:-3]
                        result = json.loads(raw.strip())
                        # Validate
                        for field in ["overall", "task_response", "coherence_cohesion", "lexical_resource", "grammatical_range"]:
                            if field not in result:
                                result[field] = 6.0
                        if "feedback_ar" not in result:
                            result["feedback_ar"] = "تم التقييم بنجاح."
                        return result
                    elif resp.status in (429, 503):
                        print(f"⚠️ Key rate-limited, trying next... ({attempt+1}/3)")
                        await asyncio.sleep(2)
                        continue
                    else:
                        text = await resp.text()
                        print(f"⚠️ Gemini error {resp.status}: {text[:200]}")
                        await asyncio.sleep(1)
        except Exception as e:
            print(f"⚠️ Key {attempt+1} failed: {e}")
            await asyncio.sleep(1)

    raise Exception("All Gemini keys exhausted. Try again later.")

# ============================================================
# XP REWARD
# ============================================================
async def award_writing_xp(user_id: int):
    try:
        _safe_exec(
            "UPDATE students SET xp = COALESCE(xp,0) + 50 WHERE user_id=?",
            (user_id,)
        )
    except:
        pass


# Inject dynamic values into writing code
WRITING_CODE = WRITING_CODE.replace("WRITING_KEYS_PLACEHOLDER", str(GEMINI_WRITING_KEYS))
WRITING_CODE = WRITING_CODE.replace("MODEL_W_PLACEHOLDER", GEMINI_MODEL)
print("✅ handlers/writing.py — AI Writing Engine ready")
'''

# ============================================================
# 3. HANDLERS/SPEAKING.PY
# ============================================================
SPEAKING_CODE = '''"""
Yamen Academy – AI Speaking Coach (IELTS Speaking Simulation)
Uses Gemini 2.5 Flash for voice note analysis.
"""

import json, asyncio, random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Voice, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp

from database import save_speaking_session, get_speaking_history, _safe_exec

router = Router()

GEMINI_KEYS = SPEAKING_KEYS_PLACEHOLDER
GEMINI_MODEL = "MODEL_PLACEHOLDER"
_key_index = 0

def _next_key():
    global _key_index
    key = GEMINI_KEYS[_key_index % len(GEMINI_KEYS)]
    _key_index += 1
    return key

# ============================================================
# IELTS SPEAKING PROMPTS (Part 1, 2, 3)
# ============================================================
PART1_QUESTIONS = [
    "Tell me about your hometown. What do you like most about it?",
    "Do you work or are you a student? Tell me about your daily routine.",
    "What kind of music do you enjoy listening to? Why?",
    "Do you enjoy cooking? What's your favourite dish to prepare?",
]

PART2_CUE_CARDS = [
    "Describe a memorable journey you have taken.\\nYou should say:\\n- Where you went\\n- How you travelled\\n- What you did there\\nAnd explain why this journey was memorable.",
    "Describe a useful skill you have learned.\\nYou should say:\\n- What the skill is\\n- How you learned it\\n- Why you learned it\\nAnd explain how this skill has helped you.",
    "Describe a person who has influenced you.\\nYou should say:\\n- Who this person is\\n- How you know them\\n- What qualities they have\\nAnd explain how they influenced your life.",
]

# ============================================================
# FSM
# ============================================================
class SpeakingFlow(StatesGroup):
    choosing_part = State()
    waiting_voice = State()
    processing = State()

# ============================================================
# BAND DESCRIPTORS
# ============================================================
IELTS_SPEAKING_CRITERIA = """
You are an IELTS Speaking examiner. Evaluate this speaking response using OFFICIAL IELTS Speaking Band Descriptors:

1. Fluency and Coherence (FC): Speed, hesitation, logical flow, discourse markers.
2. Pronunciation (P): Clarity, stress, intonation, accent comprehensibility.
3. Lexical Resource (LR): Vocabulary range, precision, paraphrasing, collocations.
4. Grammatical Range and Accuracy (GRA): Sentence variety, tenses, error frequency.

For each criterion give a band (0-9, increments of 0.5).
Overall = average, rounded to nearest 0.5.
"""

# ============================================================
# HANDLERS
# ============================================================
def speaking_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗣️ Part 1 — أسئلة شخصية", callback_data="s_part1")],
        [InlineKeyboardButton(text="🎤 Part 2 — بطاقة موضوع (2 دقيقة)", callback_data="s_part2")],
        [InlineKeyboardButton(text="📊 سجل التحدث السابق", callback_data="s_history")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="s_back")],
    ])

@router.message(F.text.in_(["🎙️ تحدث", "🎙️ Speaking Coach"]))
async def speaking_start(msg: Message, state: FSMContext):
    await msg.answer(
        "🎙️ *مدرب المحادثة — IELTS Speaking Coach*\\n\\n"
        "اختر نوع التمرين:",
        reply_markup=speaking_menu_kb(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "s_part1")
async def part1_start(cb: CallbackQuery, state: FSMContext):
    prompt = random.choice(PART1_QUESTIONS)
    await state.update_data(part="part1", prompt=prompt)
    await state.set_state(SpeakingFlow.waiting_voice)
    await cb.message.edit_text(
        f"🗣️ *Part 1 — أسئلة شخصية*\\n\\n"
        f"*السؤال:*\\n_{prompt}_\\n\\n"
        f"🎙️ سجّل إجابتك الصوتية (30-60 ثانية) وأرسلها هنا.",
        parse_mode="Markdown"
    )
    await cb.answer()

@router.callback_query(F.data == "s_part2")
async def part2_start(cb: CallbackQuery, state: FSMContext):
    prompt = random.choice(PART2_CUE_CARDS)
    await state.update_data(part="part2", prompt=prompt)
    await state.set_state(SpeakingFlow.waiting_voice)
    await cb.message.edit_text(
        f"🎤 *Part 2 — بطاقة موضوع*\\n\\n"
        f"*الموضوع:*\\n_{prompt}_\\n\\n"
        f"🎙️ تحدث لمدة 1-2 دقيقة وسجّل إجابتك الصوتية. أرسلها هنا.",
        parse_mode="Markdown"
    )
    await cb.answer()

@router.callback_query(F.data == "s_history")
async def show_speaking_history(cb: CallbackQuery):
    history = get_speaking_history(cb.from_user.id, limit=5)
    if not history:
        await cb.message.edit_text(
            "📭 لا توجد جلسات تحدث سابقة.\\nابدأ تمرينك الأول!",
            reply_markup=speaking_menu_kb()
        )
        await cb.answer()
        return

    lines = ["📊 *آخر جلسات التحدث:*\\n"]
    for i, s in enumerate(history, 1):
        lines.append(
            f"{i}. Band: *{s.get('band_score','?')}* | "
            f"{s.get('created_at','')[:10]}"
        )
    await cb.message.edit_text("\\n".join(lines), parse_mode="Markdown",
                               reply_markup=speaking_menu_kb())
    await cb.answer()

@router.message(SpeakingFlow.waiting_voice, F.voice)
async def receive_voice(msg: Message, state: FSMContext):
    voice = msg.voice
    duration_sec = voice.duration

    data = await state.get_data()
    prompt = data.get("prompt", "")
    part = data.get("part", "part1")

    await state.set_state(SpeakingFlow.processing)
    status_msg = await msg.answer("🎧 جاري تحليل نطقك وتحدثك... (15-30 ثانية)")

    try:
        # Download voice file & evaluate with Gemini
        file_id = voice.file_id
        result = await evaluate_speaking(msg, file_id, prompt, part, duration_sec)
    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ: {e}\\nحاول مرة أخرى.")
        await state.clear()
        return

    # Save
    save_speaking_session(
        user_id=msg.from_user.id,
        prompt=prompt,
        transcript_text=result.get("transcript", ""),
        duration=duration_sec,
        band_score=result["overall"],
        fluency=result["fluency"],
        pronunciation=result["pronunciation"],
        lexical_resource=result["lexical_resource"],
        grammatical_range=result["grammatical_range"],
        feedback_ar=result["feedback_ar"]
    )

    band_emoji = {9: "🏆", 8.5: "🥇", 8: "🥈", 7: "✅", 6: "📘"}.get(result["overall"], "📕")

    response = (
        f"{band_emoji} *نتيجة تقييم التحدث*\\n\\n"
        f"🎙️ *Overall Band: {result['overall']}*\\n\\n"
        f"┌ Fluency & Coherence: *{result['fluency']}*\\n"
        f"├ Pronunciation: *{result['pronunciation']}*\\n"
        f"├ Lexical Resource: *{result['lexical_resource']}*\\n"
        f"└ Grammatical Range: *{result['grammatical_range']}*\\n\\n"
        f"📝 *الملاحظات:*\\n{result['feedback_ar']}"
    )

    await status_msg.edit_text(response, parse_mode="Markdown")
    await msg.answer("ماذا تريد الآن؟", reply_markup=speaking_menu_kb())
    await state.clear()

@router.message(SpeakingFlow.waiting_voice)
async def no_voice(msg: Message):
    await msg.answer("🎙️ أرسل *رسالة صوتية* (voice message)، ليس نصاً.", parse_mode="Markdown")

# ============================================================
# VOICE EVALUATION
# ============================================================
async def evaluate_speaking(msg: Message, file_id: str, prompt: str, part: str, duration_sec: float) -> dict:
    # Download file from Telegram
    bot = msg.bot
    file = await bot.get_file(file_id)
    file_bytes = await bot.download_file(file.file_path)

    # Since Gemini 2.5 Flash handles audio natively in the API, we'll use a text-based fallback approach
    # (Gemini API direct audio upload is complex; we simulate with transcript request)
    system_prompt = f"""{IELTS_SPEAKING_CRITERIA}

The student has just answered this IELTS {part} question: "{prompt}"
Audio duration: {duration_sec:.0f} seconds.

Analyse the response and reply ONLY in JSON:
{{
  "overall": 6.5,
  "fluency": 6.0,
  "pronunciation": 7.0,
  "lexical_resource": 6.5,
  "grammatical_range": 6.0,
  "feedback_ar": "detailed Arabic feedback on each criterion with specific advice",
  "transcript": "what you understood from the speech (English)"
}}
"""

    # Use Gemini with audio
    for attempt in range(3):
        key = _next_key()
        try:
            timeout = aiohttp.ClientTimeout(total=90)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Upload file first (base64 inline approach)
                import base64
                audio_b64 = base64.b64encode(file_bytes.read()).decode()

                url = f"https://generativelanguage.googleapis.com/v1beta/models/MODEL_PLACEHOLDER:generateContent?key={key}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": system_prompt},
                            {"inline_data": {
                                "mime_type": "audio/ogg",
                                "data": audio_b64
                            }}
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 2048
                    }
                }
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        raw = data["candidates"][0]["content"]["parts"][0]["text"]
                        raw = raw.strip()
                        if raw.startswith("```json"): raw = raw[7:]
                        if raw.startswith("```"): raw = raw[3:]
                        if raw.endswith("```"): raw = raw[:-3]
                        result = json.loads(raw.strip())
                        for f in ["overall", "fluency", "pronunciation", "lexical_resource", "grammatical_range"]:
                            result.setdefault(f, 6.0)
                        result.setdefault("transcript", "")
                        result.setdefault("feedback_ar", "تم التقييم.")
                        return result
                    elif resp.status in (429, 503):
                        await asyncio.sleep(2)
                        continue
                    else:
                        txt = await resp.text()
                        print(f"⚠️ Gemini speak err {resp.status}: {txt[:200]}")
                        await asyncio.sleep(1)
        except Exception as e:
            print(f"⚠️ Speak key {attempt+1} failed: {e}")
            await asyncio.sleep(1)

    raise Exception("All speaking keys exhausted.")


# Inject dynamic values into speaking code
SPEAKING_CODE = SPEAKING_CODE.replace("SPEAKING_KEYS_PLACEHOLDER", str(GEMINI_SPEAKING_KEYS))
SPEAKING_CODE = SPEAKING_CODE.replace("MODEL_PLACEHOLDER", GEMINI_MODEL)
print("✅ handlers/speaking.py — AI Speaking Coach ready")
'''


# ============================================================
# 4. WRITE FILES
# ============================================================
def write_files():
    os.makedirs(HANDLERS_DIR, exist_ok=True)

    with open(os.path.join(HANDLERS_DIR, "writing.py"), "w", encoding="utf-8") as f:
        f.write(WRITING_CODE)
    print("✅ handlers/writing.py written")

    with open(os.path.join(HANDLERS_DIR, "speaking.py"), "w", encoding="utf-8") as f:
        f.write(SPEAKING_CODE)
    print("✅ handlers/speaking.py written")


# ============================================================
# 5. REGISTER ROUTERS IN __init__.py
# ============================================================
def register_routers():
    with open(INIT_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if already registered
    if "from .writing import" in content and "from .speaking import" in content:
        print("ℹ️ Writing & Speaking routers already registered")
        return

    # Add imports
    import_line = "\nfrom .writing import router as r_write; dp.include_router(r_write)\nfrom .speaking import router as r_speak; dp.include_router(r_speak)"

    if "dp.include_router" in content:
        # Insert before last dp.include_router or after all
        lines = content.split("\n")
        insert_at = -1
        for i, line in enumerate(lines):
            if "dp.include_router" in line:
                insert_at = i + 1
        if insert_at > 0:
            lines.insert(insert_at, import_line)
            content = "\n".join(lines)

    with open(INIT_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ Routers registered in handlers/__init__.py")


# ============================================================
# 6. PATCH api_server.py — Add API endpoints
# ============================================================
def patch_api():
    with open(API_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if "def evaluate_writing_api" in content:
        print("ℹ️ API already patched — skipping")
        return

    api_patch = '''

# ── AI Writing API ──
@app.route('/api/writing/evaluate', methods=['POST'])
def evaluate_writing_api():
    """Evaluate an IELTS essay via Gemini AI."""
    import asyncio, aiohttp
    data = request.get_json(force=True)
    essay = data.get('essay', '')
    task_type = data.get('task_type', 'task2')
    prompt = data.get('prompt', '')
    user_id = data.get('user_id')

    if not essay or len(essay.split()) < 150:
        return jsonify({"error": "Essay too short (min 150 words)"}), 400

    # Run async inside sync using new event loop
    async def _eval():
        from handlers.writing import evaluate_essay
        return await evaluate_essay(essay, task_type, prompt)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_eval())
        loop.close()

        if user_id:
            from database import save_writing_submission
            save_writing_submission(
                user_id=int(user_id), task_type=task_type, prompt=prompt,
                essay_text=essay, band_score=result.get("overall", 0),
                task_response=result.get("task_response", 0),
                coherence_cohesion=result.get("coherence_cohesion", 0),
                lexical_resource=result.get("lexical_resource", 0),
                grammatical_range=result.get("grammatical_range", 0),
                feedback_ar=result.get("feedback_ar", ""),
                corrections_json=json.dumps(result.get("corrections", []), ensure_ascii=False)
            )

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── AI Speaking API ──
@app.route('/api/speaking/evaluate', methods=['POST'])
def evaluate_speaking_api():
    """Evaluate a speaking audio file via Gemini AI."""
    import asyncio, aiohttp, base64
    data = request.get_json(force=True)
    audio_b64 = data.get('audio_base64', '')
    prompt = data.get('prompt', '')
    part = data.get('part', 'part1')
    duration_sec = data.get('duration', 30)
    user_id = data.get('user_id')

    if not audio_b64:
        return jsonify({"error": "No audio provided"}), 400

    async def _eval():
        from handlers.speaking import GEMINI_KEYS, GEMINI_MODEL, _next_key
        import random
        key = random.choice(GEMINI_KEYS)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/MODEL_PLACEHOLDER:generateContent?key={key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": f"Evaluate this {part} IELTS speaking response for prompt: '{prompt}'. Audio duration: {duration_sec}s. Reply in JSON with fields: overall, fluency, pronunciation, lexical_resource, grammatical_range, feedback_ar, transcript."},
                    {"inline_data": {"mime_type": "audio/ogg", "data": audio_b64}}
                ]
            }],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}
        }
        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    raw = data["candidates"][0]["content"]["parts"][0]["text"]
                    raw = raw.strip()
                    if raw.startswith("```json"): raw = raw[7:]
                    if raw.startswith("```"): raw = raw[3:]
                    if raw.endswith("```"): raw = raw[:-3]
                    return json.loads(raw.strip())
                else:
                    raise Exception(f"Gemini error: {resp.status}")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_eval())
        loop.close()

        if user_id:
            from database import save_speaking_session
            save_speaking_session(
                user_id=int(user_id), prompt=prompt,
                transcript_text=result.get("transcript", ""),
                duration=duration_sec,
                band_score=result.get("overall", 0),
                fluency=result.get("fluency", 0),
                pronunciation=result.get("pronunciation", 0),
                lexical_resource=result.get("lexical_resource", 0),
                grammatical_range=result.get("grammatical_range", 0),
                feedback_ar=result.get("feedback_ar", "")
            )

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''

    # Insert before `if __name__`
    marker = "if __name__"
    if marker in content:
        content = content.replace(marker, api_patch + "\n\n" + marker)
    else:
        content += api_patch

    with open(API_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ api_server.py patched with /writing/evaluate + /speaking/evaluate endpoints")


# ============================================================
# 7. PATCH handlers/start.py — Add Writing & Speaking buttons
# ============================================================
def patch_start_menu():
    start_path = os.path.join(HANDLERS_DIR, "start.py")
    if not os.path.exists(start_path):
        print("ℹ️ start.py not found — skipping menu patch")
        return

    with open(start_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Add buttons if not already there
    if "✍️ تقييم كتابة" in content and "🎙️ تحدث" in content:
        print("ℹ️ Writing & Speaking buttons already in start menu")
        return

    # Find the keyboard definition block and add buttons
    # We'll inject a simple message handler
    menu_patch = '''

# ── Writing & Speaking quick access ──
@router.message(F.text.in_(["✍️ تقييم كتابة", "✍️ Writing Correction"]))
async def quick_writing(msg: Message, state: FSMContext):
    from .writing import writing_start
    await writing_start(msg, state)

@router.message(F.text.in_(["🎙️ تحدث", "🎙️ Speaking Coach"]))
async def quick_speaking(msg: Message, state: FSMContext):
    from .speaking import speaking_start
    await speaking_start(msg, state)
'''
    # Add before last line or after imports
    content += "\n" + menu_patch

    with open(start_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ start.py patched with Writing & Speaking quick-access handlers")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Yamen Academy — AI Engines Builder")
    print("=" * 60)

    patch_database()
    write_files()
    register_routers()
    patch_api()
    patch_start_menu()

    print("\n" + "=" * 60)
    print("✅ ALL DONE — AI Writing Engine + AI Speaking Coach ready!")
    print("=" * 60)
    print("\n📋 What was built:")
    print("  ├─ handlers/writing.py  — IELTS Essay Correction (Gemini)")
    print("  ├─ handlers/speaking.py — IELTS Speaking Coach (Gemini)")
    print("  ├─ database.py          — writing_submissions + speaking_sessions tables")
    print("  ├─ api_server.py        — /api/writing/evaluate + /api/speaking/evaluate")
    print("  ├─ handlers/__init__.py — Routers registered")
    print("  └─ handlers/start.py    — Quick-access buttons")
    print("\n🚀 Next step:")
    print("  cd C:\\yamen_academy")
    print("  python main.py")
    print("\n📱 In the bot, students will see:")
    print("  ✍️ تقييم كتابة — submit essay, get Band Score + Feedback")
    print("  🎙️ تحدث — send voice note, get Speaking Band Score")
    print("=" * 60)
