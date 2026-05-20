import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FIXED = os.path.join(ROOT, "academy.db")

# إصلاح handlers/placement_test.py
with open("handlers/placement_test.py", "r", encoding="utf-8") as f:
    text = f.read()

old = '''DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "academy.db")
)'''

new = '''DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "academy.db"))
)'''

text = text.replace(old, new)
with open("handlers/placement_test.py", "w", encoding="utf-8") as f:
    f.write(text)
print("placement_test.py fixed")

# إصلاح handlers/start.py
with open("handlers/start.py", "r", encoding="utf-8") as f:
    text = f.read()

old2 = '''DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "academy.db")
)'''

new2 = '''DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "academy.db"))
)'''

text = text.replace(old2, new2)
with open("handlers/start.py", "w", encoding="utf-8") as f:
    f.write(text)
print("start.py fixed")
