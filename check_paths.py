import sqlite3, os

# ما هو المسار الذي يستخدمه bot_database؟
with open("bot_database.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if "DB_PATH" in line and i < 20:
            print(f"line {i+1}: {line.strip()}")

# ما هو المسار الذي تستخدمه db.py؟
print("---")
with open("db.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if "DB_PATH" in line and i < 20:
            print(f"line {i+1}: {line.strip()}")
