import re

with open("app.py", "r", encoding="utf-8") as f:
    text = f.read()

seen = set()
out  = []
skip = False
func = None

for line in text.split("\n"):
    m = re.match(r"^def (api_\w+|admin_\w+|student_\w+)\(", line)
    if m:
        func = m.group(1)
        if func in seen:
            skip = True
        else:
            seen.add(func)
            skip = False

    if not skip:
        out.append(line)
    else:
        # توقف التخطي عند الدالة التالية
        if line.startswith("@app.route") or line.startswith("if __name__"):
            skip = False
            out.append(line)

with open("app.py", "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print(f"app.py cleaned - {len(seen)} unique functions kept")
