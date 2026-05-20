with open("handlers/start.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if line.strip() == ")" and i > 0 and "DB_PATH" in lines[i-1]:
        print(f"removed line {i+1}: {repr(line)}")
        continue
    new_lines.append(line)

with open("handlers/start.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("DONE")
