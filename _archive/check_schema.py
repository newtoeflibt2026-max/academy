import sqlite3
conn = sqlite3.connect('academy.db')
row = conn.execute("SELECT sql FROM sqlite_master WHERE name='lessons'").fetchone()
print(row[0] if row else 'TABLE NOT FOUND')
conn.close()
