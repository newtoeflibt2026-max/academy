# -*- coding: utf-8 -*-
"""
init_db.py - Initialize SQLite DB on Railway Volume
- Copies seed DB from repo if Volume is empty
- Validates critical tables exist
- Replaces DB if too small or missing key tables
"""
import os
import shutil
import sqlite3

VOLUME_DIR = "/app/data"
VOLUME_DB = "/app/data/academy.db"
REPO_DB = "/app/academy.db"
MIN_DB_SIZE = 100 * 1024  # 100 KB

# Critical tables that MUST exist for bot/web to work
CRITICAL_TABLES = [
    "students", "lessons", "lesson_questions",
    "subscription_plans", "stages", "phase_settings"
]


def _get_tables(db_path):
    """Return list of table names in the DB."""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        print(f"[init_db] Cannot read tables from {db_path}: {e}")
        return []


def _validate_schema(db_path):
    """Check that all critical tables exist."""
    tables = _get_tables(db_path)
    missing = [t for t in CRITICAL_TABLES if t not in tables]
    return (len(missing) == 0, missing, len(tables))


def ensure_db():
    """Make sure academy.db exists, has data, and has all critical tables."""
    try:
        os.makedirs(VOLUME_DIR, exist_ok=True)
        print(f"[init_db] Volume directory ready: {VOLUME_DIR}")

        # Check repo seed DB
        if not os.path.exists(REPO_DB):
            print(f"[init_db] WARNING: No seed DB at {REPO_DB}")
            return False

        repo_size = os.path.getsize(REPO_DB)
        repo_ok, repo_missing, repo_table_count = _validate_schema(REPO_DB)
        print(f"[init_db] Repo seed DB: {repo_size/1024:.1f} KB, {repo_table_count} tables, valid={repo_ok}")
        if not repo_ok:
            print(f"[init_db] Repo missing tables: {repo_missing}")

        # Check existing Volume DB
        if os.path.exists(VOLUME_DB):
            vol_size = os.path.getsize(VOLUME_DB)
            vol_ok, vol_missing, vol_table_count = _validate_schema(VOLUME_DB)
            print(f"[init_db] Volume DB: {vol_size/1024:.1f} KB, {vol_table_count} tables, valid={vol_ok}")

            # Replace if too small OR missing critical tables
            if vol_size < MIN_DB_SIZE:
                print(f"[init_db] Volume DB too small. Replacing...")
                shutil.copy2(REPO_DB, VOLUME_DB)
                print(f"[init_db] DB replaced ({os.path.getsize(VOLUME_DB)/1024:.1f} KB)")
                return True

            if not vol_ok:
                print(f"[init_db] Volume DB missing critical tables: {vol_missing}")
                print(f"[init_db] Backing up and replacing with seed...")
                # Backup current volume DB
                bak = VOLUME_DB + ".broken"
                try:
                    shutil.copy2(VOLUME_DB, bak)
                    print(f"[init_db] Backup saved to {bak}")
                except Exception as e:
                    print(f"[init_db] Could not backup: {e}")
                shutil.copy2(REPO_DB, VOLUME_DB)
                print(f"[init_db] DB replaced ({os.path.getsize(VOLUME_DB)/1024:.1f} KB)")
                return True

            print(f"[init_db] Using existing Volume DB")
            return True

        # Volume DB doesn't exist - seed from repo
        shutil.copy2(REPO_DB, VOLUME_DB)
        print(f"[init_db] Seeded DB from repo ({os.path.getsize(VOLUME_DB)/1024:.1f} KB)")
        return True

    except Exception as e:
        print(f"[init_db] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    ensure_db()