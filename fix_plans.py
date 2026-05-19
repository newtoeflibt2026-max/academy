# -*- coding: utf-8 -*-
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")
conn = sqlite3.connect(DB_PATH)

# 1. افحص الأعمدة الموجودة
cols = [r[1] for r in conn.execute("PRAGMA table_info(subscription_plans)").fetchall()]
print("Current columns:", cols)

# 2. أضف plan_id إذا لم يكن موجوداً
if "plan_id" not in cols:
    try:
        conn.execute("ALTER TABLE subscription_plans ADD COLUMN plan_id TEXT")
        print("Added plan_id column")
    except Exception as e:
        print("plan_id:", e)

# 3. احذف المكررات وأبقِ صف واحد لكل باقة
plans = [
    ("flex_30",      "الباقة المرنة 30 يوم",    25000,  30,  1, "درس يومي + تصحيح كتابي"),
    ("excellence_90","باقة التميز 90 يوم",       60000,  90,  1, "90 يوما من التدريب المكثف"),
    ("emergency_30", "باقة الطوارئ 30 يوم",      45000,  30,  4, "تدريب مكثف 4 دروس يوميا"),
    ("vip_20h",      "VIP 20 ساعة خاصة",        400000, 60,  1, "20 ساعة تدريس خاص"),
]

# 4. احذف كل الباقات الحالية وأعد إدخالها بشكل صحيح
conn.execute("DELETE FROM subscription_plans")
print("Cleared old plans")

for plan_id, name_ar, price, days, per_day, desc in plans:
    # نكتشف اسم العمود الصحيح (plan_key أو plan_id)
    cols_now = [r[1] for r in conn.execute("PRAGMA table_info(subscription_plans)").fetchall()]
    
    if "plan_key" in cols_now and "plan_id" in cols_now:
        conn.execute(
            "INSERT INTO subscription_plans (plan_key, plan_id, name_ar, price, duration_days, lessons_per_day, description) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (plan_id, plan_id, name_ar, price, days, per_day, desc)
        )
    elif "plan_key" in cols_now:
        conn.execute(
            "INSERT INTO subscription_plans (plan_key, name_ar, price, duration_days, lessons_per_day, description) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (plan_id, name_ar, price, days, per_day, desc)
        )
    else:
        conn.execute(
            "INSERT INTO subscription_plans (plan_id, name_ar, price, duration_days, lessons_per_day, description) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (plan_id, name_ar, price, days, per_day, desc)
        )
    print("Inserted:", plan_id)

conn.commit()

# 5. تحقق من النتيجة
rows = conn.execute("SELECT * FROM subscription_plans").fetchall()
print("\nFinal plans count:", len(rows))
for r in rows:
    print(" -", r)

conn.close()
print("\nDONE!")
