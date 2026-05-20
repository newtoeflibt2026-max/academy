import sqlite3, json

conn = sqlite3.connect("academy.db")

# تحقق من أعمدة payments
cols = [r[1] for r in conn.execute("PRAGMA table_info(payments)").fetchall()]
print("payments columns:", cols)

# تحقق من أعمدة students  
scols = [r[1] for r in conn.execute("PRAGMA table_info(students)").fetchall()]
print("students columns:", scols)

# اعرض المدفوعات الموجودة
pays = conn.execute("SELECT * FROM payments LIMIT 3").fetchall()
print(f"\npayments rows: {conn.execute('SELECT COUNT(*) FROM payments').fetchone()[0]}")
for p in pays:
    print(" ", dict(p))

conn.close()
