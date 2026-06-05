import os
if os.environ.get("DISABLE_BOT", "").strip() in ("1","true","yes","on"):
    print("[main] DISABLE_BOT=1 -> bot polling disabled (Flask only)")
    import sys
    # شغّل Flask فقط بدون البوت
    try:
        from app import app
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
    except Exception as _e:
        print(f"[main] flask error: {_e}")
    sys.exit(0)

# -*- coding: utf-8 -*-
"""
main.py — Telegram bot worker (separated from Flask web).
- On Railway, this runs as a SEPARATE worker process (see Procfile).
- For local dev, you can still run `python main.py` to run BOTH web + bot
  in the same process (development convenience).
"""
import asyncio
import logging
import importlib
import os
import sys

# Ensure DB_PATH is unified
if not os.environ.get("DB_PATH"):
    if os.path.isdir("/app/data"):
        os.environ["DB_PATH"] = "/app/data/academy.db"
    else:
        os.environ["DB_PATH"] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "academy.db"
        )

from init_db import ensure_db
ensure_db()

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from db import init_bot_db


def try_router(mod_name):
    """Optional router loader — tolerate missing modules."""
    try:
        mod = importlib.import_module(mod_name)
        r = getattr(mod, "router", None)
        if r:
            print(f"  + {mod_name}")
        return r
    except Exception as e:
        print(f"  - {mod_name}: {e}")
        return None


async def run_bot():
    """Run the Telegram bot polling loop."""
    init_bot_db()

    if not settings.BOT_TOKEN:
        print("[bot] BOT_TOKEN missing - bot will not start")
        return

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Core routers (must exist)
    try:
        from handlers.start import router as start_router
        dp.include_router(start_router)
    except Exception as e:
        print(f"[bot] start router skipped: {e}")
    try:
        from handlers.payments import router as pay_router
        dp.include_router(pay_router)
    except Exception as e:
        print(f"[bot] payments router skipped: {e}")
    try:
        from handlers.admin import router as admin_router
        dp.include_router(admin_router)
    except Exception as e:
        print(f"[bot] admin router skipped: {e}")

    # Optional routers
    optional = [
        "handlers.listening", "handlers.lessons",
        "handlers.placement_inline", "handlers.writing",
        "handlers.speaking", "handlers.correction",
    ]
    print("Loading optional handlers:")
    for mod in optional:
        r = try_router(mod)
        if r:
            dp.include_router(r)

    await bot.delete_webhook(drop_pending_updates=True)
    print("=" * 40)
    print("Telegram bot is running")
    print(f"DB: {os.environ.get('DB_PATH')}")
    print("=" * 40)
    await dp.start_polling(bot, drop_pending_updates=True)


def run_flask():
    """Local dev only - in production gunicorn runs wsgi:app instead."""
    import threading
    try:
        from app import app
        port = int(os.environ.get("PORT", 8080))
        print(f"[Flask DEV] starting on port {port}")
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[Flask DEV] ERROR: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)

    # If RUN_MODE=bot we ONLY start the bot (production worker)
    # Otherwise we start BOTH (local dev convenience)
    run_mode = os.environ.get("RUN_MODE", "all").lower()

    if run_mode == "bot":
        asyncio.run(run_bot())
    elif run_mode == "web":
        run_flask()
    else:
        # Default: local dev — both in same process
        import threading
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        asyncio.run(run_bot())
