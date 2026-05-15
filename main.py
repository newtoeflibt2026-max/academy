# main.py - Yamen Academy LMS Bot (Aiogram 3 + Scheduler)
import asyncio, logging, sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramConflictError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, ADMIN_IDS
from database import (
    init_db, get_db_connection, get_conn, get_stats, get_all_students,
    toggle_student_active, get_pending_payments, update_payment_status,
    add_subscription, add_payment, get_admin_setting, set_admin_setting,
    get_leaderboard, add_xp, upsert_student, log_activity, get_absent_students,
    add_to_error_bank, get_due_reviews, record_correct_review
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    logger.critical("❌ BOT_TOKEN not set!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# ===================== FSM STATES =====================

class AddCourse(StatesGroup):
    waiting_name = State()
    waiting_level = State()
    waiting_skill = State()
    waiting_price = State()
    waiting_duration = State()
    waiting_time_limit = State()
    waiting_target_score = State()
    waiting_template = State()

class AddVault(StatesGroup):
    waiting_title = State()
    waiting_content = State()
    waiting_category = State()
    waiting_unlock_level = State()

class AddQuestion(StatesGroup):
    waiting_course = State()
    waiting_lesson = State()
    waiting_question = State()
    waiting_answer = State()
    waiting_skill = State()

class ChallengeBuilder(StatesGroup):
    waiting_skill_type = State()
    waiting_time_limit = State()
    waiting_target = State()

# ===================== HELPERS =====================

def is_admin(uid):
    return uid in ADMIN_IDS

def admin_only(f):
    async def wrapper(message: Message, *args, **kwargs):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ مخصص للمسؤولين فقط.")
            return
        return await f(message, *args, **kwargs)
    return wrapper

def build_admin_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 إحصائيات", callback_data="admin_stats")
    kb.button(text="📚 الدورات", callback_data="admin_courses")
    kb.button(text="👥 الطلاب", callback_data="admin_students")
    kb.button(text="💰 المدفوعات", callback_data="admin_payments")
    kb.button(text="🗄️ الخزنة", callback_data="admin_vault")
    kb.button(text="⚙️ إعدادات", callback_data="admin_settings")
    kb.button(text="🎮 التحديات", callback_data="admin_challenges")
    kb.button(text="➕ إضافة دورة", callback_data="admin_add_course")
    kb.button(text="➕ إضافة للخزنة", callback_data="admin_add_vault")
    kb.adjust(2, 2, 2, 2, 2)
    return kb.as_markup()

# ===================== BASIC HANDLERS =====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    upsert_student(uid, message.from_user.username or "", message.from_user.first_name or "")
    log_activity(uid, "start")
    await message.answer(
        f"👋 أهلاً {message.from_user.first_name or 'مستخدم'}!\n"
        f"🆔 `{uid}`\n\n"
        f"📋 الأوامر:\n/help | /leaderboard | /profile | /review",
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("🎓 **أكاديمية يامن**\n/leaderboard | /profile | /review | /admin", parse_mode="Markdown")

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    uid = message.from_user.id
    conn = get_db_connection()
    try:
        s = conn.execute("SELECT * FROM students WHERE user_id=?", (uid,)).fetchone()
        if s:
            total_courses = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
            completed = conn.execute("SELECT COUNT(DISTINCT course_id) FROM progress WHERE user_id=? AND completed=1", (uid,)).fetchone()[0]
            pct = round(completed / total_courses * 100) if total_courses else 0
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            await message.answer(
                f"👤 **{s['first_name']}**\n"
                f"⭐ XP: {s['xp']} | 🎚️ المستوى: {s['level']}\n"
                f"📊 التقدم: [{bar}] {pct}%\n"
                f"📚 {completed}/{total_courses} دورة",
                parse_mode="Markdown"
            )
    finally:
        conn.close()

@dp.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message):
    lb = get_leaderboard(5)
    if not lb:
        await message.answer("لا يوجد طلاب بعد.")
        return
    text = "🏆 **قائمة الأوائل**:\n\n"
    for i, s in enumerate(lb, 1):
        medal = ["🥇","🥈","🥉","4️⃣","5️⃣"][i-1]
        text += f"{medal} {s['first_name'] or 'طالب'} — {s['xp']} XP\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("review"))
async def cmd_review(message: Message):
    """عرض الأسئلة المستحقة للمراجعة من بنك الأخطاء."""
    uid = message.from_user.id
    reviews = get_due_reviews(uid)
    if not reviews:
        await message.answer("✅ لا توجد أسئلة للمراجعة حالياً. أحسنت!")
        return
    for r in reviews[:5]:
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ صحيح", callback_data=f"correct_{r['id']}")
        kb.button(text="❌ خطأ", callback_data=f"wrong_{r['id']}")
        await message.answer(
            f"🔄 **مراجعة**: {r['question_text']}\n"
            f"إجابتك السابقة: _{r['wrong_answer']}_",
            reply_markup=kb.as_markup(), parse_mode="Markdown"
        )

@dp.callback_query(F.data.startswith("correct_"))
async def on_correct(callback: CallbackQuery):
    bid = int(callback.data.split("_")[1])
    record_correct_review(callback.from_user.id, bid)
    await callback.message.edit_text(callback.message.text + "\n\n✅ **إجابة صحيحة!**", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("wrong_"))
async def on_wrong(callback: CallbackQuery):
    await callback.message.edit_text(callback.message.text + "\n\n❌ حاول مرة أخرى قريباً.")
    await callback.answer()

# ===================== ADMIN PANEL =====================

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    uid = message.from_user.id
    logger.info(f"⚡ /admin from {uid}")
    if uid not in ADMIN_IDS:
        await message.answer(f"⛔ غير مصرح. معرفك: `{uid}`", parse_mode="Markdown")
        return
    update_user_role(uid, "admin")
    await message.answer("👑 **لوحة تحكم المسؤول**", reply_markup=build_admin_menu(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_stats")
async def cb_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return await callback.answer("⛔", show_alert=True)
    stats = get_stats()
    conn = get_conn()
    total_xp = conn.execute("SELECT COALESCE(SUM(xp),0) FROM students").fetchone()[0]
    conn.close()
    await callback.message.edit_text(
        f"📊 **إحصائيات المنصة**\n\n"
        f"👥 الطلاب: {stats['students']}\n"
        f"📚 الدورات: {stats['courses']}\n"
        f"🟢 نشط اليوم: {stats['active_today']}\n"
        f"⭐ مجموع XP: {total_xp}",
        reply_markup=build_admin_menu(), parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_courses")
async def cb_courses(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return await callback.answer("⛔", show_alert=True)
    conn = get_conn()
    courses = conn.execute("SELECT * FROM courses ORDER BY id").fetchall()
    conn.close()
    if not courses:
        await callback.message.edit_text("📚 لا توجد دورات. أضف دورة باستخدام ➕ إضافة دورة.", reply_markup=build_admin_menu())
        return await callback.answer()
    text = "📚 **الدورات الحالية**:\n\n"
    kb = InlineKeyboardBuilder()
    for c in courses:
        text += f"🔹 {c['name']} ({c['level']}) — {c['price']} ريال\n"
        kb.button(text=f"🗑️ {c['name']}", callback_data=f"del_course_{c['id']}")
    kb.adjust(1)
    kb2 = InlineKeyboardBuilder()
    kb2.button(text="🔙 رجوع", callback_data="admin_back")
    kb.attach(kb2)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("del_course_"))
async def cb_del_course(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return await callback.answer("⛔", show_alert=True)
    cid = int(callback.data.split("_")[2])
    conn = get_conn()
    conn.execute("DELETE FROM courses WHERE id=?", (cid,))
    conn.commit(); conn.close()
    await callback.answer("✅ تم الحذف")
    await cb_courses(callback)

@dp.callback_query(F.data == "admin_add_course")
async def cb_add_course(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return await callback.answer("⛔", show_alert=True)

    kb = InlineKeyboardBuilder()
    kb.button(text="🗣️ تحدث 45ث", callback_data="skill_speaking")
    kb.button(text="✍️ إكمال كلمة", callback_data="skill_spelling")
    kb.button(text="📝 ترتيب جمل", callback_data="skill_writing")
    kb.button(text="📧 كتابة إيميل", callback_data="skill_email")
    kb.button(text="🎧 استماع وترديد", callback_data="skill_listening")
    kb.adjust(2, 2, 1)
    await callback.message.edit_text("🎯 اختر نوع المهارة:", reply_markup=kb.as_markup())
    await state.set_state(AddCourse.waiting_skill)
    await callback.answer()

@dp.callback_query(F.data.startswith("skill_"), AddCourse.waiting_skill)
async def cb_skill_selected(callback: CallbackQuery, state: FSMContext):
    skill = callback.data.split("_")[1]
    await state.update_data(skill_type=skill)
    await callback.message.edit_text(f"✅ المهارة: {skill}\n\n📝 أدخل اسم الدورة:")
    await state.set_state(AddCourse.waiting_name)
    await callback.answer()

@dp.message(AddCourse.waiting_name)
async def course_name_entered(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    kb = InlineKeyboardBuilder()
    for lvl in ["beginner", "intermediate", "advanced", "expert"]:
        kb.button(text=lvl.capitalize(), callback_data=f"lvl_{lvl}")
    kb.adjust(2)
    await message.answer("📊 اختر المستوى:", reply_markup=kb.as_markup())
    await state.set_state(AddCourse.waiting_level)

@dp.callback_query(F.data.startswith("lvl_"), AddCourse.waiting_level)
async def cb_level(callback: CallbackQuery, state: FSMContext):
    await state.update_data(level=callback.data.split("_")[1])
    await callback.message.edit_text("💰 أدخل السعر (ريال):")
    await state.set_state(AddCourse.waiting_price)
    await callback.answer()

@dp.message(AddCourse.waiting_price)
async def course_price(message: Message, state: FSMContext):
    try:
        float(message.text)
    except ValueError:
        await message.answer("⚠️ أدخل رقماً صحيحاً:")
        return
    await state.update_data(price=message.text)
    await message.answer("📅 عدد الأيام:")
    await state.set_state(AddCourse.waiting_duration)

@dp.message(AddCourse.waiting_duration)
async def course_duration(message: Message, state: FSMContext):
    await state.update_data(duration=message.text)
    await message.answer("⏱️ الوقت المحدد (بالثواني):")
    await state.set_state(AddCourse.waiting_time_limit)

@dp.message(AddCourse.waiting_time_limit)
async def course_timelimit(message: Message, state: FSMContext):
    await state.update_data(time_limit=message.text)
    await message.answer("🎯 الهدف (الدرجة المطلوبة: 59، 69، أو 90):")
    await state.set_state(AddCourse.waiting_target_score)

@dp.message(AddCourse.waiting_target_score)
async def course_target(message: Message, state: FSMContext):
    data = await state.get_data()
    conn = get_conn()
    conn.execute("""
        INSERT INTO courses (name, level, skill_type, price, duration_days, time_limit, target_score)
        VALUES (?,?,?,?,?,?,?)
    """, (data['name'], data['level'], data['skill_type'], data['price'], data['duration'], data['time_limit'], message.text))
    conn.commit(); conn.close()
    await message.answer(f"✅ تمت إضافة **{data['name']}** بنجاح!", parse_mode="Markdown", reply_markup=build_admin_menu())
    await state.clear()

@dp.callback_query(F.data == "admin_students")
async def cb_students(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return await callback.answer("⛔")
    students = get_all_students()
    text = "👥 **الطلاب**:\n\n"
    for s in students[:15]:
        status = "🟢" if s['is_active'] else "🔴"
        text += f"{status} {s['first_name'] or '---'} ({s['user_id']}) — {s['xp']} XP\n"
    await callback.message.edit_text(text, reply_markup=build_admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "admin_payments")
async def cb_payments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return await callback.answer("⛔")
    payments = get_pending_payments()
    if not payments:
        await callback.message.edit_text("💰 لا توجد مدفوعات معلقة.", reply_markup=build_admin_menu())
        return await callback.answer()
    text = "💰 المدفوعات المعلقة:\n"
    kb = InlineKeyboardBuilder()
    for p in payments:
        text += f"• #{p['id']} | {p['user_id']} | {p['plan_name']} | {p['amount']} ريال\n"
        kb.button(text=f"✅ الموافقة #{p['id']}", callback_data=f"approve_{p['id']}")
        kb.button(text=f"❌ رفض #{p['id']}", callback_data=f"reject_{p['id']}")
    kb.adjust(2)
    kb.button(text="🔙 رجوع", callback_data="admin_back")
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("approve_"))
async def cb_approve(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return await callback.answer("⛔")
    pid = int(callback.data.split("_")[1])
    update_payment_status(pid, "approved")
    conn = get_conn()
    p = conn.execute("SELECT user_id, plan_name FROM payments WHERE id=?", (pid,)).fetchone()
    if p:
        days = 90 if "Excellence" in p[1] else (60 if "VIP" in p[1] else 30)
        add_subscription(p[0], p[1], days)
    conn.close()
    await callback.answer("✅ تمت الموافقة")
    await cb_payments(callback)

@dp.callback_query(F.data.startswith("reject_"))
async def cb_reject(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return await callback.answer("⛔")
    pid = int(callback.data.split("_")[1])
    update_payment_status(pid, "rejected")
    await callback.answer("❌ تم الرفض")
    await cb_payments(callback)

@dp.callback_query(F.data == "admin_vault")
async def cb_vault(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return await callback.answer("⛔")
    conn = get_conn()
    items = conn.execute("SELECT * FROM vault_items ORDER BY id").fetchall()
    conn.close()
    text = "🗄️ **مكتبة القوالب الإمبراطورية**:\n\n"
    if not items:
        text += "لا توجد قوالب."
    for v in items:
        text += f"📁 {v['title']} ({v['category']}) — مستوى {v['unlock_level']}\n"
    await callback.message.edit_text(text, reply_markup=build_admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "admin_add_vault")
async def cb_add_vault(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return await callback.answer("⛔")
    await callback.message.edit_text("📁 أدخل عنوان القالب:")
    await state.set_state(AddVault.waiting_title)
    await callback.answer()

@dp.message(AddVault.waiting_title)
async def vault_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("📝 أدخل محتوى القالب:")
    await state.set_state(AddVault.waiting_content)

@dp.message(AddVault.waiting_content)
async def vault_content(message: Message, state: FSMContext):
    await state.update_data(content=message.text)
    kb = InlineKeyboardBuilder()
    for cat in ["speaking", "email", "writing", "listening"]:
        kb.button(text=cat, callback_data=f"vcat_{cat}")
    await message.answer("📂 التصنيف:", reply_markup=kb.as_markup())
    await state.set_state(AddVault.waiting_category)

@dp.callback_query(F.data.startswith("vcat_"), AddVault.waiting_category)
async def vault_cat(callback: CallbackQuery, state: FSMContext):
    await state.update_data(category=callback.data.split("_")[1])
    await callback.message.edit_text("🔓 مستوى الفتح (1-10):")
    await state.set_state(AddVault.waiting_unlock_level)
    await callback.answer()

@dp.message(AddVault.waiting_unlock_level)
async def vault_level(message: Message, state: FSMContext):
    data = await state.get_data()
    conn = get_conn()
    conn.execute("INSERT INTO vault_items (title, content, category, unlock_level) VALUES (?,?,?,?)",
                 (data['title'], data['content'], data['category'], message.text))
    conn.commit(); conn.close()
    await message.answer("✅ تمت إضافة القالب!", reply_markup=build_admin_menu())
    await state.clear()

@dp.callback_query(F.data == "admin_settings")
async def cb_settings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return await callback.answer("⛔")
    settings = {
        "show_writing": get_admin_setting("show_writing", "1"),
        "speaking_strict": get_admin_setting("speaking_strict", "0"),
        "wallet_number": get_admin_setting("wallet_number", "0798919150"),
        "xp_multiplier": get_admin_setting("xp_multiplier", "1"),
        "challenge_timer": get_admin_setting("challenge_timer", "5"),
    }
    text = "⚙️ **الإعدادات**:\n\n" + "\n".join([f"• {k}: {v}" for k, v in settings.items()])
    await callback.message.edit_text(text, reply_markup=build_admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "admin_back")
async def cb_back(callback: CallbackQuery):
    await callback.message.edit_text("👑 **لوحة تحكم المسؤول**", reply_markup=build_admin_menu())
    await callback.answer()

# ===================== SCHEDULER TASKS =====================

async def absence_check():
    """كل ساعة: تفقد الطلاب الغائبين 48 ساعة وأرسل تنبيه."""
    logger.info("🔔 Running absence check...")
    absent = get_absent_students(48)
    for s in absent:
        try:
            await bot.send_message(
                s['user_id'],
                f"🌟 {s['first_name'] or 'طالبنا العزيز'}،\n\n"
                f"نشتاق إليك! آخر ظهور كان {s['last_active']}.\n"
                f"عوداً حميداً لاستكمال رحلتك التعليمية في أكاديمية يامن 📚"
            )
        except Exception as e:
            logger.warning(f"Failed to notify {s['user_id']}: {e}")

async def weekly_report():
    """كل جمعة: تقرير أسبوعي لجميع الطلاب."""
    logger.info("📊 Running weekly report...")
    conn = get_conn()
    students = conn.execute("SELECT user_id, first_name, xp FROM students WHERE is_active=1").fetchall()
    conn.close()
    today = datetime.now().strftime("%Y-%m-%d")
    for s in students:
        try:
            w = (datetime.now() - timedelta(days=7)).isoformat()
            conn2 = get_conn()
            activity = conn2.execute("SELECT COUNT(*) FROM activity_log WHERE user_id=? AND created_at > ?", (s['user_id'], w)).fetchone()[0]
            conn2.close()
            await bot.send_message(
                s['user_id'],
                f"📊 **الحصاد الأسبوعي** 🗓️ {today}\n\n"
                f"👤 {s['first_name']}\n"
                f"⭐ النقاط: {s['xp']} XP\n"
                f"🔥 النشاط: {activity} تفاعل\n\n"
                f"استمر في التقدم! 🚀"
            )
        except Exception as e:
            logger.warning(f"Weekly report failed for {s['user_id']}: {e}")

# ===================== MAIN =====================

async def main():
    logger.info(f"🚀 Yamen LMS starting | ADMIN_IDS={ADMIN_IDS}")
    await bot.delete_webhook(drop_pending_updates=True)
    init_db()
    logger.info("✅ DB ready.")

    # 🔔 جدولة المهام
    scheduler.add_job(absence_check, "interval", hours=1, id="absence_check")
    scheduler.add_job(weekly_report, "cron", day_of_week="fri", hour=9, id="weekly_report")
    scheduler.start()
    logger.info("⏰ Scheduler started (absence check hourly, weekly report Fridays 9AM).")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
