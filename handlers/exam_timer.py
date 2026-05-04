"""
Yamen Academy — IELTS Exam Timer System
Realistic exam simulation with countdown, pressure sounds, and auto-submission
"""
from aiogram import Router, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import _safe_exec, dict_rows, dict_row, add_quiz_attempt
import asyncio, json, random

router = Router()

# ============================================================
# IELTS EXAM STRUCTURE (exact timing)
# ============================================================
IELTS_TIMING = {
    "listening": {
        "total_seconds": 2400,  # 40 min (30 audio + 10 transfer)
        "sections": [
            {"name": "Section 1 - Social", "questions": 10, "audio_seconds": 420},
            {"name": "Section 2 - Monologue", "questions": 10, "audio_seconds": 420},
            {"name": "Section 3 - Academic Discussion", "questions": 10, "audio_seconds": 480},
            {"name": "Section 4 - Lecture", "questions": 10, "audio_seconds": 480},
        ],
        "transfer_time": 600,  # 10 min to transfer answers
        "emoji": "🎧"
    },
    "reading": {
        "total_seconds": 3600,  # 60 min
        "passages": [
            {"name": "Passage 1", "recommended_seconds": 1020},  # 17 min
            {"name": "Passage 2", "recommended_seconds": 1200},  # 20 min
            {"name": "Passage 3", "recommended_seconds": 1380},  # 23 min
        ],
        "emoji": "📖"
    },
    "writing": {
        "total_seconds": 3600,  # 60 min
        "tasks": [
            {"name": "Task 1 (150 words)", "recommended_seconds": 1200},  # 20 min
            {"name": "Task 2 (250 words)", "recommended_seconds": 2400},  # 40 min
        ],
        "emoji": "✍️"
    },
    "speaking": {
        "total_seconds": 840,  # ~14 min
        "parts": [
            {"name": "Part 1 - Introduction", "seconds": 270},   # 4-5 min
            {"name": "Part 2 - Cue Card (prep)", "seconds": 60},  # 1 min prep
            {"name": "Part 2 - Cue Card (speak)", "seconds": 120}, # 2 min speak
            {"name": "Part 3 - Discussion", "seconds": 270},      # 4-5 min
        ],
        "emoji": "🎤"
    }
}

# ============================================================
# FSM STATES
# ============================================================
class ExamSession(StatesGroup):
    choosing_module = State()
    in_progress = State()
    awaiting_answer = State()
    reviewing = State()

# ============================================================
# TIMER DISPLAY FORMATTER
# ============================================================
def format_time(seconds: int) -> str:
    """Convert seconds to MM:SS or HH:MM:SS"""
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"

def get_urgency_level(remaining_seconds: int, total_seconds: int) -> str:
    """Get urgency indicator based on remaining time"""
    pct = remaining_seconds / total_seconds
    if pct > 0.5: return "🟢"
    if pct > 0.25: return "🟡"
    if pct > 0.1: return "🟠"
    return "🔴"

def generate_progress_bar(remaining: int, total: int, width: int = 20) -> str:
    """Visual progress bar"""
    filled = int((remaining / total) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}]"

