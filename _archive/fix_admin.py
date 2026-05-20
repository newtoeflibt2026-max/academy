import os
base = r'C:\yamen_academy'
path = os.path.join(base, 'handlers', 'admin.py')
with open(path, 'w', encoding='utf-8') as f:
    f.write(open(os.path.join(base, 'admin_source.txt'), 'r', encoding='utf-8').read())
print('Done')
