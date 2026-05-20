# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║         أكاديمية يامن — ملف التشغيل الموحد              ║
║  يشغّل: Flask (لوحة التحكم + طالب) + بوت تليجرام + Ngrok ║
╚══════════════════════════════════════════════════════════╝
تشغيل: python run_project.py [--no-ngrok] [--bot-only] [--web-only]
"""

import os, sys, asyncio, logging, threading, time, argparse, importlib

# ── تحميل .env قبل أي شيء ────────────────────────────────────────
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("YamenAcademy")

# ─────────────────────────────────────────────────────────────────
# 1. سيرفر Flask (لوحة التحكم + واجهة الطالب)
# ─────────────────────────────────────────────────────────────────
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def run_flask(port: int = 5000):
    """تشغيل سيرفر Flask"""
    try:
        from app import app
        from database import init_db, seed_demo_data
        log.info("🗄️  تهيئة قاعدة بيانات Flask …")
        init_db()
        seed_demo_data()
        log.info(f"🌐 Flask يعمل على http://0.0.0.0:{port}")
        # To avoid the warning about development server:
        import logging as _logging
        _logging.getLogger('werkzeug').setLevel(_logging.ERROR)
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        import traceback
        log.error(f"❌ خطأ في Flask:\n{traceback.format_exc()}")


# ─────────────────────────────────────────────────────────────────
# 2. بوت تليجرام (Polling)
# ─────────────────────────────────────────────────────────────────
async def _kill_old_sessions(token: str):
    """إيقاف أي جلسة polling قديمة بحذف الـ webhook وانتظار التحرر"""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as s:
            # حذف الـ webhook أولاً
            await s.post(f"https://api.telegram.org/bot{token}/deleteWebhook",
                         json={"drop_pending_updates": True})
            # إلغاء getUpdates الجارية بإرسال offset=-1
            await s.post(f"https://api.telegram.org/bot{token}/getUpdates",
                         json={"offset": -1, "timeout": 0})
    except Exception:
        pass
    # انتظر 2 ثانية لضمان إغلاق الجلسة القديمة
    await asyncio.sleep(2)


async def run_bot():
    """تشغيل بوت تليجرام بوضع Polling مع معالجة التعارض"""
    from aiogram import Bot, Dispatcher
    from aiogram.enums import ParseMode
    from aiogram.client.default import DefaultBotProperties
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.exceptions import TelegramConflictError
    from bot_database import init_bot_db

    if not settings.BOT_TOKEN:
        log.error("❌ BOT_TOKEN غير موجود في .env — البوت لن يعمل")
        return

    log.info("🤖 تهيئة قاعدة بيانات البوت …")
    init_bot_db()

    # ── إيقاف الجلسات القديمة أولاً ──────────────────────────
    log.info("⏳ إيقاف أي جلسة بوت قديمة …")
    await _kill_old_sessions(settings.BOT_TOKEN)
    log.info("✅ الجلسة القديمة أُغلقت")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # تحميل الـ routers
    def load_router(mod_name):
        try:
            mod = importlib.import_module(mod_name)
            r = getattr(mod, "router", None)
            if r:
                log.info(f"  ✅ {mod_name}")
            return r
        except Exception as e:
            log.warning(f"  ⚠️  {mod_name}: {e}")
            return None

    from handlers.start import router as start_router
    from handlers.subscriptions import router as sub_router
    from handlers.admin import router as admin_router

    # ── Force Sub Middleware ───────────────────────────────────
    try:
        from middlewares.force_sub import ForceSub
        dp.message.middleware(ForceSub())
        dp.callback_query.middleware(ForceSub())
        log.info("  ✅ Force Sub Middleware مفعّل")
    except Exception as e:
        log.warning(f"  ⚠️  Force Sub: {e}")

    dp.include_router(start_router)
    dp.include_router(sub_router)
    dp.include_router(admin_router)

    for mod in [
        "handlers.listening", "handlers.courses",
        "handlers.placement_test", "handlers.writing",
        "handlers.speaking", "handlers.spelling",
        "handlers.daily_challenge", "handlers.exam_timer",
    ]:
        r = load_router(mod)
        if r:
            dp.include_router(r)

    await bot.delete_webhook(drop_pending_updates=True)
    log.info("=" * 50)
    log.info("🤖 البوت يعمل الآن — Polling Mode")
    log.info(f"📁 DB: {settings.DB_PATH}")
    log.info("=" * 50)

    MAX_RETRIES = 3
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # مسح أي ويب هوك قديم وتحديثات معلقة قبل البدء بالـ polling
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
                handle_signals=False,
            )
            break  # خرج بشكل طبيعي
        except TelegramConflictError:
            log.warning(
                f"⚠️  تعارض في الجلسة (محاولة {attempt}/{MAX_RETRIES}) — "
                "تأكد من إغلاق أي نسخة بوت أخرى"
            )
            if attempt < MAX_RETRIES:
                wait = attempt * 5
                log.info(f"⏳ انتظار {wait}ث ثم إعادة المحاولة …")
                await bot.session.close()
                await _kill_old_sessions(settings.BOT_TOKEN)
                # أعد إنشاء Bot لأن الـ session أُغلق
                bot = Bot(
                    token=settings.BOT_TOKEN,
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
                )
                await asyncio.sleep(wait)
            else:
                log.error(
                    "❌ فشل تشغيل البوت بعد عدة محاولات.\n"
                    "   ► أغلق أي terminal آخر يشغّل البوت وأعد التشغيل."
                )
        except Exception as e:
            log.error(f"❌ خطأ في البوت: {e}")
            break
        finally:
            try:
                await bot.session.close()
            except Exception:
                pass


def run_bot_thread():
    """تشغيل البوت في thread منفصل بـ event loop خاص"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


