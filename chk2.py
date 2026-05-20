with open("handlers/placement_test.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines[1:35], start=2):
    print(f"{i}: {line}", end="")
