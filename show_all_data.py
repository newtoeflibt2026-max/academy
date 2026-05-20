import sqlite3, json
conn = sqlite3.connect("academy.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

tables = ["students", "lessons", "questions", "missions", "payments", "subscription_plans"]

for t in tables:
    try:
        cur.execute(f"SELECT COUNT(*) as c FROM {t}")
        count = cur.fetchone()["c"]
        print(f"\n{'='*60}")
        print(f"📊 جدول: {t}  →  العدد: {count}")
        print('='*60)
        if count > 0:
            cur.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 5")
            rows = cur.fetchall()
            for i, r in enumerate(rows, 1):
                d = dict(r)
                # اعرض فقط الحقول المهمة
                keys = list(d.keys())[:6]
                preview = {k: str(d[k])[:40] for k in keys}
                print(f"  [{i}] {preview}")
    except Exception as e:
        print(f"❌ {t}: {e}")

conn.close()
