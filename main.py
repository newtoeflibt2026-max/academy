# -*- coding: utf-8 -*-
import asyncio, logging, importlib, threading
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from bot_database import init_bot_db
from handlers.start import router as start_router
from handlers.subscriptions import router as sub_router
from handlers.admin import router as admin_router

# ─── Flask ───────────────────────────────────────────────
def run_flask():
    try:
        from app import app
        from admin_routes import register_admin_routes
        register_admin_routes(app)
        print(f"[Flask] starting on port {settings.PORT}")
        app.run(host="0.0.0.0", port=settings.PORT, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[Flask] ERROR: {e}")

# ─── Optional handlers ───────────────────────────────────
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

# ─── Bot (Polling) ───────────────────────────────────────
async def run_bot():
    init_bot_db()
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start_router)
    dp.include_router(sub_router)
    dp.include_router(admin_router)

    optional = [
        "handlers.listening", "handlers.lessons",
        "handlers.placement_test", "handlers.writing",
        "handlers.speaking", "handlers.correction"
    ]
    print("تحميل الـ handlers الاختيارية:")
    for mod in optional:
        r = try_router(mod)
        if r:
            dp.include_router(r)

    await bot.delete_webhook(drop_pending_updates=True)
    print("=" * 40)
    print("البوت يعمل الان!")
    print(f"DB: {settings.DB_PATH}")
    print("=" * 40)
    await dp.start_polling(bot, drop_pending_updates=True)

# ─── Entry point ─────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)

    # شغّل Flask في thread منفصل
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # شغّل البوت في الـ event loop الرئيسي
    asyncio.run(run_bot())
