import re, sys, shutil, datetime

# Backup first
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2("app.py", f"_backups/manual_fix_{ts}_app.py")
print(f"Backup saved: _backups/manual_fix_{ts}_app.py")

with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
i = 0
fixes = 0

while i < len(lines):
    line = lines[i]
    
    # Match: with _db_safe() as (conn, c):
    m = re.match(r'^(\s*)with\s+_db_safe\(\)\s+as\s+\(\s*conn\s*,\s*c\s*\)\s*:\s*$', line)
    
    if m:
        outer_indent = m.group(1)  # e.g. "        " (8 spaces)
        fixes += 1
        line_num = i + 1
        
        # Collect body lines (everything indented deeper than outer_indent)
        body_start = i + 1
        body_lines = []
        j = body_start
        
        while j < len(lines):
            bline = lines[j]
            # blank line inside block - keep it
            if bline.strip() == '':
                body_lines.append(bline)
                j += 1
                continue
            # check indent
            stripped = bline.lstrip()
            current_indent = bline[:len(bline) - len(stripped)]
            if len(current_indent) > len(outer_indent):
                body_lines.append(bline)
                j += 1
            else:
                break
        
        # Remove trailing blank lines from body
        while body_lines and body_lines[-1].strip() == '':
            body_lines.pop()
        
        # The body lines are currently indented at outer_indent + "    " (one level in from with)
        # We need to KEEP them at the SAME indent because they'll go inside try: block
        # which replaces the with: block at the same level
        
        # Check if body already has conn.commit() - we need conn.close() too
        body_has_commit = any('conn.commit()' in bl for bl in body_lines)
        body_has_close = any('conn.close()' in bl for bl in body_lines)
        
        inner_indent = outer_indent + "    "
        
        # Write replacement
        new_lines.append(f"{outer_indent}conn = _db_safe()\n")
        new_lines.append(f"{outer_indent}c = conn.cursor()\n")
        new_lines.append(f"{outer_indent}try:\n")
        
        # Body lines stay exactly as they are (same indent level)
        for bl in body_lines:
            new_lines.append(bl)
        
        # Add finally with conn.close()
        new_lines.append(f"{outer_indent}finally:\n")
        new_lines.append(f"{inner_indent}conn.close()\n")
        
        print(f"  Fix #{fixes}: line {line_num} -> replaced 'with _db_safe() as (conn, c):' ")
        print(f"         outer_indent={len(outer_indent)} spaces, body_lines={len(body_lines)}")
        
        i = j
    else:
        new_lines.append(line)
        i += 1

if fixes == 0:
    print("No patterns found!")
    sys.exit(1)

# Write
with open("app.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"\nTotal fixes: {fixes}")
print("Running syntax check...")

import py_compile
try:
    py_compile.compile("app.py", doraise=True)
    print("SYNTAX CHECK PASSED!")
except py_compile.PyCompileError as e:
    print(f"SYNTAX CHECK FAILED: {e}")
    # Restore backup
    shutil.copy2(f"_backups/manual_fix_{ts}_app.py", "app.py")
    print("Restored from backup.")
    sys.exit(1)
