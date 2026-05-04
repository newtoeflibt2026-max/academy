path = r'C:\yamen_academy\api_server.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Print lines 278-290 to see the damage
for i in range(277, min(291, len(lines))):
    print(f'Line {i+1}: {repr(lines[i][:120])}')
