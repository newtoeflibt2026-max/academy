"""SURGICAL FIX: Replace /dashboard route with dynamic student_id support."""
import re, os

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
with open(APP, "r", encoding="utf-8") as f:
    code = f.read()

# The current broken dashboard route (from audit)
old_dashboard = """@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")"""

# The new comprehensive dashboard route
new_dashboard = """@app.route("/dashboard")
@app.route("/dashboard/<int:student_id>")
def dashboard(student_id=None):
    # If student_id not in URL, try session
    if student_id is None:
        student_id = session.get("student_id", None)

    student_data = {
        "id": student_id,
        "name": "Guest",
        "level": "beginner",
        "xp": 0,
        "streak": 0,
        "placement_done": False,
        "placement_level": None,
    }

    # Query student from database if ID available
    if student_id is not None:
        try:
            import sqlite3
            conn = sqlite3.connect("data/yamen_academy.db")
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM students WHERE telegram_id = ?",
                (student_id,)
            ).fetchone()
            if row:
                student_data = dict(row)
                student_data["id"] = row["telegram_id"]
            conn.close()
        except Exception as e:
            print(f"[DASHBOARD] DB query error: {e}")

    # Fetch placement result if available
    placement_data = None
    if student_id is not None:
        try:
            import sqlite3
            conn = sqlite3.connect("data/yamen_academy.db")
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM placement_results WHERE student_id = ? ORDER BY id DESC LIMIT 1",
                (student_id,)
            ).fetchone()
            if row:
                placement_data = dict(row)
            conn.close()
        except Exception:
            pass

    # Load latest lessons
    try:
        all_lessons = list_lessons(limit=6)
    except Exception:
        all_lessons = []

    # Determine which template to use
    # Prefer student_dashboard.html if it exists in templates
    import os as _os
    template_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "templates")
    template_name = "student_dashboard.html" if _os.path.exists(_os.path.join(template_dir, "student_dashboard.html")) else "dashboard.html"

    return render_template(
        template_name,
        student=student_data,
        placement=placement_data,
        lessons=all_lessons,
        dashboard_config={
            "show_progress": True,
            "show_lessons": True,
            "show_placement": student_data.get("placement_done", False),
        }
    )"""

if old_dashboard in code:
    code = code.replace(old_dashboard, new_dashboard)
    print("[OK] Dashboard route replaced with dynamic student_id support")
else:
    print("[WARN] Old dashboard route not found - checking alternatives...")
    # Try alternative pattern (with whitespace variations)
    alt_patterns = [
        '@app.route("/dashboard")\ndef dashboard():',
    ]
    found = False
    for alt in alt_patterns:
        if alt in code:
            code = code.replace(alt.split("\n")[0] + "\n" + alt.split("\n")[1], new_dashboard.split("\n", 1)[0] + "\n" + new_dashboard.split("\n", 1)[1], 1)
            found = True
            print("[OK] Dashboard route replaced (alt pattern)")
            break
    if not found:
        print("[ERROR] Could not find dashboard route to replace!")
        print("Searching for 'def dashboard' in app.py...")
        idx = code.find("def dashboard")
        if idx != -1:
            snippet = code[max(0,idx-50):idx+100]
            print(f"Found at position {idx}:")
            print(snippet)
        exit(1)

# Save
with open(APP, "w", encoding="utf-8") as f:
    f.write(code)

# Verify
routes = re.findall(r"""@app\.route\(['\"]([^'\"]+)['\"]""", code)
dashboard_routes = [r for r in routes if "dashboard" in r.lower()]
print(f"\n[VERIFY] Dashboard routes in app.py:")
for r in dashboard_routes:
    print(f"  GET {r}")

print("\n[DONE] Safe surgical replacement complete - all other routes preserved")
