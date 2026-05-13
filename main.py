# main.py - Yamen Academy Bot (Aiogram 3)
import asyncio, logging, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from config import BOT_TOKEN, ADMIN_IDS
from database import init_db, get_db_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ============ HANDLERS ============

@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    logger.info(f"/start from {uid}")
    await message.answer(f"👋 أهلاً {message.from_user.first_name or 'مستخدم'}!\n🆔 {uid}\n\n/help | /admin | /courses")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("🎓 أوامر البوت:\n/start\n/admin (للمسؤول)\n/courses\n/stats")

@dp.message(Command("courses"))
async def cmd_courses(message: Message):
    await message.answer("📚 تفضل بزيارة موقع الأكاديمية لعرض الدورات.")

# ✅✅✅ أمر /admin بكل الصيغ ✅✅✅
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    uid = message.from_user.id
    logger.info(f"⚡ /admin triggered by {uid} | ADMIN_IDS={ADMIN_IDS}")
    try:
        if uid in ADMIN_IDS:
            await message.answer(f"👑 لوحة تحكم المسؤول\n🆔 {uid}\n✅ صلاحية: مدير")
        else:
            await message.answer(f"⛔ غير مصرح. معرفك: {uid}")
    except Exception as e:
        logger.error(f"admin handler crash: {e}")
        await message.answer("⚠️ خطأ داخلي")

# ✅ صيغة احتياطية: أي رسالة نصها "/admin"
@dp.message(F.text == "/admin")
async def cmd_admin_fallback(message: Message):
    await cmd_admin(message)  # يعيد التوجيه لنفس المعالج

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    uid = message.from_user.id
    if uid not in ADMIN_IDS:
        await message.answer("⛔ غير مصرح.")
        return
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM students"); s = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM courses"); co = c.fetchone()[0]
        conn.close()
        await message.answer(f"📊 الطلاب: {s} | الدورات: {co}")
    except Exception as e:
        await message.answer(f"⚠️ {e}")

# ============ MAIN ============
async def main():
    logger.info(f"🚀 Bot starting | ADMIN_IDS={ADMIN_IDS}")
    await bot.delete_webhook(drop_pending_updates=True)
    init_db()
    logger.info("✅ DB ready. Registered handlers: start, help, courses, admin, admin_fallback, stats")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
