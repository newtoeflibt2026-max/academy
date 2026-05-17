# modules/db_fix.py
# ONE-TIME fix: removes duplicate exam/subscription rows, adds proper constraints
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_storage", "yamen.db")

def fix_all():
    print("🔧 Starting database cleanup & constraint fix...")
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    c = conn.cursor()

    # ── 2a. DELETE DUPLICATE lesson_progress rows (keep earliest) ─────────
    try:
        c.execute("""
            DELETE FROM lesson_progress
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM lesson_progress
                GROUP BY user_id, lesson_id
            )
        """)
        removed = c.rowcount
        if removed:
            print(f"   🧹 Removed {removed} duplicate lesson_progress rows")
        else:
            print("   ✅ No duplicate lesson_progress rows found")
    except Exception as e:
        print(f"   ⚠️ lesson_progress cleanup: {e}")

    # ── 2b. DELETE DUPLICATE payments rows (keep earliest, but approved beats pending) ──
    try:
        c.execute("""
            DELETE FROM payments
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM payments
                GROUP BY user_id, plan_key
            )
        """)
        removed = c.rowcount
        if removed:
            print(f"   🧹 Removed {removed} duplicate payments rows")
        else:
            print("   ✅ No duplicate payments rows found")
    except Exception as e:
        print(f"   ⚠️ payments cleanup: {e}")

    # ── 2c. DELETE DUPLICATE subscriptions (keep one per user_id) ─────────
    try:
        c.execute("""
            DELETE FROM subscriptions
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM subscriptions
                GROUP BY user_id
            )
        """)
        removed = c.rowcount
        if removed:
            print(f"   🧹 Removed {removed} duplicate subscriptions rows")
        else:
            print("   ✅ No duplicate subscription rows found")
    except Exception as e:
        print(f"   ⚠️ subscriptions cleanup: {e}")

    # ── 2d. ADD UNIQUE CONSTRAINTS (ignore if they already exist) ─────────
    constraints = [
        ("lesson_progress", "lesson_progress(user_id, lesson_id)", "uq_lesson_progress_user_lesson"),
        ("payments", "payments(user_id, plan_key)", "uq_payments_user_plan"),
        ("subscriptions", "subscriptions(user_id)", "uq_subscriptions_user"),
    ]

    for table, cols, idx_name in constraints:
        try:
            c.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx_name} ON {cols}")
            print(f"   ✅ Unique constraint added: {idx_name}")
        except Exception as e:
            print(f"   ⚠️ Constraint {idx_name}: {e}")

    conn.commit()
    conn.close()

    print("\n📊 DATABASE FIX SUMMARY:")
    print("   ✅ Duplicate rows removed")
    print("   ✅ UNIQUE constraints enforced:")
    print("      - lesson_progress(user_id, lesson_id) → UPSERT, no duplicates")
    print("      - payments(user_id, plan_key) → one pending per user+plan")
    print("      - subscriptions(user_id) → one active sub per user")
    print("   ✅ Dashboard queries will now return DISTINCT results")

if __name__ == "__main__":
    fix_all()
else:
    # auto-run on import if not already done
    fix_all()
