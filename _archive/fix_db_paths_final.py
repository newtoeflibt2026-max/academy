import os

DB_ABSOLUTE = "C:/Users/nelt2/yamen_academy/academy.db"

# إصلاح handlers/start.py
with open("handlers/start.py", "r", encoding="utf-8") as f:
    text = f.read()

# استبدل كل تعريف DB_PATH
import re
text = re.sub(
    r'DB_PATH\s*=\s*os\.environ\.get\([^)]+\)|DB_PATH\s*=\s*os\.path\.[^\n]+',
    f'DB_PATH = os.environ.get("DB_PATH", r"{DB_ABSOLUTE}")',
    text,
    count=1
)
with open("handlers/start.py", "w", encoding="utf-8") as f:
    f.write(text)
print("start.py fixed")

# إصلاح handlers/placement_test.py
with open("handlers/placement_test.py", "r", encoding="utf-8") as f:
    text = f.read()

text = re.sub(
    r'DB_PATH\s*=\s*os\.environ\.get\([^\n]+\n[^\n]+\n[^\n]+\)',
    f'DB_PATH = os.environ.get("DB_PATH", r"{DB_ABSOLUTE}")',
    text,
    count=1
)
with open("handlers/placement_test.py", "w", encoding="utf-8") as f:
    f.write(text)
print("placement_test.py fixed")

# إصلاح باقي الـ handlers
for handler in ["handlers/lessons.py", "handlers/subscriptions.py", "handlers/admin.py"]:
    try:
        with open(handler, "r", encoding="utf-8") as f:
            text = f.read()
        text = re.sub(
            r'DB_PATH\s*=\s*os\.environ\.get\([^\n]+\n[^\n]+\n[^\n]+\)',
            f'DB_PATH = os.environ.get("DB_PATH", r"{DB_ABSOLUTE}")',
            text,
            count=1
        )
        with open(handler, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"{handler} fixed")
    except Exception as e:
        print(f"{handler} skip: {e}")

print("ALL DONE")
