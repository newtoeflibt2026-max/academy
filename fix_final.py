path = r'C:\yamen_academy\build_ai_engines.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Target the whole part line
target = '{"text": f"ESSAY:\\\\n\\\\n{essay}"}'
replacement = '{"text": "ESSAY:\n\n" + essay}'

count = content.count(target)
print(f'Occurrences found: {count}')

if count > 0:
    content = content.replace(target, replacement)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    # verify
    with open(path, 'r', encoding='utf-8') as f:
        new_content = f.read()
    if target in new_content:
        print('FAILED - still present')
    else:
        print('SUCCESS - replaced')
else:
    print('Pattern not found, trying raw bytes match...')
    # search differently
    for i, line in enumerate(content.split('\n'), 1):
        if 'ESSAY' in line and '{essay}' in line:
            print(f'Line {i}: {repr(line.strip())}')
            # replace the f-string part only
            old_part = 'f"ESSAY:\\\\n\\\\n{essay}"'
            new_part = '"ESSAY:\n\n" + essay'
            if old_part in line:
                new_line = line.replace(old_part, new_part)
                content = content.replace(line, new_line)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print('Fixed via line replacement')
                break
