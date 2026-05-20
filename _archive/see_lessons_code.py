with open("handlers/start.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines[98:165], start=99):
    print(f"{i}: {line}", end="")
