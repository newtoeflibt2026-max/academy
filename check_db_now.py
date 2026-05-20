import sqlite3, os
from pathlib import Path

# ابحث عن كل ملفات .db
dbs = list(Path(".").rglob("*.db"))
if not dbs:
    print("NO .db files found!")
else:
    for db in dbs:
        print(f"\n=== {db} ===")
        try:
            conn = sqlite3.connect(str(db))
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            for (tname,) in tables:
                try:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM [" + tname + "]"
                    ).fetchone()[0]
                    print(f"  {tname:<35} {count:>6} rows")
                except Exception as ex:
                    print(f"  {tname:<35} ERROR: {ex}")
            conn.close()
        except Exception as e:
            print(f"  CONNECT ERROR: {e}")
