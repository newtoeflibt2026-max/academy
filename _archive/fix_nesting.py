path = r'C:\yamen_academy\build_ai_engines.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
old = '{"text": f"ESSAY:\\n\\n{essay}"}' 
new = '{"text": "ESSAY:\n\n" + essay}'
content = content.replace(old, new)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed')
