with open("bot_database.py", "r", encoding="utf-8") as f:
    text = f.read()

# إصلاح الدالة لتتجاهل target_date تماماً
old = """def get_daily_missions(target_date=None):
    conn = get_db()
    try:
        if target_date:
            rows = conn.execute(
                "SELECT * FROM daily_missions WHERE is_active=1"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM daily_missions WHERE is_active=1 ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()"""

new = """def get_daily_missions(target_date=None):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM daily_missions WHERE is_active=1 ORDER BY id DESC LIMIT 10"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()"""

if old in text:
    text = text.replace(old, new)
    print("fixed get_daily_missions")
else:
    print("pattern not found - trying line edit")
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "get_daily_missions" in line and "def " in line:
            print(f"found at line {i+1}: {line}")

with open("bot_database.py", "w", encoding="utf-8") as f:
    f.write(text)
print("done")
