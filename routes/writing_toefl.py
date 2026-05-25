import json
# -*- coding: utf-8 -*-
"""
TOEFL Writing Track - Flask Blueprint
Routes for: track overview, stages, lessons, exams, AI grading
"""
import os, json, sqlite3, time
from flask import Blueprint, render_template, request, jsonify, redirect, url_for

writing_bp = Blueprint("writing_toefl", __name__)

DB_PATH = os.environ.get("DB_PATH", "academy.db")

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _get_tg_id():
    """Get telegram_id from query/cookie/header. Same pattern as app.py."""
    return (request.args.get("user_id")
        or request.args.get("tg_id")
        or request.cookies.get("user_id")
        or request.headers.get("X-User-Id")
        or "guest")

# ═══════════════════════════════════════════════════════════
# PAGE: Writing Track Overview (الصفحة الرئيسية للمسار)
# ═══════════════════════════════════════════════════════════
@writing_bp.route("/writing")
def writing_track_page():
    tg_id = _get_tg_id()
    conn = _db()
    c = conn.cursor()

    track = c.execute("SELECT * FROM writing_tracks WHERE code='toefl_writing'").fetchone()
    if not track:
        return "Writing track not initialized", 500

    stages = c.execute("""
        SELECT s.*,
            (SELECT COUNT(*) FROM writing_lessons WHERE stage_id=s.id) AS lesson_count,
            (SELECT COUNT(*) FROM writing_progress wp WHERE wp.stage_id=s.id AND wp.telegram_id=? AND wp.status='completed') AS done_count
        FROM writing_stages s
        WHERE s.track_id=?
        ORDER BY s.order_index
    """, (tg_id, track["id"])).fetchall()

    stages_list = []
    for s in stages:
        sd = dict(s)
        sd["progress_pct"] = int((sd["done_count"] / sd["lesson_count"]) * 100) if sd["lesson_count"] else 0
        stages_list.append(sd)

    conn.close()
    return render_template("toefl_writing/track.html",
        track=dict(track), stages=stages_list, user_id=tg_id)

# ═══════════════════════════════════════════════════════════
# PAGE: Stage detail (الدروس داخل المرحلة)
# ═══════════════════════════════════════════════════════════
@writing_bp.route("/writing/stage/<int:stage_id>")
def view_stage(stage_id):
    tg_id = request.args.get("user_id") or _get_tg_id()
    conn = _db(); c = conn.cursor()
    stage = c.execute("SELECT * FROM writing_stages WHERE id=?", (stage_id,)).fetchone()
    if not stage:
        conn.close()
        return "Stage not found", 404

    lessons = c.execute("""SELECT * FROM writing_lessons
        WHERE stage_id=? ORDER BY order_index""", (stage_id,)).fetchall()

    prog_rows = c.execute("""SELECT lesson_id, status, best_score
        FROM writing_progress WHERE telegram_id=?""", (tg_id,)).fetchall()
    progress_map = {r["lesson_id"]: dict(r) for r in prog_rows}
    conn.close()

    lessons_list = [dict(l) for l in lessons]
    prev_completed = True
    for L in lessons_list:
        if L.get("is_exam"):
            all_done = all(
                progress_map.get(x["id"], {}).get("status") == "completed"
                for x in lessons_list if not x.get("is_exam")
            ) and len([x for x in lessons_list if not x.get("is_exam")]) > 0
            L["locked"] = not all_done
        else:
            L["locked"] = not prev_completed
            prev_completed = progress_map.get(L["id"], {}).get("status") == "completed"

    return render_template("toefl_writing/stage.html",
        stage=stage, lessons=lessons_list,
        progress_map=progress_map, user_id=tg_id)


