# -*- coding: utf-8 -*-
"""
اختبار تحديد المستوى داخل Telegram (10 أسئلة)
+ توجيه تلقائي بعد النتيجة (Foundation أو TOEFL مباشر)
"""
from aiogram import types, Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import settings
import sqlite3
import logging

logger = logging.getLogger(__name__)
router = Router(name="placement_inline")

DB_PATH = settings.DB_PATH

# ═══════════════════════════════════════════════════
#  بنك الأسئلة (10 أسئلة متدرجة)
# ═══════════════════════════════════════════════════
QUESTIONS = [
    {
        "id": 1, "skill": "grammar",
        "q": "Choose the correct verb form:\n\nShe ____ to the library every Sunday.",
        "options": {"A": "go", "B": "goes", "C": "going", "D": "gone"},
        "answer": "B"
    },
    {
        "id": 2, "skill": "vocab",
        "q": "What does \"benefit\" mean?",
        "options": {"A": "harm", "B": "advantage", "C": "danger", "D": "problem"},
        "answer": "B"
    },
    {
        "id": 3, "skill": "grammar",
        "q": "Fill in the blank:\n\nIf I ____ rich, I would travel the world.",
        "options": {"A": "am", "B": "was", "C": "were", "D": "be"},
        "answer": "C"
    },
    {
        "id": 4, "skill": "vocab",
        "q": "Choose the synonym of \"significant\":",
        "options": {"A": "small", "B": "important", "C": "easy", "D": "quick"},
        "answer": "B"
    },
    {
        "id": 5, "skill": "grammar",
        "q": "Choose the correct option:\n\nThe report ____ by the manager yesterday.",
        "options": {"A": "wrote", "B": "was written", "C": "is writing", "D": "writes"},
        "answer": "B"
    },
    {
        "id": 6, "skill": "reading",
        "q": "Read: \"Despite the heavy rain, the match continued.\"\n\nWhat does this sentence imply?",
        "options": {
            "A": "The rain stopped the match",
            "B": "The match was cancelled",
            "C": "The match went on even though it rained",
            "D": "There was no rain"
        },
        "answer": "C"
    },
    {
        "id": 7, "skill": "vocab",
        "q": "Choose the opposite of \"abundant\":",
        "options": {"A": "plentiful", "B": "scarce", "C": "rich", "D": "full"},
        "answer": "B"
    },
    {
        "id": 8, "skill": "grammar",
        "q": "Choose the correct sentence:",
        "options": {
            "A": "He don't like coffee",
            "B": "He doesn't likes coffee",
            "C": "He doesn't like coffee",
            "D": "He not like coffee"
        },
        "answer": "C"
    },
    {
        "id": 9, "skill": "reading",
        "q": "\"The researcher's findings were inconclusive.\"\n\nThis means:",
        "options": {
            "A": "The results were very clear",
            "B": "No clear conclusion was reached",
            "C": "The research was successful",
            "D": "The findings were published"
        },
        "answer": "B"
    },
    {
        "id": 10, "skill": "vocab",
        "q": "Choose the meaning of \"elaborate\":",
        "options": {
            "A": "simple and brief",
            "B": "detailed and complex",
            "C": "wrong and false",
            "D": "quick and easy"
        },
        "answer": "B"
    },
]

# تخزين مؤقت في الذاكرة: user_id -> {idx, answers, correct}
SESSIONS = {}


# ═══════════════════════════════════════════════════
#  أدوات DB
# ═══════════════════════════════════════════════════
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _save_placement_result(user_id, score_pct, path, stage_id):
    conn = _db()
    cur = conn.cursor()
    cur.execute("""UPDATE students
                   SET placement_done=1, placement_score=?, placement_path=?,
                       current_stage_id=?
                   WHERE telegram_id=?""",
                (float(score_pct), path, stage_id, user_id))
    conn.commit()
    # إنشاء سجل في stage_progress للمرحلة الأولى
    cur.execute("""INSERT OR IGNORE INTO stage_progress
                   (student_id, stage_id, status, started_at)
                   VALUES (?, ?, 'unlocked', datetime('now'))""",
                (user_id, stage_id))
    conn.commit()
    conn.close()


