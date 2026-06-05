# -*- coding: utf-8 -*-
"""
wsgi.py - Production entry point for gunicorn / Railway web service.
Usage: gunicorn -w 2 -b 0.0.0.0:$PORT wsgi:app
"""
import os

# Ensure DB_PATH is set BEFORE importing app
if not os.environ.get("DB_PATH"):
    if os.path.isdir("/app/data"):
        os.environ["DB_PATH"] = "/app/data/academy.db"
    else:
        os.environ["DB_PATH"] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "academy.db"
        )

try:
    from init_db import ensure_db
    ensure_db()
except Exception as _e:
    print(f"[wsgi] init_db skipped: {_e}")

from app import app  # noqa: E402

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
