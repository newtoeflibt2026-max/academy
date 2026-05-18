# -*- coding: utf-8 -*-
import asyncio, logging, importlib
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from bot_database import init_bot_db
from handlers.start import router as start_router
from handlers.subscriptions import router as sub_router
from handlers.admin import router as admin_router

def try_router(mod_name):
    try:
        mod = importlib.import_module(mod_name)
        r = getattr(mod, "router", None)
        if r:
            print(f"  + {mod_name}")
        return r
    except Exception as e:
        print(f"  - {mod_name}: {e}")
        return None

async def main():
    init_bot_db()
    bot = Bot(token=settings.BOT_TOKEN,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start_router)
    dp.include_router(sub_router)
    dp.include_router(admin_router)

    print("تحميل الـ handlers الاختيارية:")
    for mod in ["handlers.listening","handlers.lessons",
                "handlers.placement_test","handlers.writing",
                "handlers.speaking","handlers.correction"]:
        r = try_router(mod)
        if r:
            dp.include_router(r)

    await bot.delete_webhook(drop_pending_updates=True)
    print("=" * 40)
    print("البوت يعمل الآن!")
    print(f"DB: {settings.DB_PATH}")
    print("=" * 40)
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
