with open("handlers/start.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# اعرض السطور 12-20
for i, line in enumerate(lines[11:20], start=12):
    print(f"{i}: {repr(line)}")
