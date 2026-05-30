# -*- coding: utf-8 -*-
"""
TOEFL Reading - Flask Blueprint
Routes: list, start, exam screen, submit, result
Content-agnostic: reads JSON via services.content_loader
"""
import os, json, sqlite3, time
from flask import Blueprint, render_template, request, jsonify, redirect, url_for

import services.content_loader as cl

reading_bp = Blueprint("reading_exam", __name__, url_prefix="/reading")

DB_PATH = os.environ.get("DB_PATH", "academy.db")
if not os.path.exists(DB_PATH) and os.path.exists("data/academy.db"):
    DB_PATH = "data/academy.db"


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _get_tg_id():
    return (request.args.get("user_id")
        or request.args.get("tg_id")
        or request.cookies.get("user_id")
        or request.headers.get("X-User-Id")
        or "guest")


def _student_id():
    raw = _get_tg_id()
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


# ============================================================
# 1) LIST: GET /reading/
# ============================================================
@reading_bp.route("/")
def list_content():
    all_items = cl.load_all()
    items_by_type = {"academic_reading": [], "daily_reading": [], "complete_words": []}
    for cid, item in all_items.items():
        t = item.get("type", "")
        if t in items_by_type:
            items_by_type[t].append({
                "id": item["id"],
                "title_ar": item.get("title_ar", ""),
                "title_en": item.get("title_en", ""),
                "tier": item.get("tier", ""),
                "duration_min": int(item.get("duration_seconds", 0)) // 60,
                "num_questions": len(item.get("questions", [])),
            })
    return render_template("reading/list.html",
                           items_by_type=items_by_type,
                           user_id=_get_tg_id())


# ============================================================
# 2) START: GET /reading/start/<content_id>
# ============================================================
@reading_bp.route("/start/<content_id>")
def start(content_id):
    content = cl.get_by_id(content_id)
    if not content:
        return f"Content not found: {content_id}", 404

    sid = _student_id()
    conn = _db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reading_attempts (student_id, content_id, content_type, total, status)
        VALUES (?, ?, ?, ?, 'in_progress')
    """, (sid, content_id, content.get("type", ""), len(content.get("questions", []))))
    attempt_id = cur.lastrowid
    conn.commit()
    conn.close()

    return redirect(url_for("reading_exam.exam_screen",
                            attempt_id=attempt_id, user_id=_get_tg_id()))


# ============================================================
# 3) EXAM SCREEN: GET /reading/exam/<attempt_id>
# ============================================================
@reading_bp.route("/exam/<int:attempt_id>")
def exam_screen(attempt_id):
    conn = _db()
    row = conn.execute("SELECT * FROM reading_attempts WHERE attempt_id=?",
                       (attempt_id,)).fetchone()
    conn.close()
    if not row:
        return "Attempt not found", 404
    if row["status"] == "submitted":
        return redirect(url_for("reading_exam.result",
                                attempt_id=attempt_id, user_id=_get_tg_id()))

    content = cl.get_by_id(row["content_id"])
    if not content:
        return f"Content missing: {row['content_id']}", 500

    return render_template("reading/exam_screen.html",
                           attempt_id=attempt_id,
                           content=content,
                           submit_url=url_for("reading_exam.submit"))


# ============================================================
# 4) SUBMIT: POST /reading/submit
# ============================================================
@reading_bp.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(silent=True) or {}
    attempt_id = int(data.get("attempt_id", 0))
    answers = data.get("answers", {}) or {}
    marked = data.get("marked", {}) or {}
    reason = data.get("reason", "manual")

    conn = _db()
    row = conn.execute("SELECT * FROM reading_attempts WHERE attempt_id=?",
                       (attempt_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "attempt not found"}), 404
    if row["status"] == "submitted":
        conn.close()
        return jsonify({"redirect": url_for("reading_exam.result",
                                            attempt_id=attempt_id,
                                            user_id=_get_tg_id())})

    content = cl.get_by_id(row["content_id"])
    if not content:
        conn.close()
        return jsonify({"error": "content missing"}), 500

    questions = content.get("questions", [])
    correct = 0
    cur = conn.cursor()
    for i, q in enumerate(questions):
        sel_raw = answers.get(str(i), answers.get(i))
        try:
            sel = int(sel_raw) if sel_raw is not None else None
        except (TypeError, ValueError):
            sel = None
        correct_idx = q.get("correct_index", q.get("answer_index"))
        try:
            correct_idx = int(correct_idx) if correct_idx is not None else None
        except (TypeError, ValueError):
            correct_idx = None
        is_correct = 1 if (sel is not None and sel == correct_idx) else 0
        if is_correct:
            correct += 1
        is_marked = 1 if marked.get(str(i), marked.get(i)) else 0
        cur.execute("""INSERT INTO reading_answers
                       (attempt_id, q_index, selected, is_correct, marked)
                       VALUES (?, ?, ?, ?, ?)""",
                    (attempt_id, i, sel, is_correct, is_marked))

    total = len(questions)
    score = int(round(correct * 100 / total)) if total else 0
    cur.execute("""UPDATE reading_attempts
                   SET finished_at=CURRENT_TIMESTAMP, score=?, total=?,
                       status='submitted', submit_reason=?
                   WHERE attempt_id=?""",
                (score, total, reason, attempt_id))
    conn.commit()
    conn.close()

    return jsonify({"redirect": url_for("reading_exam.result",
                                        attempt_id=attempt_id,
                                        user_id=_get_tg_id())})


# ============================================================
# 5) RESULT: GET /reading/result/<attempt_id>
# ============================================================
@reading_bp.route("/result/<int:attempt_id>")
def result(attempt_id):
    conn = _db()
    att = conn.execute("SELECT * FROM reading_attempts WHERE attempt_id=?",
                       (attempt_id,)).fetchone()
    if not att:
        conn.close()
        return "Attempt not found", 404
    answers = conn.execute("""SELECT * FROM reading_answers
                              WHERE attempt_id=? ORDER BY q_index""",
                           (attempt_id,)).fetchall()
    conn.close()

    content = cl.get_by_id(att["content_id"]) or {}
    questions = content.get("questions", [])
    details = []
    for ans in answers:
        i = ans["q_index"]
        q = questions[i] if i < len(questions) else {}
        opts = q.get("options", [])
        sel = ans["selected"]
        cidx = q.get("correct_index", q.get("answer_index"))
        details.append({
            "index": i + 1,
            "question": q.get("question_en", q.get("question", "")),
            "selected_text": (opts[sel].get("text_en") if sel is not None and sel < len(opts)
                              and isinstance(opts[sel], dict) else
                              (opts[sel] if sel is not None and sel < len(opts) else None)),
            "correct_text": (opts[cidx].get("text_en") if cidx is not None and cidx < len(opts)
                             and isinstance(opts[cidx], dict) else
                             (opts[cidx] if cidx is not None and cidx < len(opts) else None)),
            "is_correct": bool(ans["is_correct"]),
            "explanation": q.get("explanation_ar", q.get("explanation", "")),
        })

    return render_template("reading/result.html",
                           attempt=dict(att),
                           content=content,
                           details=details,
                           user_id=_get_tg_id())
