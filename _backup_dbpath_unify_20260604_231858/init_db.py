# -*- coding: utf-8 -*-
"""
init_db.py — Initialize SQLite DB safely.
- On Railway: seed /app/data/academy.db from repo if empty/broken.
- Locally: no-op (returns True), the local academy.db is used directly.
"""
import os
import shutil
import sqlite3

VOLUME_DIR = "/app/data"
VOLUME_DB = os.path.join(VOLUME_DIR, "academy.db")
REPO_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")
MIN_DB_SIZE = 100 * 1024  # 100 KB

CRITICAL_TABLES = [
    "students", "lessons", "lesson_questions",
    "subscription_plans", "stages",
]


def _get_tables(db_path):
    try:
        conn = sqlite3.connect(db_path)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        return tables
    except Exception as e:
        print(f"[init_db] cannot read tables from {db_path}: {e}")
        return []


def _validate(db_path):
    tables = _get_tables(db_path)
    missing = [t for t in CRITICAL_TABLES if t not in tables]
    return (len(missing) == 0, missing, len(tables))


def ensure_db():
    """Only acts when running on Railway (volume exists)."""
    try:
        if not os.path.isdir(VOLUME_DIR):
            # Local dev — nothing to do
            print(f"[init_db] local mode (no {VOLUME_DIR}), skipping seed")
            return True

        os.makedirs(VOLUME_DIR, exist_ok=True)

        if not os.path.exists(REPO_DB):
            print(f"[init_db] WARN: no seed DB at {REPO_DB}")
            return False

        repo_ok, repo_missing, repo_tables = _validate(REPO_DB)
        repo_size = os.path.getsize(REPO_DB)
        print(f"[init_db] seed DB: {repo_size/1024:.1f}KB, {repo_tables} tables, valid={repo_ok}")

        if os.path.exists(VOLUME_DB):
            vol_size = os.path.getsize(VOLUME_DB)
            vol_ok, vol_missing, vol_tables = _validate(VOLUME_DB)
            print(f"[init_db] volume DB: {vol_size/1024:.1f}KB, {vol_tables} tables, valid={vol_ok}")

            if vol_size < MIN_DB_SIZE or not vol_ok:
                try:
                    shutil.copy2(VOLUME_DB, VOLUME_DB + ".broken")
                except Exception:
                    pass
                shutil.copy2(REPO_DB, VOLUME_DB)
                print(f"[init_db] volume DB replaced with seed")
                return True

            print(f"[init_db] using existing volume DB")
            return True

        shutil.copy2(REPO_DB, VOLUME_DB)
        print(f"[init_db] seeded volume DB ({os.path.getsize(VOLUME_DB)/1024:.1f}KB)")
        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[init_db] ERROR: {e}")
        return False


if __name__ == "__main__":
    ensure_db()
