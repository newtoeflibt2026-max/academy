path = r'C:\yamen_academy\build_ai_engines.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
idx = content.find('ESSAY')
print('Found at index:', idx)
print('Context:', repr(content[idx:idx+80]))