@writing_bp.route("/writing/lesson/<int:lesson_id>")
def writing_lesson_page(lesson_id):
    tg_id = _get_tg_id()
    conn = _db()
    c = conn.cursor()

    lesson = c.execute("SELECT * FROM writing_lessons WHERE id=?", (lesson_id,)).fetchone()
    if not lesson:
        return "Lesson not found", 404

    questions = c.execute("""
        SELECT * FROM writing_questions
        WHERE lesson_id=? AND is_exam=0
        ORDER BY order_index
    """, (lesson_id,)).fetchall()

    stage = c.execute("SELECT * FROM writing_stages WHERE id=?", (lesson["stage_id"],)).fetchone()

    qs = []
    for q in questions:
        qd = dict(q)
        if qd.get("options_json"):
            try: qd["options"] = json.loads(qd["options_json"])
            except: qd["options"] = []
        qs.append(qd)

    conn.close()
    return render_template("toefl_writing/lesson.html",
        lesson=dict(lesson), stage=dict(stage) if stage else None,
        questions=qs, user_id=tg_id)

# ═══════════════════════════════════════════════════════════
# API: Submit lesson quiz answers
# ═══════════════════════════════════════════════════════════
@writing_bp.route("/api/writing/lesson/<int:lesson_id>/submit", methods=["POST"])
def api_lesson_submit(lesson_id):
    data = request.get_json(force=True, silent=True) or {}
    tg_id = data.get("user_id") or _get_tg_id()
    answers = data.get("answers", {})

    conn = _db(); c = conn.cursor()
    lesson = c.execute("SELECT * FROM writing_lessons WHERE id=?", (lesson_id,)).fetchone()
    if not lesson:
        conn.close()
        return jsonify({"success": False, "error": "Lesson not found"}), 404

    # Get student tier (default tier69)
    tier_row = c.execute("SELECT tier FROM student_writing_target WHERE telegram_id=?", (tg_id,)).fetchone()
    student_tier = tier_row["tier"] if tier_row else "tier69"

    is_exam_lesson = bool(lesson["is_exam"])
    threshold = 80 if is_exam_lesson else (65 if student_tier=="tier59" else (75 if student_tier=="tier69" else 85))

    # Get questions (filter by tier if applicable; "all" always included)
    questions = c.execute("""SELECT * FROM writing_questions
        WHERE lesson_id=? AND (target_tier='all' OR target_tier=?)
        ORDER BY order_index""", (lesson_id, student_tier)).fetchall()

    correct = 0
    total = len(questions)
    feedback = []

    for q in questions:
        qid = str(q["id"])
        student_ans = (answers.get(qid) or "").strip()
        is_correct = False

        if q["q_type"] == "mcq":
            is_correct = student_ans.lower() == (q["correct_answer"] or "").strip().lower()
        elif q["q_type"] == "sentence_order":
            try:
                from ai.toefl_grader import grade_sentence_order
                try:
                    student_words = json.loads(student_ans) if student_ans.startswith("[") else student_ans.split()
                except Exception:
                    student_words = student_ans.split()
                res = grade_sentence_order(q["correct_answer"] or "", student_words)
                is_correct = res.get("correct", False) if isinstance(res, dict) else bool(res)
            except Exception:
                # Fallback: exact match ignoring case and extra spaces
                norm_correct = " ".join((q["correct_answer"] or "").lower().split())
                norm_student = " ".join(student_ans.lower().split())
                is_correct = norm_correct == norm_student

        if is_correct:
            correct += 1

        feedback.append({
            "question_id": q["id"],
            "is_correct": is_correct,
            "your_answer": student_ans,
            "correct_answer": q["correct_answer"],
            "explanation": q["explanation_ar"]
        })

        c.execute("""INSERT INTO writing_attempts
            (telegram_id, question_id, stage_id, lesson_id, answer_text, is_correct, created_at)
            VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
            (tg_id, q["id"], lesson["stage_id"], lesson_id, student_ans, 1 if is_correct else 0))

    score_pct = (correct/total*100) if total else 0
    passed = score_pct >= threshold

    # Update progress
    existing = c.execute("""SELECT id, best_score FROM writing_progress
        WHERE telegram_id=? AND lesson_id=?""", (tg_id, lesson_id)).fetchone()
    if existing:
        new_best = max(existing["best_score"] or 0, score_pct)
        new_status = "completed" if (passed or (existing["best_score"] or 0) >= threshold) else "in_progress"
        c.execute("""UPDATE writing_progress
            SET best_score=?, attempts_count=attempts_count+1, status=?,
                completed_at=CASE WHEN ?='completed' AND completed_at IS NULL THEN CURRENT_TIMESTAMP ELSE completed_at END
            WHERE id=?""",
            (new_best, new_status, new_status, existing["id"]))
    else:
        c.execute("""INSERT INTO writing_progress
            (telegram_id, track_id, stage_id, lesson_id, status, best_score, attempts_count, completed_at)
            VALUES (?, 1, ?, ?, ?, ?, 1, CASE WHEN ?=1 THEN CURRENT_TIMESTAMP ELSE NULL END)""",
            (tg_id, lesson["stage_id"], lesson_id,
             "completed" if passed else "in_progress",
             score_pct, 1 if passed else 0))

    # Next lesson / stage exam / next stage
    next_lesson_id = None
    stage_exam_id = None
    next_stage_id = None

    if is_exam_lesson:
        ns = c.execute("""SELECT id FROM writing_stages
            WHERE order_index > (SELECT order_index FROM writing_stages WHERE id=?)
            ORDER BY order_index ASC LIMIT 1""", (lesson["stage_id"],)).fetchone()
        next_stage_id = ns["id"] if (ns and passed) else None
    else:
        nl = c.execute("""SELECT id FROM writing_lessons
            WHERE stage_id=? AND order_index>? AND is_exam=0
            ORDER BY order_index ASC LIMIT 1""",
            (lesson["stage_id"], lesson["order_index"])).fetchone()
        next_lesson_id = nl["id"] if nl else None
        if not next_lesson_id:
            ex = c.execute("""SELECT id FROM writing_lessons
                WHERE stage_id=? AND is_exam=1 LIMIT 1""", (lesson["stage_id"],)).fetchone()
            stage_exam_id = ex["id"] if ex else None

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "score": round(score_pct, 1),
        "correct": correct,
        "total": total,
        "passed": passed,
        "threshold": threshold,
        "tier": student_tier,
        "is_exam": is_exam_lesson,
        "feedback": feedback,
        "next_lesson_id": next_lesson_id,
        "stage_exam_id": stage_exam_id,
        "next_stage_id": next_stage_id
    })


@writing_bp.route("/api/writing/grade-email", methods=["POST"])
def api_grade_email():
    data = request.get_json(force=True, silent=True) or {}
    tg_id = data.get("user_id") or _get_tg_id()
    question_id = data.get("question_id")
    student_email = data.get("email_text", "")

    conn = _db()
    c = conn.cursor()
    q = c.execute("SELECT * FROM writing_questions WHERE id=?", (question_id,)).fetchone()
    if not q:
        conn.close()
        return jsonify({"success": False, "error": "Question not found"}), 404

    requirements = []
    try:
        requirements = json.loads(q["requirements_json"]) if q["requirements_json"] else []
    except: pass

    from ai.toefl_grader import grade_email
    result = grade_email(q["scenario_text"] or "", requirements, student_email)

    # Save attempt
    c.execute("""INSERT INTO writing_attempts
        (telegram_id, question_id, stage_id, lesson_id, answer_text, ai_score, ai_band, ai_feedback_json, created_at)
        VALUES (?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
        (tg_id, question_id, q["stage_id"], q["lesson_id"], student_email,
         result.get("score", 0), result.get("band_label", ""), json.dumps(result, ensure_ascii=False)))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "result": result})

