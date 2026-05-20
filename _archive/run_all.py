# -*- coding: utf-8 -*-
import asyncio, logging, os, threading
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
PORT      = int(os.environ.get("PORT", 8080))


def run_flask():
    from app import app
    from startup_seed import seed
    seed()
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


async def run_bot():
    if not BOT_TOKEN or len(BOT_TOKEN) < 20:
        logger.error("BOT_TOKEN missing — bot disabled")
        return

    from aiogram import Bot, Dispatcher
    from aiogram.enums import ParseMode
    from aiogram.client.default import DefaultBotProperties
    from aiogram.fsm.storage.memory import MemoryStorage

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # تحميل الـ handlers
    handler_modules = [
        "handlers.start",
        "handlers.placement_test",
        "handlers.lessons",
        "handlers.subscriptions",
        "handlers.writing",
        "handlers.speaking",
        "handlers.listening",
        "handlers.correction",
        "handlers.admin",
    ]

    for mod_name in handler_modules:
        try:
            import importlib
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "router"):
                dp.include_router(mod.router)
                logger.info(f"  + {mod_name}")
        except Exception as e:
            logger.warning(f"  - {mod_name}: {e}")

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("=" * 40)
    logger.info("البوت يعمل الآن!")
    logger.info("=" * 40)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    asyncio.run(run_bot())
