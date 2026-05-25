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


# ============================================================
# Phase 3: Email Task Routes
# ============================================================
@writing_bp.route("/writing/email", methods=["GET"])
def view_email_list():
    """قائمة سيناريوهات الإيميل المتاحة حسب tier الطالب."""
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()
    # احصل على tier الطالب
    tier_row = c.execute(
        "SELECT tier FROM student_writing_target WHERE telegram_id=?",
        (tg_id,)
    ).fetchone()
    tier = tier_row[0] if tier_row else "tier59"
    # جلب السيناريوهات المناسبة
    scenarios = c.execute("""
        SELECT id, code, title_ar, title_en, scenario_text, recipient_role,
               requirements_json, target_tier, min_words, difficulty, order_index
        FROM writing_email_scenarios
        WHERE is_active=1 AND (target_tier=? OR target_tier='all')
        ORDER BY order_index
    """, (tier,)).fetchall()
    # تحويل لقواميس
    scenarios_list = []
    for s in scenarios:
        scenarios_list.append({
            "id": s[0], "code": s[1], "title_ar": s[2], "title_en": s[3],
            "scenario_text": s[4], "recipient_role": s[5],
            "requirements": json.loads(s[6]) if s[6] else [],
            "target_tier": s[7], "min_words": s[8],
            "difficulty": s[9], "order_index": s[10]
        })
    return render_template("toefl_writing/email_list.html",
                           scenarios=scenarios_list, tier=tier, user_id=tg_id)


@writing_bp.route("/writing/email/<int:scenario_id>", methods=["GET"])
def view_email_task(scenario_id):
    """صفحة كتابة إيميل واحد مع تايمر 7 دقائق."""
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()
    row = c.execute("""
        SELECT id, code, title_ar, title_en, scenario_text, recipient_role,
               requirements_json, target_tier, min_words, difficulty
        FROM writing_email_scenarios WHERE id=?
    """, (scenario_id,)).fetchone()
    if not row:
        return "Scenario not found", 404
    scenario = {
        "id": row[0], "code": row[1], "title_ar": row[2], "title_en": row[3],
        "scenario_text": row[4], "recipient_role": row[5],
        "requirements": json.loads(row[6]) if row[6] else [],
        "target_tier": row[7], "min_words": row[8], "difficulty": row[9]
    }
    # تايمر بحسب tier
    timer_map = {"tier59": 420, "tier69": 420, "tier90": 420}  # 7 دقائق ثابت
    tier_row = c.execute(
        "SELECT tier FROM student_writing_target WHERE telegram_id=?",
        (tg_id,)
    ).fetchone()
    student_tier = tier_row[0] if tier_row else "tier59"
    return render_template("toefl_writing/email_task.html",
                           scenario=scenario,
                           timer_seconds=timer_map.get(student_tier, 420),
                           student_tier=student_tier,
                           user_id=tg_id)


