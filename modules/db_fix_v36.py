# modules/db_fix_v36.py
"""ينظف السجلات المكررة ويضيف UNIQUE constraints لمنع التكرار مستقبلاً"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_storage", "yamen.db")

def cleanup_and_constrain():
    print("=" * 55)
    print("🧹 v36 Database Cleanup & Constraint Fix")
    print("=" * 55)

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # ── 1. تنظيف lesson_progress المكررة ──────────────────────────────────
    c.execute("SELECT COUNT(*) FROM lesson_progress")
    before_lp = c.fetchone()[0]
    c.execute("""
        DELETE FROM lesson_progress
        WHERE rowid NOT IN (
            SELECT MIN(rowid) FROM lesson_progress GROUP BY user_id, lesson_id
        )
    """)
    removed_lp = c.rowcount
    c.execute("SELECT COUNT(*) FROM lesson_progress")
    after_lp = c.fetchone()[0]
    print(f"   lesson_progress: {before_lp} → {after_lp} (حُذف {removed_lp} مكرر)")

    # ── 2. تنظيف payments المكررة (نفس المستخدم + نفس الباقة) ──────────────
    c.execute("SELECT COUNT(*) FROM payments")
    before_p = c.fetchone()[0]
    c.execute("""
        DELETE FROM payments
        WHERE rowid NOT IN (
            SELECT MIN(rowid) FROM payments GROUP BY user_id, plan_key
        )
    """)
    removed_p = c.rowcount
    c.execute("SELECT COUNT(*) FROM payments")
    after_p = c.fetchone()[0]
    print(f"   payments: {before_p} → {after_p} (حُذف {removed_p} مكرر)")

    # ── 3. تنظيف subscriptions المكررة ────────────────────────────────────
    c.execute("SELECT COUNT(*) FROM subscriptions")
    before_s = c.fetchone()[0]
    c.execute("""
        DELETE FROM subscriptions
        WHERE rowid NOT IN (
            SELECT MIN(rowid) FROM subscriptions GROUP BY user_id
        )
    """)
    removed_s = c.rowcount
    c.execute("SELECT COUNT(*) FROM subscriptions")
    after_s = c.fetchone()[0]
    print(f"   subscriptions: {before_s} → {after_s} (حُذف {removed_s} مكرر)")

    # ── 4. تنظيف placement_results المكررة (نفس المستخدم) ─────────────────
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='placement_results'")
    if c.fetchone():
        c.execute("SELECT COUNT(*) FROM placement_results")
        before_pr = c.fetchone()[0]
        c.execute("""
            DELETE FROM placement_results
            WHERE rowid NOT IN (
                SELECT MIN(rowid) FROM placement_results GROUP BY student_id
            )
        """)
        removed_pr = c.rowcount
        c.execute("SELECT COUNT(*) FROM placement_results")
        after_pr = c.fetchone()[0]
        print(f"   placement_results: {before_pr} → {after_pr} (حُذف {removed_pr} مكرر)")
    else:
        print("   ⚠️ placement_results table not found — skipping")

    # ── 5. إضافة UNIQUE constraints إذا لم تكن موجودة ─────────────────────
    constraints = [
        ("uq_lesson_progress_user_lesson", "lesson_progress(user_id, lesson_id)"),
        ("uq_payments_user_plan",           "payments(user_id, plan_key)"),
        ("uq_subscriptions_user",           "subscriptions(user_id)"),
    ]
    for name, cols in constraints:
        try:
            c.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {cols}")
            print(f"   ✅ {name} — تم")
        except Exception as e:
            print(f"   ⚠️ {name}: {e}")

    conn.commit()
    conn.close()
    print("=" * 55)
    print("✅ اكتمل التنظيف — جميع القيود مفعلة")
    print("=" * 55)

if __name__ == "__main__":
    cleanup_and_constrain()
