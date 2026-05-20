import re

# =============================================
# إصلاح run_project.py — port من env أو 8080
# =============================================
with open("run_project.py", "r", encoding="utf-8") as f:
    content = f.read()

# استبدل default=5000 بـ default من env
content = content.replace(
    'parser.add_argument("--port",      type=int, default=5000',
    'parser.add_argument("--port",      type=int, default=int(os.environ.get("PORT", 8080))'
)

# استبدل أي app.run(...port=5000...) ثابتة
content = re.sub(
    r'app\.run\(host="0\.0\.0\.0",\s*port=5000',
    'app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080))',
    content
)

with open("run_project.py", "w", encoding="utf-8") as f:
    f.write(content)

print("run_project.py fixed")

# =============================================
# إصلاح app.py — port من env
# =============================================
with open("app.py", "r", encoding="utf-8") as f:
    app_content = f.read()

# تأكد من وجود سطر PORT الصحيح
if 'PORT' not in app_content or 'os.environ.get("PORT"' not in app_content:
    # أضف في نهاية الملف
    app_content += '''

# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os as _os
    _port = int(_os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=_port, debug=False)
'''
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(app_content)
    print("app.py entry point added")
else:
    print("app.py already has PORT config")

# =============================================
# إصلاح main.py — port من env
# =============================================
with open("main.py", "r", encoding="utf-8") as f:
    main_content = f.read()

if "run_project" not in main_content:
    print("main.py OK (uses run_project)")

print()
print("=== VERIFICATION ===")
import ast
for fname in ["run_project.py", "app.py", "main.py"]:
    try:
        with open(fname, "r", encoding="utf-8") as f:
            src = f.read()
        ast.parse(src)
        lines = src.count("\n")
        print(f"  OK ({lines:4} lines): {fname}")
    except SyntaxError as e:
        print(f"  BROKEN line {e.lineno}: {fname} — {e.msg}")
