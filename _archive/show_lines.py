with open("bot_database.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines[484:502], start=485):
    print(f"{i}: {line}", end="")
