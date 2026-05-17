"""SURGICAL FIX: Placement test submit — grade, save, lock exam."""
import re, os

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
with open(APP, "r", encoding="utf-8") as f:
    code = f.read()

# Find and replace the placement_submit route (the duplicate/broken one)
# We need to find ALL occurrences of placement_submit and keep only ONE clean version

# Strategy: Remove ALL existing placement_submit functions, then inject one clean version

# Step 1: Remove all existing placement_submit functions
lines = code.split("\n")
clean_lines = []
skip = False
skip_count = 0
removed = 0

for line in lines:
    stripped = line.strip()
    
    # Detect start of a placement_submit route
    if "@app.route" in stripped and "placement/submit" in stripped:
        skip = True
        removed += 1
        continue
    
    if skip:
        # Find the function definition
        if "def " in stripped and "placement" in stripped and "submit" in stripped:
            skip_count = 0
            continue
        # Track indentation to find end of function
        if stripped == "":
            skip_count += 1
            if skip_count >= 2:
                skip = False
                skip_count = 0
            continue
        skip_count = 0
        # Skip the line (it's part of the function body)
        continue
    
    clean_lines.append(line)

code = "\n".join(clean_lines)
print(f"Removed {removed} duplicate placement_submit route(s)")

# Step 2: Inject the single clean placement_submit
new_route = """

@app.route("/api/placement/submit", methods=["POST"])
def placement_test_submit():
    import sqlite3

    # 1. Parse incoming data
    data = request.get_json(force=True) if request.is_json else request.form.to_dict()
    student_id = data.get("student_id") or session.get("student_id") or data.get("telegram_id")
    answers = data.get("answers", [])

    if not student_id:
        return jsonify({"error": "Missing student_id"}), 400
    if not answers:
        return jsonify({"error": "No answers provided"}), 400

    # 2. Grade against the questions table
    total = len(answers)
    correct = 0
    conn = sqlite3.connect("data/yamen_academy.db")

    for ans in answers:
        qid = ans.get("question_id")
        user_answer = (ans.get("answer") or "").strip().upper()
        if not qid:
            continue
        row = conn.execute(
            "SELECT correct_answer FROM questions WHERE id = ?",
            (int(qid),)
        ).fetchone()
        if row and row[0].strip().upper() == user_answer:
            correct += 1

    # 3. Calculate score and map to CEFR level
    score_pct = round((correct / total) * 100, 1) if total > 0 else 0

    if score_pct < 35:
        band, level, label = "A1", "beginner", "Beginner"
    elif score_pct < 50:
        band, level, label = "A2", "beginner", "Elementary"
    elif score_pct < 65:
        band, level, label = "B1", "intermediate", "Intermediate"
    elif score_pct < 80:
        band, level, label = "B2", "intermediate", "Upper Intermediate"
    else:
        band, level, label = "C1", "advanced", "Advanced"

    # 4. Save to placement_results table
    conn.execute(
        "INSERT INTO placement_results (student_id, band, level, path, score_pct) VALUES (?, ?, ?, ?, ?)",
        (int(student_id), band, level, level, score_pct)
    )

    # 5. LOCK THE EXAM: Update student record
    conn.execute(
        "UPDATE students SET level = ?, placement_level = ?, placement_done = 1 WHERE telegram_id = ?",
        (level, level, int(student_id))
    )

    # Also update users table if it exists
    try:
        conn.execute(
            "UPDATE users SET level = ? WHERE id = ?",
            (level, int(student_id))
        )
    except Exception:
        pass

    conn.commit()
    conn.close()

    # 6. Store in session
    session["student_id"] = int(student_id)
    session["placement_level"] = level
    session["placement_done"] = True
    session["placement_band"] = band
    session["placement_score"] = score_pct

    # 7. Return result
    result = {
        "status": "ok",
        "score": score_pct,
        "correct": correct,
        "total": total,
        "band": band,
        "level": level,
        "label": label,
        "redirect": f"/dashboard/{student_id}",
        "message": f"You scored {score_pct}% — your level is {label} ({band})"
    }
    print(f"[PLACEMENT] Student {student_id}: {correct}/{total} ({score_pct}%) -> {level} ({band})")
    return jsonify(result)

"""

# Inject before if __name__
insert_point = code.find("if __name__")
if insert_point == -1:
    insert_point = code.find("if __name__")

if insert_point != -1:
    code = code[:insert_point] + new_route + "\n" + code[insert_point:]
else:
    code += new_route

# Save
with open(APP, "w", encoding="utf-8") as f:
    f.write(code)

# Step 3: Verify — check how many placement_submit routes remain
route_count = code.count("placement/submit")
print(f"\nPlacement submit routes remaining: {route_count}")
print("[DONE] Placement test workflow fixed:")
print("  - Auto-grading against questions table")
print("  - CEFR level mapping (A1/A2/B1/B2/C1)")
print("  - students.placement_done = 1 (exams locked)")
print("  - placement_results table updated")
print("  - Session stored for dashboard display")
