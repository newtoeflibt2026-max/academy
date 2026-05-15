import asyncio, logging, sys, os
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

# ── استيراد الإعدادات ────────────────────────────────────────
try:
    from config import ADMIN_IDS, BOT_TOKEN, DATABASE_PATH, WEBHOOK_HOST, WEBHOOK_PATH, WEBAPP_HOST, WEBAPP_PORT
except ImportError:
    ADMIN_IDS = [5602495831]
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yamen_academy.db")
    WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "")
    WEBHOOK_PATH = "/webhook"
    WEBAPP_HOST = "0.0.0.0"
    WEBAPP_PORT = int(os.environ.get("PORT", 8080))

import aiohttp
import sqlite3

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

dp = Dispatcher()

# ── معالجات البوت ────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    is_admin = user.id in ADMIN_IDS
    logger.info(f"/start from {user.full_name} (ID:{user.id}) | Admin:{is_admin}")

    # حفظ الطالب في القاعدة
    db = sqlite3.connect(DATABASE_PATH)
    db.execute("INSERT OR IGNORE INTO students (telegram_id, username, first_name, is_active) VALUES (?,?,?,1)",
               (user.id, user.username, user.first_name))
    db.execute("UPDATE students SET username=?, first_name=?, last_active=datetime('now') WHERE telegram_id=?",
               (user.username, user.first_name, user.id))
    db.commit(); db.close()

    await message.answer(
        f"🦅 أهلاً بك في **يامن أكاديمي**، {user.full_name}!\n\n"
        f"⚡ مستواك: 0\n"
        f"📊 XP: 0\n\n"
        f"{'👑 أنتِ الإمبراطورة! استخدمي /admin للوحة التحكم' if is_admin else '🎯 استخدم /help لمعرفة الأوامر المتاحة'}"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📋 **الأوامر المتاحة:**\n"
        "/start — بدء التشغيل\n"
        "/help — هذه القائمة\n"
        "/profile — ملفك الشخصي\n"
        "/leaderboard — قائمة المتفوقين\n"
        "/review — مراجعة الأخطاء\n"
        + ("/admin — 👑 لوحة الإمبراطورة\n" if message.from_user.id in ADMIN_IDS else "")
    )

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    db = sqlite3.connect(DATABASE_PATH); db.row_factory = sqlite3.Row
    row = db.execute("SELECT * FROM students WHERE telegram_id=?",(message.from_user.id,)).fetchone()
    db.close()
    if row:
        await message.answer(f"👤 {row['first_name'] or row['username']}\n⭐ XP: {row['xp'] or 0}\n📊 المستوى: {row['level'] or 0}\n🔥 Streak: {row.get('streak',0) or 0}")
    else:
        await message.answer("❌ لم يتم العثور على ملفك. اكتب /start أولاً.")

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ غير مصرح لك بالدخول.")
        return
    await message.answer(
        f"👑 **لوحة الإمبراطورة** — يامن أكاديمي\n\n"
        f"🔗 افتحي الرابط:\n`{WEBHOOK_HOST}/admin`\n\n"
        f"📊 الميزات:\n"
        f"• تفعيل/تعطيل المهارات الست\n"
        f"• إضافة/حذف دروس (فيديو/PDF)\n"
        f"• عرض قائمة الطلاب والإحصائيات"
    )

@dp.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message):
    db = sqlite3.connect(DATABASE_PATH); db.row_factory = sqlite3.Row
    rows = db.execute("SELECT first_name,username,xp,level FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT 5").fetchall()
    db.close()
    if rows:
        text = "🏅 **قائمة المتفوقين:**\n\n" + "\n".join(f"{i+1}. {r['first_name'] or r['username']} — {r['xp'] or 0} XP" for i,r in enumerate(rows))
    else:
        text = "لا يوجد طلاب بعد!"
    await message.answer(text)

@dp.message()
async def echo(message: Message):
    await message.answer("اكتب /help لمعرفة الأوامر المتاحة.")

# ── الدالة الرئيسية ──────────────────────────────────────────
async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))

    # ⚡ حذف الـ Webhook القديم + مسح التحديثات المعلقة
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Old webhook deleted, pending updates dropped")

    # ⚡ محاولة تعيين Webhook جديد إذا كان WEBHOOK_HOST موجوداً
    if WEBHOOK_HOST and WEBHOOK_HOST.startswith("https://"):
        webhook_url = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
        try:
            await bot.set_webhook(webhook_url)
            logger.info(f"🔗 Webhook set to: {webhook_url}")
            # بدء webhook server
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
            from aiohttp import web
            app_web = web.Application()
            handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
            handler.register(app_web, path=WEBHOOK_PATH)
            setup_application(app_web, dp, bot=bot)
            logger.info(f"🌐 Webhook server starting on {WEBAPP_HOST}:{WEBAPP_PORT}")
            await web._run_app(app_web, host=WEBAPP_HOST, port=WEBAPP_PORT)
        except Exception as e:
            logger.error(f"❌ Webhook setup failed: {e}. Falling back to polling...")
            await dp.start_polling(bot)
    else:
        logger.info("🔄 No WEBHOOK_HOST set. Starting polling mode...")
        await dp.start_polling(bot)

if __name__ == "__main__":
    logger.info(f"🚀 Starting Yamen Academy Bot | ADMIN_IDS: {ADMIN_IDS}")
    asyncio.run(main())
