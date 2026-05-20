import sqlite3

conn = sqlite3.connect("academy.db")
conn.row_factory = sqlite3.Row

# ============================================================
# 1. تحقق من أعمدة جدول students
# ============================================================
cols = [r[1] for r in conn.execute("PRAGMA table_info(students)").fetchall()]
print("students columns:", cols)

# ============================================================
# 2. تحقق من أعمدة subscription_plans
# ============================================================
cols2 = [r[1] for r in conn.execute("PRAGMA table_info(subscription_plans)").fetchall()]
print("subscription_plans columns:", cols2)

# ============================================================
# 3. اعرض الباقات الموجودة
# ============================================================
plans = conn.execute("SELECT * FROM subscription_plans WHERE is_active=1").fetchall()
print(f"\nActive plans ({len(plans)}):")
for p in plans:
    print("  ", dict(p))

# ============================================================
# 4. اعرض بيانات الطالب
# ============================================================
s = conn.execute("SELECT * FROM students WHERE telegram_id=5572314718").fetchone()
if s:
    print("\nStudent:", dict(s))
else:
    print("\nStudent NOT FOUND")

conn.close()
