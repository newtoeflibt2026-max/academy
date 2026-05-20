with open("templates/admin_dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# تحقق من الصفحات الموجودة
pages = ["page-lessons", "page-broadcast", "page-messages"]
for p in pages:
    if p in html:
        print(f"EXISTS: {p}")
    else:
        print(f"MISSING: {p}")

# تحقق من nav
if "page-lessons" in html:
    print("nav lessons: OK")
else:
    print("nav lessons: MISSING")

print("File size:", len(html), "chars")
