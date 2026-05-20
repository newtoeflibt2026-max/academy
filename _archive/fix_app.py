import re

# Read app.py
with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix 1: Relax middleware to allow /dashboard, /lessons, /admin
old_mid = '''@app.before_request
def check_admin_bypass():
    if request.path.startswith(\"/static/\"):
        return None
    public = (\"/placement\", \"/login\", \"/api/\", \"/health\")
    if request.path == \"/\" or request.path.startswith(public):
        return None
    try:
        user_id = session.get(\"user_id\")
        if user_id is not None and int(user_id) in ADMIN_IDS:
            return None
    except Exception as mid_err:
        print(f\"[MIDDLEWARE] admin check error: {mid_err}\", file=sys.stderr)
    try:
        student_id = session.get(\"student_id\", 1)
        row = query_db(
            \"SELECT band, level, path FROM placement_results \"
            \"WHERE student_id = ? ORDER BY id DESC LIMIT 1\",
            (student_id,),
            one=True,
        )
        if not row or not row.get(\"band\"):
            return redirect(url_for(\"placement_page\"))
    except Exception:
        pass
    return None'''

new_mid = '''@app.before_request
def check_admin_bypass():
    if request.path.startswith(\"/static/\"):
        return None
    public = (\"/placement\", \"/login\", \"/api/\", \"/health\", \"/dashboard\", \"/lessons\", \"/admin\", \"/\")
    if request.path == \"/\" or request.path.startswith(public):
        return None
    try:
        user_id = session.get(\"user_id\")
        if user_id is not None and int(user_id) in ADMIN_IDS:
            return None
    except Exception as mid_err:
        print(f\"[MIDDLEWARE] admin check error: {mid_err}\", file=sys.stderr)
    return None'''

if old_mid in code:
    code = code.replace(old_mid, new_mid)
    print('[FIX 1] Middleware relaxed - /dashboard, /lessons, /admin now public')
else:
    print('[SKIP 1] Middleware already patched or not found')

# Fix 2: Update /lessons route to use category filter
old_lessons = '''@app.route(\"/lessons\")
def lessons_page():
    skill = request.args.get(\"skill\", \"\")
    try:
        all_lessons = list_lessons()
    except Exception as e:
        print(f\"[LESSONS] Error: {e}\")
        all_lessons = []
    filtered = [l for l in all_lessons if not skill or l.get(\"skill\") == skill]
    return render_template(\"lessons.html\", lessons=filtered, skill_filter=skill)'''

new_lessons = '''@app.route(\"/lessons\")
def lessons_page():
    skill = request.args.get(\"skill\", request.args.get(\"category\", \"\")).strip().lower()
    try:
        all_lessons = list_lessons(category=skill if skill else None)
    except Exception as e:
        print(f\"[LESSONS] Error: {e}\")
        all_lessons = []
    print(f\"[LESSONS] Found {len(all_lessons)} lessons (filter={skill or 'all'})\")
    return render_template(\"lessons.html\", lessons=all_lessons, skill_filter=skill)'''

if old_lessons in code:
    code = code.replace(old_lessons, new_lessons)
    print('[FIX 2] /lessons route updated - uses list_lessons(category=...)')
else:
    print('[SKIP 2] /lessons route already patched or not found')

# Fix 3: Update /dashboard route to pass lessons
old_dash = '''@app.route(\"/dashboard\")
def dashboard():
    return render_template(\"dashboard.html\")'''

new_dash = '''@app.route(\"/dashboard\")
def dashboard():
    try:
        all_lessons = list_lessons(limit=6)
    except Exception as e:
        print(f\"[DASHBOARD] Lessons error: {e}\")
        all_lessons = []
    return render_template(\"dashboard.html\", lessons=all_lessons)'''

if old_dash in code:
    code = code.replace(old_dash, new_dash)
    print('[FIX 3] /dashboard route updated - passes lessons to template')
else:
    print('[SKIP 3] /dashboard already patched or not found')

# Save
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('[DONE] app.py fully patched and saved!')
