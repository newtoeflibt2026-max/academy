from flask import Blueprint, request, jsonify, g
from modules.models import query_db

placement_mw = Blueprint("placement_mw", __name__)

# --- Middleware: check if student completed placement test ---
def check_placement(student_id):
    """Returns True if student has a placement result, else False"""
    if not student_id:
        return False
    row = query_db(
        "SELECT id FROM placement_results WHERE student_id=?",
        (student_id,), one=True
    )
    return row is not None

# --- API: fetch placement questions ---
@placement_mw.route("/api/placement/questions")
def placement_questions():
    rows = query_db(
        "SELECT id, question_text, option_a, option_b, option_c, option_d, difficulty FROM placement_questions WHERE is_active=1"
    )
    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "question_text": r["question_text"],
            "option_a": r["option_a"],
            "option_b": r["option_b"],
            "option_c": r["option_c"],
            "option_d": r["option_d"],
            "difficulty": r["difficulty"],
        })
    return jsonify(result)

# --- API: submit placement test ---
@placement_mw.route("/api/placement/submit", methods=["POST"])
def placement_submit():
    data = request.get_json()
    student_id = data.get("student_id")
    answers = data.get("answers", {})  # {question_id: chosen_option}

    if not student_id:
        return jsonify({"error": "student_id required"}), 400

    # Ensure student exists
    from modules.models import execute_db
    execute_db(
        "INSERT OR IGNORE INTO students (telegram_id) VALUES (?)",
        (student_id,)
    )

    total = 0
    correct = 0
    for qid_str, ans in answers.items():
        qid = int(qid_str)
        row = query_db(
            "SELECT correct_answer FROM placement_questions WHERE id=?",
            (qid,), one=True
        )
        if row:
            total += 1
            if ans.upper() == row["correct_answer"].upper():
                correct += 1

    # Determine level
    if total == 0:
        level = "Beginner"
    else:
        pct = correct / total
        if pct >= 0.8:
            level = "Advanced"
        elif pct >= 0.5:
            level = "Intermediate"
        else:
            level = "Beginner"

    execute_db(
        "INSERT INTO placement_results (student_id, score, total, level) VALUES (?,?,?,?)",
        (student_id, correct, total, level)
    )
    execute_db(
        "UPDATE students SET level=? WHERE telegram_id=?",
        (1 if level=="Beginner" else (2 if level=="Intermediate" else 3), student_id)
    )

    return jsonify({
        "score": correct,
        "total": total,
        "level": level,
        "percentage": round(correct/total*100, 1) if total>0 else 0
    })

# --- API: check placement status ---
@placement_mw.route("/api/placement/status/<int:student_id>")
def placement_status(student_id):
    completed = check_placement(student_id)
    result = None
    if completed:
        row = query_db(
            "SELECT score, total, level, completed_at FROM placement_results WHERE student_id=? ORDER BY id DESC LIMIT 1",
            (student_id,), one=True
        )
        if row:
            result = {"score": row["score"], "total": row["total"], "level": row["level"], "completed_at": row["completed_at"]}
    return jsonify({"completed": completed, "result": result})
