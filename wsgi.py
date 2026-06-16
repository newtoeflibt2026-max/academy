# -*- coding: utf-8 -*-
"""
wsgi.py - Production entry point for gunicorn / Railway web service.
Usage: gunicorn -w 2 -b 0.0.0.0:$PORT wsgi:app
"""
import os
import sys
import sqlite3

# 1) DB_PATH
if not os.environ.get("DB_PATH"):
    if os.path.isdir("/app/data"):
        os.environ["DB_PATH"] = "/app/data/academy.db"
    else:
        os.environ["DB_PATH"] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "academy.db"
        )

DB_PATH = os.environ["DB_PATH"]
print(f"[wsgi] DB_PATH = {DB_PATH}", flush=True)

# 2) init_db
try:
    from init_db import ensure_db
    ensure_db()
    print("[wsgi] init_db ensure_db() done", flush=True)
except Exception as _e:
    print(f"[wsgi] init_db skipped: {_e}", flush=True)


# 2.4) Schema Migration - يضمن وجود كل الأعمدة المطلوبة
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from migrations.ensure_schema import ensure_schema
    ensure_schema()
    print("[wsgi] schema migration applied", flush=True)
except Exception as _e:
    print(f"[wsgi] schema migration skipped: {_e}", flush=True)

# 2.5) F3 Migration - يضيف F3 + next_review دون مساس ببيانات الطلاب
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from migrations.apply_f3 import apply_f3_migration
    apply_f3_migration()
    print("[wsgi] F3 migration applied", flush=True)
except Exception as _e:
    print(f"[wsgi] F3 migration skipped: {_e}", flush=True)

# 2.5b) F1 Migration - يضيف/يحدّث دروس F1 الكاملة (5 دروس + 70 سؤال)
try:
    from migrations.apply_f1 import apply_f1_migration
    apply_f1_migration()
    print("[wsgi] F1 migration applied", flush=True)
except Exception as _e:
    print(f"[wsgi] F1 migration skipped: {_e}", flush=True)

# 2.6) Admin Subscriptions - يفعّل اشتراك للأدمنز
try:
    from migrations.ensure_admin_subscriptions import ensure_admin_subscriptions
    ensure_admin_subscriptions()
    print("[wsgi] admin subscriptions applied", flush=True)
except Exception as _e:
    print(f"[wsgi] admin subscriptions skipped: {_e}", flush=True)

# 2.6) Show F1 + F2 lessons (rebuild order)
try:
    from migrations.show_f1_f2 import show_and_order_f1_f2
    show_and_order_f1_f2()
    print("[wsgi] show_f1_f2 migration applied")
except Exception as _e:
    print(f"[wsgi] show_f1_f2 migration failed: {_e}")


# 2.7) Hide F4 (not built yet)
try:
    from migrations.hide_f4 import hide_f4
    hide_f4()
    print("[wsgi] hide_f4 migration applied")
except Exception as _e:
    print(f"[wsgi] hide_f4 migration failed: {_e}")

from app import app  # noqa: E402
print("[wsgi] Flask app imported successfully", flush=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

# === Auto-register Telegram webhook (direct, runs under gunicorn import) ===
def _force_set_webhook():
    import os, json, urllib.request, urllib.parse
    token = os.environ.get("BOT_TOKEN", "")
    if not token:
        print("[wsgi-wh] BOT_TOKEN missing - skip", flush=True)
        return
    host = os.environ.get("WEBHOOK_HOST", "https://yamenacademyapp.up.railway.app").rstrip("/")
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "yamen-webhook-secret-2026")
    wh = host + "/telegram-webhook"
    qs = urllib.parse.urlencode({"url": wh, "secret_token": secret, "drop_pending_updates": "true"})
    api = "https://api.telegram.org/bot" + token + "/setWebhook?" + qs
    try:
        with urllib.request.urlopen(api, timeout=15) as r:
            res = json.loads(r.read().decode("utf-8"))
        if res.get("ok"):
            print("[wsgi-wh] OK webhook set -> " + wh, flush=True)
        else:
            print("[wsgi-wh] FAIL: " + str(res.get("description")), flush=True)
    except Exception as e:
        print("[wsgi-wh] ERROR: " + str(e), flush=True)

try:
    _force_set_webhook()
except Exception as _e:
    print("[wsgi-wh] outer error: " + str(_e), flush=True)


# === Webhook self-healing guardian (runs forever in background) ===
def _webhook_guardian():
    import os, time, json, urllib.request, urllib.parse
    token = os.environ.get("BOT_TOKEN", "")
    if not token:
        print("[guardian] BOT_TOKEN missing - guardian disabled", flush=True)
        return
    host = os.environ.get("WEBHOOK_HOST", "https://yamenacademyapp.up.railway.app").rstrip("/")
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "yamen-webhook-secret-2026")
    want = host + "/telegram-webhook"
    api = "https://api.telegram.org/bot" + token
    time.sleep(20)  # let app finish booting
    while True:
        try:
            with urllib.request.urlopen(api + "/getWebhookInfo", timeout=15) as r:
                info = json.loads(r.read().decode("utf-8")).get("result", {})
            cur = info.get("url", "")
            if cur != want:
                qs = urllib.parse.urlencode({"url": want, "secret_token": secret,
                    "allowed_updates": json.dumps(["message","callback_query","pre_checkout_query"])})
                with urllib.request.urlopen(api + "/setWebhook?" + qs, timeout=15) as r2:
                    res = json.loads(r2.read().decode("utf-8"))
                print("[guardian] webhook re-set -> " + want + " ok=" + str(res.get("ok")), flush=True)
        except Exception as e:
            print("[guardian] check error: " + str(e), flush=True)
        time.sleep(180)  # re-check every 3 minutes

try:
    import threading
    threading.Thread(target=_webhook_guardian, daemon=True).start()
    print("[guardian] started", flush=True)
except Exception as _ge:
    print("[guardian] failed to start: " + str(_ge), flush=True)
