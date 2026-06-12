# -*- coding: utf-8 -*-
from aiogram import types, Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from database_v2 import (
    create_student, get_student, update_streak,
    get_skills_progress, check_graduation,
    get_setting, get_daily_missions, get_leaderboard
)
from config import settings
import logging, sqlite3, os
from datetime import datetime

# ─── Safe edit helper ───
async def _safe_edit(message, text, reply_markup=None):
    """يتجاهل خطأ 'message is not modified' عند تعديل رسالة بنفس المحتوى."""
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass  # تجاهل بصمت
        else:
            raise


logger = logging.getLogger(__name__)
router = Router(name="start")

DB_PATH = settings.DB_PATH
WEBAPP_BASE = settings.WEBHOOK_HOST.rstrip("/")


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _save_track_and_target(user_id, track=None, target_score=None):
    conn = _db()
    cur = conn.cursor()
    updates, params = [], []
    if track:
        updates.append("track=?"); params.append(track)
    if target_score is not None:
        updates.append("target_score=?"); params.append(int(target_score))
    if updates:
        cur.execute("SELECT signup_date FROM students WHERE telegram_id=?", (user_id,))
        row = cur.fetchone()
        if row and not row["signup_date"]:
            updates.append("signup_date=?")
            params.append(datetime.now().isoformat(timespec="seconds"))
        params.append(user_id)
        cur.execute(f"UPDATE students SET {','.join(updates)} WHERE telegram_id=?", params)
        conn.commit()
    conn.close()


def _get_student_setup(user_id):
    conn = _db()
    cur = conn.cursor()
    cur.execute("""SELECT track, target_score, placement_done, placement_score,
                          placement_path, current_stage_id, is_paid
                   FROM students WHERE telegram_id=?""", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {}
    return dict(row)


def kb_choose_track():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 TOEFL iBT الدولي", callback_data="track:toefl")],
        [InlineKeyboardButton(text="🔒 IELTS — قريباً", callback_data="track:soon")],
        [InlineKeyboardButton(text="🔒 SAT — قريباً", callback_data="track:soon")],
        [InlineKeyboardButton(text="🔒 GRE — قريباً", callback_data="track:soon")],
    ])


def kb_choose_target():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥉 59 — جامعات أساسية", callback_data="target:59")],
        [InlineKeyboardButton(text="🥈 69 — جامعات متوسطة", callback_data="target:69")],
        [InlineKeyboardButton(text="🥇 90 — جامعات مرموقة", callback_data="target:90")],
        [InlineKeyboardButton(text="↩️ رجوع لاختيار المسار", callback_data="back:track")],
    ])


def kb_start_placement(user_id):
    webapp_url = f"{settings.WEBHOOK_HOST}/student?student_id={user_id}&mode=placement"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔬 ابدأ اختبار تحديد المستوى", web_app=WebAppInfo(url=webapp_url))],
        [InlineKeyboardButton(text="↩️ تغيير العلامة المستهدفة", callback_data="back:target")],
    ])