# ═══════════════════════════════════════════════════════════
# API: Grade Discussion (Task 3)
# ═══════════════════════════════════════════════════════════
@writing_bp.route("/api/writing/grade-discussion", methods=["POST"])
def api_grade_discussion():
    data = request.get_json(force=True, silent=True) or {}
    tg_id = data.get("user_id") or _get_tg_id()
    question_id = data.get("question_id")
    student_response = data.get("response_text", "")

    conn = _db()
    c = conn.cursor()
    q = c.execute("SELECT * FROM writing_questions WHERE id=?", (question_id,)).fetchone()
    if not q:
        conn.close()
        return jsonify({"success": False, "error": "Question not found"}), 404

    from ai.toefl_grader import grade_discussion
    result = grade_discussion(
        q["professor_question"] or "",
        q["student1_opinion"] or "",
        q["student2_opinion"] or "",
        student_response
    )

    c.execute("""INSERT INTO writing_attempts
        (telegram_id, question_id, stage_id, lesson_id, answer_text, ai_score, ai_band, ai_feedback_json, created_at)
        VALUES (?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
        (tg_id, question_id, q["stage_id"], q["lesson_id"], student_response,
         result.get("score", 0), result.get("band_label", ""), json.dumps(result, ensure_ascii=False)))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "result": result})

# ═══════════════════════════════════════════════════════════
# API: Health check
# ═══════════════════════════════════════════════════════════
@writing_bp.route("/api/writing/health")
def api_health():
    conn = _db()
    c = conn.cursor()
    stats = {
        "tracks": c.execute("SELECT COUNT(*) FROM writing_tracks").fetchone()[0],
        "stages": c.execute("SELECT COUNT(*) FROM writing_stages").fetchone()[0],
        "lessons": c.execute("SELECT COUNT(*) FROM writing_lessons").fetchone()[0],
        "questions": c.execute("SELECT COUNT(*) FROM writing_questions").fetchone()[0],
        "ai_keys_loaded": bool(os.environ.get("GEMINI_WRITING_KEYS") or os.environ.get("GEMINI_API_KEY"))
    }
    conn.close()
    return jsonify({"ok": True, "stats": stats})
# Jinja filter for parsing JSON strings in templates
@writing_bp.app_template_filter('fromjson')
def fromjson_filter(s):
    import json
    if not s: return []
    try:
        return json.loads(s) if isinstance(s, str) else s
    except:
        return []


@writing_bp.route("/writing/stage/<int:stage_id>/exam")
def view_stage_exam(stage_id):
    """Render stage exam page (reuses lesson template)."""
    tg_id = request.args.get("user_id") or _get_tg_id()
    conn = _db(); c = conn.cursor()
    exam = c.execute("""SELECT * FROM writing_lessons
        WHERE stage_id=? AND is_exam=1 LIMIT 1""", (stage_id,)).fetchone()
    if not exam:
        conn.close()
        return "Stage exam not found", 404
    stage = c.execute("SELECT * FROM writing_stages WHERE id=?", (stage_id,)).fetchone()
    questions = c.execute("""SELECT * FROM writing_questions
        WHERE lesson_id=? ORDER BY order_index""", (exam["id"],)).fetchall()
    conn.close()
    return render_template("toefl_writing/lesson.html",
        lesson=exam, stage=stage, questions=questions,
        user_id=tg_id, is_exam=True)


@writing_bp.route("/api/writing/stage/<int:stage_id>/exam/submit", methods=["POST"])
def api_stage_exam_submit(stage_id):
    """Submit stage exam - threshold 80% to unlock next stage."""
    data = request.get_json(force=True, silent=True) or {}
    tg_id = data.get("user_id") or _get_tg_id()
    answers = data.get("answers", {})

    conn = _db(); c = conn.cursor()
    exam = c.execute("""SELECT * FROM writing_lessons
        WHERE stage_id=? AND is_exam=1 LIMIT 1""", (stage_id,)).fetchone()
    if not exam:
        conn.close()
        return jsonify({"success": False, "error": "Exam not found"}), 404

    questions = c.execute("""SELECT * FROM writing_questions
        WHERE lesson_id=? ORDER BY order_index""", (exam["id"],)).fetchall()

    correct = 0
    total = len(questions)
    feedback = []

    for q in questions:
        qid = str(q["id"])
        student_ans = (answers.get(qid) or "").strip()
        is_correct = False

        if q["q_type"] == "mcq":
            is_correct = student_ans.lower() == (q["correct_answer"] or "").strip().lower()
        elif q["q_type"] == "sentence_order":
            from ai.toefl_grader import grade_sentence_order
            try:
                student_words = json.loads(student_ans) if student_ans.startswith("[") else student_ans.split()
            except Exception:
                student_words = student_ans.split()
            res = grade_sentence_order(q["correct_answer"] or "", student_words)
            is_correct = res.get("correct", False)

        if is_correct: correct += 1
        feedback.append({
            "question_id": q["id"],
            "is_correct": is_correct,
            "your_answer": student_ans,
            "correct_answer": q["correct_answer"],
            "explanation": q["explanation_ar"]
        })

        c.execute("""INSERT INTO writing_attempts
            (telegram_id, question_id, stage_id, lesson_id, answer_text, is_correct, created_at)
            VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
            (tg_id, q["id"], stage_id, exam["id"], student_ans, 1 if is_correct else 0))

    score_pct = (correct / total * 100) if total else 0
    passed = score_pct >= 80  # higher threshold for stage exam

    # Save progress on exam lesson row
    existing = c.execute("""SELECT id, best_score FROM writing_progress
        WHERE telegram_id=? AND lesson_id=?""", (tg_id, exam["id"])).fetchone()
    if existing:
        new_best = max(existing["best_score"] or 0, score_pct)
        new_status = "completed" if (passed or (existing["best_score"] or 0) >= 80) else "in_progress"
        c.execute("""UPDATE writing_progress
            SET best_score=?, attempts_count=attempts_count+1, status=?,
                completed_at=CASE WHEN ?='completed' AND completed_at IS NULL THEN CURRENT_TIMESTAMP ELSE completed_at END
            WHERE id=?""",
            (new_best, new_status, new_status, existing["id"]))
    else:
        c.execute("""INSERT INTO writing_progress
            (telegram_id, track_id, stage_id, lesson_id, status, best_score, attempts_count, completed_at)
            VALUES (?, 1, ?, ?, ?, ?, 1, CASE WHEN ?=1 THEN CURRENT_TIMESTAMP ELSE NULL END)""",
            (tg_id, stage_id, exam["id"],
             "completed" if passed else "in_progress",
             score_pct, 1 if passed else 0))

    # Find next stage
    next_stage = c.execute("""SELECT id FROM writing_stages
        WHERE order_index > (SELECT order_index FROM writing_stages WHERE id=?)
        ORDER BY order_index ASC LIMIT 1""", (stage_id,)).fetchone()
    next_stage_id = next_stage["id"] if next_stage else None

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "score": round(score_pct, 1),
        "correct": correct,
        "total": total,
        "passed": passed,
        "threshold": 80,
        "feedback": feedback,
        "next_stage_id": next_stage_id if passed else None,
        "is_exam": True
    })


