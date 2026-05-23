"""Yamen Academy - Placement Test Blueprint (Phase 7 — aligned with actual academy.db schema)"""
from flask import Blueprint, request, jsonify, render_template
import sqlite3, traceback, os

placement_bp = Blueprint("placement_bp", __name__)

def _db():
    # academy.db at project root
    db_path = "academy.db"
    if not os.path.exists(db_path):
        # Railway fallback
        for cand in ["/app/academy.db", "data/academy.db"]:
            if os.path.exists(cand):
                db_path = cand
                break
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def _target_from_score(pct):
    """Map placement % → target_score (TOEFL scale)."""
    if pct < 35:   return 59   # foundation
    if pct < 50:   return 59
    if pct < 65:   return 69
    if pct < 80:   return 79
    return 90

def _path_from_score(pct):
    if pct < 50:  return "foundation"
    if pct < 70:  return "intermediate"
    return "advanced"

def _level_from_score(pct):
    if pct < 35:   return "A1"
    if pct < 50:   return "A2"
    if pct < 65:   return "B1"
    if pct < 80:   return "B2"
    return "C1"

@placement_bp.route("/placement")
def placement_page():
    return render_template("placement.html")

@placement_bp.route("/api/placement/questions")
def placement_questions_api():
    try:
        conn = _db()
        rows = conn.execute("""
            SELECT id, question_text, option_a, option_b, option_c, option_d,
                   skill, difficulty
            FROM placement_questions
            WHERE is_active=1
            ORDER BY RANDOM()
            LIMIT 20
        """).fetchall()
        conn.close()
        out = []
        for r in rows:
            out.append({
                "id": r["id"],
                "question": r["question_text"],
                "question_text": r["question_text"],
                "option_a": r["option_a"],
                "option_b": r["option_b"],
                "option_c": r["option_c"],
                "option_d": r["option_d"],
                "skill": r["skill"] or "",
                "difficulty": r["difficulty"] or "medium",
            })
        return jsonify(out)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@placement_bp.route("/api/placement/submit", methods=["POST"])
def placement_submit():
    try:
        data = request.get_json(force=True) or {}
    except Exception:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    student_id = data.get("student_id") or data.get("telegram_id")
    answers = data.get("answers", [])

    if not student_id:
        return jsonify({"status": "error", "message": "Missing student_id"}), 400
    if not answers:
        return jsonify({"status": "error", "message": "No answers provided"}), 400

    try:
        sid = int(student_id)
        conn = _db()

        # Normalize answers to list of {question_id, answer}
        norm = []
        if isinstance(answers, dict):
            for k, v in answers.items():
                norm.append({"question_id": k, "answer": v})
        else:
            norm = answers

        total = 0
        correct = 0
        for a in norm:
            qid = a.get("question_id") or a.get("id")
            user_ans = (a.get("answer") or a.get("selected") or "").strip().upper()
            if not qid:
                continue
            row = conn.execute(
                "SELECT correct_option FROM placement_questions WHERE id=?",
                (int(qid),)
            ).fetchone()
            if row:
                total += 1
                if (row["correct_option"] or "").strip().upper() == user_ans:
                    correct += 1

        pct = round((correct / total) * 100, 1) if total > 0 else 0.0
        level     = _level_from_score(pct)
        path      = _path_from_score(pct)
        target    = _target_from_score(pct)

        # Ensure student row exists
        conn.execute("INSERT OR IGNORE INTO students (telegram_id) VALUES (?)", (sid,))

        # Save into students table (the columns that actually exist)
        conn.execute("""
            UPDATE students
               SET placement_done = 1,
                   placement_score = ?,
                   placement_path = ?,
                   level = ?,
                   target_score = COALESCE(target_score, ?)
             WHERE telegram_id = ?
        """, (pct, path, path, target, sid))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "ok",
            "score": pct,
            "correct": correct,
            "total": total,
            "level": level,
            "path": path,
            "target_score": target,
            "message": "تم حفظ نتيجتك بنجاح",
            "redirect": "/student?student_id={}".format(sid),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Server error: {}".format(str(e))}), 500

@placement_bp.route("/api/placement/status/<int:student_id>")
def placement_status(student_id):
    try:
        conn = _db()
        row = conn.execute(
            "SELECT placement_done, placement_score, placement_path, level, target_score FROM students WHERE telegram_id=?",
            (student_id,)
        ).fetchone()
        conn.close()
        if row and row["placement_done"] == 1:
            return jsonify({
                "placement_done": True,
                "score": row["placement_score"],
                "path": row["placement_path"],
                "level": row["level"],
                "target_score": row["target_score"],
            })
        return jsonify({"placement_done": False})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