def get_main_keyboard(is_paid=False, user_id=0):
    base = settings.WEBHOOK_HOST.rstrip("/")
    def wa(path):
        sep = "&" if "?" in path else "?"
        return WebAppInfo(url=f"{base}{path}{sep}user_id={user_id}&student_id={user_id}")
    buttons = [
        [InlineKeyboardButton(text="🛠️ التأسيس الشامل", web_app=wa("/foundation"))],
        [InlineKeyboardButton(text="🔖 دفتر أخطائي", web_app=wa("/mistakes"))],
        [InlineKeyboardButton(text="📖 القراءة", web_app=wa("/reading/")),
         InlineKeyboardButton(text="🎧 الاستماع", web_app=wa("/listening"))],
        [InlineKeyboardButton(text="✍️ الكتابة", web_app=wa("/writing")),
         InlineKeyboardButton(text="🗣️ المحادثة", web_app=wa("/speaking"))],
        [InlineKeyboardButton(text="🏠 الرئيسية", web_app=wa("/home")),
         InlineKeyboardButton(text="📊 لوحتي", web_app=wa("/student"))],
        [InlineKeyboardButton(text="💳 الباقات والاشتراك", web_app=wa("/miniapp/plans"))],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""

    create_student(user_id, username=username, full_name=full_name)
    student = get_student(user_id) or {}
    streak = update_streak(user_id)
    setup = _get_student_setup(user_id) or {}

    welcome_msg = get_setting("bot_welcome_message", "أهلاً بك في أكاديمية يامن! 🎓")
    is_paid = bool(student.get("is_paid", 0))
    xp = student.get("xp", 0)
    level = student.get("level", "beginner")
    target = setup.get("target_score") or 0
    target_txt = f"<b>{target}</b>" if target else "<i>غير محدد</i>"
    level_ar = {"beginner":"مبتدئ 🔵","intermediate":"متوسط 🟡","advanced":"متقدم 🟢"}.get(level, level)
    paid_badge = "👑 مشترك" if is_paid else "🆓 مجاني"

    text = (
        f"{welcome_msg}\n\n"
        f"👤 <b>{full_name}</b> | {paid_badge}\n"
        f"⭐ XP: {xp} | 🔥 Streak: {streak} | 📈 {level_ar}\n"
        f"🎯 الهدف: {target_txt}\n\n"
        "اختر من القائمة 👇"
    )
    await message.answer(text, reply_markup=get_main_keyboard(is_paid, user_id=user_id))


@router.callback_query(F.data == "track:toefl")
async def cb_track_toefl(callback: types.CallbackQuery):
    await callback.answer("✅ تم اختيار TOEFL iBT")
    user_id = callback.from_user.id
    _save_track_and_target(user_id, track="toefl")

    text = (
        "🎯 <b>تم اختيار TOEFL iBT الدولي</b> ✅\n\n"
        "الآن حدد <b>العلامة المستهدفة</b>:\n\n"
        "🥉 <b>59</b> — تكفي للقبول في معظم الجامعات الأساسية\n"
        "🥈 <b>69</b> — مطلوبة في الجامعات المتوسطة والبرامج التخصصية\n"
        "🥇 <b>90</b> — للجامعات المرموقة وبرامج المنح\n\n"
        "💡 كلما كان هدفك أعلى، كانت بوابة Mock النهائية أعلى."
    )
    await _safe_edit(callback.message, text, reply_markup=kb_choose_target())


@router.callback_query(F.data == "track:soon")
async def cb_track_soon(callback: types.CallbackQuery):
    await callback.answer("⏳ هذا المسار سيُفتح قريباً — تابعنا!", show_alert=True)


@router.callback_query(F.data.startswith("target:"))
async def cb_target(callback: types.CallbackQuery):
    try:
        target = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ خيار غير صالح", show_alert=True)
        return
    if target not in (59, 69, 90):
        await callback.answer("❌ علامة غير مسموحة", show_alert=True)
        return

    user_id = callback.from_user.id
    _save_track_and_target(user_id, track="toefl", target_score=target)
    await callback.answer(f"✅ هدفك: {target}")

    mock_gate = target + 10
    text = (
        f"🎯 <b>تم تثبيت هدفك: {target}</b> في TOEFL iBT ✅\n\n"
        f"📊 <b>بوابة التخرج في Mock Exam: {mock_gate} من 120</b>\n\n"
        "🔬 <b>الخطوة التالية: اختبار تحديد المستوى</b>\n"
        "• 10 أسئلة سريعة (حوالي 10 دقائق)\n"
        "• نتيجة أقل من 50 بالمئة تعني مسار التأسيس\n"
        "• نتيجة 50 بالمئة فأكثر تعني TOEFL مباشرة\n\n"
        "اضغط الزر لبدء الاختبار 👇"
    )
    await _safe_edit(callback.message, text, reply_markup=kb_start_placement(user_id))


@router.callback_query(F.data == "back:track")
async def cb_back_track(callback: types.CallbackQuery):
    await callback.answer()
    full_name = callback.from_user.full_name or ""
    text = (
        f"مرحباً يا <b>{full_name}</b>! 🎓\n\n"
        "🚀 <b>اختر المسار:</b>\n\n"
        "🎯 TOEFL iBT الدولي — متاح الآن\n"
        "🔒 IELTS و SAT و GRE — قريباً"
    )
    await _safe_edit(callback.message, text, reply_markup=kb_choose_track())


@router.callback_query(F.data == "back:target")
async def cb_back_target(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "🎯 <b>اختر العلامة المستهدفة</b> في TOEFL iBT:\n\n"
        "🥉 59  •  🥈 69  •  🥇 90"
    )
    await _safe_edit(callback.message, text, reply_markup=kb_choose_target())


@router.message(Command("menu"))
async def cmd_menu(message: types.Message):
    user_id = message.from_user.id
    student = get_student(user_id) or {}
    is_paid = bool(student.get("is_paid", 0))
    await message.answer("📋 القائمة الرئيسية:", reply_markup=get_main_keyboard(is_paid, user_id=user_id))


@router.callback_query(F.data == "locked_feature")
async def cb_locked(callback: types.CallbackQuery):
    await callback.answer("🔒 هذه الميزة متاحة للمشتركين فقط. اشترك من 💳 الباقات", show_alert=True)

# ═══════════════════════════════════════════════════════════
# Universal Menu Handlers - all open WebApp (Wave 7)
# ═══════════════════════════════════════════════════════════
_MENU_BUTTONS_TO_WEBAPP = {
    "menu_lessons": "📚 دروسي",
    "menu_progress": "📊 تقدمي",
    "menu_leaderboard": "🏆 المتصدرون",
    "menu_writing": "✍️ تدريب الكتابة",
    "menu_listening": "🎧 تدريب الاستماع",
    "menu_missions": "🎯 مهامي اليومية",
    "menu_mock": "📝 Mock Exam",
    "menu_graduation": "🎓 التخرج",
    "menu_subscriptions": "💳 الباقات",
    "menu_settings": "⚙️ إعداداتي",
}

@router.callback_query(F.data.in_(list(_MENU_BUTTONS_TO_WEBAPP.keys())))
async def cb_menu_to_webapp(callback: types.CallbackQuery):
    """All menu buttons -> open WebApp."""
    btn_label = _MENU_BUTTONS_TO_WEBAPP.get(callback.data, "البوابة")
    user_id = callback.from_user.id
    webapp_url = f"{settings.WEBHOOK_HOST}/student?student_id={user_id}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🌐 افتح {btn_label}", web_app=WebAppInfo(url=webapp_url))],
        [InlineKeyboardButton(text="↩️ رجوع للقائمة", callback_data="back:menu")],
    ])

    await callback.answer()
    try:
        await callback.message.edit_text(
            f"<b>{btn_label}</b>\n\n"
            "اضغط الزر أدناه لفتح البوابة داخل Telegram 👇\n\n"
            "✨ تجربة سلسة وسريعة بدون مغادرة المحادثة.",
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.warning(f"cb_menu_to_webapp edit failed: {e}")
        await callback.message.answer(
            f"<b>{btn_label}</b>\n\nاضغط الزر أدناه لفتح البوابة 👇",
            reply_markup=kb,
            parse_mode="HTML"
        )


@router.callback_query(F.data == "back:menu")
async def cb_back_to_main_menu(callback: types.CallbackQuery):
    """Return to main menu."""
    await callback.answer()
    user_id = callback.from_user.id
    student = _get_student_setup(user_id)
    is_paid = student.get("is_paid", False) if student else False

    try:
        await callback.message.edit_text(
            "🎓 <b>القائمة الرئيسية</b>\n\nاختر من القائمة:",
            reply_markup=get_main_keyboard(is_paid=is_paid, user_id=user_id),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.warning(f"cb_back_to_main_menu edit failed: {e}")
