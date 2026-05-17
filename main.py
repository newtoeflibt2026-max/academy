# في handlers/start.py — استبدل show_main_menu بهذا

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import WEBHOOK_HOST   # رابط الموقع المنشور

async def show_main_menu(message, uid: int):
    from database import get_student, has_active_subscription

    student   = get_student(uid)
    has_place = student and student.get("placement_done")
    has_sub   = has_active_subscription(uid)

    # ── رابط الـ Mini App مع هوية الطالب
    webapp_url = f"{WEBHOOK_HOST}/dashboard?student_id={uid}"

    rows = []

    if not has_place:
        # ← اختبار التشخيص
        rows.append([InlineKeyboardButton(
            text="📝 اختبار تحديد المستوى — مجاني",
            web_app=WebAppInfo(url=f"{WEBHOOK_HOST}/placement?student_id={uid}")
        )])
        rows.append([InlineKeyboardButton(
            text="💎 الباقات والاشتراكات",
            callback_data="menu_subscribe"
        )])

    elif not has_sub:
        rows.append([InlineKeyboardButton(
            text="📊 نتيجتي ← اشترك للمتابعة",
            web_app=WebAppInfo(url=webapp_url)
        )])
        rows.append([InlineKeyboardButton(
            text="💎 اشترك الآن",
            callback_data="menu_subscribe"
        )])

    else:
        # ← المستخدم المفعَّل — الزر الرئيسي يفتح الـ Dashboard
        rows.append([InlineKeyboardButton(
            text="🚀 افتح لوحة التحكم",
            web_app=WebAppInfo(url=webapp_url)
        )])
        rows.append([
            InlineKeyboardButton(text="⚡ تحدي 60 ثانية", callback_data="daily_challenge"),
            InlineKeyboardButton(text="🔬 بنك الأخطاء",   callback_data="error_bank_review"),
        ])
        rows.append([InlineKeyboardButton(text="📊 تقدمي السريع", callback_data="my_progress")])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    lvl = student.get("level","—") if student else "—"
    status = (
        "🔵 أهلاً! ابدأ باختبار المستوى" if not has_place else
        f"🟡 مستواك: *{lvl}* · اشترك للمتابعة" if not has_sub else
        f"✅ مستواك: *{lvl}* · مرحباً بعودتك!"
    )

    name = message.from_user.first_name if hasattr(message, 'from_user') else "طالب"
    await message.answer(
        f"🦅 *أكاديمية يامن* — TOEFL\n\n"
        f"مرحباً *{name}*\n"
        f"{status}",
        reply_markup=kb,
        parse_mode="Markdown"
    )
