import os, sqlite3

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")

# تحقق من المسار الفعلي
print("DB PATH:", DB)
print("EXISTS:", os.path.exists(DB))

conn = sqlite3.connect(DB)
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("TABLES:", sorted(tables))

# تحقق من handlers/start.py DB_PATH المحسوب
handler_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "handlers")
handler_db  = os.path.join(handler_dir, "..", "academy.db")
handler_db  = os.path.normpath(handler_db)
print("HANDLER DB PATH:", handler_db)
print("HANDLER DB EXISTS:", os.path.exists(handler_db))
conn.close()
