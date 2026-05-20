"""FULL CLEAN: Remove ALL old admin/placement routes, inject clean ones."""
import re

path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# STEP 1: Remove ALL old route blocks between error handlers and if __name__
# Find the last error handler or the last safe route before the injection zone
lines = code.split("\n")
new_lines = []
skip_until_empty = False
in_old_block = False

for line in lines:
    stripped = line.strip()
    
    # Detect old admin content routes
    if '@app.route("/api/admin/content/create"' in stripped:
        in_old_block = True
        continue
    if '@app.route("/api/admin/content/update"' in stripped:
        in_old_block = True
        continue
    if '@app.route("/api/admin/content/delete"' in stripped:
        in_old_block = True
        continue
    
    # Detect old admin questions routes (if any)
    if '@app.route("/api/admin/questions"' in stripped and 'def admin_list_questions' not in stripped:
        if '_admin_qlist' not in stripped:
            in_old_block = True
            continue
    
    # Detect old placement routes
    if '@app.route("/api/placement/questions"' in stripped and '_placement_qs' not in stripped:
        in_old_block = True
        continue
    if '@app.route("/api/placement/submit"' in stripped and '_placement_submit' not in stripped:
        in_old_block = True
        continue
    
    # Detect renamed old functions
    if '_old_admin' in stripped or 'def admin_create_content' in stripped or 'def admin_update_content' in stripped or 'def admin_delete_content' in stripped:
        if '_new' not in stripped and '_edit' not in stripped and '_del' not in stripped:
            in_old_block = True
            continue
    
    # Skip backend block markers
    if stripped.startswith("# ADMIN CRUD") or stripped.startswith("# YAMEN ACADEMY v40"):
        in_old_block = True
        continue
    if stripped.startswith("# ═══════"):
        in_old_block = True
        continue
    if stripped == 'import sqlite3' and in_old_block:
        continue
    if 'def _db():' in stripped:
        in_old_block = True
        continue
    
    # End of old block
    if in_old_block:
        if stripped == "" or stripped.startswith("@app.") or stripped.startswith("#"):
            in_old_block = False
        else:
            continue
    
    new_lines.append(line)

code = "\n".join(new_lines)

# STEP 2: Also strip any backend block between the last error handler and if __name__
# Find "if __name__" position
if_pos = code.find("if __name__ ==")

# Find the SECOND-last @app before if __name__
# We want to keep everything up to the LAST legitimate route
app_indices = [m.start() for m in re.finditer(r"@app\.route", code)]
# Find the last app.route before if __name__ that is part of original code
last_good = 0
for idx in app_indices:
    if idx < if_pos and idx > last_good:
        # Find the function name after this route
        func_match = re.search(r"def (\w+)", code[idx:idx+200])
        if func_match:
            fname = func_match.group(1)
            # Keep routes that are NOT our injected ones
            if not fname.startswith("_") or fname in ["_old_admin_create_content_removed", "_old_admin_update_content_removed", "_old_admin_delete_content_removed"]:
                continue
        last_good = idx

if last_good > 0:
    # Find the end of the function at last_good
    # Simple: find the next @app or if __name__
    next_block = code.find("@app.route", last_good + 100)
    if next_block == -1 or next_block > if_pos:
        next_block = code.find("if __name__", last_good + 100)
    if next_block > last_good:
        code = code[:next_block] + code[if_pos:]

# Save cleaned version
with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print("[STEP 1] Old routes stripped from app.py")
print("[READY] Run inject_routes.py next")
