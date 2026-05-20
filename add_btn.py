with open("templates/admin_dashboard.html", "r", encoding="utf-8") as f:
    content = f.read()

# السطر 140 يحتوي على عنوان قسم الطلاب
# نضيف زر بجانب span.ct
old = '<span class="ct">👥 الطلاب</span>'
new = '''<span class="ct">👥 الطلاب</span>
          <button class="btn btn-p btn-sm" onclick="document.getElementById('modalAddStudent').classList.add('open')">&#43; إضافة طالب</button>'''

if old in content:
    content = content.replace(old, new, 1)
    print("OK: زر إضافة طالب أُضيف بنجاح")
else:
    print("NOT FOUND - searching similar...")
    lines = content.split("\n")
    for i, l in enumerate(lines[135:145], start=136):
        print(f"{i}: {repr(l[:100])}")

with open("templates/admin_dashboard.html", "w", encoding="utf-8") as f:
    f.write(content)