@writing_bp.route("/api/writing/progress/<user_id>")
def api_progress(user_id):
    """Get user's progress across all lessons for lock logic."""
    conn = _db(); c = conn.cursor()
    rows = c.execute("""SELECT lesson_id, stage_id, status, best_score
        FROM writing_progress WHERE telegram_id=?""", (user_id,)).fetchall()
    conn.close()
    return jsonify({
        "success": True,
        "progress": [dict(r) for r in rows]
    })


@writing_bp.route("/api/writing/tier", methods=["GET", "POST"])
def api_writing_tier():
    """Get or set student's target tier."""
    tg_id = (request.args.get("user_id") or
             (request.get_json(silent=True) or {}).get("user_id") or
             _get_tg_id())
    conn = _db(); c = conn.cursor()

    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        target = int(data.get("target_score", 69))
        if target <= 65:
            tier = "tier59"
        elif target <= 79:
            tier = "tier69"
        else:
            tier = "tier90"
        c.execute("""INSERT INTO student_writing_target (telegram_id, target_score, tier, set_at)
            VALUES (?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(telegram_id) DO UPDATE SET
                target_score=excluded.target_score,
                tier=excluded.tier,
                set_at=CURRENT_TIMESTAMP""", (tg_id, target, tier))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "tier": tier, "target_score": target})

    row = c.execute("SELECT tier, target_score FROM student_writing_target WHERE telegram_id=?", (tg_id,)).fetchone()
    conn.close()
    if row:
        return jsonify({"success": True, "tier": row["tier"], "target_score": row["target_score"]})
    return jsonify({"success": True, "tier": "tier69", "target_score": 69, "default": True})


@writing_bp.route("/api/writing/progress/<user_id>")
def api_writing_progress(user_id):
    conn = _db(); c = conn.cursor()
    rows = c.execute("""SELECT lesson_id, stage_id, status, best_score
        FROM writing_progress WHERE telegram_id=?""", (user_id,)).fetchall()
    conn.close()
    return jsonify({"success": True, "progress": [dict(r) for r in rows]})

