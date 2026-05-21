# -*- coding: utf-8 -*-
"""
init_db.py - Initialize SQLite DB on Railway Volume
Runs at container startup. If Volume is empty, copies seed DB from repo.
"""
import os
import shutil

VOLUME_DIR = "/app/data"
VOLUME_DB = "/app/data/academy.db"
REPO_DB = "/app/academy.db"

def ensure_db():
    """Make sure academy.db exists in the Railway Volume."""
    try:
        # Create volume directory if it doesn't exist
        os.makedirs(VOLUME_DIR, exist_ok=True)
        print(f"[init_db] Volume directory ready: {VOLUME_DIR}")

        # If DB already in volume, use it
        if os.path.exists(VOLUME_DB):
            size_kb = os.path.getsize(VOLUME_DB) / 1024
            print(f"[init_db] ✅ DB exists in Volume ({size_kb:.1f} KB) - using existing")
            return True

        # Otherwise, copy seed DB from repo to volume
        if os.path.exists(REPO_DB):
            shutil.copy2(REPO_DB, VOLUME_DB)
            size_kb = os.path.getsize(VOLUME_DB) / 1024
            print(f"[init_db] ✅ Seeded DB from repo to Volume ({size_kb:.1f} KB)")
            return True

        # Neither exists - warning
        print(f"[init_db] ⚠️ WARNING: No source DB found!")
        print(f"[init_db]    Checked: {REPO_DB}")
        print(f"[init_db]    Checked: {VOLUME_DB}")
        return False

    except Exception as e:
        print(f"[init_db] ❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    ensure_db()
