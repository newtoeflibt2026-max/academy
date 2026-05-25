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
def writing_stage_page(stage_id):
    tg_id = _get_tg_id()
    conn = _db()
    c = conn.cursor()

    stage = c.execute("SELECT * FROM writing_stages WHERE id=?", (stage_id,)).fetchone()
    if not stage:
        return "Stage not found", 404

    lessons = c.execute("""
        SELECT l.*,
            (SELECT status FROM writing_progress WHERE lesson_id=l.id AND telegram_id=?) AS status,
            (SELECT best_score FROM writing_progress WHERE lesson_id=l.id AND telegram_id=?) AS best_score
        FROM writing_lessons l
        WHERE l.stage_id=?
        ORDER BY l.order_index
    """, (tg_id, tg_id, stage_id)).fetchall()

    # Has exam questions?
    exam_count = c.execute(
        "SELECT COUNT(*) FROM writing_questions WHERE stage_id=? AND is_exam=1", (stage_id,)
    ).fetchone()[0]

    conn.close()
    return render_template("toefl_writing/stage.html",
        stage=dict(stage), lessons=[dict(l) for l in lessons],
        exam_count=exam_count, user_id=tg_id)

# ═══════════════════════════════════════════════════════════
# PAGE: Lesson detail (محتوى الدرس + اختبار قصير)
# ═══════════════════════════════════════════════════════════
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

    conn = _db()
    c = conn.cursor()

    lesson = c.execute("SELECT * FROM writing_lessons WHERE id=?", (lesson_id,)).fetchone()
    if not lesson:
        conn.close()
        return jsonify({"success": False, "error": "Lesson not found"}), 404

    questions = c.execute(
        "SELECT * FROM writing_questions WHERE lesson_id=? AND is_exam=0",
        (lesson_id,)
    ).fetchall()

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
            except:
                student_words = student_ans.split()
            res = grade_sentence_order(q["correct_answer"] or "", student_words)
            is_correct = res["correct"]

        if is_correct: correct += 1

        feedback.append({
            "question_id": q["id"],
            "is_correct": is_correct,
            "your_answer": student_ans,
            "correct_answer": q["correct_answer"],
            "explanation": q["explanation_ar"]
        })

        # log attempt
        c.execute("""INSERT INTO writing_attempts
            (telegram_id, question_id, stage_id, lesson_id, answer_text, is_correct, created_at)
            VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
            (tg_id, q["id"], lesson["stage_id"], lesson_id, student_ans, 1 if is_correct else 0))

    score_pct = (correct / total * 100) if total else 0
    passed = score_pct >= 70

    # Update progress
    if passed:
        c.execute("""INSERT INTO writing_progress
            (telegram_id, stage_id, lesson_id, status, best_score, attempts_count, completed_at)
            VALUES (?,?,?,'completed',?,1,CURRENT_TIMESTAMP)
            ON CONFLICT(telegram_id, lesson_id) DO UPDATE SET
                status='completed',
                best_score=MAX(best_score, ?),
                attempts_count=attempts_count+1,
                completed_at=CURRENT_TIMESTAMP""",
            (tg_id, lesson["stage_id"], lesson_id, score_pct, score_pct))
    else:
        c.execute("""INSERT INTO writing_progress
            (telegram_id, stage_id, lesson_id, status, best_score, attempts_count)
            VALUES (?,?,?,'in_progress',?,1)
            ON CONFLICT(telegram_id, lesson_id) DO UPDATE SET
                best_score=MAX(best_score, ?),
                attempts_count=attempts_count+1""",
            (tg_id, lesson["stage_id"], lesson_id, score_pct, score_pct))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "score": correct, "total": total, "score_pct": round(score_pct, 1),
        "passed": passed, "feedback": feedback
    })

# ═══════════════════════════════════════════════════════════
# API: Grade Email (Task 2)
# ═══════════════════════════════════════════════════════════
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