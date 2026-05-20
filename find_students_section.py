with open("templates/admin_dashboard.html", "r", encoding="utf-8") as f:
    content = f.read()

# ابحث عن قسم الطلاب في الـ topbar او الـ content
lines = content.split("\n")
for i, l in enumerate(lines, 1):
    if "students" in l.lower() or "طالب" in l or "الطلاب" in l:
        print(f"{i}: {l[:100]}")
