# -*- coding: utf-8 -*-

from init_db import ensure_db
ensure_db()  # Initialize DB on Railway Volume
import asyncio, logging, importlib, threading
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from db import init_bot_db
from handlers.start import router as start_router
from handlers.payments import router as pay_router
from handlers.admin import router as admin_router

# â”€â”€â”€ Flask â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def run_flask():
    try:
        from app import app
        print(f"[Flask] starting on port {settings.PORT}")
        app.run(host="0.0.0.0", port=settings.PORT, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[Flask] ERROR: {e}")

# â”€â”€â”€ Optional handlers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

# â”€â”€â”€ Bot (Polling) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async def run_bot():
    init_bot_db()
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start_router)
    dp.include_router(pay_router)
    dp.include_router(admin_router)

    optional = [
        "handlers.listening", "handlers.lessons",
        "handlers.placement_inline", "handlers.writing",
        "handlers.speaking", "handlers.correction"
    ]
    print("ØªØ­Ù…ÙŠÙ„ Ø§Ù„Ù€ handlers Ø§Ù„Ø§Ø®ØªÙŠØ§Ø±ÙŠØ©:")
    for mod in optional:
        r = try_router(mod)
        if r:
            dp.include_router(r)

    await bot.delete_webhook(drop_pending_updates=True)
    print("=" * 40)
    print("Ø§Ù„Ø¨ÙˆØª ÙŠØ¹Ù…Ù„ Ø§Ù„Ø§Ù†!")
    print(f"DB: {settings.DB_PATH}")
    print("=" * 40)
    await dp.start_polling(bot, drop_pending_updates=True)

# â”€â”€â”€ Entry point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    asyncio.run(run_bot())
