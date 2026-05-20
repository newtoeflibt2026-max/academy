import re

for handler in ["handlers/start.py", "handlers/placement_test.py", "handlers/lessons.py", "handlers/subscriptions.py", "handlers/admin.py"]:
    try:
        with open(handler, "r", encoding="utf-8") as f:
            text = f.read()
        
        # احذف كل تعريفات DB_PATH واستبدلها بسطر واحد نظيف
        text = re.sub(
            r'DB_PATH\s*=\s*[^\n]+\n?(\s+[^\n]+\n?)*?(?=\n\n|\ndef |\nclass |\n@)',
            'DB_PATH = r"C:\\Users\\nelt2\\yamen_academy\\academy.db"\n',
            text
        )
        
        with open(handler, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"fixed: {handler}")
    except Exception as e:
        print(f"error {handler}: {e}")