# ============================================================
# START EXAM
# ============================================================
@router.callback_query(F.data == "start_mock_exam")
async def start_mock_exam(cb: types.CallbackQuery, state: FSMContext):
    """Choose which module to practice"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎧 Listening (40 min)", callback_data="mock_listening")],
        [InlineKeyboardButton(text="📖 Reading (60 min)", callback_data="mock_reading")],
        [InlineKeyboardButton(text="✍️ Writing (60 min)", callback_data="mock_writing")],
        [InlineKeyboardButton(text="🎤 Speaking (14 min)", callback_data="mock_speaking")],
        [InlineKeyboardButton(text="🏆 Full Test (3 hours)", callback_data="mock_full")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="student_menu")],
    ])
    
    await cb.message.edit_text(
        "⏱️ *IELTS Mock Test*\n\n"
        "Choose a module to practice with real exam timing.\n"
        "The timer will run EXACTLY like the real IELTS.\n"
        "When time ends, your answers auto-submit.\n\n"
        "⚠️ *No pauses allowed* — just like the real exam!",
        reply_markup=kb, parse_mode="Markdown"
    )
    await cb.answer()

# ============================================================
# MODULE HANDLERS
# ============================================================
@router.callback_query(F.data.startswith("mock_"))
async def start_module(cb: types.CallbackQuery, state: FSMContext):
    module = cb.data.split("_")[1]
    
    if module == "full":
        await cb.message.edit_text("🏆 Full Test coming soon. Choose a module first.")
        await cb.answer()
        return
    
    timing = IELTS_TIMING.get(module)
    if not timing:
        await cb.answer("Module not found", show_alert=True); return
    
    # Get questions for this module
    questions = await get_module_questions(module)
    if not questions:
        await cb.message.edit_text(f"⚠️ No {module} questions added yet. Add from Admin Panel.")
        await cb.answer(); return
    
    # Store exam session data
    await state.update_data(
        module=module,
        total_seconds=timing["total_seconds"],
        questions=questions,
        current_q=0,
        answers=[],
        start_time=asyncio.get_event_loop().time(),
        paused=False
    )
    
    await state.set_state(ExamSession.in_progress)
    
    # Start the countdown
    await run_timed_exam(cb.message, state, timing, questions)
    await cb.answer()

# ============================================================
# MAIN EXAM LOOP WITH LIVE TIMER
# ============================================================
async def run_timed_exam(msg: types.Message, state: FSMContext, timing: dict, questions: list):
    """Run the timed exam with live countdown display"""
    total = timing["total_seconds"]
    data = await state.get_data()
    start_time = data["start_time"]
    module = data["module"]
    current_q = data.get("current_q", 0)
    answers = data.get("answers", [])
    
    # Update timer every second until time runs out
    for remaining in range(total, -1, -1):
        # Check if we should break (exam finished or user submitted)
        current_data = await state.get_data()
        if current_data.get("exam_complete"):
            return
        
        if remaining % 2 == 0 or remaining == total:  # Update display every 2 sec
            await update_exam_display(msg, state, remaining, total, module, questions, current_q)
        
        await asyncio.sleep(1)

    # Time's up! Auto-submit
    await auto_submit_exam(msg, state)

async def update_exam_display(msg: types.Message, state: FSMContext, remaining: int, total: int,
                               module: str, questions: list, current_q: int):
    """Update the exam message with live timer and current question"""
    data = await state.get_data()
    current_q = data.get("current_q", 0)
    
    urgency = get_urgency_level(remaining, total)
    bar = generate_progress_bar(remaining, total)
    time_display = format_time(remaining)
    emoji = IELTS_TIMING[module]["emoji"]
    
    # Current question display
    if current_q < len(questions):
        q = questions[current_q]
        q_text = f"\n\n📝 *Question {current_q + 1}/{len(questions)}*\n{q.get('question_text', '...')}"
        
        # Build answer keyboard
        if q.get('question_type') == 'mcq' and q.get('options'):
            opts = json.loads(q['options'])
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=opt, callback_data=f"exam_ans_{current_q}_{i}")]
                for i, opt in enumerate(opts)
            ] + [
                [InlineKeyboardButton(text="⏭️ Skip", callback_data=f"exam_skip_{current_q}")],
                [InlineKeyboardButton(text="🏁 Submit Early", callback_data="exam_submit_early")],
            ])
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Skip", callback_data=f"exam_skip_{current_q}")],
                [InlineKeyboardButton(text="🏁 Submit Early", callback_data="exam_submit_early")],
            ])
    else:
        q_text = "\n\n✅ All questions answered! Waiting for timer..."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏁 Submit Now", callback_data="exam_submit_early")],
        ])
    
    text = (
        f"{emoji} *{module.upper()} EXAM*\n"
        f"{bar}\n"
        f"{urgency} ⏱️ *{time_display}* remaining\n"
        f"{'🔴 FINAL MINUTE! ' if remaining <= 60 else ''}"
        f"{q_text}"
    )
    
    try:
        await msg.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass  # Message not modified (same content)

# ============================================================
# ANSWER HANDLERS
# ============================================================
@router.callback_query(ExamSession.in_progress, F.data.startswith("exam_ans_"))
async def handle_exam_answer(cb: types.CallbackQuery, state: FSMContext):
    """Record answer and move to next question"""
    parts = cb.data.split("_")
    q_idx = int(parts[2])
    chosen = int(parts[3])
    
    data = await state.get_data()
    questions = data["questions"]
    answers = data.get("answers", [])
    
    # Record answer
    if q_idx < len(questions):
        q = questions[q_idx]
        opts = json.loads(q.get('options', '[]'))
        answers.append({
            "question_id": q_idx,
            "chosen": opts[chosen] if chosen < len(opts) else "",
            "correct": q.get('correct_answer', ''),
            "is_correct": opts[chosen] == q.get('correct_answer', '') if chosen < len(opts) else False
        })
    
    # Move to next question
    next_q = q_idx + 1
    await state.update_data(current_q=next_q, answers=answers)
    
    # Flash feedback
    is_correct = answers[-1]["is_correct"] if answers else False
    await cb.answer("✅ Correct!" if is_correct else "❌ Wrong", show_alert=True if not is_correct else False)

@router.callback_query(ExamSession.in_progress, F.data.startswith("exam_skip_"))
async def skip_question(cb: types.CallbackQuery, state: FSMContext):
    """Skip to next question"""
    data = await state.get_data()
    current_q = data.get("current_q", 0)
    await state.update_data(current_q=current_q + 1)
    await cb.answer("Skipped ⏭️")

# ============================================================
# EARLY SUBMIT
# ============================================================
@router.callback_query(ExamSession.in_progress, F.data == "exam_submit_early")
async def early_submit(cb: types.CallbackQuery, state: FSMContext):
    """Student clicks Submit Early"""
    await state.update_data(exam_complete=True)
    
    # Confirmation
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes, Submit", callback_data="confirm_submit")],
        [InlineKeyboardButton(text="❌ No, Continue", callback_data="cancel_submit")],
    ])
    await cb.message.edit_text("⚠️ *Submit exam early?*\nYou cannot return after submitting.", 
                              reply_markup=kb, parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data == "confirm_submit")
async def confirm_submit(cb: types.CallbackQuery, state: FSMContext):
    await auto_submit_exam(cb.message, state)
    await cb.answer()

@router.callback_query(F.data == "cancel_submit")
async def cancel_submit(cb: types.CallbackQuery, state: FSMContext):
    await state.update_data(exam_complete=False)
    await cb.answer("Continue!")

# ============================================================
# AUTO-SUBMIT + RESULTS
# ============================================================
async def auto_submit_exam(msg: types.Message, state: FSMContext):
    """Time's up or student submitted — calculate score"""
    data = await state.get_data()
    await state.clear()
    
    questions = data.get("questions", [])
    answers = data.get("answers", [])
    module = data.get("module", "reading")
    total_questions = len(questions)
    
    # Calculate score
    correct = sum(1 for a in answers if a.get("is_correct"))
    skipped = total_questions - len(answers)
    wrong = len(answers) - correct
    
    # IELTS Band Score conversion (approximate)
    if total_questions == 40:  # Listening/Reading standard
        band = ielts_band_score(correct)
    else:
        pct = correct / max(total_questions, 1) * 100
        band = estimate_band_from_pct(pct)
    
    # Performance breakdown
    speed = "Fast ⚡" if len(answers) >= total_questions * 0.9 else "Needs improvement 🐢"
    
    # Generate feedback
    feedback = generate_exam_feedback(module, correct, total_questions, answers, questions)
    
    result_text = (
        f"📊 *{module.upper()} RESULTS*\n\n"
        f"🏆 *Band Score: {band}*\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"✅ Correct: {correct}\n"
        f"❌ Wrong: {wrong}\n"
        f"⏭️ Skipped: {skipped}\n"
        f"📝 Total: {total_questions}\n"
        f"⚡ Speed: {speed}\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"{feedback}\n\n"
        f"🎯 *Focus areas:*\n{get_focus_areas(module, answers, questions)}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Retry This Module", callback_data=f"mock_{module}")],
        [InlineKeyboardButton(text="📊 Detailed Report", callback_data="exam_detailed_report")],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="student_menu")],
    ])
    
    await msg.edit_text(result_text, reply_markup=kb, parse_mode="Markdown")
    
    # Save attempt to database
    try:
        user_id = msg.chat.id
        add_quiz_attempt(user_id, 0, answers, correct)
        # Add XP
        _safe_exec("UPDATE students SET xp = xp + ? WHERE user_id = ?", 
                  (correct * 10, user_id))
    except:
        pass

