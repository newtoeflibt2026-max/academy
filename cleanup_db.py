import sqlite3
conn = sqlite3.connect("academy.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 60)
print("🧹 بدء تنظيف قاعدة البيانات")
print("=" * 60)

# ── 1) تنظيف الباقات ───────────────────────────
print("\n[1/6] 📦 تنظيف الباقات...")
before = cur.execute("SELECT COUNT(*) FROM subscription_plans").fetchone()[0]

# احذف كل ما عدا IDs 61, 62, 63
cur.execute("DELETE FROM subscription_plans WHERE id NOT IN (61, 62, 63)")
deleted = cur.rowcount

# تأكد أن الباقات الباقية بإعدادات صحيحة (JOD، أسعار صحيحة)
cur.execute("""UPDATE subscription_plans
               SET currency='JOD', is_active=1
               WHERE id IN (61, 62, 63)""")

# تأكد من الأسعار:
cur.execute("UPDATE subscription_plans SET price=0,  duration_days=7  WHERE id=61")  # free
cur.execute("UPDATE subscription_plans SET price=25, duration_days=30 WHERE id=62")  # basic
cur.execute("UPDATE subscription_plans SET price=45, duration_days=90 WHERE id=63")  # standard/premium

# اجعل الباقة الوسطى مميزة (featured)
try:
    cur.execute("UPDATE subscription_plans SET is_featured=0")
    cur.execute("UPDATE subscription_plans SET is_featured=1 WHERE id=62")
except Exception:
    pass

after = cur.execute("SELECT COUNT(*) FROM subscription_plans").fetchone()[0]
print(f"   حذف: {deleted} | باقي: {after}")

# ── 2) تنظيف الطلاب ────────────────────────────
print("\n[2/6] 👥 تنظيف الطلاب التجريبيين...")
before = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]

# احذف كل الطلاب ما عدا الأدمن
cur.execute("DELETE FROM students WHERE user_id != 5572314718")
deleted = cur.rowcount

# تأكد أن الأدمن مفعّل ومدفوع
cur.execute("""UPDATE students
               SET is_paid=1, is_active=1, full_name='Yamen Academy Admin'
               WHERE user_id=5572314718""")

after = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]
print(f"   حذف: {deleted} | باقي: {after}")

# ── 3) تنظيف الدروس التجريبية ──────────────────
print("\n[3/6] 📚 تنظيف الدروس التجريبية...")
before = cur.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]

# احذف الدروس IDs 14-18 (التجريبية: سس، لق، يسيس، سللقفق، 555555)
cur.execute("DELETE FROM lessons WHERE id IN (14, 15, 16, 17, 18)")
deleted = cur.rowcount

after = cur.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
print(f"   حذف: {deleted} | باقي: {after}")

# ── 4) تنظيف الأسئلة التجريبية ─────────────────
print("\n[4/6] ❓ تنظيف الأسئلة التجريبية...")
before = cur.execute("SELECT COUNT(*) FROM questions").fetchone()[0]

# احذف الأسئلة IDs 21-24 (التجريبية)
cur.execute("DELETE FROM questions WHERE id IN (21, 22, 23, 24)")
deleted = cur.rowcount

after = cur.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
print(f"   حذف: {deleted} | باقي: {after}")

# ── 5) تنظيف المدفوعات التجريبية ───────────────
print("\n[5/6] 💳 تنظيف المدفوعات التجريبية...")
before = cur.execute("SELECT COUNT(*) FROM payments").fetchone()[0]

cur.execute("DELETE FROM payments")
deleted = cur.rowcount

after = cur.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
print(f"   حذف: {deleted} | باقي: {after}")

# ── 6) تنظيف الجداول المرتبطة (إن وُجدت) ───────
print("\n[6/6] 🔗 تنظيف بيانات مرتبطة...")
related = ["subscriptions", "broadcast_history", "user_progress", "user_xp",
           "user_lessons", "user_missions", "messages", "student_messages"]
for t in related:
    try:
        # احذف فقط ما لا يخص الأدمن (إن كان فيه عمود user_id أو telegram_id)
        cur.execute(f"PRAGMA table_info({t})")
        cols = [c[1] for c in cur.fetchall()]
        if not cols:
            continue
        n_before = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        if "user_id" in cols:
            cur.execute(f"DELETE FROM {t} WHERE user_id != 5572314718")
        elif "telegram_id" in cols:
            cur.execute(f"DELETE FROM {t} WHERE telegram_id != '5572314718' AND telegram_id != 5572314718")
        else:
            cur.execute(f"DELETE FROM {t}")
        n_after = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"   {t}: حذف {n_before - n_after} | باقي: {n_after}")
    except Exception as e:
        print(f"   {t}: (تخطّى - {e})")

conn.commit()

# VACUUM لاسترجاع المساحة
print("\n🔧 ضغط قاعدة البيانات (VACUUM)...")
conn.execute("VACUUM")

print("\n" + "=" * 60)
print("✅ تم التنظيف بنجاح!")
print("=" * 60)

# تقرير نهائي
print("\n📊 الحالة النهائية:")
for t in ["subscription_plans", "students", "lessons", "questions", "payments", "missions"]:
    try:
        c = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"   {t:25s} → {c}")
    except Exception as e:
        print(f"   {t:25s} → (خطأ: {e})")

print("\n📋 الباقات النهائية:")
cur.execute("SELECT id, name, name_ar, price, currency, duration_days, is_featured FROM subscription_plans ORDER BY price")
for r in cur.fetchall():
    star = "⭐" if r["is_featured"] else "  "
    price_t = f"{r['price']:.0f} {r['currency']}" if r['price'] else "مجاناً"
    print(f"   {star} [{r['id']}] {r['name_ar']:25s} | {price_t:>15s} | {r['duration_days']} يوم")

conn.close()
