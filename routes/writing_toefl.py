import json
# -*- coding: utf-8 -*-
"""
TOEFL Writing Track - Flask Blueprint
Routes for: track overview, stages, lessons, exams, AI grading
"""
import os, json, sqlite3, time
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from subscription_helpers import require_section_access

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
@require_section_access("writing")
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
@require_section_access("writing")
def view_stage(stage_id):
    tg_id = request.args.get("user_id") or _get_tg_id()
    conn = _db(); c = conn.cursor()
    stage = c.execute("SELECT * FROM writing_stages WHERE id=?", (stage_id,)).fetchone()
    if not stage:
        conn.close()
        return "Stage not found", 404

    # REDIRECT_STAGE_TO_LIST: stages 3 and 4 have no lessons - use list pages instead
    if stage_id == 3:
        conn.close()
        from flask import redirect, url_for
        return redirect("/writing/email?user_id=" + str(tg_id or ""))
    if stage_id == 4:
        conn.close()
        from flask import redirect
        return redirect("/writing/discussion/list?user_id=" + str(tg_id or ""))
    if stage_id == 5:
        conn.close()
        from flask import redirect
        return redirect("/writing?user_id=" + str(tg_id or "") + "&msg=mastery_soon")

    lessons = c.execute("""SELECT * FROM writing_lessons
        WHERE stage_id=? ORDER BY order_index""", (stage_id,)).fetchall()

    prog_rows = c.execute("""SELECT lesson_id, status, best_score
        FROM writing_progress WHERE telegram_id=?""", (str(tg_id),)).fetchall()
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
@require_section_access("writing")
def writing_lesson_page(lesson_id):
    tg_id = _get_tg_id()
    conn = _db()
    c = conn.cursor()

    lesson = c.execute("SELECT * FROM writing_lessons WHERE id=?", (lesson_id,)).fetchone()
    if not lesson:
        conn.close()
        return "Lesson not found", 404

    # Fetch any MCQ questions from writing_questions
    questions = c.execute(
        "SELECT * FROM writing_questions WHERE lesson_id=? AND is_exam=0 ORDER BY order_index",
        (lesson_id,)
    ).fetchall()

    qs = []
    for q in questions:
        qd = dict(q)
        if qd.get("options_json"):
            try: qd["options"] = json.loads(qd["options_json"])
            except: qd["options"] = []
        qs.append(qd)

    # Also fetch sentence_building exercises tied to this lesson
    # sentence_building_exercises has no lesson_id column; skip for now
    sb_rows = []

    for sb in sb_rows:
        sd = dict(sb)
        qs.append({
            "id": "sb_" + str(sd["id"]),
            "q_type": "sentence_order",
            "question_ar": "رتّب الكلمات لتكوين جملة صحيحة:",
            "scrambled_words": sd.get("scrambled_words_json") or "[]",
            "correct_answer": sd["correct_sentence"],
            "arabic_translation": sd.get("arabic_translation", ""),
            "rule_applied": sd.get("rule_applied", ""),
            "strategy_ar": sd.get("strategy_ar", ""),
            "explanation_ar": sd.get("explanation_ar", ""),
            "common_error_ar": sd.get("common_error_ar", ""),
            "hint_ar": sd.get("hint_ar", ""),
            "order_index": sd.get("order_index", 99),
        })

    # === practice link (email/discussion) matched to student tier ===
    practice_url = None
    try:
        if lesson["is_exam"] == 0 and lesson["stage_id"] in (3, 4):
            trow = c.execute("SELECT tier FROM student_writing_target WHERE telegram_id=?", (tg_id,)).fetchone()
            tier = (trow["tier"] if trow else None) or "tier59"
            if lesson["stage_id"] == 3:
                sc = c.execute("SELECT id FROM writing_email_scenarios WHERE is_active=1 AND target_tier=? ORDER BY order_index LIMIT 1", (tier,)).fetchone() or c.execute("SELECT id FROM writing_email_scenarios WHERE is_active=1 ORDER BY order_index LIMIT 1").fetchone()
                if sc: practice_url = "/writing/email/" + str(sc["id"]) + "?user_id=" + str(tg_id)
            else:
                sc = c.execute("SELECT id FROM writing_discussion_scenarios WHERE is_active=1 AND target_tier=? ORDER BY order_index LIMIT 1", (tier,)).fetchone() or c.execute("SELECT id FROM writing_discussion_scenarios WHERE is_active=1 ORDER BY order_index LIMIT 1").fetchone()
                if sc: practice_url = "/writing/discussion/" + str(sc["id"]) + "/exam?user_id=" + str(tg_id)
    except Exception as _e:
        practice_url = None

    stage = c.execute("SELECT * FROM writing_stages WHERE id=?", (lesson["stage_id"],)).fetchone()
    conn.close()
    return render_template("toefl_writing/lesson.html",
        lesson=dict(lesson),
        stage=dict(stage) if stage else None,
        questions=qs,
        user_id=tg_id,
        is_exam=False,
        practice_url=practice_url
    )


