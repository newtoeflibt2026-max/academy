import sqlite3, re, os

BASE = r"C:\Users\nelt2\yamen_academy"

# ══ 1. إصلاح قاعدة البيانات ══
print("1. إصلاح قاعدة البيانات...")
db = os.path.join(BASE, "academy.db")
conn = sqlite3.connect(db)

# إصلاح جدول subscriptions
try:
    conn.execute("ALTER TABLE subscriptions ADD COLUMN telegram_id TEXT")
    conn.execute("UPDATE subscriptions SET telegram_id=CAST(user_id AS TEXT) WHERE telegram_id IS NULL")
    print("   OK: telegram_id أضيف لـ subscriptions")
except Exception as e:
    print(f"   SKIP: {e}")

# إصلاح جدول payments
try:
    conn.execute("ALTER TABLE payments ADD COLUMN telegram_id TEXT")
    conn.execute("UPDATE payments SET telegram_id=CAST(student_id AS TEXT) WHERE telegram_id IS NULL")
    print("   OK: telegram_id أضيف لـ payments")
except Exception as e:
    print(f"   SKIP: {e}")

# تأكد من وجود الجداول
conn.executescript("""
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id TEXT NOT NULL,
    plan_key TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ends_at TIMESTAMP,
    is_active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id TEXT NOT NULL,
    plan_key TEXT,
    plan_name TEXT,
    amount REAL DEFAULT 0,
    status TEXT DEFAULT 'pending',
    receipt_photo_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

conn.commit()
conn.close()
print("   OK: قاعدة البيانات جاهزة")

# ══ 2. إصلاح app.py - تكرار الدوال ══
print("\n2. إصلاح app.py...")
app_path = os.path.join(BASE, "app.py")
with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

# البحث عن الدوال المكررة وإعادة تسميتها
fixes = [
    (
        'def api_approve_payment(pid):\n    conn = get_db()\n    p    = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()\n    if p:\n        conn.execute("UPDATE payments SET status=\'\'approved\'\'',
        'def api_approve_admin_payment_v2(pid):\n    conn = get_db()\n    p    = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()\n    if p:\n        conn.execute("UPDATE payments SET status=\'\'approved\'\''
    ),
]

# الحل الأبسط: إزالة التكرار
lines = content.split('\n')
seen_routes = {}
new_lines = []
skip_until = -1
i = 0

while i < len(lines):
    line = lines[i]
    
    # كشف تعريف route
    if '@app.route(' in line and 'approve' in line.lower():
        route_sig = line.strip()
        if route_sig in seen_routes:
            # تخطي هذا الـ route والدالة التابعة له
            print(f"   SKIP duplicate: {route_sig}")
            i += 1
            # تخطي حتى الـ route التالي أو نهاية الملف
            while i < len(lines) and not lines[i].startswith('@app.route') and not lines[i].startswith('# ══'):
                i += 1
            continue
        else:
            seen_routes[route_sig] = True
    
    new_lines.append(line)
    i += 1

with open(app_path, "w", encoding="utf-8") as f:
    f.write('\n'.join(new_lines))
print("   OK: app.py تم إصلاحه")

# ══ 3. إصلاح run_project.py ══
print("\n3. إصلاح run_project.py...")
run_path = os.path.join(BASE, "run_project.py")

if os.path.exists(run_path):
    with open(run_path, "r", encoding="utf-8") as f:
        run_content = f.read()
    
    # إضافة drop_pending_updates
    run_content = run_content.replace(
        'start_polling(bot)',
        'start_polling(bot, drop_pending_updates=True)'
    )
    run_content = run_content.replace(
        'start_polling(dp)',
        'start_polling(dp, drop_pending_updates=True)'
    )
    
    with open(run_path, "w", encoding="utf-8") as f:
        f.write(run_content)
    print("   OK: run_project.py تم إصلاحه")
else:
    print("   SKIP: run_project.py غير موجود")

# ══ 4. إصلاح main.py - إضافة drop_pending_updates ══
print("\n4. إصلاح main.py...")
main_path = os.path.join(BASE, "main.py")
with open(main_path, "r", encoding="utf-8") as f:
    main_content = f.read()

main_content = main_content.replace(
    'await dp.start_polling(bot)',
    'await dp.start_polling(bot, drop_pending_updates=True)'
)

with open(main_path, "w", encoding="utf-8") as f:
    f.write(main_content)
print("   OK: main.py تم إصلاحه")

print("\n" + "="*40)
print("✅ كل الإصلاحات تمت!")
print("="*40)
print("\nالآن شغّل:")
print("python run_project.py")
print("أو")
print("python main.py  (للبوت فقط)")
