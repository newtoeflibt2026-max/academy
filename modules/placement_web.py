"""Yamen Academy v40 - Placement Test Blueprint (Fixed)"""
from flask import Blueprint, request, jsonify, session
import sqlite3, traceback

placement_bp = Blueprint("placement", __name__)

def _db():
    conn = sqlite3.connect("data/yamen_academy.db")
    conn.row_factory = sqlite3.Row
    return conn

@placement_bp.route("/placement")
def placement_page():
    from flask import render_template
    return render_template("placement.html")

@placement_bp.route("/api/placement/questions")
def placement_questions_api():
    try:
        conn = _db()
        rows = conn.execute("SELECT id, skill, question, option_a, option_b, option_c, option_d, difficulty FROM questions ORDER BY RANDOM()").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@placement_bp.route("/api/placement/submit", methods=["POST"])
def placement_submit():
    try:
        data = request.get_json(force=True)
    except Exception:
        try:
            import json
            data = json.loads(request.data) if request.data else {}
        except Exception:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    student_id = data.get("student_id") or data.get("telegram_id")
    answers = data.get("answers", [])

    if not student_id:
        return jsonify({"status": "error", "message": "Missing student_id"}), 400
    if not answers:
        return jsonify({"status": "error", "message": "No answers provided"}), 400

    try:
        conn = _db()
        total = len(answers)
        correct = 0

        for a in answers:
            qid = a.get("question_id")
            user_ans = (a.get("answer") or "").strip().upper()
            if not qid:
                continue
            row = conn.execute(
                "SELECT correct_answer FROM questions WHERE id = ?",
                (int(qid),)
            ).fetchone()
            if row and row["correct_answer"].strip().upper() == user_ans:
                correct += 1

        pct = round((correct / total) * 100, 1) if total > 0 else 0

        if pct < 35:
            band, level, label = "A1", "beginner", "Beginner"
        elif pct < 50:
            band, level, label = "A2", "beginner", "Elementary"
        elif pct < 65:
            band, level, label = "B1", "intermediate", "Intermediate"
        elif pct < 80:
            band, level, label = "B2", "intermediate", "Upper Intermediate"
        else:
            band, level, label = "C1", "advanced", "Advanced"

        sid_int = int(student_id)

        # Save results
        conn.execute(
            "INSERT INTO placement_results (student_id, band, level, path, score_pct) VALUES (?,?,?,?,?)",
            (sid_int, band, level, level, pct)
        )
        conn.execute(
            "UPDATE students SET level = ?, placement_level = ?, placement_done = 1 WHERE telegram_id = ?",
            (level, level, sid_int)
        )
        try:
            conn.execute("UPDATE users SET level = ? WHERE id = ?", (level, sid_int))
        except Exception:
            pass

        conn.commit()
        conn.close()

        session["student_id"] = sid_int
        session["placement_level"] = level
        session["placement_done"] = True
        session["placement_score"] = pct
        session["placement_band"] = band

        return jsonify({
            "status": "ok",
            "score": pct,
            "correct": correct,
            "total": total,
            "band": band,
            "level": level,
            "label": label,
            "redirect": "/dashboard/{}".format(student_id),
            "message": "Score: {}% - Level: {} ({})".format(pct, label, band)
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Server error: {}".format(str(e))}), 500

@placement_bp.route("/api/placement/status/<int:student_id>")
def placement_status(student_id):
    try:
        conn = _db()
        row = conn.execute(
            "SELECT placement_done, placement_level, level FROM students WHERE telegram_id = ?",
            (student_id,)
        ).fetchone()
        conn.close()
        if row and row["placement_done"] == 1:
            return jsonify({
                "placement_done": True,
                "level": row["placement_level"] or row["level"],
                "locked": True
            })
        return jsonify({"placement_done": False, "locked": False})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
