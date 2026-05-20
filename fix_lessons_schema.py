import sqlite3, sys

DB = "academy.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

# الأعمدة المطلوبة من app.py (INSERT في api_add_lesson)
required = {
    "title":         "TEXT",
    "title_ar":      "TEXT",
    "description":   "TEXT",
    "skill":         "TEXT DEFAULT 'reading'",
    "phase":         "INTEGER DEFAULT 1",
    "order_num":     "INTEGER DEFAULT 0",
    "content":       "TEXT",
    "xp_reward":     "INTEGER DEFAULT 10",
    "timer_minutes": "INTEGER DEFAULT 0",
    "is_active":     "INTEGER DEFAULT 1",
}

# اقرأ الأعمدة الحالية
cur.execute("PRAGMA table_info(lessons)")
existing = {row[1]: row[2] for row in cur.fetchall()}
print("📋 الأعمدة الحالية في جدول lessons:")
for c, t in existing.items():
    print(f"   - {c} ({t})")

# جد الناقصة
missing = [c for c in required if c not in existing]
print(f"\n🔍 الأعمدة الناقصة: {missing if missing else 'لا شيء — الجدول كامل'}")

# أضف الناقصة
for col in missing:
    sql = f"ALTER TABLE lessons ADD COLUMN {col} {required[col]}"
    try:
        cur.execute(sql)
        print(f"   ✅ أُضيف: {col}")
    except sqlite3.OperationalError as e:
        print(f"   ⚠️  {col}: {e}")

conn.commit()

# تأكيد نهائي
cur.execute("PRAGMA table_info(lessons)")
final = [row[1] for row in cur.fetchall()]
print(f"\n📋 الأعمدة بعد الإصلاح ({len(final)}):")
print("   " + ", ".join(final))

# تأكد إن جميع المطلوبة موجودة
still_missing = [c for c in required if c not in final]
if still_missing:
    print(f"\n❌ لا تزال ناقصة: {still_missing}")
    sys.exit(1)
else:
    print("\n✅ جدول lessons جاهز بالكامل")

conn.close()