def _get_first_stage_id(path):
    """يرجع ID المرحلة الأولى حسب المسار."""
    conn = _db()
    cur = conn.cursor()
    if path == "foundation":
        cur.execute("SELECT id FROM stages WHERE code='F1'")
    else:
        cur.execute("SELECT id FROM stages WHERE code='TR1'")
    row = cur.fetchone()
    conn.close()
    return row["id"] if row else None


# ═══════════════════════════════════════════════════
#  لوحات المفاتيح
# ═══════════════════════════════════════════════════
def kb_question(qid):
    q = QUESTIONS[qid]
    rows = []
    for letter in ["A", "B", "C", "D"]:
        rows.append([InlineKeyboardButton(
            text=f"{letter}) {q['options'][letter]}",
            callback_data=f"pl:ans:{qid}:{letter}"
        )])
    rows.append([InlineKeyboardButton(text="❌ إلغاء الاختبار", callback_data="pl:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_after_result(path):
    btn_text = "🛠️ ابدأ التأسيس (المرحلة F1)" if path == "foundation" else "🎯 ابدأ TOEFL (المرحلة TR1)"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, callback_data="open_first_stage")],
        [InlineKeyboardButton(text="📋 القائمة الرئيسية", callback_data="back_to_menu")],
    ])


def kb_start_test():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 ابدأ الآن", callback_data="pl:start")],
        [InlineKeyboardButton(text="↩️ لاحقاً", callback_data="back_to_menu")],
    ])


# ═══════════════════════════════════════════════════
#  نقطة الدخول: بدء الاختبار (يُستدعى من start.py)
# ═══════════════════════════════════════════════════
@router.callback_query(F.data == "pl:begin")
async def cb_begin_placement(callback: types.CallbackQuery):
    """يظهر شاشة تعليمات الاختبار."""
    await callback.answer()
    text = (
        "🔬 <b>اختبار تحديد المستوى</b>\n\n"
        "📝 <b>التعليمات:</b>\n"
        "• 10 أسئلة (قواعد + مفردات + قراءة)\n"
        "• لا يوجد وقت محدد، خذ راحتك\n"
        "• اختر إجابة واحدة لكل سؤال\n"
        "• لا توجد عودة للسؤال السابق\n\n"
        "🎯 <b>التوجيه التلقائي:</b>\n"
        "• نتيجة أقل من 50 بالمئة تعني مسار التأسيس\n"
        "• نتيجة 50 بالمئة فأكثر تعني TOEFL مباشرة\n\n"
        "هل أنت مستعد؟ 👇"
    )
    await callback.message.edit_text(text, reply_markup=kb_start_test())


@router.callback_query(F.data == "pl:start")
async def cb_start_test(callback: types.CallbackQuery):
    """يبدأ السؤال الأول."""
    user_id = callback.from_user.id
    SESSIONS[user_id] = {"idx": 0, "answers": [], "correct": 0}
    await _show_question(callback, 0)


async def _show_question(callback, qid):
    q = QUESTIONS[qid]
    skill_ar = {"grammar": "📐 قواعد", "vocab": "📚 مفردات", "reading": "📖 قراءة"}.get(q["skill"], "")
    text = (
        f"<b>السؤال {qid+1} من {len(QUESTIONS)}</b> | {skill_ar}\n\n"
        f"{q['q']}"
    )
    await callback.message.edit_text(text, reply_markup=kb_question(qid))


@router.callback_query(F.data.startswith("pl:ans:"))
async def cb_answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in SESSIONS:
        await callback.answer("⚠️ ابدأ الاختبار من جديد بالأمر /start", show_alert=True)
        return

    try:
        parts = callback.data.split(":")
        qid = int(parts[2])
        chosen = parts[3]
    except (ValueError, IndexError):
        await callback.answer("❌ خطأ في البيانات", show_alert=True)
        return

    session = SESSIONS[user_id]
    q = QUESTIONS[qid]
    is_correct = (chosen == q["answer"])
    session["answers"].append({"qid": qid, "chosen": chosen, "correct": is_correct})
    if is_correct:
        session["correct"] += 1

    await callback.answer("✅ صحيح!" if is_correct else f"❌ الإجابة الصحيحة: {q['answer']}", show_alert=False)

    # الانتقال للسؤال التالي
    next_idx = qid + 1
    if next_idx < len(QUESTIONS):
        session["idx"] = next_idx
        await _show_question(callback, next_idx)
    else:
        await _finish_test(callback, user_id)


