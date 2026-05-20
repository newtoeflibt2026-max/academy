import sqlite3
conn = sqlite3.connect("academy.db")
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("tables in academy.db:")
for t in sorted(tables):
    print(" -", t)
conn.close()
