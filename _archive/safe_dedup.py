"""SAFE DEDUPLICATION: Remove duplicate admin routes, inject once cleanly."""
import re, os

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
with open(APP, "r", encoding="utf-8") as f:
    code = f.read()

# STEP 1: Preserve everything before the first injection
# Find "if __name__" - our boundary
if_pos = code.rfind("if __name__")

# Find the ORIGINAL code block (before any injection)
# The original app.py stops at the /lessons route and error handlers
# Find the LAST original route before injections started
original_end_marker = "def server_error(e):"
original_end = code.find(original_end_marker)
if original_end != -1:
    # Find the end of this function
    func_end = code.find("\n\n", original_end + len(original_end_marker))
    if func_end == -1 or func_end > if_pos:
        func_end = code.find("\n@app", original_end + len(original_end_marker))
        if func_end == -1 or func_end > if_pos:
            func_end = code.find("\n#", original_end + len(original_end_marker))
            if func_end == -1:
                func_end = if_pos

    # Extract the CLEAN original part (up to end of error handlers)
    clean_part = code[:func_end].rstrip()

    # STEP 2: Build the ONE clean injection block
    injection = """


# ============================================================
# ADMIN CRUD + PLACEMENT ENGINE (v40 - Single Clean Injection)
# ============================================================
import sqlite3

def _admin_db():
    conn = sqlite3.connect("data/yamen_academy.db")
    conn.row_factory = sqlite3.Row
    return conn

# --- Lesson CRUD (disk-backed via content_engine) ---
@app.route("/api/admin/content/create", methods=["POST"])
def admin_lesson_create():
    try:
        return jsonify(create_lesson_from_admin(request.get_json(force=True)))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/admin/content/update", methods=["POST"])
def admin_lesson_update():
    try:
        return jsonify(update_lesson_from_admin(request.get_json(force=True)))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/admin/content/delete", methods=["POST"])
def admin_lesson_delete():
    try:
        return jsonify(delete_lesson_from_admin(request.get_json(force=True).get("lesson_id")))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Question CRUD (SQLite-backed) ---
@app.route("/api/admin/questions")
def admin_question_list():
    conn = _admin_db()
    rows = conn.execute("SELECT * FROM questions ORDER BY skill, id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/questions/add", methods=["POST"])
def admin_question_add():
    data = request.get_json(force=True)
    conn = _admin_db()
    conn.execute(
        "INSERT INTO questions(skill,question,option_a,option_b,option_c,option_d,correct_answer,difficulty) VALUES(?,?,?,?,?,?,?,?)",
        (data["skill"], data["question"], data["option_a"], data["option_b"],
         data["option_c"], data["option_d"], data["correct_answer"].strip().upper(),
         data.get("difficulty", "beginner"))
    )
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201

@app.route("/api/admin/questions/edit/<int:qid>", methods=["POST"])
def admin_question_edit(qid):
    data = request.get_json(force=True)
    sets, vals = [], []
    for key in ["skill", "question", "option_a", "option_b", "option_c", "option_d", "correct_answer", "difficulty"]:
        if key in data:
            sets.append(key + "=?")
            vals.append(data[key])
    if not sets:
        return jsonify({"error": "No fields to update"}), 400
    sets.append('updated_at=datetime("now","localtime")')
    vals.append(qid)
    conn = _admin_db()
    conn.execute("UPDATE questions SET " + ",".join(sets) + " WHERE id=?", vals)
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/admin/questions/delete/<int:qid>", methods=["POST"])
def admin_question_delete(qid):
    conn = _admin_db()
    conn.execute("DELETE FROM questions WHERE id=?", (qid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# --- Placement Test Engine ---
@app.route("/api/placement/questions")
def placement_question_list():
    conn = _admin_db()
    rows = conn.execute(
        "SELECT id, skill, question, option_a, option_b, option_c, option_d, difficulty FROM questions ORDER BY RANDOM()"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/placement/submit", methods=["POST"])
def placement_test_submit():
    data = request.get_json(force=True)
    student_id = data.get("student_id", session.get("student_id", 1))
    answers = data.get("answers", [])
    if not answers:
        return jsonify({"error": "No answers provided"}), 400

    total = len(answers)
    correct = 0
    conn = _admin_db()
    for ans in answers:
        row = conn.execute(
            "SELECT correct_answer FROM questions WHERE id=?",
            (ans.get("question_id"),)
        ).fetchone()
        if row and row["correct_answer"].strip().upper() == ans.get("answer", "").strip().upper():
            correct += 1

    score_pct = round((correct / total) * 100, 1) if total > 0 else 0

    if score_pct < 50:
        band, level, label, path = "A1-A2", "beginner", "Weak", "foundations"
    elif score_pct <= 75:
        band, level, label, path = "B1-B2", "intermediate", "Intermediate", "core"
    else:
        band, level, label, path = "C1-C2", "advanced", "Advanced", "mastery"

    conn.execute(
        "INSERT INTO placement_results(student_id,band,level,path,score_pct) VALUES(?,?,?,?,?)",
        (student_id, band, level, path, score_pct)
    )
    try:
        conn.execute("UPDATE students SET level=?, placement_done=1, placement_level=? WHERE telegram_id=?",
                     (level, level, student_id))
    except:
        pass
    conn.commit()
    conn.close()

    session["student_id"] = student_id
    session["placement_level"] = level

    return jsonify({
        "status": "ok",
        "score": score_pct,
        "correct": correct,
        "total": total,
        "band": band,
        "level": level,
        "label": label,
        "path": path,
        "message": f"Score: {score_pct}% - Level: {label} ({band})"
    })

"""

    # STEP 3: Reconstruct app.py = clean original + injection + if __name__
    new_code = clean_part + injection + "\n" + code[if_pos:]

    with open(APP, "w", encoding="utf-8") as f:
        f.write(new_code)

    # STEP 4: Verify no duplicates
    routes = re.findall(r"""@app\.route\(['\"]([^'\"]+)['\"]""", new_code)
    from collections import Counter
    counts = Counter(routes)
    dupes = {k: v for k, v in counts.items() if v > 1}
    if dupes:
        print("WARNING: STILL HAVE DUPLICATES:")
        for k, v in dupes.items():
            print(f"  {k}: {v}x")
    else:
        print(f"SUCCESS: {len(routes)} unique routes, 0 duplicates")

    # STEP 5: List all routes for confirmation
    print(f"\n{'='*60}")
    print(f"  FINAL ROUTE MAP ({len(routes)} routes)")
    print(f"{'='*60}")
    for r in sorted(set(routes)):
        print(f"  {r}")