@writing_bp.route("/api/writing/email/submit", methods=["POST"])
def api_email_submit():
    """استلام إيميل الطالب، محاولة تصحيح AI، حفظ النتيجة."""
    data = request.get_json(force=True, silent=True) or {}
    tg_id = data.get("user_id") or _get_tg_id()
    scenario_id = data.get("scenario_id")
    email_text = (data.get("email_text") or "").strip()
    time_spent = int(data.get("time_spent_sec") or 0)
    request_admin = bool(data.get("request_admin_review"))

    if not scenario_id or not email_text:
        return jsonify({"success": False, "error": "Missing data"}), 400

    conn = _db(); c = conn.cursor()
    row = c.execute("""
        SELECT scenario_text, requirements_json, min_words, target_tier
        FROM writing_email_scenarios WHERE id=?
    """, (scenario_id,)).fetchone()
    if not row:
        return jsonify({"success": False, "error": "Scenario not found"}), 404

    scenario_text, req_json, min_words, target_tier = row
    requirements = json.loads(req_json) if req_json else []
    word_count = len([w for w in email_text.split() if w.strip()])

    # tier الطالب
    tier_row = c.execute(
        "SELECT tier FROM student_writing_target WHERE telegram_id=?",
        (tg_id,)
    ).fetchone()
    student_tier = tier_row[0] if tier_row else "tier59"

    # محاولة تصحيح AI
    ai_result = None
    ai_available = False
    try:
        from ai.toefl_grader import grade_email
        ai_result = grade_email(scenario_text, requirements, email_text)
        ai_available = bool(ai_result.get("ai_available"))
    except Exception as e:
        ai_result = {"ai_available": False, "error": str(e)}
        ai_available = False

    # حدد إذا نحتاج مراجعة يدوية
    needs_admin = (not ai_available) or request_admin or (student_tier == "tier90" and request_admin)

    # إذا كان AI متاح: نعرض النتيجة فوراً
    if ai_available:
        score = ai_result.get("score", 0)
        max_score = 5
        score_pct = round((score / max_score) * 100, 1)
        c.execute("""
            INSERT INTO writing_attempts
            (telegram_id, question_id, stage_id, lesson_id, answer_text,
             answer_json, is_correct, ai_score, ai_band, ai_feedback_json, time_spent_sec)
            VALUES (?, NULL, 3, NULL, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tg_id, email_text, json.dumps({"scenario_id": scenario_id}, ensure_ascii=False),
            1 if score >= 3 else 0, score, ai_result.get("band_label",""),
            json.dumps(ai_result, ensure_ascii=False), time_spent
        ))

    # إذا needs_admin: أضف في قائمة الانتظار
    queue_id = None
    if needs_admin:
        c.execute("""
            INSERT INTO writing_admin_queue
            (telegram_id, task_type, scenario_id, student_text, word_count,
             ai_score, ai_feedback_json, ai_available, target_tier)
            VALUES (?, 'email', ?, ?, ?, ?, ?, ?, ?)
        """, (
            tg_id, scenario_id, email_text, word_count,
            ai_result.get("score") if ai_result else None,
            json.dumps(ai_result, ensure_ascii=False) if ai_result else None,
            1 if ai_available else 0, student_tier
        ))
        queue_id = c.lastrowid

    # تحديث cooldown
    c.execute("""
        INSERT OR REPLACE INTO writing_cooldown (telegram_id, scenario_id, last_attempt)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (tg_id, scenario_id))

    conn.commit()

    response = {
        "success": True,
        "ai_available": ai_available,
        "word_count": word_count,
        "min_words_required": min_words,
        "queued_for_admin": needs_admin,
        "queue_id": queue_id,
        "cooldown_minutes": 30
    }
    if ai_available:
        response["score"] = ai_result.get("score", 0)
        response["max_score"] = 5
        response["score_pct"] = round((ai_result.get("score",0)/5)*100, 1)
        response["band_label"] = ai_result.get("band_label", "")
        response["strengths"] = ai_result.get("strengths", [])
        response["improvements"] = ai_result.get("improvements", [])
        response["errors"] = ai_result.get("errors", [])
        response["feedback_ar"] = ai_result.get("feedback_ar", "")
        response["passed"] = ai_result.get("score", 0) >= 3
    else:
        response["message_ar"] = "تم استلام إجابتك ✅ سيقوم المدرّس بمراجعتها خلال 24 ساعة."
        response["passed"] = None  # غير محدد بعد

    return jsonify(response)


@writing_bp.route("/api/writing/email/cooldown/<int:scenario_id>", methods=["GET"])
def api_email_cooldown(scenario_id):
    """فحص cooldown قبل إعادة محاولة سيناريو."""
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()
    row = c.execute("""
        SELECT CAST((julianday('now') - julianday(last_attempt)) * 1440 AS INTEGER)
        FROM writing_cooldown WHERE telegram_id=? AND scenario_id=?
    """, (tg_id, scenario_id)).fetchone()
    if not row:
        return jsonify({"can_retry": True, "minutes_left": 0})
    minutes_passed = row[0] or 0
    minutes_left = max(0, 30 - minutes_passed)
    return jsonify({"can_retry": minutes_left == 0, "minutes_left": minutes_left})


@writing_bp.route("/admin/writing/queue", methods=["GET"])
def admin_writing_queue():
    """لوحة الأدمن لمراجعة الإيميلات المُرسلة."""
    conn = _db(); c = conn.cursor()
    items = c.execute("""
        SELECT q.id, q.telegram_id, q.task_type, q.scenario_id, q.student_text,
               q.word_count, q.ai_score, q.ai_available, q.status, q.target_tier,
               q.created_at, s.title_ar, s.scenario_text
        FROM writing_admin_queue q
        LEFT JOIN writing_email_scenarios s ON q.scenario_id = s.id
        WHERE q.status='pending'
        ORDER BY q.created_at ASC
    """).fetchall()
    items_list = []
    for it in items:
        items_list.append({
            "id": it[0], "telegram_id": it[1], "task_type": it[2],
            "scenario_id": it[3], "student_text": it[4], "word_count": it[5],
            "ai_score": it[6], "ai_available": bool(it[7]), "status": it[8],
            "target_tier": it[9], "created_at": it[10],
            "scenario_title": it[11], "scenario_text": it[12]
        })
    return render_template("toefl_writing/admin_queue.html", items=items_list)


