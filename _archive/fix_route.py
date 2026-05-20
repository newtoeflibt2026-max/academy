import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# The old (current) route pattern to find and replace
old_route = '''@app.route("/lessons")
def lessons_page():
    skill = request.args.get("skill", "")
    try:
        all_lessons = list_lessons()
    except Exception as e:
        print(f"[LESSONS] Error: {e}")
        all_lessons = []
    filtered = [l for l in all_lessons if not skill or l.get("skill") == skill]
    return render_template("lessons.html", lessons=filtered, skill_filter=skill)'''

new_route = '''@app.route("/lessons")
def lessons_page():
    skill = request.args.get("skill", "").strip().lower()
    try:
        if skill:
            all_lessons = list_lessons(category=skill)
        else:
            all_lessons = list_lessons()
    except Exception as e:
        print("[LESSONS] Error:", e)
        all_lessons = []
    print("[LESSONS] Returning", len(all_lessons), "lessons (filter:", skill or "all", ")")
    return render_template("lessons.html", lessons=all_lessons, skill_filter=skill)'''

if old_route in code:
    code = code.replace(old_route, new_route)
    print("[OK] /lessons route updated!")
elif "def lessons_page" in code:
    print("[WARN] Route found but pattern mismatch - checking...")
    # Find the route by function name and replace
    start = code.find('@app.route("/lessons")')
    end = code.find('@app.route', start + 10)
    if end == -1:
        end = code.find('if __name__', start)
    if start != -1 and end != -1:
        code = code[:start] + new_route + '\n\n' + code[end:]
        print("[OK] /lessons route replaced by position!")
    else:
        print("[ERROR] Could not find /lessons route!")
else:
    print("[WARN] /lessons route not found - injecting before if __name__")
    insert_point = 'if __name__ == "__main__":'
    code = code.replace(insert_point, new_route + '\n\n' + insert_point)
    print("[OK] /lessons route injected!")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("[DONE] app.py saved!")
