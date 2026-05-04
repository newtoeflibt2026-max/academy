path = r'C:\yamen_academy\build_ai_engines.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
old = 'ESSAY:\\\\\\\\n\\\\\\\\n{essay}'
new = 'ESSAY:\n\n" + essay'
if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed - replaced exact match')
else:
    print('NOT FOUND - searching for substring')
    for i, line in enumerate(content.split('\n')):
        if 'ESSAY' in line and 'f"' in line:
            print(f'Line {i+1}: {repr(line.strip()[:120])}')
