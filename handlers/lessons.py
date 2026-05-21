# -*- coding: utf-8 -*-
"""
handlers/lessons.py — Wave 5.3-C (Integrated)
يربط: الدروس + الكويز + قفل 24 ساعة + XP + التقدم بين المراحل.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import sqlite3
import logging
from datetime import datetime

from bot_database import add_xp
from subscription_helpers import (
    can_start_new_lesson,
    mark_lesson_completed_now,
    get_lock_message_ar,
)
from quiz_engine import (
    get_lesson_quiz,
    check_answer,
    start_quiz_attempt,
    finish_quiz_attempt,
    record_mistake,
    get_quiz_result_message_ar,
    get_student_lesson_stats,
    get_required_streak,
    get_student_target,
    get_cooldown_status,
    register_failed_attempt,
    clear_cooldown,
    format_cooldown_time,
)

logger = logging.getLogger(__name__)
router = Router(name="lessons")

DB_PATH = r"C:\Users\nelt2\yamen_academy\academy.db"
LESSONS_PER_STAGE = 5
XP_PER_LESSON = 20

SECTION_EMOJI = {"grammar": "📝", "vocabulary": "📚", "reading": "📖",
                 "listening": "🎧", "speaking": "🗣️", "writing": "✍️"}

# ============ خدمات DB ============
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_student(tid):
    conn = _db()
    try:
        return conn.execute(
            "SELECT * FROM students WHERE telegram_id = ?", (str(tid),)
        ).fetchone()
    finally:
        conn.close()

def get_stage(stage_id):
    conn = _db()
    try:
        return conn.execute(
            "SELECT * FROM stages WHERE id = ?", (stage_id,)
        ).fetchone()
    finally:
        conn.close()

def get_stage_lessons(stage_id):
    conn = _db()
    try:
        return conn.execute("""
            SELECT id, title, content, section_name, order_index
            FROM lessons WHERE stage_id = ?
            ORDER BY order_index
        """, (stage_id,)).fetchall()
    finally:
        conn.close()

def get_next_stage_id(current_stage_id):
    """يرجع id المرحلة التالية حسب order_num."""
    conn = _db()
    try:
        current = conn.execute(
            "SELECT order_num, track FROM stages WHERE id = ?", (current_stage_id,)
        ).fetchone()
        if not current:
            return None
        nxt = conn.execute("""
            SELECT id FROM stages
            WHERE order_num > ? AND is_active = 1
            ORDER BY order_num LIMIT 1
        """, (current["order_num"],)).fetchone()
        return nxt["id"] if nxt else None
    finally:
        conn.close()

def update_stage_progress(tid, stage_id):
    """يزيد lessons_completed وينشئ صفًا إذا لم يوجد."""
    conn = _db()
    try:
        row = conn.execute("""
            SELECT id, lessons_completed FROM stage_progress
            WHERE student_id = ? AND stage_id = ?
        """, (tid, stage_id)).fetchone()
        if row:
            new_count = row["lessons_completed"] + 1
            conn.execute("""
                UPDATE stage_progress
                SET lessons_completed = ?, status = 'in_progress'
                WHERE id = ?
            """, (new_count, row["id"]))
        else:
            new_count = 1
            conn.execute("""
                INSERT INTO stage_progress
                (student_id, stage_id, status, lessons_completed, started_at)
                VALUES (?, ?, 'in_progress', 1, CURRENT_TIMESTAMP)
            """, (tid, stage_id))
        # إذا اكتملت 5 دروس → تحديث الحالة
        if new_count >= LESSONS_PER_STAGE:
            conn.execute("""
                UPDATE stage_progress
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE student_id = ? AND stage_id = ?
            """, (tid, stage_id))
        conn.commit()
        return new_count
    finally:
        conn.close()

def promote_to_next_stage(tid, next_stage_id):
    conn = _db()
    try:
        conn.execute(
            "UPDATE students SET current_stage_id = ? WHERE telegram_id = ?",
            (next_stage_id, str(tid))
        )
        conn.commit()
    finally:
        conn.close()

def is_lesson_completed(tid, lesson_id):
    """هل اجتاز الطالب كويز هذا الدرس؟"""
    stats = get_student_lesson_stats(tid, lesson_id)
    return stats["passed"]

# ============ Handlers ============

@router.callback_query(F.data == "menu_lessons")
async def show_lessons(cb: CallbackQuery):
    """عرض دروس المرحلة الحالية مع فحص قفل 24 ساعة."""
    tid = str(cb.from_user.id)
    student = get_student(tid)
    if not student:
        await cb.answer("⚠️ لم يتم العثور على حسابك. استخدم /start أولاً.", show_alert=True)
        return

    stage_id = student["current_stage_id"]
    if not stage_id:
        await cb.message.edit_text(
            "⚠️ لم تحدد مرحلتك بعد.\nاستخدم /start لإجراء اختبار التحديد.",
            reply_markup=None
        )
        return

    stage = get_stage(stage_id)
    if not stage:
        await cb.answer("⚠️ المرحلة غير موجودة.", show_alert=True)
        return

    lessons = get_stage_lessons(stage_id)
    if not lessons:
        await cb.message.edit_text(
            f"⚠️ لا توجد دروس في المرحلة {stage['code']}.",
            reply_markup=None
        )
        return

    # حساب عدد المكتملة
    completed_count = sum(1 for l in lessons if is_lesson_completed(tid, l["id"]))

    # فحص قفل 24 ساعة
    allowed, reason, wait_seconds = can_start_new_lesson(tid)

    text = (
        f"📚 المرحلة الحالية: {stage['code']} - {stage['name_ar']}\n"
        f"📊 التقدم: {completed_count}/{len(lessons)} دروس\n\n"
    )

    if not allowed and reason == "daily_lock":
        lock_msg = get_lock_message_ar(tid)
        if lock_msg:
            text += f"{lock_msg}\n\n"
        else:
            text += "⏰ الدرس التالي مقفل حالياً.\n\n"
    else:
        text += "اختر درساً للبدء:"

    kb = InlineKeyboardBuilder()
    for l in lessons:
        completed = is_lesson_completed(tid, l["id"])
        order = int(l["order_index"])
        emoji = SECTION_EMOJI.get(l["section_name"], "📄")

        # المنطق: مكتمل ✅، أو متاح 🔓 إذا (السابق مكتمل أو هو الأول) والقفل غير مفعل
        prev_completed = (order == 1) or any(
            is_lesson_completed(tid, x["id"]) and int(x["order_index"]) == order - 1
            for x in lessons
        )

        if completed:
            icon = "✅"
            callback = f"lesson:{l['id']}"
        elif prev_completed and allowed:
            icon = "🔓"
            callback = f"lesson:{l['id']}"
        else:
            icon = "🔒"
            callback = "locked"

        kb.button(text=f"{icon} {emoji} {l['title'][:35]}", callback_data=callback)

    kb.button(text="🔙 القائمة الرئيسية", callback_data="back_main")
    kb.adjust(1)

    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "locked")
async def locked_lesson(cb: CallbackQuery):
    await cb.answer("🔒 أكمل الدرس السابق أولاً أو انتظر انتهاء قفل اليوم.", show_alert=True)


@router.callback_query(F.data.startswith("lesson:"))
async def show_lesson(cb: CallbackQuery):
    """عرض محتوى الدرس مع زر بدء الكويز."""
    lesson_id = int(cb.data.split(":")[1])
    tid = str(cb.from_user.id)

    conn = _db()
    try:
        lesson = conn.execute(
            "SELECT * FROM lessons WHERE id = ?", (lesson_id,)
        ).fetchone()
    finally:
        conn.close()

    if not lesson:
        await cb.answer("⚠️ الدرس غير موجود.", show_alert=True)
        return

    section = lesson["section_name"] or "lesson"
    emoji = SECTION_EMOJI.get(section, "📄")
    content = lesson["content"] or "(لا يوجد محتوى)"

    # إذا كان المحتوى placeholder ("..."), نعرض رسالة افتراضية
    if content.strip() == "..." or len(content.strip()) < 10:
        content = (
            f"📖 هذا درس {section} في مرحلة الأساس.\n\n"
            f"بعد قراءة العنوان، انتقل مباشرة إلى الكويز لاختبار فهمك."
        )

    text = (
        f"{emoji} {lesson['title']}\n"
        f"{'─' * 25}\n\n"
        f"{content}\n\n"
        f"{'─' * 25}\n"
        f"📝 الكويز: 3 أسئلة | النجاح: 2 من 3"
    )

    kb = InlineKeyboardBuilder()
    stats = get_student_lesson_stats(tid, lesson_id)
    if stats["passed"]:
        kb.button(text="🔁 إعادة الكويز", callback_data=f"quiz_start:{lesson_id}")
        kb.button(text="✅ مكتمل", callback_data="locked")
    else:
        kb.button(text="📝 ابدأ الكويز", callback_data=f"quiz_start:{lesson_id}")
    kb.button(text="🔙 رجوع للدروس", callback_data="menu_lessons")
    kb.adjust(1)

    await cb.message.edit_text(text, reply_markup=kb.as_markup())
    await cb.answer()


# تخزين حالة الكويز في الذاكرة (بسيط — يكفي للاستخدام المحلي)
_quiz_sessions = {}  # {tid: {"attempt_id":, "lesson_id":, "questions":[], "current":0, "correct":0, "answers":[]}}


@router.callback_query(F.data.startswith("quiz_start:"))
async def quiz_start(cb: CallbackQuery):
    """بدء الكويز: فحص cooldown ثم عرض أول سؤال."""
    lesson_id = int(cb.data.split(":")[1])
    tid = str(cb.from_user.id)

    # فحص الانتظار المتدرج
    cooldown = get_cooldown_status(tid, lesson_id)
    if cooldown["in_cooldown"]:
        time_str = format_cooldown_time(cooldown["seconds_left"])
        text = (
            f"⏰ المحاولة التالية بعد: {time_str}\n\n"
            f"{cooldown['motivation']}\n\n"
            f"📚 رسبت {cooldown['failed_attempts']} مرة في هذا الدرس\n"
            f"💡 استغل الوقت لمراجعة الدرس بتمعّن\n"
            f"🎁 ستحصل على أسئلة جديدة في المحاولة القادمة!"
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="📖 مراجعة الدرس", callback_data=f"lesson:{lesson_id}")
        kb.button(text="🔙 رجوع للدروس", callback_data="menu_lessons")
        kb.adjust(1)
        await cb.message.edit_text(text, reply_markup=kb.as_markup())
        await cb.answer()
        return

    questions = get_lesson_quiz(lesson_id)
    if not questions:
        await cb.answer("⚠️ لا توجد أسئلة لهذا الدرس.", show_alert=True)
        return

    attempt_id = start_quiz_attempt(tid, lesson_id)
    target = get_student_target(tid)
    required = get_required_streak(target)
    _quiz_sessions[tid] = {
        "attempt_id": attempt_id,
        "lesson_id": lesson_id,
        "questions": questions,
        "current": 0,
        "correct": 0,
        "streak": 0,              # السلسلة الحالية
        "required_streak": required,
        "target_score": target,
        "max_questions": 8,
        "answers": [],
    }

    await _show_question(cb, tid)


async def _show_question(cb: CallbackQuery, tid: str):
    """عرض السؤال الحالي."""
    session = _quiz_sessions.get(tid)
    if not session:
        await cb.answer("⚠️ انتهت جلسة الكويز. ابدأ من جديد.", show_alert=True)
        return

    idx = session["current"]
    q = session["questions"][idx]
    total = len(session["questions"])

    streak = session.get("streak", 0)
    required = session.get("required_streak", 3)
    target = session.get("target_score", 69)
    max_q = session.get("max_questions", 8)
    # شريط التقدم: 🟢 للنجاح، ⚪ للفارغ
    streak_bar = "🟢" * streak + "⚪" * (required - streak)

    text = (
        f"📝 السؤال {idx + 1} من {max_q} كحد أقصى\n"
        f"🎯 هدفك: TOEFL {target} → تحتاج {required} متتالية\n"
        f"📊 السلسلة: {streak_bar} ({streak}/{required})\n"
        f"{'─' * 25}\n\n"
        f"{q['question']}\n"
    )

    kb = InlineKeyboardBuilder()
    options = q.get("options", {})
    for key in ["A", "B", "C", "D"]:
        if key in options:
            kb.button(
                text=f"{key}) {options[key][:40]}",
                callback_data=f"quiz_ans:{key}"
            )
    kb.adjust(1)

    try:
        await cb.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception:
        await cb.message.answer(text, reply_markup=kb.as_markup())
    await cb.answer()


@router.callback_query(F.data.startswith("quiz_ans:"))
async def quiz_answer(cb: CallbackQuery):
    """معالجة إجابة سؤال."""
    tid = str(cb.from_user.id)
    session = _quiz_sessions.get(tid)
    if not session:
        await cb.answer("⚠️ انتهت الجلسة. ابدأ الكويز من جديد.", show_alert=True)
        return

    user_ans = cb.data.split(":")[1]
    idx = session["current"]
    q = session["questions"][idx]

    # استخدم correct_answer من الـ session (بعد الخلط)
    correct_ans = q.get("correct_answer", "")
    explanation = q.get("explanation", "") or ""
    is_correct = (user_ans or "").strip().upper() == (correct_ans or "").strip().upper()

    session["answers"].append({
        "q_id": q["q_id"], "user": user_ans,
        "correct": correct_ans, "is_correct": is_correct
    })

    required = session.get("required_streak", 3)
    max_q = session.get("max_questions", 8)

    if is_correct:
        session["correct"] += 1
        session["streak"] += 1
        new_streak = session["streak"]
        streak_bar = "🟢" * new_streak + "⚪" * max(0, required - new_streak)
        feedback = (
            f"✅ إجابة صحيحة!\n"
            f"📊 السلسلة: {streak_bar} ({new_streak}/{required})\n\n"
            f"💡 {explanation}"
        )
    else:
        record_mistake(tid, q["id"], user_ans, correct_ans)
        old_streak = session["streak"]
        session["streak"] = 0  # إعادة العدّاد
        reset_msg = f"\n🔄 العدّاد عاد إلى الصفر (كان {old_streak})" if old_streak > 0 else ""
        streak_bar = "⚪" * required
        feedback = (
            f"❌ إجابة غير صحيحة{reset_msg}\n"
            f"📊 السلسلة: {streak_bar} (0/{required})\n\n"
            f"🤔 فكّر مرة أخرى في هذا المفهوم:\n"
            f"💡 {explanation}\n\n"
            f"💪 لا تيأس، استمر!"
        )

    session["current"] += 1

    # شروط الإنهاء: حقق السلسلة المطلوبة، أو وصل للحد الأقصى
    streak_achieved = session["streak"] >= required
    max_reached = session["current"] >= max_q
    out_of_questions = session["current"] >= len(session["questions"])

    if streak_achieved or max_reached or out_of_questions:
        await _finish_quiz(cb, tid, feedback)
    else:
        kb = InlineKeyboardBuilder()
        kb.button(text="➡️ السؤال التالي", callback_data="quiz_next")
        await cb.message.edit_text(feedback, reply_markup=kb.as_markup())
        await cb.answer()


@router.callback_query(F.data == "quiz_next")
async def quiz_next(cb: CallbackQuery):
    tid = str(cb.from_user.id)
    await _show_question(cb, tid)


async def _finish_quiz(cb: CallbackQuery, tid: str, last_feedback: str):
    """إنهاء الكويز وعرض النتيجة."""
    session = _quiz_sessions.get(tid)
    if not session:
        return

    correct = session["correct"]
    total = session["current"]  # عدد الأسئلة المُجاب عليها فعلياً
    lesson_id = session["lesson_id"]
    required = session.get("required_streak", 3)
    final_streak = session["streak"]

    # النجاح = حقق السلسلة المطلوبة
    passed_streak = final_streak >= required

    # نحفظ في DB: المرور إذا حقق السلسلة
    passed_db, score = finish_quiz_attempt(
        session["attempt_id"], correct, total, session["answers"]
    )
    passed = passed_streak  # نتجاوز معيار الـ DB القديم

    score_pct = round((correct / total) * 100) if total > 0 else 0
    if passed:
        result_msg = (
            f"🎉 مبروك! نجحت في الكويز\n\n"
            f"🏆 حققت {required} إجابات متتالية صحيحة!\n"
            f"📊 إجمالي: {correct}/{total} ({score_pct}%)\n"
            f"✅ تم فتح الدرس التالي\n"
            f"⏰ القفل اليومي: 24 ساعة (باقة مجانية)\n\n"
            f"💪 استمر في التقدم!"
        )
    else:
        # تسجيل رسوب وحساب وقت الانتظار
        fail_info = register_failed_attempt(tid, lesson_id)
        wait_time_str = format_cooldown_time(fail_info["wait_seconds"])

        # المفاهيم التي أخطأ فيها
        wrong_concepts = []
        for ans in session["answers"]:
            if not ans["is_correct"]:
                wrong_concepts.append(f"   ❌ {ans['q_id']}")

        concepts_text = ""
        if wrong_concepts:
            concepts_text = "\n📚 أسئلة أخطأت فيها:\n" + "\n".join(wrong_concepts[:3])

        result_msg = (
            f"📝 لم تحقق السلسلة المطلوبة\n\n"
            f"🎯 المطلوب: {required} إجابات متتالية\n"
            f"📊 أفضل سلسلة وصلت لها: {final_streak}\n"
            f"📈 إجمالي الصحيح: {correct}/{total} ({score_pct}%)"
            f"{concepts_text}\n\n"
            f"⏰ المحاولة التالية بعد: {wait_time_str}\n"
            f"{fail_info['motivation']}\n\n"
            f"💡 استرح وراجع الدرس — ستحصل على أسئلة جديدة!"
        )
    full_text = f"{last_feedback}\n\n{'═' * 25}\n\n{result_msg}"

    # عرض ملخص الإجابات الصحيحة عند النجاح فقط
    if passed:
        summary_lines = ["\n\n📖 ملخص الإجابات الصحيحة:"]
        for i, ans in enumerate(session["answers"], 1):
            mark = "✅" if ans["is_correct"] else "❌"
            summary_lines.append(f"  {mark} س{i}: الإجابة = {ans['correct']}")
        full_text += "\n".join(summary_lines)

    # إذا نجح: تحديث XP + قفل 24 ساعة + ترقية المرحلة
    promotion_msg = ""
    if passed:
        # تحقق: هل هذه أول مرة ينجح فيها بهذا الدرس؟
        # نتفقد المحاولات السابقة قبل الحالية
        conn = _db()
        try:
            prev_passed = conn.execute("""
                SELECT COUNT(*) FROM lesson_attempts
                WHERE telegram_id = ? AND lesson_id = ? AND passed = 1 AND id < ?
            """, (tid, lesson_id, session["attempt_id"])).fetchone()[0]
        finally:
            conn.close()

        if prev_passed == 0:  # أول نجاح
            # حساب عدد المحاولات الفاشلة قبل النجاح
            cd_info = get_cooldown_status(tid, lesson_id)
            persistence_attempts = cd_info.get("failed_attempts", 0)

            try:
                add_xp(tid, XP_PER_LESSON, reason=f"lesson_{lesson_id}_complete")
            except Exception as e:
                logger.error(f"add_xp failed: {e}")

            # مكافأة المثابرة (10 XP لكل محاولة فاشلة، حتى 30 XP)
            if persistence_attempts >= 1:
                bonus = min(persistence_attempts * 10, 30)
                try:
                    add_xp(tid, bonus, reason=f"persistence_bonus_lesson_{lesson_id}")
                    promotion_msg_extra = f"\n🏅 مكافأة المثابرة: +{bonus} XP (بعد {persistence_attempts} محاولات)"
                except Exception:
                    promotion_msg_extra = ""
            else:
                promotion_msg_extra = ""

            clear_cooldown(tid, lesson_id)
            mark_lesson_completed_now(tid)

            # تحديث stage_progress
            student = get_student(tid)
            stage_id = student["current_stage_id"]
            new_count = update_stage_progress(tid, stage_id)

            promotion_msg = f"\n\n⭐ +{XP_PER_LESSON} XP{promotion_msg_extra}\n📊 تقدم المرحلة: {new_count}/{LESSONS_PER_STAGE}"

            # ترقية إذا اكتملت المرحلة
            if new_count >= LESSONS_PER_STAGE:
                next_id = get_next_stage_id(stage_id)
                if next_id:
                    promote_to_next_stage(tid, next_id)
                    next_stage = get_stage(next_id)
                    promotion_msg += (
                        f"\n\n🎊 مبروك! أكملت المرحلة!\n"
                        f"➡️ المرحلة التالية: {next_stage['code']} - {next_stage['name_ar']}"
                    )
                else:
                    promotion_msg += "\n\n🏆 لقد أكملت جميع المراحل!"

    full_text += promotion_msg

    kb = InlineKeyboardBuilder()
    if not passed:
        kb.button(text="🔄 أعد المحاولة", callback_data=f"quiz_start:{lesson_id}")
    kb.button(text="📚 العودة للدروس", callback_data="menu_lessons")
    kb.button(text="🏠 القائمة الرئيسية", callback_data="back_main")
    kb.adjust(1)

    await cb.message.edit_text(full_text, reply_markup=kb.as_markup())
    await cb.answer()

    # تنظيف الجلسة
    _quiz_sessions.pop(tid, None)