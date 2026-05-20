import os
path = r'C:\yamen_academy\handlers\admin.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('ADMIN_IDS = {469136626}', 'ADMIN_IDS = {469136626, 5572314718}')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('DONE — admin IDs updated')
