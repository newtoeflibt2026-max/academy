import sqlite3
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

# Import DB_PATH from single source of truth (db.py)
from db import DB_PATH


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
    sid = _student_id()

    # Fetch best score per content_id for this student
    best_scores = {}
    completed_count = 0
    total_score = 0
    if sid:
        conn = _db()
        rows = conn.execute("""
            SELECT content_id, MAX(score) as best, COUNT(*) as attempts
            FROM reading_attempts
            WHERE student_id=? AND status='submitted'
            GROUP BY content_id
        """, (sid,)).fetchall()
        conn.close()
        for r in rows:
            best_scores[r["content_id"]] = {"best": r["best"], "attempts": r["attempts"]}
            completed_count += 1
            total_score += r["best"] or 0

    avg_score = (total_score // completed_count) if completed_count else 0

    items_by_type = {"academic_reading": [], "daily_reading": [], "complete_words": []}
    for cid, item in all_items.items():
        t = item.get("type", "")
        if t in items_by_type:
            tier = item.get("tier", "")
            difficulty = {"tier59": 1, "tier69": 2, "tier90": 3}.get(tier, 2)
            stats = best_scores.get(item["id"], {})
            items_by_type[t].append({
                "id": item["id"],
                "title_ar": item.get("title_ar", ""),
                "title_en": item.get("title_en", ""),
                "tier": tier,
                "difficulty": difficulty,
                "duration_min": int(item.get("duration_seconds", 0)) // 60,
                "num_questions": len(item.get("questions", [])),
                "best_score": stats.get("best"),
                "attempts": stats.get("attempts", 0),
                "topic": item.get("metadata", {}).get("topic", "General"),
            })

    return render_template("reading/list.html",
                           items_by_type=items_by_type,
                           user_id=_get_tg_id(),
                           stats={"completed": completed_count,
                                  "total_content": len(all_items),
                                  "avg_score": avg_score,
                                  "target": 90})


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


# ============================================================
# Phase 5.6: Complete Words routes (separate from MCQ)
# ============================================================

@reading_bp.route("/cw/learn")
def cw_learn():
    """Learning page for Complete Words skill (read once)."""
    tg_id = _get_tg_id()
    return render_template("reading/cw_learn.html", user_id=tg_id)


@reading_bp.route("/cw/exam/<content_id>")
def cw_exam(content_id):
    """Exam screen for complete_words items."""
    tg_id = _get_tg_id()
    items = cl.load_all()
    item = items.get(content_id)
    if not item or item.get("type") != "complete_words":
        return f"Content not found: {content_id}", 404

    # Compute total blanks + grouped structure for JS
    total_blanks = 0
    blanks_grouped = []
    for seg in item.get("segments", []):
        if "blank" in seg:
            b = seg["blank"]
            missing_len = len(b.get("missing", ""))
            total_blanks += missing_len
            blanks_grouped.append({
                "prefix": b["prefix"],
                "missing_len": missing_len,
                "full_word": b["full_word"]
            })

    return render_template(
        "reading/cw_exam.html",
        item=item,
        user_id=tg_id,
        total_blanks=total_blanks,
        blanks_grouped=blanks_grouped
    )


@reading_bp.route("/cw/submit", methods=["POST"])
def cw_submit():
    """Grade complete_words answers + save errors to error_bank."""
    tg_id = _get_tg_id()
    data = request.get_json(silent=True) or {}
    content_id = data.get("content_id")
    answers = data.get("answers", [])
    time_spent = int(data.get("time_spent", 0))

    items = cl.load_all()
    item = items.get(content_id)
    if not item:
        return jsonify({"error": "content not found"}), 404

    # Grade
    correct = 0
    total = len(answers)
    detailed = []
    errors_saved = 0

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Create attempt
            cur.execute("""
                INSERT INTO reading_attempts (student_id, content_id, content_type, started_at, finished_at, score, total, status)
                VALUES (?, ?, ?, datetime('now', '-' || ? || ' seconds'), datetime('now'), 0, ?, 'submitted')
            """, (tg_id, content_id, "complete_words", time_spent, total))
            attempt_id = cur.lastrowid

            for i, ans in enumerate(answers):
                given = (ans.get("full_word") or "").strip().lower()
                expected = (ans.get("expected") or "").strip().lower()
                is_correct = (given == expected) and len(given) > 0
                if is_correct:
                    correct += 1
                else:
                    # Save to error_bank
                    try:
                        cur.execute("""
                            INSERT INTO error_bank (user_id, question_id, error_type, wrong_answer, correct_answer, created_at)
                            VALUES (?, ?, ?, ?, ?, datetime('now'))
                        """, (
                            tg_id,
                            0,  # question_id is INTEGER; we use 0 + encode context in error_type
                            f"complete_words:{content_id}:blank_{i}",
                            given or "(empty)",
                            expected
                        ))
                        errors_saved += 1
                    except Exception as ex:
                        print(f"[cw_submit] error_bank insert failed: {ex}")

                detailed.append({
                    "given": given,
                    "expected": expected,
                    "correct": is_correct
                })

            # Update score
            percentage = round((correct / total) * 100) if total > 0 else 0
            cur.execute("UPDATE reading_attempts SET score=? WHERE attempt_id=?", (percentage, attempt_id))
            conn.commit()

        # Stash detailed in a tiny in-memory cache keyed by attempt_id for the result page
        _CW_RESULT_CACHE[attempt_id] = {
            "detailed": detailed,
            "errors_saved": errors_saved,
            "time_spent": time_spent
        }

        return jsonify({
            "redirect": f"/reading/cw/result/{attempt_id}?user_id={tg_id}",
            "score": percentage,
            "correct": correct,
            "total": total
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# In-memory cache for result details (lightweight, no schema change needed)
_CW_RESULT_CACHE = {}


@reading_bp.route("/cw/result/<int:attempt_id>")
def cw_result(attempt_id):
    """Result page for complete_words."""
    tg_id = _get_tg_id()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM reading_attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
        if not row:
            return "Attempt not found", 404

        content_id = row["content_id"]
        items = cl.load_all()
        item = items.get(content_id, {"title_en": "Unknown", "title_ar": "غير معروف"})

        cached = _CW_RESULT_CACHE.get(attempt_id, {})
        detailed = cached.get("detailed", [])
        errors_saved = cached.get("errors_saved", 0)
        time_spent = cached.get("time_spent", 0)

        percentage = row["score"]
        correct = sum(1 for a in detailed if a["correct"])
        total = len(detailed) or row["total"]

        time_spent_fmt = f"{time_spent // 60:02d}:{time_spent % 60:02d}"
        finished_at = row["finished_at"] or ""

        return render_template(
            "reading/cw_result.html",
            item=item,
            user_id=tg_id,
            percentage=percentage,
            correct=correct,
            total=total,
            detailed_answers=detailed,
            errors_saved=errors_saved,
            time_spent_fmt=time_spent_fmt,
            finished_at=finished_at
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        return f"Error: {e}", 500

