import asyncio, logging, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, ADMIN_IDS
from database import (init_db, get_db_connection, get_stats, get_all_students,
    get_leaderboard, get_absent_students, upsert_student, log_activity,
    add_to_error_bank, get_due_reviews, record_correct_review, update_user_role,
    get_admin_setting, set_admin_setting)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    logger.critical("❌ BOT_TOKEN missing!"); sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def is_admin(uid): return uid in ADMIN_IDS

def menu():
    b = InlineKeyboardBuilder()
    for txt, cb in [("📊 إحصائيات","stats"),("📚 الدورات","courses"),("👥 الطلاب","students"),
        ("💰 المدفوعات","payments"),("🗄️ الخزنة","vault"),("⚙️ الإعدادات","settings"),
        ("➕ إضافة دورة","add_course"),("➕ إضافة قالب","add_vault")]:
        b.button(text=txt, callback_data=cb)
    b.adjust(2,2,2,2)
    return b.as_markup()

# ═══════ HANDLERS ═══════

@dp.message(Command("start"))
async def start(msg: Message):
    uid = msg.from_user.id
    upsert_student(uid, msg.from_user.username or "", msg.from_user.first_name or "")
    log_activity(uid, "start")
    await msg.answer(f"👋 أهلاً {msg.from_user.first_name or 'مستخدم'}!\n🆔 `{uid}`",
                     parse_mode="Markdown")

@dp.message(Command("leaderboard"))
async def leaderboard(msg: Message):
    lb = get_leaderboard(5)
    if not lb: return await msg.answer("لا يوجد طلاب.")
    t = "🏆 **Top 5**:\n\n"
    for i,s in enumerate(lb,1):
        t += f"{['🥇','🥈','🥉','4️⃣','5️⃣'][i-1]} {s['first_name'] or '---'} — {s['xp']} XP\n"
    await msg.answer(t, parse_mode="Markdown")