@writing_bp.route("/api/writing/admin/review", methods=["POST"])
def api_admin_review():
    """حفظ تقييم الأدمن لإيميل في قائمة الانتظار."""
    data = request.get_json(force=True, silent=True) or {}
    queue_id = data.get("queue_id")
    admin_score = data.get("admin_score")
    admin_feedback = (data.get("admin_feedback") or "").strip()
    admin_tg = data.get("admin_telegram_id") or _get_tg_id()
    if not queue_id or admin_score is None:
        return jsonify({"success": False, "error": "Missing fields"}), 400
    conn = _db(); c = conn.cursor()
    c.execute("""
        UPDATE writing_admin_queue
        SET status='reviewed', admin_score=?, admin_feedback=?,
            admin_telegram_id=?, reviewed_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (float(admin_score), admin_feedback, admin_tg, queue_id))
    conn.commit()
    return jsonify({"success": True})


@writing_bp.route("/writing/my-corrections", methods=["GET"])
def view_my_corrections():
    """صفحة الطالب لعرض تصحيحاته السابقة."""
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()
    items = c.execute("""
        SELECT q.id, q.task_type, q.student_text, q.word_count, q.ai_score,
               q.ai_feedback_json, q.status, q.admin_score, q.admin_feedback,
               q.created_at, q.reviewed_at, s.title_ar
        FROM writing_admin_queue q
        LEFT JOIN writing_email_scenarios s ON q.scenario_id = s.id
        WHERE q.telegram_id=?
        ORDER BY q.created_at DESC LIMIT 20
    """, (tg_id,)).fetchall()
    items_list = []
    for it in items:
        ai_fb = {}
        try:
            ai_fb = json.loads(it[5]) if it[5] else {}
        except Exception:
            pass
        items_list.append({
            "id": it[0], "task_type": it[1], "student_text": it[2],
            "word_count": it[3], "ai_score": it[4], "ai_feedback": ai_fb,
            "status": it[6], "admin_score": it[7], "admin_feedback": it[8],
            "created_at": it[9], "reviewed_at": it[10], "scenario_title": it[11]
        })
    return render_template("toefl_writing/my_corrections.html",
                           items=items_list, user_id=tg_id)


# ============================================================
# Phase 3.5: Email Coach (6-step learning)
# ============================================================
@writing_bp.route("/writing/email/<int:scenario_id>/coach", methods=["GET"])
@writing_bp.route("/writing/email/<int:scenario_id>/coach/<int:step>", methods=["GET"])
def view_email_coach(scenario_id, step=1):
    """ØµÙØ­Ø© Ø§Ù„ØªØ¹Ù„Ù… Ø®Ø·ÙˆØ© Ø¨Ø®Ø·ÙˆØ© Ù‚Ø¨Ù„ ÙƒØªØ§Ø¨Ø© Ø§Ù„Ø¥ÙŠÙ…ÙŠÙ„."""
    import json as _json
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()
    # Ø§Ù„Ø³ÙŠÙ†Ø§Ø±ÙŠÙˆ Ø§Ù„Ø£Ø³Ø§Ø³ÙŠ
    s_row = c.execute("""
        SELECT id, code, title_ar, title_en, scenario_text, recipient_role,
               requirements_json, min_words, target_tier
        FROM writing_email_scenarios WHERE id=?
    """, (scenario_id,)).fetchone()
    if not s_row:
        return "Scenario not found", 404
    scenario = {
        "id": s_row[0], "code": s_row[1], "title_ar": s_row[2], "title_en": s_row[3],
        "scenario_text": s_row[4], "recipient_role": s_row[5],
        "requirements": _json.loads(s_row[6]) if s_row[6] else [],
        "min_words": s_row[7], "target_tier": s_row[8]
    }
    # Ø§Ù„Ù…Ø­ØªÙˆÙ‰ Ø§Ù„ØªØ¹Ù„ÙŠÙ…ÙŠ
    cc_row = c.execute("""
        SELECT step1_situation_ar, step1_situation_en, step1_recipient_ar,
               step1_tone_ar, step1_goals_json,
               step2_structure_json, step3_phrases_json,
               step4_model_email, step4_annotations_json,
               step5_fill_template, step5_blanks_hints_json,
               step6_checklist_json, common_mistakes_json
        FROM email_coach_content WHERE scenario_id=?
    """, (scenario_id,)).fetchone()
    if not cc_row:
        return f"No coach content for scenario {scenario_id}", 404
    coach = {
        "step1_situation_ar": cc_row[0], "step1_situation_en": cc_row[1],
        "step1_recipient_ar": cc_row[2], "step1_tone_ar": cc_row[3],
        "step1_goals": _json.loads(cc_row[4]) if cc_row[4] else [],
        "step2_structure": _json.loads(cc_row[5]) if cc_row[5] else [],
        "step3_phrases": _json.loads(cc_row[6]) if cc_row[6] else {},
        "step4_model_email": cc_row[7],
        "step4_annotations": _json.loads(cc_row[8]) if cc_row[8] else [],
        "step5_fill_template": cc_row[9],
        "step5_blanks_hints": _json.loads(cc_row[10]) if cc_row[10] else [],
        "step6_checklist": _json.loads(cc_row[11]) if cc_row[11] else [],
        "common_mistakes": _json.loads(cc_row[12]) if cc_row[12] else []
    }
    # ØªØ­Ø¯ÙŠØ« Ø§Ù„ØªÙ‚Ø¯Ù…
    c.execute("""
        INSERT OR REPLACE INTO email_coach_progress
        (telegram_id, scenario_id, step_completed, last_seen_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (tg_id, scenario_id, step))
    conn.commit()
    step = max(1, min(6, int(step)))
    return render_template("toefl_writing/email_coach.html",
                           scenario=scenario, coach=coach,
                           current_step=step, user_id=tg_id)