# ============================================================
# IELTS BAND SCORE CALCULATOR
# ============================================================
def ielts_band_score(correct: int) -> float:
    """Convert raw score to IELTS Band (Listening/Reading - Academic)"""
    band_table = {
        40: 9.0, 39: 9.0, 38: 8.5, 37: 8.5,
        36: 8.0, 35: 8.0, 34: 7.5, 33: 7.5,
        32: 7.0, 31: 7.0, 30: 7.0, 29: 6.5,
        28: 6.5, 27: 6.5, 26: 6.0, 25: 6.0,
        24: 6.0, 23: 6.0, 22: 5.5, 21: 5.5,
        20: 5.5, 19: 5.5, 18: 5.0, 17: 5.0,
        16: 5.0, 15: 5.0, 14: 4.5, 13: 4.5,
        12: 4.0, 11: 4.0, 10: 4.0, 9: 3.5,
        8: 3.5, 7: 3.0, 6: 3.0, 5: 2.5,
        4: 2.5, 3: 2.0, 2: 2.0, 1: 1.0, 0: 1.0
    }
    return band_table.get(min(correct, 40), 1.0)

def estimate_band_from_pct(pct: float) -> str:
    """Estimate band from percentage"""
    bands = [
        (95, "8.5+"),
        (85, "7.5-8.0"),
        (75, "6.5-7.0"),
        (60, "5.5-6.0"),
        (45, "4.5-5.0"),
        (0, "Below 4.5")
    ]
    for threshold, band in bands:
        if pct >= threshold: return band
    return "N/A"

