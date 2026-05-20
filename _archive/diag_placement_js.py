import os

js_path = "js/placement.js"
if not os.path.exists(js_path):
    print("MISSING: " + js_path)
    exit()

with open(js_path, "r", encoding="utf-8") as f:
    js = f.read()

print("=== SIZE ===")
print(len(js), "bytes")
print()

# Find all string literals that look like URLs
import re
urls = re.findall(r'["\']((?:/api/|/placement|/submit|/dashboard)[^"\']*)["\']', js)
print("=== API URLS ===")
for u in urls:
    print("  " + u)

# Find submit-related code
if "submit" in js.lower():
    idx = js.lower().find("submit")
    print()
    print("=== SUBMIT CONTEXT ===")
    print(js[max(0, idx-150):idx+300])

# Find all function names
funcs = re.findall(r'function\s+(\w+)', js)
print()
print("=== FUNCTIONS ===")
for f in funcs:
    print("  " + f)

# Find event listeners
events = re.findall(r'\.addEventListener\(["\']([^"\']+)["\']', js)
print()
print("=== EVENT LISTENERS ===")
for e in events:
    print("  " + e)
