import json, os
from flask import Blueprint, request, jsonify
from config import JSON_PLACEMENT
from modules.models import query_db, execute_db

placement_bp = Blueprint("placement_bp", __name__)

def load_questions():
    with open(JSON_PLACEMENT, "r", encoding="utf-8") as f:
        questions = json.load(f)
    return questions

def save_questions(questions):
    with open(JSON_PLACEMENT, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

def classify_level(score, total):
    if total == 0:
        return "ضعيف (Beginner)"
    if score <= 3:
        return "ضعيف (Beginner)"
    elif score <= 7:
        return "متوسط (Intermediate)"
    else:
        return "متقدم (Advanced)"

# ===== STUDENT API: get questions (without correct_answer) =====
@placement_bp.route("/api/placement/questions")
def get_questions():
    questions = load_questions()
    # Strip correct_answer for students
    safe = []
    for q in questions:
        safe.append({
            "id": q["id"],
            "question_text": q["question_text"],
            "option_a": q["option_a"],
            "option_b": q["option_b"],
            "option_c": q["option_c"],
            "option_d": q["option_d"],
            "difficulty": q.get("difficulty", "medium")
        })
    return jsonify(safe)

# ===== STUDENT API: submit =====
@placement_bp.route("/api/placement/submit", methods=["POST"])
def submit_placement():
    data = request.get_json()
    student_id = data.get("student_id")
    answers = data.get("answers", {})  # { "1": "B", "2": "B", ... }

    if not student_id:
        return jsonify({"error": "student_id required"}), 400

    execute_db("INSERT OR IGNORE INTO students (telegram_id) VALUES (?)", (student_id,))

    questions = load_questions()
    total = len(questions)
    correct = 0

    for q in questions:
        qid = str(q["id"])
        chosen = answers.get(qid, "").upper()
        if chosen == q["correct_answer"].upper():
            correct += 1

    level = classify_level(correct, total)

    # Save to DB
    execute_db(
        "INSERT INTO placement_results (student_id, score, total, level, answers_json) VALUES (?,?,?,?,?)",
        (student_id, correct, total, level, json.dumps(answers))
    )
    execute_db(
        "UPDATE students SET placement_done=1, placement_level=? WHERE telegram_id=?",
        (level, student_id)
    )

    return jsonify({
        "score": correct,
        "total": total,
        "level": level,
        "percentage": round(correct/total*100, 1) if total > 0 else 0
    })

# ===== STUDENT API: placement status =====
@placement_bp.route("/api/placement/status/<int:student_id>")
def placement_status(student_id):
    row = query_db(
        "SELECT placement_done, placement_level FROM students WHERE telegram_id=?",
        (student_id,), one=True
    )
    if not row:
        return jsonify({"completed": False, "level": None})
    result_row = query_db(
        "SELECT score, total, level, completed_at FROM placement_results WHERE student_id=? ORDER BY id DESC LIMIT 1",
        (student_id,), one=True
    )
    return jsonify({
        "completed": bool(row["placement_done"]),
        "level": row["placement_level"],
        "result": {"score": result_row["score"], "total": result_row["total"], "level": result_row["level"], "completed_at": result_row["completed_at"]} if result_row else None
    })

# ===== ADMIN API: full questions with correct_answer =====
@placement_bp.route("/api/admin/placement_questions_full")
def admin_placement_questions():
    questions = load_questions()
    return jsonify(questions)

# ===== ADMIN API: update a question =====
@placement_bp.route("/api/admin/placement_questions/update/<int:qid>", methods=["PUT"])
def update_placement_question(qid):
    data = request.get_json()
    questions = load_questions()
    for q in questions:
        if q["id"] == qid:
            q["question_text"] = data.get("question_text", q["question_text"])
            q["option_a"] = data.get("option_a", q["option_a"])
            q["option_b"] = data.get("option_b", q["option_b"])
            q["option_c"] = data.get("option_c", q["option_c"])
            q["option_d"] = data.get("option_d", q["option_d"])
            q["correct_answer"] = data.get("correct_answer", q["correct_answer"]).upper()
            q["difficulty"] = data.get("difficulty", q.get("difficulty", "medium"))
            break
    save_questions(questions)
    return jsonify({"ok": True})

# ===== ADMIN API: placement results =====
@placement_bp.route("/api/admin/placement_results")
def admin_placement_results():
    rows = query_db("""
        SELECT pr.*, s.name as student_name
        FROM placement_results pr
        JOIN students s ON pr.student_id = s.telegram_id
        ORDER BY pr.completed_at DESC
    """)
    return jsonify([dict(r) for r in rows])