@writing_bp.route("/api/writing/lesson/<int:lesson_id>/submit", methods=["POST"])
def api_lesson_submit(lesson_id):
    from flask import request, jsonify
    import json as _json, re as _re
    data = request.get_json(silent=True) or {}
    user_id = str(data.get("user_id") or "")
    answers = data.get("answers") or {}

    conn = _db()
    c = conn.cursor()
    lesson = c.execute("SELECT * FROM writing_lessons WHERE id=?", (lesson_id,)).fetchone()
    if not lesson:
        conn.close()
        return jsonify({"success": False, "error": "lesson not found"}), 404

    # Count available exercises in BOTH tables
    wq_count = c.execute("SELECT COUNT(*) FROM writing_questions WHERE lesson_id=? AND is_exam=0", (lesson_id,)).fetchone()[0]
    sb_count = 0  # sentence_building_exercises has no lesson_id; handled by separate tier route
    total_available = wq_count + sb_count

    # CASE A: Reading-only lesson (no exercises) -> auto-complete
    if total_available == 0:
        existing = c.execute(
            "SELECT id FROM writing_progress WHERE telegram_id=? AND lesson_id=?",
            (user_id, lesson_id)
        ).fetchone()
        if existing:
            c.execute("""UPDATE writing_progress SET status='completed', best_score=100.0,
                         attempts_count=attempts_count+1, completed_at=CURRENT_TIMESTAMP WHERE id=?""",
                      (existing["id"],))
        else:
            c.execute("""INSERT INTO writing_progress
                         (telegram_id, track_id, stage_id, lesson_id, status, best_score, attempts_count, completed_at)
                         VALUES (?, 1, ?, ?, 'completed', 100.0, 1, CURRENT_TIMESTAMP)""",
                      (user_id, lesson["stage_id"], lesson_id))
        conn.commit()
        nxt_lesson = c.execute("""SELECT id FROM writing_lessons WHERE stage_id=? AND order_index>? AND is_exam=0
                                  ORDER BY order_index LIMIT 1""",
                               (lesson["stage_id"], lesson["order_index"])).fetchone()
        next_lesson_id = nxt_lesson["id"] if nxt_lesson else None
        conn.close()
        return jsonify({
            "success": True, "score": 100.0, "correct": 0, "total": 0,
            "passed": True, "threshold": 0, "feedback": [],
            "next_lesson_id": next_lesson_id, "stage_exam_id": None,
            "stage_id": lesson["stage_id"]
        })

    # CASE B: Lesson HAS exercises - must answer ALL of them
    if not answers or len(answers) == 0:
        conn.close()
        return jsonify({"success": False, "error": "no answers submitted"}), 400

    # Determine threshold by tier
    tier = (lesson["target_tier"] if "target_tier" in lesson.keys() else "tier59") or "tier59"
    if tier == "tier90": threshold = 85
    elif tier == "tier69": threshold = 75
    else: threshold = 65

    def _norm(s):
        return _re.sub(r"[.!?,]+", "", str(s).strip().lower())

    feedback = []
    correct_count = 0

    for qid_str, user_ans in answers.items():
        is_correct = False
        correct_answer = ""
        user_sentence = ""
        arabic_translation = ""
        rule_applied = ""
        strategy_ar = ""
        explanation_ar = ""
        common_error_ar = ""
        hint_ar = ""

        if str(qid_str).startswith("sb_"):
            try: sb_id = int(str(qid_str)[3:])
            except: continue
            sb = c.execute("SELECT * FROM sentence_building_exercises WHERE id=?", (sb_id,)).fetchone()
            if sb:
                correct_answer = sb["correct_sentence"]
                arabic_translation = sb["arabic_translation"] or ""
                rule_applied = sb["rule_applied"] or ""
                strategy_ar = sb["strategy_ar"] or ""
                explanation_ar = sb["explanation_ar"] or ""
                common_error_ar = sb["common_error_ar"] or ""
                hint_ar = sb["hint_ar"] or ""
                try:
                    words = _json.loads(user_ans) if isinstance(user_ans, str) else user_ans
                    user_sentence = " ".join(words).strip()
                except:
                    user_sentence = str(user_ans)
                if user_sentence:
                    is_correct = _norm(user_sentence) == _norm(correct_answer)
        else:
            try: qid = int(qid_str)
            except: continue
            q = c.execute("SELECT * FROM writing_questions WHERE id=?", (qid,)).fetchone()
            if q:
                correct_answer = q["correct_answer"] or ""
                user_sentence = str(user_ans)
                is_correct = _norm(user_sentence) == _norm(correct_answer)
                explanation_ar = (q["explanation_ar"] if "explanation_ar" in q.keys() else "") or ""

        if is_correct:
            correct_count += 1

        feedback.append({
            "qid": qid_str,
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "user_answer": user_sentence,
            "arabic_translation": arabic_translation,
            "rule_applied": rule_applied,
            "strategy_ar": strategy_ar,
            "explanation_ar": explanation_ar,
            "common_error_ar": common_error_ar,
            "hint_ar": hint_ar,
        })

    # Score = correct / TOTAL AVAILABLE (not just answered)
    score = (correct_count / total_available) * 100.0
    passed = score >= threshold
    total = total_available

    next_lesson_id = None
    stage_exam_id = None
    if passed:
        existing = c.execute(
            "SELECT id, best_score FROM writing_progress WHERE telegram_id=? AND lesson_id=?",
            (user_id, lesson_id)
        ).fetchone()
        if existing:
            new_score = max(existing["best_score"] or 0, score)
            c.execute("""UPDATE writing_progress SET status='completed', best_score=?,
                         attempts_count=attempts_count+1, completed_at=CURRENT_TIMESTAMP WHERE id=?""",
                      (new_score, existing["id"]))
        else:
            c.execute("""INSERT INTO writing_progress
                         (telegram_id, track_id, stage_id, lesson_id, status, best_score, attempts_count, completed_at)
                         VALUES (?, 1, ?, ?, 'completed', ?, 1, CURRENT_TIMESTAMP)""",
                      (user_id, lesson["stage_id"], lesson_id, score))
        conn.commit()
        nxt_lesson = c.execute("""SELECT id FROM writing_lessons WHERE stage_id=? AND order_index>? AND is_exam=0
                                  ORDER BY order_index LIMIT 1""",
                               (lesson["stage_id"], lesson["order_index"])).fetchone()
        if nxt_lesson:
            next_lesson_id = nxt_lesson["id"]
        else:
            exm = c.execute("SELECT id FROM writing_lessons WHERE stage_id=? AND is_exam=1 LIMIT 1",
                            (lesson["stage_id"],)).fetchone()
            if exm: stage_exam_id = exm["id"]

    conn.close()
    return jsonify({
        "success": True, "score": score, "correct": correct_count, "total": total,
        "passed": passed, "threshold": threshold, "feedback": feedback,
        "next_lesson_id": next_lesson_id, "stage_exam_id": stage_exam_id,
        "stage_id": lesson["stage_id"]
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
@require_section_access("writing")
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
@require_section_access("writing")
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
@require_section_access("writing")
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



def _prune_attempts(conn, telegram_id, task_label):
    """????? ???? ?????? + ???? ???????? ??? ????/??? ????? ???? ??????."""
    try:
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT id FROM writing_attempts WHERE telegram_id=? "
            "AND answer_json LIKE ? ORDER BY id ASC",
            (str(telegram_id), '%"task": "' + task_label + '"%')
        ).fetchall()
        ids = [r[0] for r in rows]
        if len(ids) <= 3:
            return
        keep = {ids[0], ids[-1], ids[-2]}   # ?????? + ??? ??????
        to_del = [i for i in ids if i not in keep]
        if to_del:
            cur.executemany("DELETE FROM writing_attempts WHERE id=?",
                            [(i,) for i in to_del])
    except Exception:
        pass

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
    needs_admin = False  # ?????? ?????? ??????? - ??????? ??? Gemini

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
            tg_id, email_text, json.dumps({"scenario_id": scenario_id, "task": "email"}, ensure_ascii=False),
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

    if ai_available:
        _prune_attempts(conn, tg_id, "email")
        conn.commit()
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
        response["display"] = ai_result.get("display", "")
        response["score6"] = ai_result.get("score6", 0)
        response["score120"] = ai_result.get("score120", 0)
        response["gemini_prompt"] = ai_result.get("gemini_prompt", "")
        response["gemini_url"] = ai_result.get("gemini_url", "")
        response["is_estimate"] = True
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
@require_section_access("writing")
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



@writing_bp.route("/writing/email/<int:scenario_id>/coach", methods=["GET"])
@writing_bp.route("/writing/email/<int:scenario_id>/coach/<int:step>", methods=["GET"])


# ============================================================
# Phase 3.5: Email Coach (Final - clean encoding)
# ============================================================
def view_email_coach(scenario_id, step=1):
    from flask import request, render_template, abort
    import sqlite3, json
    from config import settings

    tg_id = request.args.get("user_id", "TEST_TIER")
    step = max(1, min(6, int(step)))

    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    scenario_row = cur.execute(
        "SELECT * FROM writing_email_scenarios WHERE id=?", (scenario_id,)
    ).fetchone()
    if not scenario_row:
        conn.close()
        abort(404)
    scenario = dict(scenario_row)

    coach_row = cur.execute(
        "SELECT * FROM email_coach_content WHERE scenario_id=?", (scenario_id,)
    ).fetchone()
    conn.close()

    def _safe_json(val, default):
        if not val:
            return default
        try:
            return json.loads(val)
        except Exception:
            return default

    DEFAULT_TIP1 = 'اقرأ الموقف بعناية وحدّد بدقة ما المطلوب منك قبل أن تبدأ الكتابة.'
    DEFAULT_TIP2 = 'كن واضحاً ومباشراً. الإيميل الجامعي ليس مكاناً للحشو والتكرار.'
    DEFAULT_TONE = 'رسمي ومهذّب'
    NO_CONTENT_MSG = 'لا يوجد محتوى تعليمي لهذا السيناريو بعد.'
    NO_SIT_MSG = 'لا يوجد شرح للموقف بعد.'

    if coach_row:
        cr = dict(coach_row)
        coach = {
            "situation_ar": cr.get("step1_situation_ar") or NO_SIT_MSG,
            "situation_en": cr.get("step1_situation_en") or scenario.get("scenario_text", ""),
            "recipient_ar": cr.get("step1_recipient_ar") or scenario.get("recipient_role", ""),
            "tone_ar": cr.get("step1_tone_ar") or DEFAULT_TONE,
            "goals": _safe_json(cr.get("step1_goals_json"), []),
            "structure": _safe_json(cr.get("step2_structure_json"), []),
            "phrases": _safe_json(cr.get("step3_phrases_json"), []),
            "model_email": cr.get("step4_model_email") or "",
            "annotations": _safe_json(cr.get("step4_annotations_json"), []),
            "fill_template": cr.get("step5_fill_template") or "",
            "blanks_hints": _safe_json(cr.get("step5_blanks_hints_json"), []),
            "checklist": _safe_json(cr.get("step6_checklist_json"), []),
            "common_mistakes": _safe_json(cr.get("common_mistakes_json"), []),
            "video_url": cr.get("video_url") or "",
            "coach_tip_1": DEFAULT_TIP1,
            "coach_tip_2": DEFAULT_TIP2,
        }
    else:
        coach = {
            "situation_ar": NO_CONTENT_MSG,
            "situation_en": scenario.get("scenario_text", ""),
            "recipient_ar": scenario.get("recipient_role", ""),
            "tone_ar": DEFAULT_TONE,
            "goals": [], "structure": [], "phrases": [],
            "model_email": "", "annotations": [],
            "fill_template": "", "blanks_hints": [],
            "checklist": [], "common_mistakes": [],
            "video_url": "",
            "coach_tip_1": "", "coach_tip_2": "",
        }

    return render_template(
        "toefl_writing/email_coach.html",
        scenario=scenario, coach=coach,
        step=step, user_id=tg_id,
    )



# ============================================
# ACADEMIC DISCUSSION ROUTES (TOEFL Task 1)
# ============================================
import json as _disc_json

def _disc_safe_json(value, default):
    """Safely parse JSON string from DB"""
    if not value:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return _disc_json.loads(value)
    except Exception:
        return default

@writing_bp.route("/writing/discussion/list")
@require_section_access("writing")
def list_discussions():
    """List all academic discussion scenarios"""
    from flask import render_template, request
    import sqlite3, os
    db = os.environ.get("DB_PATH", "academy.db")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, code, title_ar, title_en, topic_category,
               target_tier, difficulty, min_words, time_limit_seconds
        FROM writing_discussion_scenarios
        WHERE is_active=1
        ORDER BY order_index, id
    """)
    scenarios = [dict(r) for r in cur.fetchall()]
    conn.close()
    return render_template("toefl_writing/discussion_list.html", scenarios=scenarios)


@writing_bp.route("/writing/discussion/<int:scenario_id>/exam")
@require_section_access("writing")
def view_discussion_exam(scenario_id):
    """TOEFL-like exam screen for academic discussion"""
    from flask import render_template, request, abort
    import sqlite3, os
    db = os.environ.get("DB_PATH", "academy.db")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM writing_discussion_scenarios WHERE id=?", (scenario_id,))
    sc_row = cur.fetchone()
    if not sc_row:
        conn.close()
        abort(404)
    
    scenario = dict(sc_row)
    
    cur.execute("""
        SELECT student_name, student_avatar, reply_text_en, reply_text_ar, position, order_index
        FROM discussion_student_replies
        WHERE scenario_id=?
        ORDER BY order_index
    """, (scenario_id,))
    replies = [dict(r) for r in cur.fetchall()]
    
    conn.close()
    
    user_id = request.args.get("user_id", "guest")
    return render_template(
        "toefl_writing/discussion_exam.html",
        scenario=scenario,
        replies=replies,
        user_id=user_id
    )


@writing_bp.route("/writing/discussion/<int:scenario_id>/coach")
@writing_bp.route("/writing/discussion/<int:scenario_id>/coach/<int:step>")
@require_section_access("writing")
def view_discussion_coach(scenario_id, step=1):
    """6-step coach for academic discussion"""
    from flask import render_template, request, abort
    import sqlite3, os
    db = os.environ.get("DB_PATH", "academy.db")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM writing_discussion_scenarios WHERE id=?", (scenario_id,))
    sc_row = cur.fetchone()
    if not sc_row:
        conn.close()
        abort(404)
    scenario = dict(sc_row)
    
    cur.execute("""
        SELECT student_name, student_avatar, reply_text_en, reply_text_ar, position
        FROM discussion_student_replies
        WHERE scenario_id=?
        ORDER BY order_index
    """, (scenario_id,))
    replies = [dict(r) for r in cur.fetchall()]
    
    cur.execute("SELECT * FROM discussion_coach_content WHERE scenario_id=?", (scenario_id,))
    cc_row = cur.fetchone()
    conn.close()
    
    if not cc_row:
        coach = {}
    else:
        cr = dict(cc_row)
        coach = {
            "step1_text": cr.get("step1_analyze_question_ar", ""),
            "step1_keywords": _disc_safe_json(cr.get("step1_keywords_json"), []),
            "step2_text": cr.get("step2_analyze_replies_ar", ""),
            "step2_analysis": _disc_safe_json(cr.get("step2_reply_analysis_json"), []),
            "step3_text": cr.get("step3_build_opinion_ar", ""),
            "step3_options": _disc_safe_json(cr.get("step3_position_options_json"), []),
            "phrases": _disc_safe_json(cr.get("step4_phrases_json"), {}),
            "model_response": cr.get("step5_model_response", ""),
            "annotations": _disc_safe_json(cr.get("step5_annotations_json"), []),
            "checklist": _disc_safe_json(cr.get("step6_checklist_json"), []),
            "mistakes": _disc_safe_json(cr.get("step6_common_mistakes_json"), []),
            "tier59_explanation": cr.get("tier59_explanation", ""),
            "tier69_explanation": cr.get("tier69_explanation", ""),
            "tier90_explanation": cr.get("tier90_explanation", ""),
        }
    
    user_id = request.args.get("user_id", "guest")
    return render_template(
        "toefl_writing/discussion_coach.html",
        scenario=scenario,
        replies=replies,
        coach=coach,
        step=step,
        user_id=user_id
    )


# ============================================================
# SENTENCE BUILDING ROUTES (Task 1)
# ============================================================

def _get_db_conn():
    """Helper to get DB connection"""
    import sqlite3, os
    db = os.environ.get("DB_PATH", "academy.db")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn

def _user_unlocked_tiers(user_id):
    """Determine which tiers the user has unlocked based on past correct answers"""
    conn = _get_db_conn()
    cur = conn.cursor()
    unlocked = {"tier59": True, "tier69": False, "tier90": False}

    # Count correct answers per tier
    cur.execute("""
        SELECT e.target_tier, COUNT(DISTINCT e.id) as total,
               SUM(CASE WHEN p.is_correct=1 THEN 1 ELSE 0 END) as correct
        FROM sentence_building_exercises e
        LEFT JOIN sentence_building_progress p
            ON p.exercise_id = e.id AND p.user_id = ?
        GROUP BY e.target_tier
    """, (user_id,))

    stats = {row["target_tier"]: {"total": row["total"], "correct": row["correct"] or 0}
             for row in cur.fetchall()}

    # Unlock rules: 80% correct in tier59 unlocks tier69; 80% in tier69 unlocks tier90
    if "tier59" in stats and stats["tier59"]["total"] > 0:
        pct = stats["tier59"]["correct"] / stats["tier59"]["total"]
        if pct >= 0.8:
            unlocked["tier69"] = True
    if "tier69" in stats and stats["tier69"]["total"] > 0:
        pct = stats["tier69"]["correct"] / stats["tier69"]["total"]
        if pct >= 0.8:
            unlocked["tier90"] = True

    conn.close()
    return unlocked, stats

@writing_bp.route("/writing/sentence-building")
@require_section_access("writing")
def sb_home():
    """Landing page: foundation lessons + tier selection"""
    from flask import request, render_template
    user_id = request.args.get("user_id", "anonymous")
    conn = _get_db_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM sentence_foundation_lessons WHERE is_active=1 ORDER BY rule_number")
    lessons = [dict(r) for r in cur.fetchall()]
    import json
    for L in lessons:
        try:
            L["examples"] = json.loads(L.get("examples_json","[]"))
        except:
            L["examples"] = []

    unlocked, stats = _user_unlocked_tiers(user_id)

    # Count exercises per tier
    cur.execute("SELECT target_tier, COUNT(*) as cnt FROM sentence_building_exercises WHERE is_active=1 GROUP BY target_tier")
    tier_counts = {row["target_tier"]: row["cnt"] for row in cur.fetchall()}

    conn.close()
    
    # JSON_PARSE_FIX: convert examples_json string to list for template
    import json as _json
    _parsed_lessons = []
    for _l in lessons:
        _ld = dict(_l) if not isinstance(_l, dict) else dict(_l)
        _raw = _ld.get("examples_json")
        if isinstance(_raw, str) and _raw.strip():
            try:
                _ld["examples_json"] = _json.loads(_raw)
            except Exception:
                _ld["examples_json"] = []
        elif _raw is None:
            _ld["examples_json"] = []
        _parsed_lessons.append(_ld)
    lessons = _parsed_lessons
    
    return render_template("toefl_writing/sb_home.html",
                          lessons=lessons,
                          unlocked=unlocked,
                          stats=stats,
                          tier_counts=tier_counts,
                          user_id=user_id)

@writing_bp.route("/writing/sentence-building/practice/<tier>")
@require_section_access("writing")
def sb_practice_list(tier):
    """List of exercises for a specific tier"""
    from flask import request, render_template, abort, redirect, url_for
    user_id = request.args.get("user_id", "anonymous")

    if tier not in ("tier59", "tier69", "tier90"):
        return redirect(url_for("writing_bp.sb_home", user_id=user_id))

    conn = _get_db_conn()
    conn.row_factory = __import__('sqlite3').Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM sentence_building_exercises WHERE target_tier=? AND is_active=1 ORDER BY order_index, id", (tier,))
    rows = [dict(r) for r in cur.fetchall()]

    # Get progress: which exercises completed
    done_ids = set()
    try:
        cur.execute("SELECT DISTINCT exercise_id FROM sentence_building_progress WHERE user_id=? AND is_correct=1", (user_id,))
        done_ids = {r[0] for r in cur.fetchall()}
    except Exception:
        pass
    conn.close()

    for r in rows:
        r["is_done"] = r["id"] in done_ids

    return render_template("toefl_writing/sb_practice_list.html", exercises=rows, user_id=user_id, tier=tier)

@writing_bp.route("/writing/sentence-building/exercise/<int:exercise_id>")
@require_section_access("writing")
def sb_exercise(exercise_id):
    """Show a single interactive exercise"""
    from flask import request, render_template, abort
    import json as _json
    user_id = request.args.get("user_id", "anonymous")

    conn = _get_db_conn()
    conn.row_factory = __import__('sqlite3').Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM sentence_building_exercises WHERE id=? AND is_active=1", (exercise_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        abort(404)

    ex = dict(row)
    # Parse scrambled_words_json -> scrambled_words (list)
    try:
        ex["scrambled_words"] = _json.loads(ex.get("scrambled_words_json","[]"))
    except Exception:
        ex["scrambled_words"] = []

    return render_template("toefl_writing/sb_exercise.html", exercise=ex, user_id=user_id)

@writing_bp.route("/api/writing/sentence-building/check", methods=["POST"])
def sb_check_answer():
    """Verify the student's answer and record progress"""
    from flask import request, jsonify
    data = request.get_json() or {}
    user_id = data.get("user_id", "anonymous")
    exercise_id = data.get("exercise_id")
    user_answer = (data.get("answer") or "").strip()

    if not exercise_id:
        return jsonify({"ok": False, "error": "missing exercise_id"}), 400

    conn = _get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sentence_building_exercises WHERE id = ?", (exercise_id,))
    ex = cur.fetchone()
    if not ex:
        conn.close()
        return jsonify({"ok": False, "error": "exercise not found"}), 404

    correct = (ex["correct_sentence"] or "").strip()
    # Normalize: lowercase, strip ending punctuation for comparison
    def norm(s):
        return s.lower().rstrip(".!?").strip()
    is_correct = norm(user_answer) == norm(correct)

    # Update progress
    cur.execute("""
        INSERT INTO sentence_building_progress (user_id, exercise_id, attempts, is_correct, last_attempt_at)
        VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, exercise_id) DO UPDATE SET
            attempts = attempts + 1,
            is_correct = CASE WHEN ? = 1 THEN 1 ELSE is_correct END,
            last_attempt_at = CURRENT_TIMESTAMP
    """, (user_id, exercise_id, 1 if is_correct else 0, 1 if is_correct else 0))
    conn.commit()

    # Check if a new tier was just unlocked
    unlocked, _ = _user_unlocked_tiers(user_id)

    result = {
        "ok": True,
        "is_correct": is_correct,
        "correct_sentence": correct,
        "explanation_ar": ex["explanation_ar"],
        "common_error_ar": ex["common_error_ar"],
        "strategy_ar": ex["strategy_ar"],
        "rule_applied": ex["rule_applied"],
        "unlocked": unlocked
    }
    conn.close()
    return jsonify(result)

@writing_bp.route("/api/writing/sentence-building/progress/<user_id>")
def sb_progress(user_id):
    """Get user's overall progress"""
    from flask import jsonify
    unlocked, stats = _user_unlocked_tiers(user_id)
    return jsonify({"unlocked": unlocked, "stats": stats})

# ============================================================
# END SENTENCE BUILDING ROUTES
# ============================================================


@writing_bp.route("/api/writing/gemini-score", methods=["POST"])
def api_gemini_score():
    """يحفظ درجة الطالب من Gemini ويعيد مقارنة بتطوره."""
    from flask import request, jsonify
    import sqlite3
    try:
        d = request.get_json(silent=True) or {}
        tg = str(d.get("user_id") or d.get("student_id") or "").strip()
        task = (d.get("task_type") or "email").strip()
        sid = d.get("scenario_id")
        score6 = float(d.get("score6") or 0)
        if not tg:
            return jsonify({"ok": False, "error": "user_id required"}), 400
        if score6 < 0 or score6 > 6:
            return jsonify({"ok": False, "error": "score must be 0-6"}), 400
        score120 = round((score6 - 1.0) / 5.0 * 120) if score6 >= 1 else 0
        if score120 < 0: score120 = 0

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""INSERT INTO gemini_self_scores
            (telegram_id, task_type, scenario_id, score6, score120)
            VALUES (?,?,?,?,?)""", (tg, task, sid, score6, score120))
        conn.commit()

        # سياسة الاحتفاظ: أول محاولة + آخر محاولتين لكل مهمة
        cur.execute("""SELECT id FROM gemini_self_scores
            WHERE telegram_id=? AND task_type=? ORDER BY id ASC""", (tg, task))
        ids = [r[0] for r in cur.fetchall()]
        if len(ids) > 3:
            keep = {ids[0], ids[-1], ids[-2]}
            for rid in ids:
                if rid not in keep:
                    cur.execute("DELETE FROM gemini_self_scores WHERE id=?", (rid,))
            conn.commit()

        # جلب أول وآخر للمقارنة
        cur.execute("""SELECT score6, score120 FROM gemini_self_scores
            WHERE telegram_id=? AND task_type=? ORDER BY id ASC""", (tg, task))
        rows = cur.fetchall()
        conn.close()

        first6 = rows[0][0]
        prev6 = rows[-2][0] if len(rows) >= 2 else None
        msg = f"تم حفظ درجتك: {score6:g} / 6 (\u2248 {score120} / 120)."
        if len(rows) == 1:
            msg += " هذه أول محاولة لك. اكتب أكثر لنتابع تطورك."
        else:
            diff = score6 - first6
            if diff > 0:
                msg += f" أول محاولة كانت {first6:g}/6 \u2014 تحسنت بمقدار +{diff:g} نقطة. \U0001F4C8 ممتاز!"
            elif diff < 0:
                msg += f" أول محاولة كانت {first6:g}/6 \u2014 انخفضت {abs(diff):g} نقطة. واصل التدريب."
            else:
                msg += f" نفس مستوى أول محاولة ({first6:g}/6). حاول التطوير أكثر."

        return jsonify({"ok": True, "score6": score6, "score120": score120,
                        "message_ar": msg, "history": [{"s6": r[0], "s120": r[1]} for r in rows]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

