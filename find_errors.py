with open("handlers/start.py", "r", encoding="utf-8") as f:
    text = f.read()

# ابحث عن كل الأماكن التي تستعلم عن lessons و subscription_plans
lines = text.split("\n")
for i, line in enumerate(lines, 1):
    if any(x in line for x in ["lessons", "subscription_plans", "placement_questions", "lessons error", "plans error"]):
        print(f"{i}: {line}")
