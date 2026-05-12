import asyncio, logging, sys, os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from database import get_db_connection, init_db

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

async def main():
    if not BOT_TOKEN:
        logger.critical("❌ BOT_TOKEN is empty! Set it in Railway Variables.")
        return
    
    logger.info(f"Token loaded: {BOT_TOKEN[:15]}... (length: {len(BOT_TOKEN)})")
    
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    # Register handlers
    try:
        from handlers import register_all
        register_all(dp)
    except ImportError:
        logger.warning("handlers.py not found, bot will run with basic commands only")
    
    # Basic commands
    from aiogram.filters import Command
    from aiogram.types import Message
    
    @dp.message(Command("start"))
    async def start_cmd(msg: Message):
        await msg.answer("🕌 مرحباً بك في Yamen Academy!\n\nاستخدم /help لرؤية الأوامر المتاحة.")
    
    @dp.message(Command("help"))
    async def help_cmd(msg: Message):
        await msg.answer("📚 الأوامر:\n/start - البداية\n/help - المساعدة\n/courses - الدورات\n/progress - تقدمي")
    
    logger.info("🤖 Starting bot polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")

if __name__ == "__main__":
    init_db()
    asyncio.run(main())
