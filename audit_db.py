"""SAFE AUDIT: Database schema inspection."""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yamen_academy.db")
conn = sqlite3.connect(DB)
c = conn.cursor()

# Tables
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print(f"\n{'='*60}")
print(f"  DATABASE TABLES: {len(tables)}")
print(f"{'='*60}")
for t in tables:
    cols = c.execute(f"PRAGMA table_info('{t[0]}')").fetchall()
    col_names = [col[1] for col in cols]
    row_count = c.execute(f"SELECT COUNT(*) FROM '{t[0]}'").fetchone()[0]
    print(f"  {t[0]:25s}  {len(cols)} cols  {row_count} rows")
    print(f"    Columns: {col_names}")

conn.close()
print(f"\n{'='*60}")
print(f"  DB AUDIT COMPLETE")
print(f"{'='*60}")
