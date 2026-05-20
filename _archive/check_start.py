with open(r'C:\yamen_academy\handlers\start.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(f'Total lines: {len(lines)}')
# Last 20 lines
for i, line in enumerate(lines[-20:], len(lines)-19):
    print(f'{i}: {line.rstrip()[:120]}')
