with open("handlers/start.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines[215:275], start=216):
    print(f"{i}: {line}", end="")
