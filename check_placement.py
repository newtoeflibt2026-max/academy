with open("handlers/placement_test.py", "r", encoding="utf-8") as f:
    text = f.read()

# اعرض السطور التي تستعلم عن placement_questions
lines = text.split("\n")
for i, line in enumerate(lines, 1):
    if "placement" in line.lower() and ("select" in line.lower() or "from" in line.lower() or "DB_PATH" in line or "connect" in line):
        print(f"{i}: {line}")
