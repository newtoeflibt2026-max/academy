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

# 2.5) F3 Migration - يضيف F3 + next_review دون مساس ببيانات الطلاب
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from migrations.apply_f3 import apply_f3_migration
    apply_f3_migration()
    print("[wsgi] F3 migration applied", flush=True)
except Exception as _e:
    print(f"[wsgi] F3 migration skipped: {_e}", flush=True)


# 3) BOOTSTRAP: ensure stages table exists + F1-F4 seeded
def _bootstrap_stages():
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track TEXT,
            code TEXT UNIQUE,
            name_ar TEXT,
            name_en TEXT,
            description TEXT,
            section_name TEXT,
            order_num INTEGER,
            gatekeeper_threshold INTEGER DEFAULT 80,
            is_active INTEGER DEFAULT 1,
            is_locked_future INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            order_index INTEGER DEFAULT 0,
            path TEXT,
            min_score INTEGER DEFAULT 80,
            exam_questions_count INTEGER DEFAULT 10
        )""")
        cur.execute("SELECT COUNT(*) FROM stages WHERE code LIKE 'F%'")
        n = cur.fetchone()[0]
        print(f"[wsgi.boot] stages F-rows before: {n}", flush=True)
        if n < 4:
            seeds = [
                ("foundation","F1","??????? - ??????? ???????","Foundation 1","?????","foundation",1,80,1,0,1,"foundation",80,10),
                ("foundation","F2","??????? - ?????? ??????","Foundation 2","??????","foundation",2,80,1,0,2,"foundation",80,10),
                ("foundation","F3","??????? - ????? ??????","Foundation 3","?????","foundation",3,80,1,0,3,"foundation",80,10),
                ("foundation","F4","??????? - ????? ???? ??????","Foundation 4","?????","foundation",4,80,1,0,4,"foundation",80,10),
            ]
            for row in seeds:
                cur.execute("""INSERT OR IGNORE INTO stages
                  (track,code,name_ar,name_en,description,section_name,order_num,gatekeeper_threshold,is_active,is_locked_future,order_index,path,min_score,exam_questions_count)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", row)
            con.commit()
            cur.execute("SELECT COUNT(*) FROM stages WHERE code LIKE 'F%'")
            n2 = cur.fetchone()[0]
            print(f"[wsgi.boot] stages F-rows AFTER seed: {n2}", flush=True)
        # ensure stage_progress table
        cur.execute("""CREATE TABLE IF NOT EXISTS stage_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            stage_id INTEGER,
            gatekeeper_passed INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, stage_id)
        )""")
        con.commit()
        con.close()
        print("[wsgi.boot] stages + stage_progress OK", flush=True)
    except Exception as e:
        print(f"[wsgi.boot] ERROR: {e}", flush=True)
        import traceback; traceback.print_exc()

_bootstrap_stages()

# 4) import Flask app
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

