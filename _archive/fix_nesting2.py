path = r'C:\yamen_academy\build_ai_engines.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# The actual line has 4 backslashes: \\\\n
old = '{"text": f"ESSAY:\\\\\\\\n\\\\\\\\n{essay}"}'
new = '{"text": "ESSAY:\n\n" + essay}'
content = content.replace(old, new)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
if old in content:
    print('ERROR: still not replaced')
else:
    print('Fixed')
