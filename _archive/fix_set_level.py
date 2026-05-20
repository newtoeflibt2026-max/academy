import os
base = r"C:\yamen_academy"
path = os.path.join(base, "database.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# نضيف الدالة بعد set_placement_done
old = "def set_placement_done(user_id, level):\n    _safe_exec(\"UPDATE students SET placement_done=1, level=? WHERE user_id=?\", (level, user_id))"
new = """def set_placement_done(user_id, level):
    _safe_exec("UPDATE students SET placement_done=1, level=? WHERE user_id=?", (level, user_id))

def set_student_level(user_id, level):
    _safe_exec("UPDATE students SET level=?, placement_done=1 WHERE user_id=?", (level, user_id))"""

if old in content and "def set_student_level" not in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ set_student_level added")
else:
    print("Already exists or pattern not found")
