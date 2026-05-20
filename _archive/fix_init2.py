path = r'C:\yamen_academy\handlers\__init__.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove any dp.include_router at module level (outside register_all function)
lines = content.split('\n')
inside_function = False
fixed_lines = []
for line in lines:
    if 'def register_all' in line:
        inside_function = True
    if not inside_function and 'dp.include_router' in line:
        continue  # skip module-level router registration
    fixed_lines.append(line)

content = '\n'.join(fixed_lines)

# Make sure writing and speaking routers are INSIDE register_all
if 'from .writing import' not in content:
    content = content.replace(
        'def register_all(dp):',
        "def register_all(dp):\n    from .writing import router as r_write; dp.include_router(r_write)\n    from .speaking import router as r_speak; dp.include_router(r_speak)"
    )

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('✅ __init__.py fixed')
