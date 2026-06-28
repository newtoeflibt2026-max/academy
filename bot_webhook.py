# -*- coding: utf-8 -*-
"""
bot_webhook.py - Telegram webhook handler running inside Flask.
- Receives POST /telegram-webhook from Telegram.
- Feeds updates to aiogram Dispatcher synchronously.
- Eliminates polling -> no 409 conflict, one Railway service is enough.
"""
import os, asyncio, logging, json, threading
from flask import Blueprint, request, jsonify

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

logger = logging.getLogger(__name__)
webhook_bp = Blueprint("telegram_webhook", __name__)

_BOT = None
_DP = None
_LOOP = None
_INITIALIZED = False


def _build_dispatcher():
    """Load all routers (mirrors main.py logic)."""
    dp = Dispatcher(storage=MemoryStorage())
    # Core routers
    for name in ("handlers.start", "handlers.payments", "handlers.admin"):
        try:
            mod = __import__(name, fromlist=["router"])
            dp.include_router(mod.router)
            print(f"[webhook] + {name}")
        except Exception as e:
            print(f"[webhook] - {name}: {e}")
    # Optional routers
    for name in ("handlers.listening", "handlers.lessons",
                 "handlers.placement_inline", "handlers.writing",
                 "handlers.speaking", "handlers.correction"):
        try:
            mod = __import__(name, fromlist=["router"])
            r = getattr(mod, "router", None)
            if r:
                dp.include_router(r)
                print(f"[webhook] + {name}")
        except Exception as e:
            print(f"[webhook] - {name}: {e}")
    return dp


def init_bot():
    """Initialize bot, dispatcher, and event loop once."""
    global _BOT, _DP, _LOOP, _INITIALIZED
    if _INITIALIZED:
        return _BOT, _DP

    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        print("[webhook] BOT_TOKEN missing - webhook disabled")
        return None, None

    _BOT = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    _DP = _build_dispatcher()
    _LOOP = asyncio.new_event_loop()
    def _run_loop():
        asyncio.set_event_loop(_LOOP)
        _LOOP.run_forever()
    threading.Thread(target=_run_loop, daemon=True).start()
    _INITIALIZED = True
    print("[webhook] bot + dispatcher initialized")
    return _BOT, _DP


def register_webhook_with_telegram():
    """Tell Telegram to send updates to our endpoint. Called once at startup."""
    bot, dp = init_bot()
    if not bot:
        return False

    base = os.environ.get("WEBHOOK_HOST", "").rstrip("/")
    if not base:
        print("[webhook] WEBHOOK_HOST missing - cannot set webhook")
        return False

    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "yamen-webhook-secret-2026")
    url = f"{base}/telegram-webhook"

    async def _setup():
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await bot.set_webhook(
                url=url,
                secret_token=secret,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query", "pre_checkout_query"]
            )
            info = await bot.get_webhook_info()
            print(f"[webhook] SET OK: {info.url} (pending={info.pending_update_count})")
            return True
        except Exception as e:
            print(f"[webhook] SET FAILED: {e}")
            return False

    fut = asyncio.run_coroutine_threadsafe(_setup(), _LOOP)
    try:
        return fut.result(timeout=30)
    except Exception as e:
        print(f"[webhook] setup error: {e}")
        return False


@webhook_bp.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    """Receive updates from Telegram."""
    bot, dp = init_bot()
    if not bot:
        return jsonify({"ok": False, "error": "bot not initialized"}), 503

    # Verify secret token
    expected = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "yamen-webhook-secret-2026")
    got = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if got != expected:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    data = request.get_json(silent=True) or {}
    try:
        update = Update.model_validate(data, context={"bot": bot})
        asyncio.run_coroutine_threadsafe(dp.feed_update(bot, update), _LOOP)
    except Exception as e:
        logger.exception(f"webhook process error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 200  # 200 to stop retries
    return jsonify({"ok": True})


@webhook_bp.route("/telegram-webhook/info", methods=["GET"])
def webhook_info():
    """Diagnostic endpoint."""
    bot, _ = init_bot()
    if not bot:
        return jsonify({"ok": False, "error": "bot not initialized"}), 503
    try:
        import asyncio as _a
        info = _a.run_coroutine_threadsafe(bot.get_webhook_info(), _LOOP).result(timeout=15)
        return jsonify({
            "ok": True,
            "url": info.url,
            "pending_update_count": info.pending_update_count,
            "last_error_date": info.last_error_date.isoformat() if info.last_error_date else None,
            "last_error_message": info.last_error_message,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
