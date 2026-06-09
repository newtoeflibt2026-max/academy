# -*- coding: utf-8 -*-
"""Hide F4 (not built yet). Idempotent."""
import os, sqlite3

def hide_f4():
    db = os.environ.get("DB_PATH", "academy.db")
    print(f"[hide_f4] DB: {db}")
    if not os.path.exists(db):
        return
    con = sqlite3.connect(db)
    cur = con.cursor()
    try:
        cur.execute("UPDATE lessons SET is_active=0 WHERE stage_id=4 AND is_active=1")
        n1 = cur.rowcount
        cur.execute("UPDATE stages SET is_active=0 WHERE id=4 AND is_active=1")
        n2 = cur.rowcount
        con.commit()
        print(f"[hide_f4] ✅ lessons={n1}, stage={n2}")
    except Exception as e:
        print(f"[hide_f4] ❌ {e}")
    finally:
        con.close()

if __name__ == "__main__":
    hide_f4()