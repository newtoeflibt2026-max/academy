import sqlite3
conn = sqlite3.connect("academy.db")
c = conn.cursor()
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("tables:", tables)
cols = [r[1] for r in c.execute("PRAGMA table_info(questions)").fetchall()]
print("questions cols:", cols)
conn.close()
