# -*- coding: utf-8 -*-
import os
import sys
import asyncio
import threading
import logging
from loguru import logger

# ── تحميل متغيرات البيئة ──────────────────────────────────────────────────
# ── تحميل متغيرات البيئة ──────────────────────────────────────────────────
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()

PORT = int(os.environ.get("PORT", 8080))
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# تحقق من التوكن قبل البدء
if not BOT_TOKEN or len(BOT_TOKEN) < 20:
    import sys
    print("ERROR: BOT_TOKEN missing or invalid!")
    print(f"PORT={PORT}")
    print(f"All env vars: {[k for k in os.environ.keys() if not k.startswith('_')]}")
    # شغّل Flask فقط بدون البوت
    BOT_TOKEN = None

WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "")


# ── تشغيل Flask ──────────────────────────────────────────────────────────
def run_flask():
    from app import app
    logger.info(f"Flask starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

# ── تشغيل البوت ──────────────────────────────────────────────────────────
async def run_bot():
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN not set - bot disabled, running Flask only")
        # اجعل البوت ينام بدل ما يكسر البرنامج
        while True:
            await asyncio.sleep(3600)

    from aiogram import Bot, Dispatcher
    from aiogram.enums import ParseMode
    from aiogram.client.default import DefaultBotProperties
    from aiogram.fsm.storage.memory import MemoryStorage
    import importlib

    from bot_database import init_bot_db
    init_bot_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # تحميل الـ handlers
    routers = [
        "handlers.start",
        "handlers.subscriptions",
        "handlers.admin",
        "handlers.listening",
        "handlers.lessons",
        "handlers.placement_test",
        "handlers.writing",
        "handlers.speaking",
        "handlers.correction",
    ]

    for mod_name in routers:
        try:
            mod = importlib.import_module(mod_name)
            r = getattr(mod, "router", None)
            if r:
                dp.include_router(r)
                logger.info(f"  + {mod_name}")
        except Exception as e:
            logger.warning(f"  - {mod_name}: {e}")

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("=" * 40)
    logger.info("البوت يعمل الآن!")
    logger.info("=" * 40)
    await dp.start_polling(bot, drop_pending_updates=True)

# ── نقطة الدخول ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)

    # Flask في thread منفصل
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask thread started")

    # البوت في الـ main event loop
    asyncio.run(run_bot())
