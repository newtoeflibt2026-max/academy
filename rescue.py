import os, shutil, ast
from pathlib import Path

ROOT = Path(".")
JUNK_DIR = ROOT / "_archive"
JUNK_DIR.mkdir(exist_ok=True)

# ============================================================
# 1. إصلاح BOM encoding في الملفات الأساسية
# ============================================================
CORE_FILES = [
    "app.py", "main.py", "bot_database.py",
    "admin_routes.py", "database.py", "config.py",
    "db.py", "database_v2.py"
]

print("=" * 60)
print("STEP 1: Fixing BOM encoding")
print("=" * 60)

for fname in CORE_FILES:
    fpath = ROOT / fname
    if not fpath.exists():
        print(f"  SKIP (not found): {fname}")
        continue
    
    raw = fpath.read_bytes()
    if raw.startswith(b'\xef\xbb\xbf'):
        fpath.write_bytes(raw[3:])
        print(f"  FIXED BOM: {fname}")
    else:
        print(f"  OK (no BOM): {fname}")

# ============================================================
# 2. إزالة Routes المكررة من app.py
# ============================================================
print()
print("=" * 60)
print("STEP 2: Removing duplicate routes from app.py")
print("=" * 60)

app_path = ROOT / "app.py"
if app_path.exists():
    # حفظ نسخة قبل التعديل
    shutil.copy(app_path, ROOT / "app.py.bak")
    
    lines = app_path.read_text(encoding="utf-8").splitlines(keepends=True)
    
    seen_routes = {}
    seen_funcs = {}
    skip_until = -1
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # تجاهل السطر إذا كنا في منطقة الحذف
        if i < skip_until:
            i += 1
            continue
        
        # كشف route
        if stripped.startswith("@app.route("):
            route_sig = stripped
            
            if route_sig in seen_routes:
                # route مكرر — ابحث عن نهاية الدالة وتجاهلها
                j = i + 1
                # تخطى decorators
                while j < len(lines) and lines[j].strip().startswith("@"):
                    j += 1
                # تخطى def
                if j < len(lines) and lines[j].strip().startswith("def "):
                    j += 1
                    # تخطى جسم الدالة
                    while j < len(lines):
                        l = lines[j]
                        if l.strip() == "":
                            j += 1
                            continue
                        if not l[0].isspace() and not l.strip().startswith("#"):
                            break
                        j += 1
                skip_until = j
                print(f"  REMOVED duplicate: {route_sig[:60]}")
                i += 1
                continue
            else:
                seen_routes[route_sig] = i
        
        new_lines.append(line)
        i += 1
    
    app_path.write_text("".join(new_lines), encoding="utf-8")
    
    # تحقق من صحة النتيجة
    try:
        ast.parse(app_path.read_text(encoding="utf-8"))
        print(f"  app.py is valid after dedup ({len(new_lines)} lines)")
    except SyntaxError as e:
        print(f"  SYNTAX ERROR after dedup: line {e.lineno}: {e.msg}")
        print("  Restoring backup...")
        shutil.copy(ROOT / "app.py.bak", app_path)
        print("  Restored original app.py")

# ============================================================
# 3. أرشفة ملفات fix/patch/check/see/audit/build القديمة
# ============================================================
print()
print("=" * 60)
print("STEP 3: Archiving junk files")
print("=" * 60)

KEEP = {
    "app.py", "main.py", "bot_database.py", "database.py",
    "admin_routes.py", "config.py", "db.py", "database_v2.py",
    "wsgi.py", "server.py", "api_server.py", "app_core.py",
    "content_engine_routes.py", "startup_seed.py", "seed_data.py",
    "seed_plans.py", "seed_questions.py", "seed_placement.py",
    "run_project.py", "run_webapp.py", "migrate_db.py",
    "init_missing_tables.py", "create_lessons.py"
}

JUNK_PREFIXES = (
    "fix_", "patch_", "check_", "see_", "audit_",
    "build_", "clean_", "dedup_", "debug_", "diag_",
    "deploy_", "find_", "full_", "inject_", "launch_",
    "master_", "rebuild_", "restore_", "safe_", "verify_",
    "write_", "add_", "phase", "chk", "show_"
)

JUNK_EXACT = {
    "list_routes.py", "test_run.py", "test_syntax.py",
    "start_local.py", "run_all.py", "see_damage.py",
    "app_new.py", "app.py.bak"
}

moved = 0
for f in ROOT.glob("*.py"):
    name = f.name
    if name in KEEP:
        continue
    if name in JUNK_EXACT or name.startswith(JUNK_PREFIXES):
        dest = JUNK_DIR / name
        shutil.move(str(f), str(dest))
        moved += 1

print(f"  Archived {moved} files to _archive/")

# ============================================================
# 4. التحقق النهائي من الملفات الأساسية
# ============================================================
print()
print("=" * 60)
print("STEP 4: Final validation")
print("=" * 60)

for fname in CORE_FILES:
    fpath = ROOT / fname
    if not fpath.exists():
        print(f"  MISSING: {fname}")
        continue
    try:
        src = fpath.read_text(encoding="utf-8")
        ast.parse(src)
        lines = src.count("\n")
        print(f"  OK ({lines:4} lines): {fname}")
    except SyntaxError as e:
        print(f"  BROKEN line {e.lineno}: {fname} — {e.msg}")

print()
print("=" * 60)
print("DONE. Files remaining in project root:")
remaining = sorted(ROOT.glob("*.py"))
for f in remaining:
    print(f"  {f.name}")
print("=" * 60)
