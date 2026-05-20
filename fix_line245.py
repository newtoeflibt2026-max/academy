with open("handlers/start.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # إصلاح السطر المكسور
    if 'p.get("name_ar") or p.get("name_ar", p.get("name_ar"' in line:
        new_lines.append('        name = p.get("name_ar") or p.get("name", "باقة")\n')
        print("fixed line 245")
    else:
        new_lines.append(line)

with open("handlers/start.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("DONE")
