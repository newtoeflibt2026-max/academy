"""SAFE AUDIT: Check all critical module files exist and are valid Python."""
import os, ast, sys

BASE = os.path.dirname(os.path.abspath(__file__))
modules = [
    "modules/subscription_engine.py",
    "modules/billing.py",
    "modules/ai_engine.py",
    "modules/audio_logic.py",
    "modules/content_engine.py",
    "modules/lesson_guard.py",
    "modules/placement_web.py",
    "modules/student_api.py",
    "modules/admin_api_web.py",
    "modules/dashboard_fix.py",
    "modules/models.py",
    "routes/admin_api.py",
    "utils/notifications.py",
    "utils/states.py",
    "handlers/admin.py",
    "handlers/start.py",
    "handlers/student.py",
    "handlers/subscriptions.py",
    "main.py",
]

print(f"\n{'='*60}")
print(f"  MODULE INTEGRITY CHECK")
print(f"{'='*60}")

for mod_path in modules:
    full = os.path.join(BASE, mod_path)
    if not os.path.exists(full):
        print(f"  MISSING: {mod_path}")
        continue
    size = os.path.getsize(full)
    # Check if valid Python
    try:
        with open(full, "r", encoding="utf-8") as f:
            ast.parse(f.read())
        status = "VALID"
    except SyntaxError as e:
        status = f"SYNTAX ERROR: {e}"
    print(f"  {mod_path:40s}  {size:>6d} bytes  {status}")

print(f"\n{'='*60}")
print(f"  MODULE AUDIT COMPLETE")
print(f"{'='*60}")
