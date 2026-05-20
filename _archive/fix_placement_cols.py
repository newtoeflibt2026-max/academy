import sqlite3
conn = sqlite3.connect("academy.db")
for col, typ in [("placement_done","INTEGER DEFAULT 0"), ("placement_score","REAL DEFAULT 0")]:
    try:
        conn.execute("ALTER TABLE students ADD COLUMN " + col + " " + typ)
        print("added: " + col)
    except Exception as e:
        print(str(e))
conn.commit()
conn.close()
print("DONE")
