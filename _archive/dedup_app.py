import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# ابحث عن جميع تعريفات الـ routes واحذف المكررات
seen_functions = set()
seen_routes = set()
lines = content.split('\n')
result = []
skip_until_next_route = False
current_block = []

i = 0
while i < len(lines):
    line = lines[i]
    
    # تحقق من وجود decorator route
    route_match = re.match(r'^@app\.route\(["\']([^"\']+)["\'].*methods=\[([^\]]+)\]', line)
    if not route_match:
        route_match2 = re.match(r'^@app\.route\(["\']([^"\']+)["\']', line)
    else:
        route_match2 = None
    
    if route_match or route_match2:
        # ابحث عن اسم الدالة في السطور التالية
        j = i + 1
        func_name = None
        while j < min(i+5, len(lines)):
            func_match = re.match(r'^def (\w+)', lines[j])
            if func_match:
                func_name = func_match.group(1)
                break
            j += 1
        
        if func_name and func_name in seen_functions:
            # تخطَّ هذه الدالة كاملة
            i += 1
            while i < len(lines):
                if re.match(r'^@app\.route|^if __name__', lines[i]):
                    break
                i += 1
            continue
        
        if func_name:
            seen_functions.add(func_name)
    
    result.append(line)
    i += 1

new_content = '\n'.join(result)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Done - removed duplicates")
print(f"Functions registered: {len(seen_functions)}")
