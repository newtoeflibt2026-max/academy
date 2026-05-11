import asyncio, logging, sys, os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from handlers import register_all
from database import init_db

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

async def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN is empty! Check Railway Variables.")
        return
    print(f"Token loaded: {BOT_TOKEN[:15]}... (length: {len(BOT_TOKEN)})")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    register_all(dp)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    init_db()
    asyncio.run(main())
