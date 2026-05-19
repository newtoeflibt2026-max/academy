# -*- coding: utf-8 -*-
from aiogram import types, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database_v2 import (
    create_student, get_student, update_streak,
    get_skills_progress, check_graduation,
    get_setting, get_daily_missions, get_leaderboard
)
import logging, sqlite3, os

logger = logging.getLogger(__name__)
router = Router(name="start")

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "academy.db")
)


def get_main_keyboard(is_paid: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📚 دروسي", callback_data="menu_lessons"),
            InlineKeyboardButton(text="🎯 مهامي اليومية", callback_data="menu_missions"),
        ],
        [
            InlineKeyboardButton(text="📊 تقدمي", callback_data="menu_progress"),
            InlineKeyboardButton(text="🏆 المتصدرون", callback_data="menu_leaderboard"),
        ],
        [
            InlineKeyboardButton(text="✍️ تدريب الكتابة", callback_data="menu_writing"),
            InlineKeyboardButton(text="🎧 تدريب الاستماع", callback_data="menu_listening"),
        ],
        [
            InlineKeyboardButton(text="💳 الباقات والاشتراك", callback_data="menu_subscriptions"),
        ],
        [
            InlineKeyboardButton(text="🔬 امتحان تحديد المستوى", callback_data="start_placement"),
        ],
    ]
    if is_paid:
        buttons.append([
            InlineKeyboardButton(text="📝 Mock Exam", callback_data="menu_mock"),
            InlineKeyboardButton(text="🎓 التخرج", callback_data="menu_graduation"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="🔒 Mock Exam (مدفوع فقط)", callback_data="locked_feature"),
        ])
    buttons.append([InlineKeyboardButton(text="⚙️ إعداداتي", callback_data="menu_settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""

    create_student(user_id, username=username, full_name=full_name)
    student = get_student(user_id)
    streak = update_streak(user_id)

    welcome_msg = get_setting(
        "bot_welcome_message",
        "مرحباً بك في أكاديمية يامن للتوفل! 🎓"
    )
    is_paid = bool(student.get("is_paid", 0)) if student else False
    xp = student.get("xp", 0) if student else 0
    level = student.get("level", "beginner") if student else "beginner"
    placement_done = student.get("placement_done", 0) if student else 0
    level_ar = {
        "beginner": "مبتدئ 🔵",
        "intermediate": "متوسط 🟡",
        "advanced": "متقدم 🟢"
    }.get(level, level)

    text = (
        f"{welcome_msg}\n\n"
        f"👤 <b>{full_name}</b>\n"
        f"⭐ XP: {xp} | 🔥 Streak: {streak} أيام | 📈 {level_ar}\n"
    )
    if is_paid:
        text += "✅ حساب مفعّل\n"
    else:
        text += "⚠️ حساب مجاني — بعض الميزات مقفلة\n"
    if not placement_done:
        text += "\n💡 <b>ننصحك بإجراء امتحان تحديد المستوى أولاً!</b>"
    text += "\n\nاختر من القائمة:"

    await message.answer(
        text,
        reply_markup=get_main_keyboard(is_paid),
        parse_mode="HTML"
    )


# ── الدروس ──────────────────────────────────────────────
@router.callback_query(F.data == "menu_lessons")
async def callback_lessons(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    student = get_student(user_id)
    level = (student.get("level", "beginner") if student else "beginner")

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM lessons WHERE is_active=1 ORDER BY stage, order_num LIMIT 10"
        ).fetchall()
        conn.close()
        lessons = [dict(r) for r in rows]
    except Exception as e:
        lessons = []
        logger.error(f"lessons error: {e}")

    if not lessons:
        await callback.message.answer(
            "📚 <b>الدروس</b>\n\nلا توجد دروس متاحة حالياً.\nسيتم إضافة المحتوى قريباً! 🚀",
            parse_mode="HTML"
        )
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    for lesson in lessons:
        title = lesson.get("title", "درس")
        lid = lesson.get("id", 0)
        skill = lesson.get("skill_type", "")
        emoji = {"reading": "📖", "listening": "🎧", "speaking": "🗣️",
                 "writing": "✍️", "grammar": "📝", "vocabulary": "📚"}.get(skill, "📌")
        kb.button(text=f"{emoji} {title}", callback_data=f"lesson:{lid}")
    kb.button(text="🏠 رجوع", callback_data="menu_main")
    kb.adjust(1)

    await callback.message.answer(
        f"📚 <b>الدروس المتاحة</b>\nمستواك: <b>{level}</b>\n\nاختر درساً:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("lesson:"))
async def callback_lesson_detail(callback: types.CallbackQuery):
    await callback.answer()
    lid = int(callback.data.split(":")[1])
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        lesson = conn.execute(
            "SELECT * FROM lessons WHERE id=?", (lid,)
        ).fetchone()
        conn.close()
        lesson = dict(lesson) if lesson else None
    except Exception as e:
        lesson = None
        logger.error(f"lesson detail error: {e}")

    if not lesson:
        await callback.message.answer("❌ الدرس غير موجود")
        return

    skill_emoji = {"reading": "📖", "listening": "🎧", "speaking": "🗣️",
                   "writing": "✍️", "grammar": "📝", "vocabulary": "📚"}.get(
        lesson.get("skill_type", ""), "📌"
    )
    text = (
        f"{skill_emoji} <b>{lesson.get('title', '')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{lesson.get('description') or lesson.get('content', 'لا يوجد محتوى بعد')}\n\n"
    )
    vocab = lesson.get("vocabulary", "")
    if vocab:
        text += f"📝 <b>المفردات:</b>\n{vocab}\n\n"
    grammar = lesson.get("grammar_rule", "")
    if grammar:
        text += f"📐 <b>القاعدة:</b>\n{grammar}\n\n"
    text += f"🎁 إتمام هذا الدرس = <b>{lesson.get('xp_reward', 20)} XP</b>"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ إتمام الدرس", callback_data=f"complete_lesson:{lid}")
    kb.button(text="🔙 رجوع للدروس", callback_data="menu_lessons")
    kb.adjust(1)

    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("complete_lesson:"))
async def callback_complete_lesson(callback: types.CallbackQuery):
    await callback.answer()
    lid = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    try:
        conn = sqlite3.connect(DB_PATH)
        xp_reward = conn.execute(
            "SELECT xp_reward FROM lessons WHERE id=?", (lid,)
        ).fetchone()
        xp_reward = xp_reward[0] if xp_reward else 20
        conn.close()
        from database_v2 import add_xp
        add_xp(user_id, xp_reward, "reading", f"lesson_{lid}")
    except Exception as e:
        logger.error(f"complete_lesson error: {e}")
        xp_reward = 20

    await callback.message.answer(
        f"🎉 أحسنت! أتممت الدرس\n🎁 ربحت <b>{xp_reward} XP</b>!",
        parse_mode="HTML"
    )


# ── الباقات ──────────────────────────────────────────────
@router.callback_query(F.data == "menu_subscriptions")
async def callback_subscriptions(callback: types.CallbackQuery):
    await callback.answer()
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cols = [r[1] for r in conn.execute(
            "PRAGMA table_info(subscription_plans)"
        ).fetchall()]
        name_col = "name_ar" if "name_ar" in cols else "plan_name"
        key_col = "plan_key" if "plan_key" in cols else "plan_id"
        rows = conn.execute(
            f"SELECT * FROM subscription_plans WHERE is_active=1 ORDER BY price"
        ).fetchall()
        conn.close()
        plans = [dict(r) for r in rows]
    except Exception as e:
        plans = []
        logger.error(f"plans error: {e}")

    if not plans:
        await callback.message.answer(
            "💳 لا توجد باقات متاحة حالياً.\nتواصل مع الأدمن: @YamenAdmin",
            parse_mode="HTML"
        )
        return

    text = "💳 <b>باقات الاشتراك</b>\n\nاختر الباقة المناسبة لك:\n━━━━━━━━━━━━━━━━━━\n\n"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()

    for p in plans:
        name = p.get("name_ar") or p.get("plan_name", "باقة")
        price = p.get("price", 0)
        days = p.get("duration_days") or p.get("days", 30)
        speed = p.get("lessons_per_day") or p.get("speed", 1)
        desc = p.get("description", "")
        key = p.get("plan_key") or p.get("plan_id", str(p.get("id")))
        emoji = p.get("emoji", "📚")

        text += (
            f"{emoji} <b>{name}</b>\n"
            f"💰 السعر: {price:,} دينار\n"
            f"📅 المدة: {days} يوم\n"
            f"📖 {speed} درس/يوم\n"
            f"📝 {desc}\n"
            f"━━━━━━━━━━━━\n\n"
        )
        kb.button(text=f"{emoji} اشترك — {name}", callback_data=f"subscribe:{key}")

    kb.button(text="🏠 رجوع", callback_data="menu_main")
    kb.adjust(1)

    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("subscribe:"))
async def callback_subscribe(callback: types.CallbackQuery):
    await callback.answer()
    plan_key = callback.data.split(":")[1]
    user_id = callback.from_user.id
    text = (
        f"💳 <b>طلب اشتراك</b>\n\n"
        f"الباقة: <b>{plan_key}</b>\n\n"
        f"للتفعيل تواصل مع الأدمن:\n"
        f"📱 @YamenAdmin\n\n"
        f"أرسل له:\n"
        f"1. اسمك الكامل\n"
        f"2. رقم هاتفك\n"
        f"3. اسم الباقة: <code>{plan_key}</code>\n"
        f"4. معرفك: <code>{user_id}</code>"
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="📱 تواصل مع الأدمن", url="https://t.me/YamenAdmin")
    kb.button(text="🔙 رجوع للباقات", callback_data="menu_subscriptions")
    kb.adjust(1)
    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


# ── الرجوع للرئيسية ──────────────────────────────────────
@router.callback_query(F.data == "menu_main")
async def callback_main(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    student = get_student(user_id)
    is_paid = bool(student.get("is_paid", 0)) if student else False
    full_name = callback.from_user.full_name or ""
    xp = student.get("xp", 0) if student else 0
    streak = student.get("streak", 0) if student else 0
    level = student.get("level", "beginner") if student else "beginner"
    level_ar = {
        "beginner": "مبتدئ 🔵",
        "intermediate": "متوسط 🟡",
        "advanced": "متقدم 🟢"
    }.get(level, level)
    text = (
        f"🏠 <b>القائمة الرئيسية</b>\n\n"
        f"👤 {full_name}\n"
        f"⭐ XP: {xp} | 🔥 Streak: {streak} | 📈 {level_ar}\n\n"
        f"اختر من القائمة:"
    )
    await callback.message.answer(
        text,
        reply_markup=get_main_keyboard(is_paid),
        parse_mode="HTML"
    )


# ── باقي الـ callbacks ───────────────────────────────────
@router.callback_query(F.data == "locked_feature")
async def callback_locked(callback: types.CallbackQuery):
    msg = get_setting(
        "paid_required_message",
        "هذه الميزة مخصصة للمشتركين في الباقات المدفوعة فقط.\nيرجى تفعيل اشتراكك عبر التواصل مع الإدارة."
    )
    await callback.answer(msg, show_alert=True)


@router.callback_query(F.data == "menu_graduation")
async def callback_graduation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    student = get_student(user_id)
    if not student or not student.get("is_paid"):
        await callback.answer(
            "هذه الميزة مخصصة للمشتركين في الباقات المدفوعة فقط.",
            show_alert=True
        )
        return
    result = check_graduation(user_id)
    checks_text = "\n".join(c["message"] for c in result.get("checks", []))
    if result.get("eligible"):
        text = f"🎓 <b>أهلاً بك في التخرج!</b>\n\n{checks_text}\n\n✅ أنت مؤهل! تواصل مع الأدمن."
    else:
        text = f"🎓 <b>شروط التخرج:</b>\n\n{checks_text}\n\n❌ لم تستوفِ الشروط بعد."
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "menu_progress")
async def callback_progress(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    student = get_student(user_id)
    if not student:
        await callback.message.answer("❌ سجّل أولاً بـ /start")
        return
    skills = get_skills_progress(user_id)
    text = (
        f"📊 <b>تقدمك في الأكاديمية</b>\n\n"
        f"⭐ إجمالي XP: {student.get('xp', 0)}\n"
        f"🔥 Streak: {student.get('streak', 0)} أيام\n"
        f"✅ مهام مكتملة: {student.get('missions_completed', 0)}\n"
        f"🎯 درجة الـ Placement: {student.get('placement_score', 0)}%\n\n"
        f"<b>المهارات:</b>\n"
        f"📖 القراءة: {skills.get('reading_xp', 0)} XP\n"
        f"🎧 الاستماع: {skills.get('listening_xp', 0)} XP\n"
        f"🗣️ التحدث: {skills.get('speaking_xp', 0)} XP\n"
        f"✍️ الكتابة: {skills.get('writing_xp', 0)} XP\n"
    )
    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "menu_leaderboard")
async def callback_leaderboard(callback: types.CallbackQuery):
    await callback.answer()
    leaders = get_leaderboard(10)
    if not leaders:
        await callback.message.answer("📊 لا توجد بيانات بعد")
        return
    text = "🏆 <b>المتصدرون:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    for i, s in enumerate(leaders):
        name = s.get("full_name") or s.get("username") or f"طالب_{i+1}"
        text += f"{medals[i]} {name} — {s.get('xp', 0)} XP\n"
    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "menu_missions")
async def callback_missions(callback: types.CallbackQuery):
    await callback.answer()
    from datetime import date
    today = date.today().isoformat()
    missions = get_daily_missions(today)
    if not missions:
        missions = get_daily_missions()
    if not missions:
        await callback.message.answer(
            "📋 <b>المهام اليومية</b>\n\nلا توجد مهام اليوم.\nتابع الأكاديمية لمهام جديدة! 🚀",
            parse_mode="HTML"
        )
        return
    text = "🎯 <b>المهام اليومية:</b>\n\n"
    for m in missions[:5]:
        text += f"• {m['title']} (+{m.get('xp_reward', 0)} XP)\n  {m.get('description', '')}\n\n"
    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "menu_settings")
async def callback_settings(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    student = get_student(user_id)
    if not student:
        await callback.message.answer("❌ سجّل أولاً بـ /start")
        return
    text = (
        f"⚙️ <b>إعداداتك</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 الاسم: {student.get('full_name', '—')}\n"
        f"📱 الهاتف: {student.get('phone', 'غير مسجل')}\n"
        f"💳 النوع: {'مدفوع ✅' if student.get('is_paid') else 'مجاني ⚠️'}\n"
        f"🎯 المستوى: {student.get('level', 'beginner')}\n\n"
        f"للاشتراك أو الدعم: @YamenAdmin"
    )
    await callback.message.answer(text, parse_mode="HTML")
