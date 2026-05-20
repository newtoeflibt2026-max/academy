with open("handlers/start.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines[13:25], start=14):
    print(f"{i}: {line}", end="")