async def _finish_test(callback, user_id):
    """ينهي الاختبار، يحسب النتيجة، يحفظها، ويُظهر التوجيه."""
    session = SESSIONS.get(user_id, {})
    correct = session.get("correct", 0)
    total = len(QUESTIONS)
    score_pct = round((correct / total) * 100, 1)

    # تحديد المسار
    if score_pct < 50:
        path = "foundation"
        path_msg = (
            "🛠️ <b>المسار: التأسيس الإجباري</b>\n\n"
            "ستبدأ بمراحل التأسيس (قواعد + مفردات + قراءة تمهيدية) "
            "قبل الانتقال لـ TOEFL.\n\n"
            "هذا المسار مُصمم لتقوية أساسياتك أولاً، ثم تنطلق بثقة."
        )
        first_stage_code = "F1"
    else:
        path = "toefl"
        path_msg = (
            "🎯 <b>المسار: TOEFL iBT مباشر</b>\n\n"
            "أساسياتك جيدة، يمكنك البدء مباشرة بمراحل TOEFL.\n\n"
            "ستبدأ من القراءة (TR1) ثم تتقدم لباقي المهارات."
        )
        first_stage_code = "TR1"

    # حفظ في DB
    stage_id = _get_first_stage_id(path)
    _save_placement_result(user_id, score_pct, path, stage_id)

    # رسالة النتيجة
    bar = "🟩" * int(score_pct / 10) + "⬜" * (10 - int(score_pct / 10))
    text = (
        f"🎉 <b>انتهى الاختبار!</b>\n\n"
        f"📊 <b>نتيجتك: {correct}/{total} = {score_pct}%</b>\n"
        f"{bar}\n\n"
        f"{path_msg}\n\n"
        f"📍 المرحلة الأولى: <b>{first_stage_code}</b>\n"
        "اضغط الزر التالي للانطلاق 👇"
    )
    await callback.message.edit_text(text, reply_markup=kb_after_result(path))

    # تنظيف الجلسة
    SESSIONS.pop(user_id, None)


@router.callback_query(F.data == "pl:cancel")
async def cb_cancel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    SESSIONS.pop(user_id, None)
    await callback.answer("تم الإلغاء")
    await callback.message.edit_text(
        "❌ تم إلغاء اختبار تحديد المستوى.\n\nأرسل /start للعودة."
    )


# ═══════════════════════════════════════════════════
#  بعد النتيجة: فتح المرحلة الأولى
# ═══════════════════════════════════════════════════
@router.callback_query(F.data == "open_first_stage")
async def cb_open_first(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = _db()
    cur = conn.cursor()
    cur.execute("""SELECT s.code, s.name_ar, s.description
                   FROM students st JOIN stages s ON s.id = st.current_stage_id
                   WHERE st.telegram_id=?""", (user_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        await callback.answer("⚠️ لم يتم تحديد مرحلتك بعد", show_alert=True)
        return

    await callback.answer()
    text = (
        f"📍 <b>{row['name_ar']}</b> ({row['code']})\n\n"
        f"📝 {row['description']}\n\n"
        "🚀 مرحلتك الأولى مفتوحة!\n"
        "افتح القائمة الرئيسية واختر <b>📚 دروسي</b> للبدء."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 القائمة الرئيسية", callback_data="back_to_menu")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "back_to_menu")
async def cb_back_menu(callback: types.CallbackQuery):
    from handlers.start import get_main_keyboard, _get_student_setup
    user_id = callback.from_user.id
    setup = _get_student_setup(user_id)
    is_paid = bool(setup.get("is_paid", 0))
    target = setup.get("target_score", 0)
    path = setup.get("placement_path") or "toefl"
    path_ar = "🛠️ تأسيس + TOEFL" if path == "foundation" else "🎯 TOEFL مباشر"
    text = (
        f"📋 <b>القائمة الرئيسية</b>\n\n"
        f"🎯 الهدف: <b>{target}</b> | المسار: {path_ar}"
    )
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=get_main_keyboard(is_paid))