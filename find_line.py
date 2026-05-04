with open(r'C:\yamen_academy\build_ai_engines.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if 'ESSAY' in line:
        print(f'Line {i}: {repr(line[:120])}')