@dp.message(Command("profile"))
async def profile(msg: Message):
    uid = msg.from_user.id
    conn = get_db_connection()
    try:
        s = conn.execute("SELECT * FROM students WHERE user_id=?",(uid,)).fetchone()
        if s:
            total = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0] or 1
            done = conn.execute("SELECT COUNT(DISTINCT course_id) FROM progress WHERE user_id=? AND completed=1",(uid,)).fetchone()[0]
            pct = round(done/total*100)
            bar = "█"*(pct//10) + "░"*(10-pct//10)
            await msg.answer(f"👤 {s['first_name']}\n⭐ {s['xp']} XP | 🎚️ Lv.{s['level']}\n📊 [{bar}] {pct}%")
    finally: conn.close()

@dp.message(Command("review"))
async def review(msg: Message):
    reviews = get_due_reviews(msg.from_user.id)
    if not reviews: return await msg.answer("✅ لا توجد مراجعة.")
    for r in reviews[:5]:
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ صحيح", callback_data=f"ok_{r['id']}")
        await msg.answer(f"🔄 {r['question_text']}\nإجابتك: _{r['wrong_answer']}_",
                         reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("ok_"))
async def ok_review(cb: CallbackQuery):
    record_correct_review(cb.from_user.id, int(cb.data.split("_")[1]))
    await cb.message.edit_text(cb.message.text + "\n\n✅ **إجابة صحيحة!**", parse_mode="Markdown")
    await cb.answer()

# ═══════ ADMIN ═══════

@dp.message(Command("admin"))
async def admin(msg: Message):
    uid = msg.from_user.id
    if uid not in ADMIN_IDS: return await msg.answer(f"⛔ {uid}")
    update_user_role(uid, "admin")
    await msg.answer("👑 **لوحة التحكم**", reply_markup=menu(), parse_mode="Markdown")

@dp.callback_query(F.data == "stats")
async def cb_stats(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("⛔",show_alert=True)
    s = get_stats()
    conn = get_db_connection()
    xp = conn.execute("SELECT COALESCE(SUM(xp),0) FROM students").fetchone()[0]
    conn.close()
    await cb.message.edit_text(f"📊 👥{s['students']} 📚{s['courses']} 🟢{s['active_today']} ⭐{xp}XP", reply_markup=menu())
    await cb.answer()

@dp.callback_query(F.data == "courses")
async def cb_courses(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("⛔",show_alert=True)
    conn = get_db_connection()
    cs = conn.execute("SELECT * FROM courses ORDER BY id").fetchall(); conn.close()
    t = "📚 الدورات:\n\n" + "\n".join([f"🔹 {c['name']} ({c['level']})" for c in cs]) if cs else "لا دورات."
    await cb.message.edit_text(t, reply_markup=menu()); await cb.answer()

@dp.callback_query(F.data == "students")
async def cb_students(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("⛔",show_alert=True)
    ss = get_all_students()
    t = "👥:\n\n" + "\n".join([f"{'🟢' if s['is_active'] else '🔴'} {s['first_name']} — {s['xp']}XP" for s in ss[:15]])
    await cb.message.edit_text(t, reply_markup=menu()); await cb.answer()

@dp.callback_query(F.data == "payments")
async def cb_payments(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("⛔",show_alert=True)
    conn = get_db_connection()
    ps = conn.execute("SELECT * FROM payments WHERE status='pending'").fetchall(); conn.close()
    t = "💰:\n\n" + "\n".join([f"#{p['id']} {p['plan_name']} {p['amount']}ر.س" for p in ps]) if ps else "لا مدفوعات."
    await cb.message.edit_text(t, reply_markup=menu()); await cb.answer()

@dp.callback_query(F.data == "vault")
async def cb_vault(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("⛔",show_alert=True)
    conn = get_db_connection()
    vs = conn.execute("SELECT * FROM vault_items ORDER BY id").fetchall(); conn.close()
    t = "🗄️ القوالب:\n\n" + "\n".join([f"📁 {v['title']}" for v in vs]) if vs else "لا قوالب."
    await cb.message.edit_text(t, reply_markup=menu()); await cb.answer()

@dp.callback_query(F.data == "settings")
async def cb_settings(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("⛔",show_alert=True)
    t = "\n".join([f"• {k}: {get_admin_setting(k,'---')}" for k in ['wallet_number','xp_multiplier','challenge_timer']])
    await cb.message.edit_text(f"⚙️:\n\n{t}", reply_markup=menu()); await cb.answer()

@dp.callback_query(F.data == "add_course")
async def cb_add_course(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("⛔",show_alert=True)
    kb = InlineKeyboardBuilder()
    for skill, label in [("speaking","🗣️ تحدث"),("spelling","✍️ إكمال"),("writing","📝 ترتيب"),("email","📧 إيميل"),("listening","🎧 استماع")]:
        kb.button(text=label, callback_data=f"skill_{skill}")
    kb.adjust(2,2,1)
    await cb.message.edit_text("اختر نوع المهارة:", reply_markup=kb.as_markup())
    await cb.answer()

@dp.callback_query(F.data == "add_vault")
async def cb_add_vault(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("⛔",show_alert=True)
    await cb.message.edit_text("📁 أرسل: العنوان | المحتوى | التصنيف | المستوى\nمثال: قالب تقديم | مرحبا اسمي... | speaking | 1")
    await cb.answer()

@dp.message(F.text.regexp(r"^.+ \| .+ \| .+ \| .+$"))
async def vault_input(msg: Message):
    if not is_admin(msg.from_user.id): return
    parts = [p.strip() for p in msg.text.split("|")]
    if len(parts) == 4:
        conn = get_db_connection()
        conn.execute("INSERT INTO vault_items (title,content,category,unlock_level) VALUES (?,?,?,?)", tuple(parts))
        conn.commit(); conn.close()
        await msg.answer("✅ تم!", reply_markup=menu())

@dp.message(F.text.regexp(r"^(.+)\|(.+)\|(.+)\|(.+)\|(.+)\|(.+)\|(.+)$"))
async def course_input(msg: Message):
    if not is_admin(msg.from_user.id): return
    p = [x.strip() for x in msg.text.split("|")]
    if len(p) == 7:
        conn = get_db_connection()
        conn.execute("INSERT INTO courses (name,level,skill_type,price,duration_days,time_limit,target_score) VALUES (?,?,?,?,?,?,?)", tuple(p))
        conn.commit(); conn.close()
        await msg.answer("✅ تمت!", reply_markup=menu())

@dp.callback_query(F.data.startswith("skill_"))
async def skill_pick(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("⛔",show_alert=True)
    skill = cb.data.split("_")[1]
    await cb.message.edit_text(
        f"✅ المهارة: {skill}\n\n📝 أرسل بيانات الدورة:\n`الاسم|المستوى|{skill}|السعر|المدة|الوقت|الهدف`\nمثال:\n`محادثة|beginner|{skill}|100|30|45|69`",
        parse_mode="Markdown")
    await cb.answer()

@dp.callback_query(F.data == "back")
async def back(cb: CallbackQuery):
    await cb.message.edit_text("👑 لوحة التحكم", reply_markup=menu()); await cb.answer()

# ═══════ MAIN ═══════

async def main():
    logger.info("🛑 Step 1: Hard stop – deleting webhook + dropping pending updates...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning(f"delete_webhook skipped: {e}")

    logger.info("💤 Step 2: Sleeping 5 seconds for Telegram servers to stabilize...")
    await asyncio.sleep(5)

    logger.info("🗄️ Step 3: Initializing database...")
    init_db()
    logger.info("✅ DB ready.")

    logger.info(f"🚀 Step 4: Starting polling on port={os.environ.get('PORT','8080')} | ADMIN_IDS={ADMIN_IDS}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
