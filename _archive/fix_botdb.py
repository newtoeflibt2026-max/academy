import re

with open("bot_database.py", "r", encoding="utf-8") as f:
    text = f.read()

# إصلاح الاستعلام الخاطئ
old = '"SELECT * FROM daily_missions WHERE is_active=1",\n        (target_date,)'
new = '"SELECT * FROM daily_missions WHERE is_active=1"'
text = text.replace(old, new)

# إصلاح بديل إذا كان بصيغة مختلفة
text = re.sub(
    r'"SELECT \* FROM daily_missions WHERE is_active=1"\s*,\s*\(target_date,\)',
    '"SELECT * FROM daily_missions WHERE is_active=1"',
    text
)

with open("bot_database.py", "w", encoding="utf-8") as f:
    f.write(text)
print("bot_database.py fixed")
