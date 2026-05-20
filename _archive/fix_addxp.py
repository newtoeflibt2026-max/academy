with open("handlers/placement_test.py", "r", encoding="utf-8") as f:
    text = f.read()

# إصلاح add_xp - تمرير 4 معاملات بدل 3
import re
text = re.sub(
    r'add_xp\(str\(cb\.from_user\.id\),\s*50,\s*"general",\s*"placement_test"\)',
    'add_xp(cb.from_user.id, 50, "placement_test")',
    text
)
text = re.sub(
    r'add_xp\(str\(([^,]+)\),\s*(\d+),\s*"[^"]+",\s*"[^"]+"\)',
    r'add_xp(\1, \2, "placement_test")',
    text
)

with open("handlers/placement_test.py", "w", encoding="utf-8") as f:
    f.write(text)
print("placement_test.py fixed")
