import asyncio, logging, sys, os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from database import init_db

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

async def main():
    if not BOT_TOKEN or len(BOT_TOKEN) < 20:
        logger.critical(f"❌ Invalid BOT_TOKEN (length: {len(BOT_TOKEN)})")
        return

    logger.info(f"✅ Bot starting with token: {BOT_TOKEN[:10]}...")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Basic commands
    @dp.message(Command("start"))
    async def start(msg: Message):
        await msg.answer(
            "🕌 *مرحباً بك في Yamen Academy!*\n\n"
            "📚 تعلم اللغة الإنجليزية بأحدث الأساليب\n"
            "🎯 اختبر مستواك\n"
            "📝 تابع تقدمك\n\n"
            "استخدم /help لرؤية الأوامر",
            parse_mode="Markdown"
        )

    @dp.message(Command("help"))
    async def help_cmd(msg: Message):
        await msg.answer(
            "📚 *الأوامر:*\n"
            "/start - البداية\n"
            "/help - المساعدة\n"
            "/courses - الدورات المتاحة\n"
            "/level - اختبار المستوى\n"
            "/progress - تقدمك\n"
            "/leaderboard - المتصدرون\n"
            "/daily - تحدي اليوم",
            parse_mode="Markdown"
        )

    @dp.message(Command("courses"))
    async def courses_cmd(msg: Message):
        await msg.answer("📚 الدورات ستظهر قريباً! تابع updates القناة.")

    logger.info("🤖 Bot polling started...")
    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")

if __name__ == "__main__":
    init_db()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
