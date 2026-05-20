# -*- coding: utf-8 -*-
"""
fix_db_path.py - يضمن أن جميع الملفات تستخدم متغير البيئة DB_PATH
"""
import os

files_to_fix = ['database_v2.py', 'bot_database.py', 'app.py']

OLD = "os.path.join(os.path.dirname(os.path.abspath(__file__)), 'academy.db')"
NEW = "os.environ.get('DB_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'academy.db'))"

for fname in files_to_fix:
    fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
    if not os.path.exists(fpath):
        print("not found: " + fname)
        continue
    with open(fpath, 'r', encoding='utf-8') as f:
        c = f.read()
    if OLD in c and NEW not in c:
        c = c.replace(OLD, NEW)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(c)
        print("fixed: " + fname)
    else:
        print("skip: " + fname)

print("done")
