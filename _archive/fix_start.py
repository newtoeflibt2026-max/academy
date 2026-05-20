path = r'C:\yamen_academy\handlers\start.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add missing imports
imports_to_add = 'from aiogram.types import Message\nfrom aiogram.fsm.context import FSMContext\n'
if 'from aiogram.types import Message' not in content:
    content = imports_to_add + content

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('✅ imports added to start.py')