# ─────────────────────────────────────────────────────────────────
# 3. Ngrok — نفق HTTPS للاختبار المحلي
# ─────────────────────────────────────────────────────────────────
def run_ngrok(flask_port: int = 5000) -> str | None:
    """فتح نفق Ngrok وإرجاع الرابط العام"""
    time.sleep(2)  # انتظر Flask يبدأ
    try:
        from pyngrok import ngrok, conf

        # توكن Ngrok من .env (اختياري)
        ngrok_token = os.environ.get("NGROK_AUTHTOKEN", "")
        if ngrok_token:
            conf.get_default().auth_token = ngrok_token

        # أغلق أي أنفاق قديمة
        for t in ngrok.get_tunnels():
            ngrok.disconnect(t.public_url)

        tunnel = ngrok.connect(flask_port, "http")
        public_url = tunnel.public_url.replace("http://", "https://")

        log.info("=" * 60)
        log.info(f"🌐 NGROK URL   : {public_url}")
        log.info(f"📱 Mini App    : {public_url}/")
        log.info(f"🔗 Admin Panel : {public_url}/admin")
        log.info(f"❤️  Health      : {public_url}/api/health")
        log.info("=" * 60)

        # تحديث config.js بالرابط الجديد
        _update_config_js(public_url)

        # تحديث Webhook في .env
        _patch_env("WEBHOOK_HOST", public_url)

        return public_url

    except ImportError:
        log.warning("⚠️  pyngrok غير مثبت — شغّل: pip install pyngrok")
        log.info("💡 يمكنك تشغيل ngrok يدوياً: ngrok http 5000")
        return None
    except Exception as e:
        log.error(f"❌ خطأ في Ngrok: {e}")
        return None


def _update_config_js(public_url: str):
    """تحديث ملف config.js بالرابط العام"""
    paths = [
        os.path.join(os.path.dirname(__file__), "config.js"),
        os.path.join(os.path.dirname(__file__), "webapp", "config.js"),
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read()
                import re
                content = re.sub(
                    r'(API_BASE\s*[=:]\s*)["\'].*?["\']',
                    rf'\1"{public_url}"',
                    content,
                )
                with open(p, "w", encoding="utf-8") as f:
                    f.write(content)
                log.info(f"✅ تم تحديث {p}")
            except Exception as e:
                log.warning(f"⚠️  لم يتم تحديث {p}: {e}")


def _patch_env(key: str, value: str):
    """تحديث قيمة في ملف .env"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                updated = True
                break
        if not updated:
            lines.append(f"{key}={value}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        log.warning(f"لم يتم تحديث .env: {e}")


# ─────────────────────────────────────────────────────────────────
# 4. تعيين Webhook للبوت (اختياري — للإنتاج)
# ─────────────────────────────────────────────────────────────────
async def set_webhook(public_url: str):
    """تعيين webhook للبوت على المسار /webhook"""
    if not settings.BOT_TOKEN or not public_url:
        return
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    webhook_url = f"{public_url}/webhook"
    bot = Bot(token=settings.BOT_TOKEN,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
        log.info(f"🔗 Webhook تم التعيين: {webhook_url}")
    except Exception as e:
        log.warning(f"⚠️  لم يتم تعيين Webhook: {e}")
    finally:
        await bot.session.close()


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="أكاديمية يامن — تشغيل موحد")
    parser.add_argument("--no-ngrok",  action="store_true", help="بدون Ngrok")
    parser.add_argument("--bot-only",  action="store_true", help="بوت فقط")
    parser.add_argument("--web-only",  action="store_true", help="Flask فقط")
    parser.add_argument("--port",      type=int, default=int(os.environ.get("PORT", 8080)), help="منفذ Flask")
    parser.add_argument("--webhook",   action="store_true", help="استخدام Webhook بدل Polling")
    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════════╗
║        🎓 أكاديمية يامن — TOEFL Academy System          ║
╚══════════════════════════════════════════════════════════╝
""")

    threads = []

    # ── سيرفر Flask ───────────────────────────────────────────
    if not args.bot_only:
        flask_thread = threading.Thread(
            target=run_flask, args=(args.port,), daemon=True, name="Flask"
        )
        flask_thread.start()
        threads.append(flask_thread)
        log.info(f"🚀 Flask Thread بدأ على port {args.port}")

    # ── Ngrok ─────────────────────────────────────────────────
    public_url = None
    if not args.no_ngrok and not args.bot_only:
        public_url = run_ngrok(args.port)
        if public_url and args.webhook:
            asyncio.run(set_webhook(public_url))

    # ── بوت تليجرام ───────────────────────────────────────────
    if not args.web_only:
        if args.webhook and public_url:
            # وضع Webhook — Flask يستقبل الطلبات
            log.info("🔗 البوت في وضع Webhook — يعمل عبر Flask")
        else:
            # وضع Polling (الافتراضي)
            bot_thread = threading.Thread(
                target=run_bot_thread, daemon=True, name="TelegramBot"
            )
            bot_thread.start()
            threads.append(bot_thread)
            log.info("🤖 Bot Thread بدأ — Polling Mode")

    log.info("\n✅ المنظومة تعمل بالكامل! اضغط Ctrl+C للإيقاف.\n")

    try:
        while True:
            time.sleep(1)
            # تحقق أن الـ threads ما زالت تعمل
            for t in threads:
                if not t.is_alive():
                    log.warning(f"⚠️  Thread '{t.name}' توقف بشكل غير متوقع!")
    except KeyboardInterrupt:
        log.info("\n⛔ تم إيقاف المنظومة. مع السلامة!")
        sys.exit(0)


if __name__ == "__main__":
    main()
