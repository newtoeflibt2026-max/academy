path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# Find "if __name__" position
insert_point = code.find("if __name__ ==")
if insert_point == -1:
    print("ERROR: if __name__ not found")
    exit()

# Find first backend marker
marker = "# ADMIN CRUD"
first = code.find(marker)
if first == -1:
    marker = "# YAMEN ACADEMY v40"
    first = code.find(marker)

if first != -1 and first < insert_point:
    # Nuke everything between first marker and if __name__
    code = code[:first] + code[insert_point:]
    print("Nuclear clean: removed duplicate backend block")
else:
    print("No backend block found before if __name__")

# Also strip individual duplicate routes (old admin_create_content etc.)
code = code.replace("def admin_create_content():", "def _old_admin_create_content_removed():")
code = code.replace("def admin_update_content():", "def _old_admin_update_content_removed():")
code = code.replace("def admin_delete_content():", "def _old_admin_delete_content_removed():")

with open(path, "w", encoding="utf-8") as f:
    f.write(code)
print("app.py cleaned successfully!")
