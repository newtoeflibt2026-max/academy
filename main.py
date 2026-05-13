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
        logger.critical(f"Invalid token (length: {len(BOT_TOKEN)})")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)

    dp = Dispatcher()

    @dp.message(Command("start"))
    async def start(msg: Message):
        await msg.answer("🕌 مرحباً بك في Yamen Academy!\n/help للأوامر")

    @dp.message(Command("help"))
    async def help_cmd(msg: Message):
        await msg.answer("📚 /start /help /courses /level /progress /leaderboard /daily")

    logger.info(f"Bot {bot.id} polling...")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    init_db()
    asyncio.run(main())
