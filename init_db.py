# -*- coding: utf-8 -*-
"""
init_db.py - Initialize SQLite DB on Railway Volume
- Copies seed DB from repo if Volume is empty or DB is missing
- Replaces DB if Volume DB is too small (likely empty/corrupted)
"""
import os
import shutil

VOLUME_DIR = "/app/data"
VOLUME_DB = "/app/data/academy.db"
REPO_DB = "/app/academy.db"
MIN_DB_SIZE = 100 * 1024  # 100 KB - if smaller, consider it empty/broken

def ensure_db():
    """Make sure academy.db exists and has data in the Railway Volume."""
    try:
        os.makedirs(VOLUME_DIR, exist_ok=True)
        print(f"[init_db] Volume directory ready: {VOLUME_DIR}")

        # Check if seed DB exists in repo
        if not os.path.exists(REPO_DB):
            print(f"[init_db] ⚠️ WARNING: No seed DB in repo at {REPO_DB}")
            return False

        repo_size = os.path.getsize(REPO_DB)
        print(f"[init_db] Repo seed DB: {repo_size/1024:.1f} KB")

        # If Volume DB exists and has data, use it
        if os.path.exists(VOLUME_DB):
            vol_size = os.path.getsize(VOLUME_DB)
            print(f"[init_db] Volume DB found: {vol_size/1024:.1f} KB")

            # Check if Volume DB is too small (empty or corrupted)
            if vol_size < MIN_DB_SIZE:
                print(f"[init_db] ⚠️ Volume DB too small ({vol_size} bytes < {MIN_DB_SIZE})")
                print(f"[init_db] 🔄 Replacing with fresh seed from repo...")
                shutil.copy2(REPO_DB, VOLUME_DB)
                new_size = os.path.getsize(VOLUME_DB)
                print(f"[init_db] ✅ DB replaced ({new_size/1024:.1f} KB)")
                return True

            print(f"[init_db] ✅ Using existing Volume DB ({vol_size/1024:.1f} KB)")
            return True

        # Volume DB doesn't exist - seed from repo
        shutil.copy2(REPO_DB, VOLUME_DB)
        new_size = os.path.getsize(VOLUME_DB)
        print(f"[init_db] ✅ Seeded DB from repo to Volume ({new_size/1024:.1f} KB)")
        return True

    except Exception as e:
        print(f"[init_db] ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    ensure_db()