def generate_exam_feedback(module: str, correct: int, total: int, answers: list, questions: list):
    """Generate personalized feedback"""
    pct = correct / max(total, 1) * 100
    
    feedbacks = {
        "reading": {
            "high": "Excellent reading skills! Focus on speed — try finishing 5 min early.",
            "mid": "Good comprehension. Practice Skim/Scan to increase speed.",
            "low": "Focus on: 1) Skimming 2) Keyword matching 3) True/False/NG traps"
        },
        "listening": {
            "high": "Great ear! Practice with faster audio (1.2x speed).",
            "mid": "Good. Focus on spelling and Section 3-4 (hardest).",
            "low": "Practice: 1) Dictation drills 2) Number spelling 3) Map labeling"
        },
        "writing": {
            "high": "Strong structure! Next: lexical variety.",
            "mid": "Work on: Task 2 essay structure (4 paragraphs).",
            "low": "Master: 1) Essay template 2) Linking words 3) 250 word target"
        },
        "speaking": {
            "high": "Confident speaker! Polish advanced vocabulary.",
            "mid": "Practice: 2-min monologues, hesitation fillers.",
            "low": "Daily: 1) Shadow speaking 2) Record & review 3) Fluency over accuracy"
        }
    }
    
    level = "high" if pct >= 80 else "mid" if pct >= 55 else "low"
    return feedbacks.get(module, {}).get(level, "Keep practicing!")

def get_focus_areas(module: str, answers: list, questions: list):
    """Identify weak areas"""
    weak_types = {}
    for i, ans in enumerate(answers):
        if i < len(questions) and not ans.get("is_correct"):
            qtype = questions[i].get("question_type", "general")
            weak_types[qtype] = weak_types.get(qtype, 0) + 1
    
    if weak_types:
        worst = max(weak_types, key=weak_types.get)
        return f"🔸 Focus on: *{worst}* questions ({weak_types[worst]} mistakes)"
    return "🔸 All good! Maintain your level."

# ============================================================
# QUESTION LOADER
# ============================================================
async def get_module_questions(module: str) -> list:
    """Load questions for specific IELTS module"""
    # This fetches from your existing question banks
    mapping = {
        "reading": "reading_comprehension",
        "listening": "listening_comprehension", 
        "writing": "essay_prompts",
        "speaking": "speaking_prompts"
    }
    qtype = mapping.get(module, "mcq")
    
    cur = _safe_exec(
        "SELECT * FROM quiz_questions WHERE question_type LIKE ? ORDER BY RANDOM() LIMIT 40",
        (f"%{qtype}%",)
    )
    questions = dict_rows(cur.fetchall())
    
    if not questions:
        cur = _safe_exec(
            "SELECT * FROM placement_questions ORDER BY RANDOM() LIMIT 40"
        )
        questions = dict_rows(cur.fetchall())
    
    return questions

# ============================================================
# QUICK PRACTICE (5-min drills)
# ============================================================
@router.callback_query(F.data == "quick_drill")
async def quick_drill(cb: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ 5-min Reading Sprint", callback_data="drill_reading_5min")],
        [InlineKeyboardButton(text="🎧 3-min Listening Burst", callback_data="drill_listening_3min")],
        [InlineKeyboardButton(text="✍️ 10-min Writing Drill", callback_data="drill_writing_10min")],
        [InlineKeyboardButton(text="🎤 2-min Speaking Challenge", callback_data="drill_speaking_2min")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="student_menu")],
    ])
    
    await cb.message.edit_text(
        "⚡ *Quick Drills*\n\n"
        "Short, high-intensity practice:\n"
        "- 5 min = 1 Reading passage sprint\n"
        "- 3 min = listening burst\n"
        "- 10 min = timed paragraph writing\n"
        "- 2 min = speaking cue card",
        reply_markup=kb, parse_mode="Markdown"
    )
    await cb.answer()

# ============================================================
# PRESSURE SOUNDS (Optional — plays beeps at key moments)
# ============================================================
PRESSURE_MESSAGES = {
    "halfway": "⚠️ Halfway through! Keep going!",
    "warning_5min": "🔴 5 MINUTES LEFT! Move faster!",
    "warning_1min": "🚨 1 MINUTE! Guess if unsure!",
    "end": "⏹️ TIME'S UP! Pencils down!"
}

def get_time_warnings(remaining: int, total: int) -> list:
    """Get active warnings based on remaining time"""
    warnings = []
    half = total // 2
    if remaining == half: warnings.append(PRESSURE_MESSAGES["halfway"])
    if remaining == 300: warnings.append(PRESSURE_MESSAGES["warning_5min"])
    if remaining == 60: warnings.append(PRESSURE_MESSAGES["warning_1min"])
    if remaining == 0: warnings.append(PRESSURE_MESSAGES["end"])
    return warnings
