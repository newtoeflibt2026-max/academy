with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# إصلاح المسار الرئيسي ليفتح لوحة الأدمن
old = '''@app.route("/")
@app.route("/student")
@app.route("/api/admin/stats")
def api_stats():'''

new = '''@app.route("/")
def index():
    from flask import render_template
    return render_template("admin_dashboard.html")

@app.route("/student")
def student():
    from flask import render_template
    return render_template("student_portal.html")

@app.route("/api/admin/stats")
def api_stats():'''

if old in content:
    content = content.replace(old, new)
    print("Fixed: routes separated correctly")
else:
    print("Pattern not found - checking current routes...")
    # بحث يدوي
    lines = content.split("\n")
    for i, l in enumerate(lines[:25], 1):
        print(f"{i}: {l}")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
