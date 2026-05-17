with open("modules/placement_web.py", "r", encoding="utf-8") as f:
    code = f.read()

print("=== SIZE ===")
print(len(code), "bytes")
print()

# Find all route decorators
import re
routes = re.findall(r'@\w+\.route\(["\']([^"\']+)["\']', code)
print("=== REGISTERED ROUTES ===")
for r in routes:
    print("  " + r)

# Find all function names
funcs = re.findall(r'def (\w+)\(', code)
print()
print("=== FUNCTIONS ===")
for fn in funcs:
    print("  " + fn)

# Check for try/except
if "try:" in code:
    print()
    print("try/except: FOUND")
else:
    print()
    print("try/except: MISSING - will crash on error")

# Check methods parameter
methods_found = re.findall(r'methods\s*=\s*\[([^\]]+)\]', code)
print()
print("=== METHODS PARAMS ===")
for m in methods_found:
    print("  [" + m + "]")
