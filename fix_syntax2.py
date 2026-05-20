for handler in ["handlers/start.py", "handlers/placement_test.py", 
                "handlers/lessons.py", "handlers/subscriptions.py", "handlers/admin.py"]:
    try:
        with open(handler, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        new_lines = []
        for line in lines:
            if "DB_PATH" in line and "academy.db" in line:
                new_lines.append('DB_PATH = r"C:\\Users\\nelt2\\yamen_academy\\academy.db"\n')
                print(f"fixed in {handler}: {line.strip()}")
            else:
                new_lines.append(line)
        
        with open(handler, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"skip {handler}: {e}")

print("ALL DONE")
