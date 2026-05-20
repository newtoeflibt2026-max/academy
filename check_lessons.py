import sqlite3
conn = sqlite3.connect("academy.db")
cur = conn.cursor()
cur.execute("PRAGMA table_info(lessons)")
cols = cur.fetchall()
print("=== lessons table columns ===")
for c in cols:
    print(f"  {c[1]:20s} {c[2]}")
print(f"\nTotal: {len(cols)} columns")
print(f"Has 'skill'?  {'YES ✅' if any(c[1]=='skill' for c in cols) else 'NO ❌'}")
print(f"Has 'title_ar'?  {'YES ✅' if any(c[1]=='title_ar' for c in cols) else 'NO ❌'}")
print(f"Has 'timer_minutes'?  {'YES ✅' if any(c[1]=='timer_minutes' for c in cols) else 'NO ❌'}")
conn.close()
