# -*- coding: utf-8 -*-
"""Auto-migration: sync students.is_paid with active subscriptions + add triggers"""
import sqlite3, os, sys

def run(db_path=None):
    db_path = db_path or os.environ.get("DB_PATH") or "/app/data/academy.db"
    if not os.path.exists(db_path):
        print(f"[sync_paid] DB not found: {db_path}")
        return
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("""
        UPDATE students SET is_paid = 1
         WHERE telegram_id IN (
            SELECT CAST(telegram_id AS INTEGER) FROM subscriptions
             WHERE is_active = 1
               AND (end_date IS NULL OR date(end_date) >= date('now'))
         )
    """)
    synced = cur.rowcount
    cur.execute("DROP TRIGGER IF EXISTS trg_sub_insert_set_paid")
    cur.execute("""
        CREATE TRIGGER trg_sub_insert_set_paid
        AFTER INSERT ON subscriptions
        WHEN NEW.is_active = 1
        BEGIN
            UPDATE students SET is_paid = 1
             WHERE telegram_id = CAST(NEW.telegram_id AS INTEGER)
                OR telegram_id = NEW.user_id;
        END
    """)
    cur.execute("DROP TRIGGER IF EXISTS trg_sub_update_set_paid")
    cur.execute("""
        CREATE TRIGGER trg_sub_update_set_paid
        AFTER UPDATE OF is_active ON subscriptions
        WHEN NEW.is_active = 1
        BEGIN
            UPDATE students SET is_paid = 1
             WHERE telegram_id = CAST(NEW.telegram_id AS INTEGER)
                OR telegram_id = NEW.user_id;
        END
    """)
    con.commit()
    con.close()
    print(f"[sync_paid] synced={synced}, triggers installed")

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
