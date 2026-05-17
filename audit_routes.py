"""SAFE AUDIT: Extract all routes from app.py without touching anything."""
import re, os

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# Find all @app.route declarations
routes = re.findall(r"""@app\.route\(['\"]([^'\"]+)['\"]\s*,?\s*(?:methods\s*=\s*\[([^\]]+)\])?\s*\)""", code)
print(f"\n{'='*60}")
print(f"  TOTAL @app.route DECLARATIONS: {len(routes)}")
print(f"{'='*60}")

for url, methods in routes:
    method_str = methods.strip() if methods else "GET"
    print(f"  {method_str:25s}  {url}")

# Check for duplicate routes
seen = {}
dupes = []
for url, methods in routes:
    if url in seen:
        dupes.append(url)
    seen[url] = seen.get(url, 0) + 1

if dupes:
    print(f"\n{'!'*60}")
    print(f"  WARNING: {len(dupes)} DUPLICATE ROUTES FOUND:")
    for d in dupes:
        print(f"    - {d} ({seen[d]}x)")
    print(f"{'!'*60}")
else:
    print(f"\n  ALL ROUTES UNIQUE - NO DUPLICATES")

# Find blueprints
bps = re.findall(r"""(?:safe_bp|register_blueprint)\(['\"]([^'\"]+)['\"]\s*,\s*(\w+)""", code)
print(f"\n{'='*60}")
print(f"  BLUEPRINT REGISTRATIONS: {len(bps)}")
print(f"{'='*60}")
for name, var in bps:
    print(f"  {name:30s} -> {var}")

# Check for critical imports
print(f"\n{'='*60}")
print(f"  CRITICAL SYSTEM CHECKS")
print(f"{'='*60}")
checks = {
    "subscription_engine": "modules.subscription_engine",
    "billing": "modules.billing",
    "telegram/bot": "BOT_TOKEN|bot_token|telegram",
    "lesson_guard": "lesson_guard",
    "placement_web": "placement_web",
    "student_api": "student_api",
    "dashboard_fix": "dashboard_fix",
    "admin_api": "admin_api",
}
for name, pattern in checks.items():
    found = bool(re.search(pattern, code))
    print(f"  {name:25s}: {'FOUND' if found else 'MISSING'}")

print(f"\n{'='*60}")
print(f"  AUDIT COMPLETE - No files modified")
print(f"{'='*60}")
