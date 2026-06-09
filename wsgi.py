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

from app import app  # noqa: E402
print("[wsgi] Flask app imported successfully", flush=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

# === Auto-register Telegram webhook on Railway startup ===
try:
    from bot_webhook import register_webhook_with_telegram
    register_webhook_with_telegram()
except Exception as _wh_err:
    print(f"[wsgi] webhook setup skipped: {_wh_err}")

