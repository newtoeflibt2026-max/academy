import sqlite3
conn = sqlite3.connect("academy.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# هل في اشتراكات فعلية مرتبطة بباقات راح نحذفها؟
print("=" * 60)
print("📊 المدفوعات الحالية (payments)")
print("=" * 60)
try:
    cur.execute("SELECT id, user_id, plan_id, amount, status FROM payments ORDER BY id DESC")
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  [{r['id']:3}] user={r['user_id']} plan={r['plan_id']} amount={r['amount']} status={r['status']}")
    else:
        print("  لا توجد مدفوعات")
except Exception as e:
    print(f"❌ {e}")

# هل في جدول subscriptions؟
print("\n" + "=" * 60)
print("📊 الاشتراكات (subscriptions) إن وُجد الجدول")
print("=" * 60)
try:
    cur.execute("SELECT * FROM subscriptions LIMIT 20")
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  {dict(r)}")
    else:
        print("  لا توجد اشتراكات")
except Exception as e:
    print(f"  (لا يوجد جدول subscriptions: {e})")

# تأكيد أعمدة جدول payments
print("\n" + "=" * 60)
print("📊 أعمدة جدول payments")
print("=" * 60)
cur.execute("PRAGMA table_info(payments)")
for c in cur.fetchall():
    print(f"  - {c[1]} ({c[2]})")

conn.close()
