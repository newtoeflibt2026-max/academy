import sqlite3
conn = sqlite3.connect("academy.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 60)
print("📊 الباقات الحالية (subscription_plans)")
print("=" * 60)
cur.execute("SELECT id, name, name_ar, price, duration_days, is_active FROM subscription_plans ORDER BY price, id")
for r in cur.fetchall():
    star = "⭐" if r["is_active"] else "  "
    print(f"  {star} [{r['id']:3}] {r['name']:15s} | {r['name_ar']:25s} | {r['price']:>10,.0f} | {r['duration_days']} يوم")

print(f"\nالمجموع: {cur.execute('SELECT COUNT(*) FROM subscription_plans').fetchone()[0]} باقة")

print("\n" + "=" * 60)
print("📊 الطلاب الحاليين")
print("=" * 60)
cur.execute("SELECT user_id, full_name, username, is_paid, is_active FROM students")
for r in cur.fetchall():
    paid = "💰" if r["is_paid"] else "  "
    print(f"  {paid} [{r['user_id']}] {r['full_name'] or '(فارغ)':20s} @{r['username'] or '-'}")

print("\n" + "=" * 60)
print("📊 آخر الدروس المضافة (آخر 10)")
print("=" * 60)
cur.execute("SELECT id, title, content FROM lessons ORDER BY id DESC LIMIT 10")
for r in cur.fetchall():
    print(f"  [{r['id']:3}] {(r['title'] or '')[:40]:40s} | محتوى: {(r['content'] or '')[:30]}")

print("\n" + "=" * 60)
print("📊 آخر الأسئلة المضافة (آخر 10)")
print("=" * 60)
cur.execute("SELECT id, question_text, skill FROM questions ORDER BY id DESC LIMIT 10")
for r in cur.fetchall():
    print(f"  [{r['id']:3}] {(r['question_text'] or '')[:40]:40s} | {r['skill']}")

conn.close()
