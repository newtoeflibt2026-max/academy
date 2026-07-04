import sqlite3
from datetime import datetime

# ── AUTO-UNLOCK START ─────────────────────────────────────────
_CW_NEXT = {
    "cw_easy_01":(22,23),"cw_easy_02":(23,24),"cw_easy_03":(24,25),
    "cw_medium_04":(25,26),"cw_medium_05":(26,27),"cw_medium_06":(27,28),
    "cw_medium_07":(28,29),"cw_hard_08":(29,30),"cw_hard_09":(30,31),
    "cw_hard_10":(30,91),
}
_DL_NEXT = {
    "dl_easy_01":(92,93),"dl_easy_02":(93,94),"dl_easy_03":(94,95),
    "dl_easy_04":(95,96),"dl_medium_05":(96,97),"dl_medium_06":(97,98),
    "dl_medium_07":(98,99),"dl_hard_08":(99,100),"dl_hard_09":(100,101),
    "dl_hard_10":(101,None),
}

_AR_NEXT = {
    "ar_easy_01":   (103, 104),
    "ar_easy_02":   (104, 105),
    "ar_easy_03":   (105, 106),
    "ar_medium_04": (106, 107),
    "ar_medium_05": (107, 108),
    "ar_medium_06": (108, 109),
    "ar_hard_07":   (109, 110),
    "ar_hard_08":   (110, None),
}


def _record_progress_and_unlock(student_id, content_id, score, total, kind):
    """يسجل التقدم في student_progress ويفتح الدرس التالي عند pct>=70"""
    try:
        if not student_id or not total:
            return None
        pct = round((score or 0) * 100 / total)
        mapping = _AR_NEXT if kind == "ar" else (_DL_NEXT if kind == "dl" else _CW_NEXT)
        if content_id not in mapping:
            return None
        cur_lesson_id, next_lesson_id = mapping[content_id]
        import sqlite3 as _sq, os as _os
        _db_path = _os.path.join(_os.path.dirname(__file__), "..", "academy.db")
        _db_path = _os.path.abspath(_db_path)
        _con = _sq.connect(_db_path)
        _cur = _con.cursor()
        # سجل التقدم
        _cur.execute("""
            INSERT INTO student_progress(user_id, lesson_id, status, score, best_score, attempts, started_at, completed_at)
            VALUES (?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))
            ON CONFLICT(user_id, lesson_id) DO UPDATE SET
                status=CASE WHEN ?>=70 THEN 'completed' ELSE status END,
                best_score=MAX(COALESCE(best_score,0), ?),
                attempts=COALESCE(attempts,0)+1,
                completed_at=CASE WHEN ?>=70 THEN datetime('now') ELSE completed_at END
        """, (student_id, cur_lesson_id,
              'completed' if pct >= 70 else 'in_progress',
              pct, pct, pct, pct, pct))
        # افتح الدرس التالي إذا نجح
        if pct >= 70 and next_lesson_id:
            _cur.execute("UPDATE lessons SET is_locked=0 WHERE id=? AND is_locked=1", (next_lesson_id,))
        _con.commit()
        _con.close()
        return {"pct": pct, "next_unlocked": (pct >= 70 and next_lesson_id is not None), "next_id": next_lesson_id}
    except Exception as _e:
        print(f"[auto-unlock] error: {_e}")
        return None
# ── AUTO-UNLOCK END ───────────────────────────────────────────

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
from subscription_helpers import require_section_access


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _get_tg_id():
    """Get telegram/user id from query, header, or session."""
    from flask import session
    tg = request.args.get("user_id") or request.args.get("tg_id")
    if not tg:
        tg = request.headers.get("X-User-Id")
    if tg and str(tg).strip() and str(tg) != "guest":
        try:
            session["tg_id"] = str(tg)
        except Exception:
            pass
        return str(tg)
    try:
        return session.get("tg_id", "guest")
    except Exception:
        return "guest"


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
@require_section_access("reading")
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
            WHERE student_id=? AND status='completed'
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
            difficulty = {"easy": 1, "tier59": 1, "medium": 2, "tier69": 2, "hard": 3, "tier90": 3}.get(tier, 2)
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

    # Phase 5.6: ترتيب البطاقات حسب difficulty (easy→medium→hard) ثم id

    _tier_rank = {"easy": 1, "tier59": 1, "medium": 2, "tier69": 2, "hard": 3, "tier90": 3}

    def _sort_key(it):

        tier = it.get("tier", "")

        return (_tier_rank.get(tier, 99), it.get("id", ""))

    for _t in items_by_type:

        items_by_type[_t] = sorted(items_by_type[_t], key=_sort_key)

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
@require_section_access("reading")
def start(content_id):
    content = cl.get_by_id(content_id)
    if not content:
        return f"Content not found: {content_id}", 404

    # Phase 5.6: redirect complete_words to new exam UI
    if content.get("type") == "complete_words":
        return redirect(url_for("reading_exam.cw_exam",
                                content_id=content_id, user_id=_get_tg_id()))

    # Phase 5.7: redirect daily_reading to new exam UI
    if content.get("type") == "daily_reading":
        return redirect(url_for("reading_exam.dl_exam",
                                content_id=content_id, user_id=_get_tg_id()))

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
@require_section_access("reading")
def exam_screen(attempt_id):
    conn = _db()
    row = conn.execute("SELECT * FROM reading_attempts WHERE attempt_id=?",
                       (attempt_id,)).fetchone()
    conn.close()
    if not row:
        return "Attempt not found", 404
    if row["status"] in ("submitted","completed"):
        return redirect(url_for("reading_exam.result",
                                attempt_id=attempt_id, user_id=_get_tg_id()))

    content = cl.get_by_id(row["content_id"])
    if not content:
        return f"Content missing: {row['content_id']}", 500

    return render_template("reading/exam_screen.html",
                           attempt_id=attempt_id,
                           content=content,
                           submit_url=url_for("reading_exam.submit", is_fresh=True))


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
    if row["status"] in ("submitted","completed"):
        conn.close()
        return jsonify({"redirect": url_for("reading_exam.result",
                                            attempt_id=attempt_id,
                                            user_id=_get_tg_id())})

    content = cl.get_by_id(row["content_id"])
    if not content:
        conn.close()
        return jsonify({"error": "content missing"}), 500

    # Helper: convert letter (A/B/C/D) to index (0/1/2/3)
    def _letter_to_idx(ch):
        if ch is None: return None
        s = str(ch).strip().upper()
        return {"A":0,"B":1,"C":2,"D":3,"E":4}.get(s, None)

    questions = content.get("questions", [])
    correct = 0
    cur = conn.cursor()
    for i, q in enumerate(questions):
        sel_raw = answers.get(str(i), answers.get(i))
        # accept both index (0,1,2) and letter (A,B,C) and dict {selected:...}
        if isinstance(sel_raw, dict):
            sel_raw = sel_raw.get("selected") or sel_raw.get("answer")
        sel = None
        if sel_raw is not None:
            try:
                sel = int(sel_raw)
            except (TypeError, ValueError):
                sel = _letter_to_idx(sel_raw)

        # Phase 5.7: support BOTH 'correct' (letter) AND 'correct_index'/'answer_index' (int)
        correct_raw = q.get("correct", q.get("correct_index", q.get("answer_index")))
        if isinstance(correct_raw, str):
            correct_idx = _letter_to_idx(correct_raw)
        else:
            try:
                correct_idx = int(correct_raw) if correct_raw is not None else None
            except (TypeError, ValueError):
                correct_idx = None

        is_correct = 1 if (sel is not None and correct_idx is not None and sel == correct_idx) else 0
        if is_correct:
            correct += 1
        is_marked = 1 if marked.get(str(i), marked.get(i)) else 0
        cur.execute("""INSERT INTO reading_answers
                       (attempt_id, q_index, selected, is_correct, marked)
                       VALUES (?, ?, ?, ?, ?)""",
                    (attempt_id, i, sel, is_correct, is_marked))

    total = len(questions)
    # FIXED: score = عدد الإجابات الصحيحة (وليس النسبة)
    score = int(correct)
    pct   = int(round(correct * 100 / total)) if total else 0
    cur.execute("""UPDATE reading_attempts
                   SET finished_at=CURRENT_TIMESTAMP, score=?, total=?,
                       status='completed', submit_reason=?
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
@require_section_access("reading")
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

    def _letter_to_idx(ch):
        if ch is None:
            return None
        s = str(ch).strip().upper()
        return {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}.get(s)

    def _idx_to_letter(i):
        if i is None or not isinstance(i, int) or i < 0 or i > 4:
            return "?"
        return ["A", "B", "C", "D", "E"][i]

    def _opt_text(opts, idx):
        if idx is None or idx >= len(opts):
            return None
        opt = opts[idx]
        if isinstance(opt, dict):
            return opt.get("text_en") or opt.get("text") or opt.get("text_ar") or str(opt)
        return str(opt)

    details = []
    for ans in answers:
        i = ans["q_index"]
        q = questions[i] if i < len(questions) else {}
        opts = q.get("options", [])
        sel = ans["selected"]

        correct_raw = q.get("correct", q.get("correct_index", q.get("answer_index")))
        if isinstance(correct_raw, str):
            cidx = _letter_to_idx(correct_raw)
        else:
            try:
                cidx = int(correct_raw) if correct_raw is not None else None
            except (TypeError, ValueError):
                cidx = None

        details.append({
            "index": i + 1,
            "question": q.get("prompt_en", q.get("question_en", q.get("question", ""))),
            "question_ar": q.get("prompt_ar", q.get("question_ar", "")),
            "selected_text": _opt_text(opts, sel),
            "selected_letter": _idx_to_letter(sel) if sel is not None else "—",
            "correct_text": _opt_text(opts, cidx) or "—",
            "correct_letter": _idx_to_letter(cidx),
            "is_correct": bool(ans["is_correct"]),
            "explanation": q.get("explanation_ar", q.get("explanation", "")),
        })

    
    # Build answers_by_index for review of wrong answers
    try:
        _conn = get_db()
        _conn.row_factory = sqlite3.Row
        _ans_rows = _conn.execute("SELECT q_index, selected, is_correct FROM reading_answers WHERE attempt_id=?", (attempt_id,)).fetchall()
        _conn.close()
        answers_by_index = {int(r["q_index"]): dict(r) for r in _ans_rows}
    except Exception as _e:
        answers_by_index = {}
    
    return render_template("reading/result.html", answers_by_index=answers_by_index,
                           attempt=dict(att),
                           content=content,
                           details=details,
                           user_id=_get_tg_id())


# ============================================================
# Phase 5.6: Complete Words routes (separate from MCQ)
# ============================================================

@reading_bp.route("/cw/learn")
@require_section_access("reading")
def cw_learn():
    """Learning page for Complete Words skill (read once)."""
    tg_id = _get_tg_id()
    return render_template("reading/cw_learn.html", user_id=tg_id)


@reading_bp.route("/cw/exam/<content_id>")
@require_section_access("reading")
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
                VALUES (?, ?, ?, datetime('now', '-' || ? || ' seconds'), datetime('now'), 0, ?, 'completed')
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
            cur.execute("UPDATE reading_attempts SET score=? WHERE attempt_id=?", (int(correct), attempt_id))  # FIXED: count
            conn.commit()

        # Stash detailed in a tiny in-memory cache keyed by attempt_id for the result page
        _CW_RESULT_CACHE[attempt_id] = {
            "detailed": detailed,
            "errors_saved": errors_saved,
            "time_spent": time_spent
        }

        # AUTO-UNLOCK CW
        try:
            _record_progress_and_unlock(student_id=tg_id, content_id=content_id, score=correct, total=total, kind="cw")
        except Exception as _eu:
            print(f"[cw auto-unlock] {_eu}")

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
@require_section_access("reading")
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

        percentage = int(round(row["score"] * 100 / row["total"])) if row["total"] else 0  # FIXED
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


# ============================================================
# Phase 5.7: DAILY LIFE READING ROUTES
# ============================================================
@reading_bp.route("/dl/learn")
@require_section_access("reading")
def dl_learn():
    return render_template("reading/dl_learn.html", user_id=_get_tg_id())


@reading_bp.route("/dl/exam/<content_id>")
@require_section_access("reading")
def dl_exam(content_id):
    content = cl.get_by_id(content_id)
    if not content or content.get("type") != "daily_reading":
        return f"Daily reading content not found: {content_id}", 404
    return render_template("reading/dl_exam.html",
                           item=content,
                           user_id=_get_tg_id())


@reading_bp.route("/dl/submit", methods=["POST"])
def dl_submit():
    from flask import request, jsonify
    import sqlite3, traceback
    try:
        data = request.get_json(force=True) or {}
        content_id = data.get("content_id", "")
        answers_raw = data.get("answers", [])
        time_spent = int(data.get("time_spent", 0))
        submit_reason = data.get("submit_reason", "user")

        content = cl.get_by_id(content_id)
        if not content:
            return jsonify({"ok": False, "error": "content not found"}), 404

        sid = _student_id()
        questions = content.get("questions", [])

        # Normalize answers: accept both ["A","B"] and [{question_id,selected}]
        def _extract(ans):
            if ans is None: return ""
            if isinstance(ans, str): return ans.strip()
            if isinstance(ans, dict):
                v = ans.get("selected") or ans.get("answer") or ans.get("value") or ""
                return str(v).strip()
            return str(ans).strip()

        score = 0
        detailed = []
        wrong_items = []
        for i, q in enumerate(questions):
            expected = str(q.get("correct", "")).strip()
            given = _extract(answers_raw[i]) if i < len(answers_raw) else ""
            is_correct = (given.upper() == expected.upper()) and given != ""
            if is_correct:
                score += 1
            else:
                wrong_items.append((sid, 0, f"daily_reading:{content_id}:q_{i}", given, expected))
            detailed.append({"q": i, "given": given, "expected": expected, "correct": is_correct})

        xp_earned = score * 5  # 5 XP per correct answer

        conn = sqlite3.connect("academy.db", timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        try:
            cur = conn.cursor()
            cur.execute("""INSERT INTO reading_attempts
                (student_id, content_id, content_type, score, total, status, submit_reason, finished_at)
                VALUES (?, ?, ?, ?, ?, 'completed', ?, CURRENT_TIMESTAMP)""",
                (sid, content_id, "daily_reading", score, len(questions), submit_reason))
            attempt_id = cur.lastrowid

            for item in wrong_items:
                try:
                    cur.execute("""INSERT INTO error_bank
                        (user_id, question_id, error_type, wrong_answer, correct_answer)
                        VALUES (?, ?, ?, ?, ?)""", item)
                except Exception as e:
                    print(f"[dl_submit] error_bank skipped: {e}")

            # Log XP earned
            if xp_earned > 0:
                try:
                    cur.execute("""INSERT INTO xp_log (user_id, source, amount, created_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                        (sid, f"reading:daily:{content_id}", xp_earned))
                except Exception as e:
                    print(f"[dl_submit] xp_log skipped: {e}")

            conn.commit()
        finally:
            conn.close()

        # AUTO-UNLOCK DL
        try:
            _record_progress_and_unlock(student_id=sid, content_id=content_id, score=score, total=len(questions), kind="dl")
        except Exception as _eu:
            print(f"[dl auto-unlock] {_eu}")

        return jsonify({
            "ok": True,
            "attempt_id": attempt_id,
            "score": score,
            "total": len(questions),
            "xp_earned": xp_earned,
            "detailed": detailed,
            "redirect": f"/reading/dl/result/{attempt_id}?user_id={sid}"
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500



@reading_bp.route("/dl/result/<int:attempt_id>")
@require_section_access("reading")
def dl_result(attempt_id):
    import sqlite3
    conn = sqlite3.connect("academy.db", timeout=30.0)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM reading_attempts WHERE attempt_id=?", (attempt_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return "Attempt not found", 404
    attempt = dict(row)
    content = cl.get_by_id(attempt.get("content_id", ""))
    pct = 0
    if attempt.get("total"):
        pct = round((attempt.get("score", 0) / attempt["total"]) * 100)
    return render_template("reading/dl_result.html",
                           attempt=attempt, item=content, pct=pct,
                           user_id=_get_tg_id())


# ═══════════════════════════════════════════════════════════
# Academic Reading (AR) Routes - Task 3
# ═══════════════════════════════════════════════════════════


import os as _os_ar, json as _json_ar

_AR_LESSONS_PATH = _os_ar.path.join(_os_ar.path.dirname(__file__), "..",
                                    "content", "reading", "ar_lessons", "lessons.json")

def _ar_load_lessons():
    try:
        with open(_os_ar.path.abspath(_AR_LESSONS_PATH), encoding="utf-8") as f:
            return _json_ar.load(f).get("lessons", [])
    except Exception as e:
        print(f"[ar] lessons load error: {e}")
        return []

def _ar_passages_sorted():
    """كل القطع الأكاديمية مرتبة من السهل للصعب."""
    rank = {"easy": 1, "medium": 2, "hard": 3}
    items = [it for it in cl.load_all().values()
             if it.get("type") == "academic_reading"]
    items.sort(key=lambda it: (rank.get(it.get("tier", ""), 9), it.get("id", "")))
    return items

def _ar_progress(sid):
    """يرجع dict: content_id -> best_score للطالب."""
    prog = {}
    if not sid:
        return prog
    try:
        conn = _db()
        rows = conn.execute("""
            SELECT content_id, MAX(score) AS best, COUNT(*) AS attempts
            FROM reading_attempts
            WHERE student_id=? AND status='completed' AND content_type='academic_reading'
            GROUP BY content_id
        """, (sid,)).fetchall()
        conn.close()
        for r in rows:
            prog[r["content_id"]] = {"best": r["best"] or 0, "attempts": r["attempts"]}
    except Exception as e:
        print(f"[ar] progress error: {e}")
    return prog


def _normalize_tier(t):
    '''تحويل tier من صيغة JSON (tier59/69/90) أو صيغة موحّدة (easy/medium/hard).'''
    if not t:
        return 'easy'
    s = str(t).strip().lower()
    mapping = {
        'tier59': 'easy',   'easy':   'easy',   't59': 'easy',
        'tier69': 'medium', 'medium': 'medium', 't69': 'medium',
        'tier90': 'hard',   'hard':   'hard',   't90': 'hard',
    }
    return mapping.get(s, 'easy')


def _extract_passage_text(p):
    '''استخراج نص القطعة سواء كان string أو dict فيه text_en/text.'''
    pa = p.get('passage')
    if isinstance(pa, str):
        return pa
    if isinstance(pa, dict):
        return pa.get('text_en') or pa.get('text') or pa.get('en') or ''
    if isinstance(pa, list):
        return chr(10).join(str(x) for x in pa)
    return ''


def _extract_word_count(p):
    '''عدد الكلمات: من passage.word_count إن وُجد، وإلا نحسبه.'''
    pa = p.get('passage')
    if isinstance(pa, dict) and pa.get('word_count'):
        try:
            return int(pa.get('word_count'))
        except (TypeError, ValueError):
            pass
    txt = _extract_passage_text(p)
    return len(txt.split()) if txt else 0


def _html_escape(s):
    if s is None:
        return ''
    return (str(s)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


# ETS 2026 official reading question type labels
_AR_TYPE_LABELS = {
    'factual':                {'en': 'Factual Information',           'ar': 'معلومة صريحة'},
    'negative_factual':       {'en': 'Negative Factual Information',  'ar': 'معلومة غير مذكورة'},
    'vocabulary':             {'en': 'Vocabulary in Context',         'ar': 'مفردات في السياق'},
    'inference':              {'en': 'Inference',                     'ar': 'استنتاج'},
    'rhetorical':             {'en': 'Rhetorical Purpose',            'ar': 'الغرض البلاغي'},
    'insert_sentence':        {'en': 'Insert Text',                   'ar': 'إدراج نص'},
    'important_idea':         {'en': 'Important Idea',                'ar': 'الفكرة الأهم'},
    'paragraph_relationship': {'en': 'Paragraph Relationship',        'ar': 'العلاقة بين الفقرات'},
}

_AR_STAGE_META = {
    'easy':   {'icon': '',  'name_en': 'Easy',   'name_ar': 'المستوى السهل',  'desc_en': 'Short, direct passages to build the foundation.', 'desc_ar': 'قطع قصيرة ومباشرة لبناء الأساس.'},
    'medium': {'icon': '',  'name_en': 'Medium', 'name_ar': 'المستوى المتوسط', 'desc_en': 'Longer passages requiring deeper comprehension.', 'desc_ar': 'قطع أطول تتطلب فهماً أعمق.'},
    'hard':   {'icon': '',  'name_en': 'Hard',   'name_ar': 'المستوى المتقدم', 'desc_en': 'Real TOEFL-level academic passages.',             'desc_ar': 'قطع بمستوى TOEFL الحقيقي.'},
}


def _ar_build_lesson_view(L, index=None, next_id=None):
    '''تحويل ملف الدرس الخام إلى بنية القالب.'''
    ex = L.get('example') or {}

    # الاستراتيجية: قد تكون قائمة خطوات أو نصاً واحداً
    raw_strategy = L.get('strategy') or L.get('how_ar') or []
    if isinstance(raw_strategy, str):
        strategy_list = [{'title': 'Strategy', 'body': raw_strategy}]
    elif isinstance(raw_strategy, list):
        strategy_list = []
        for i, s in enumerate(raw_strategy, start=1):
            if isinstance(s, dict):
                strategy_list.append({
                    'title': s.get('title') or ('Step ' + str(i)),
                    'body':  s.get('body')  or s.get('text') or '',
                })
            else:
                strategy_list.append({'title': 'Step ' + str(i), 'body': str(s)})
    else:
        strategy_list = []

    return {
        'id': L.get('id'),
        'number': index,
        'title_en': L.get('title_en') or L.get('title') or L.get('id'),
        'title_ar': L.get('title_ar') or '',
        'icon': L.get('icon') or '',
        'desc_ar': L.get('intro_ar') or L.get('desc_ar') or L.get('summary_ar') or '',
        'what_is_it': L.get('what_is_it') or L.get('intro_ar') or '',
        'how_to_recognize': L.get('how_to_recognize') or L.get('how_ar') or '',
        'strategy': strategy_list,
        'tips':  L.get('tips')  or L.get('tactics_ar') or [],
        'avoid': L.get('avoid') or L.get('traps_ar')   or [],
        'example': {
            'passage':      ex.get('passage_en') or ex.get('passage') or '',
            'q':            ex.get('q_en') or ex.get('question_en') or ex.get('q') or '',
            'q_ar':         ex.get('q_ar') or ex.get('q_translation_ar') or '',
            'options':      ex.get('options') or {},
            'correct':      ex.get('correct') or '',
            'wrong_show':   ex.get('wrong_show') or '',
            'explain_ar':   ex.get('explain_ar') or ex.get('explanation_ar') or '',
        },
        'next_id': next_id,
    }


# --- 1) Home: lessons + staged passages -------------------
@reading_bp.route('/ar')
@reading_bp.route('/ar/learn')
@require_section_access('reading')
def ar_home():
    user_id = _get_tg_id()
    sid = _student_id()
    raw_lessons = _ar_load_lessons() or []
    prog = _ar_progress(sid) if sid else {}
    passages_raw = _ar_passages_sorted() or []

    # قائمة الدروس للصفحة الرئيسية
    lessons = []
    for L in raw_lessons:
        lessons.append({
            'id':       L.get('id'),
            'title_en': L.get('title_en') or L.get('title') or L.get('id'),
            'title_ar': L.get('title_ar') or '',
            'icon':     L.get('icon') or '',
            'desc_ar':  L.get('intro_ar') or L.get('desc_ar') or L.get('summary_ar') or '',
        })

    # تجميع القطع حسب المرحلة
    tiers = {'easy': [], 'medium': [], 'hard': []}
    for p in passages_raw:
        tier = _normalize_tier(p.get('tier'))
        if tier not in tiers:
            tier = 'easy'
        tiers[tier].append(p)

    PASS = 70
    stages = []
    total_all = 0
    completed_all = 0
    correct_sum = 0
    questions_sum = 0
    prev_stage_done = True

    for tkey in ('easy', 'medium', 'hard'):
        meta = _AR_STAGE_META[tkey]
        plist = tiers.get(tkey, [])
        stage_total = len(plist)
        stage_completed = 0
        this_stage_locked = not prev_stage_done

        prev_done = True
        for p in plist:
            cid = p.get('id')
            best = int((prog.get(cid) or {}).get('best') or 0)
            qcount = len(p.get('questions') or [])
            if best >= PASS:
                stage_completed += 1
                completed_all += 1
            # للاحصائيات: نحسب صحيح تقريبي من أفضل نسبة
            if best > 0 and qcount > 0:
                correct_sum += int(round(best * qcount / 100.0))
                questions_sum += qcount

        total_all += stage_total
        progress_pct = int(round(100 * stage_completed / stage_total)) if stage_total else 0

        if stage_completed >= stage_total and stage_total > 0:
            css = 'completed'
        elif this_stage_locked:
            css = 'locked'
        else:
            css = 'current'

        stages.append({
            'id':           tkey,
            'key':          tkey,
            'icon':         meta['icon'],
            'name_en':      meta['name_en'],
            'name_ar':      meta['name_ar'],
            'desc_en':      meta['desc_en'],
            'desc_ar':      meta['desc_ar'],
            'total':        stage_total,
            'completed':    stage_completed,
            'progress_pct': progress_pct,
            'locked': False,
            'css_class':    css,
        })

        prev_stage_done = (stage_completed >= stage_total) and stage_total > 0

    accuracy = int(round(100 * correct_sum / questions_sum)) if questions_sum else 0
    total_xp = completed_all * 10

    stats = {
        'total':         total_all,
        'completed':     completed_all,
        'progress_pct':  int(round(100 * completed_all / total_all)) if total_all else 0,
        'lessons_count': len(lessons),
        'accuracy':      accuracy,
        'total_xp':      total_xp,
    }

    return render_template('reading/ar_main.html',
        user_id=user_id, lessons=lessons, stages=stages, stats=stats)


# --- 2) One stage (easy/medium/hard) ----------------------
@reading_bp.route('/ar/stage/<tier>')
@require_section_access('reading')
def ar_stage(tier):
    user_id = _get_tg_id()
    sid = _student_id()
    tier = (tier or '').lower()
    if tier not in ('easy', 'medium', 'hard'):
        return redirect(url_for('reading.ar_home', user_id=user_id))

    prog = _ar_progress(sid) if sid else {}
    passages_raw = [p for p in (_ar_passages_sorted() or [])
                    if _normalize_tier(p.get('tier')) == tier]

    PASS = 70
    passages_out = []
    prev_done = True
    completed = 0
    for idx, p in enumerate(passages_raw, start=1):
        cid = p.get('id')
        best = int((prog.get(cid) or {}).get('best') or 0)
        done = best >= PASS
        if done:
            completed += 1
        unlocked = prev_done
        css = 'completed' if done else ('current' if unlocked else 'locked')
        questions = p.get('questions') or []
        words = _extract_word_count(p)
        passages_out.append({
            'id': cid,
            'number': idx,
            'title_en': p.get('title_en') or cid,
            'title_ar': p.get('title_ar') or '',
            'topic_ar': p.get('topic') or '',
            'questions_count': len(questions),
            'words_count': words,
            'score': best if best > 0 else None,
            'locked': False,
            'css_class': css,
        })
        prev_done = done

    total = len(passages_raw)
    meta = _AR_STAGE_META[tier]
    stage = {
        'key':          tier,
        'id':           tier,
        'icon':         meta['icon'],
        'name_en':      meta['name_en'],
        'name_ar':      meta['name_ar'],
        'desc_en':      meta['desc_en'],
        'desc_ar':      meta['desc_ar'],
        'total':        total,
        'completed':    completed,
        'progress_pct': int(round(100 * completed / total)) if total else 0,
    }

    return render_template('reading/ar_stage.html',
        user_id=user_id, stage=stage, passages=passages_out)


# --- 3) Lesson page ---------------------------------------
@reading_bp.route('/ar/lesson/<lesson_id>')
@require_section_access('reading')
def ar_lesson(lesson_id):
    user_id = _get_tg_id()
    all_lessons = _ar_load_lessons() or []
    L = next((x for x in all_lessons if x.get('id') == lesson_id), None)
    if not L:
        return redirect(url_for('reading.ar_home', user_id=user_id))

    ids = [x.get('id') for x in all_lessons]
    next_id = None
    index = None
    try:
        i = ids.index(lesson_id)
        index = i + 1
        if i + 1 < len(ids):
            next_id = ids[i + 1]
    except ValueError:
        pass

    lesson = _ar_build_lesson_view(L, index=index, next_id=next_id)

    return render_template('reading/ar_lesson.html',
        user_id=user_id, lesson=lesson)


# --- 4) Passage page --------------------------------------
@reading_bp.route('/ar/passage/<content_id>')
@require_section_access('reading')
def ar_passage(content_id):
    import json as _json
    user_id = _get_tg_id()
    sid = _student_id()

    all_p = _ar_passages_sorted() or []
    p = next((x for x in all_p if x.get('id') == content_id), None)
    if not p:
        return redirect(url_for('reading.ar_home', user_id=user_id))

    # نص القطعة كفقرات آمنة
    passage_text = _extract_passage_text(p).strip()
    para_sep = chr(10) + chr(10)
    paragraphs = [para.strip() for para in passage_text.split(para_sep) if para.strip()]
    text_html = ''.join('<p>' + _html_escape(par) + '</p>' for par in paragraphs)

    # قائمة الأسئلة للقالب (مع type_label)
    questions = []
    questions_js = []
    for i, q in enumerate(p.get('questions') or [], start=1):
        qtype = q.get('type') or 'factual'
        label = _AR_TYPE_LABELS.get(qtype) or {'en': qtype, 'ar': qtype}
        type_label = label['en']

        item = {
            'n': i,
            'q':                 q.get('q') or q.get('q_en') or '',
            'q_en':              q.get('q') or q.get('q_en') or '',
            'q_translation_ar':  q.get('q_translation_ar') or q.get('q_ar') or '',
            'q_ar':              q.get('q_translation_ar') or q.get('q_ar') or '',
            'type':              qtype,
            'type_label':        type_label,
            'type_label_ar':     label['ar'],
            'options':           q.get('options') or {},
            'correct':           q.get('correct') or '',
            'explanation_ar':    q.get('explanation_ar') or '',
            'avoid_tip_ar':      q.get('avoid_tip_ar') or '',
        }
        questions.append(item)
        questions_js.append(item)

    tier_key = _normalize_tier(p.get('tier'))
    passage = {
        'id':              p.get('id'),
        'title_en':        p.get('title_en') or p.get('id'),
        'title_ar':        p.get('title_ar') or '',
        'topic_ar':        p.get('topic') or '',
        'tier':            tier_key,
        'tier_key':        tier_key,
        'text_html':       text_html,
        'questions':       questions,
        'questions_js':    _json.dumps(questions_js, ensure_ascii=False),
        'questions_count': len(questions),
    }

    # إنشاء/استرجاع محاولة
    attempt_id = None
    if sid:
        try:
            conn = _db()
            cur = conn.cursor()
            row = cur.execute(
                "SELECT attempt_id FROM reading_attempts "
                "WHERE student_id=? AND content_id=? AND status='in_progress' "
                "ORDER BY attempt_id DESC LIMIT 1",
                (sid, content_id)).fetchone()
            if row:
                attempt_id = row[0]
            else:
                cur.execute(
                    "INSERT INTO reading_attempts "
                    "(student_id, content_id, content_type, started_at, total, status) "
                    "VALUES (?, ?, 'academic_reading', ?, ?, 'in_progress')",
                    (sid, content_id, datetime.now().isoformat(), len(questions)))
                attempt_id = cur.lastrowid
                conn.commit()
            conn.close()
        except Exception as _ea:
            print('[ar_passage attempt] ' + str(_ea))

    return render_template('reading/ar_passage.html',
        user_id=user_id, passage=passage, attempt_id=attempt_id)


# --- 5) Check answers API ---------------------------------
@reading_bp.route('/ar/check', methods=['POST'])
def ar_check():
    data = request.get_json(silent=True) or {}
    attempt_id = data.get('attempt_id')
    content_id = data.get('content_id')
    answers = data.get('answers') or {}
    sid = _student_id()

    all_p = _ar_passages_sorted() or []
    content = next((x for x in all_p if x.get('id') == content_id), None)
    if not content:
        return jsonify({'error': 'content_not_found'}), 404

    questions = content.get('questions') or []
    total = len(questions)
    score = 0
    feedback = {}
    for i, q in enumerate(questions, start=1):
        key = str(i)
        user_ans = (answers.get(key) or '').upper()
        correct = (q.get('correct') or '').upper()
        is_correct = (user_ans == correct and user_ans != '')
        if is_correct:
            score += 1
        feedback[key] = {
            'correct': correct,
            'user': user_ans,
            'is_correct': is_correct,
            'explanation_ar': q.get('explanation_ar') or '',
            'avoid_tip_ar': q.get('avoid_tip_ar') or '',
        }

    pct = int(round(100 * score / total)) if total else 0

    try:
        conn = _db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE reading_attempts "
            "SET score=?, total=?, finished_at=?, status='completed' "
            "WHERE attempt_id=?",
            (score, total, datetime.now().isoformat(), attempt_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print('[ar_check] save error: ' + str(e))

    try:
        _record_progress_and_unlock(student_id=sid, content_id=content_id,
                                    score=score, total=total, kind='ar')
    except Exception as _eu:
        print('[ar auto-unlock] ' + str(_eu))

    try:
        from utils.notifications import send_telegram_notification
        status_txt = 'PASSED' if pct >= 70 else 'RETRY'
        title = content.get('title_en') or content.get('title_ar') or content_id
        msg = ('<b>Reading Result</b>' + chr(10) +
               'Passage: ' + str(title) + chr(10) +
               'Score: ' + str(score) + '/' + str(total) + ' (' + str(pct) + '%)' + chr(10) +
               'Status: ' + status_txt)
        if sid:
            send_telegram_notification(sid, msg)
    except Exception as _en:
        print('[ar notify] ' + str(_en))

    return jsonify({
        'score': score,
        'total': total,
        'pct': pct,
        'passed': pct >= 70,
        'feedback': feedback,
    })



# ═══════════════════════════════════════════════════════════════
# 🎯 الامتحان التكيّفي (Adaptive Reading Exam) — TOEFL 2026 Style
# ═══════════════════════════════════════════════════════════════
import random
import time as _time_mod
from flask import jsonify, request as _req

_ADAPTIVE_CACHE = {}

_TIER_POOLS = {
    "tier59": [f"ar_easy_{i:02d}" for i in range(1, 9)],
    "tier69": [f"ar_medium_{i:02d}" for i in range(9, 17)],
    "tier90": [f"ar_hard_{i:02d}" for i in range(17, 25)],
}

MODULE_DURATION_SEC = 15 * 60
PASS_THRESHOLD = 6


def _pick_passages(tier, count=2, exclude=None):
    exclude = exclude or []
    pool = [p for p in _TIER_POOLS.get(tier, []) if p not in exclude]
    random.shuffle(pool)
    return pool[:count]


def _load_passages_full(ids):
    items = cl.load_all()
    return [items[i] for i in ids if i in items]


def _score_module(passages, answers):
    correct = 0
    total = 0
    details = []
    for p in passages:
        pid = p["id"]
        for qi, q in enumerate(p.get("questions", [])):
            total += 1
            key = f"{pid}__{qi}"
            user_ans = answers.get(key, "")
            is_correct = user_ans == q.get("correct")
            if is_correct:
                correct += 1
            details.append({
                "passage_id": pid,
                "passage_title": p.get("title_en"),
                "q_index": qi,
                "q_text": q.get("q"),
                "user_answer": user_ans,
                "correct_answer": q.get("correct"),
                "is_correct": is_correct,
                "type": q.get("type"),
                "explanation_ar": q.get("explanation_ar", ""),
                "avoid_tip_ar": q.get("avoid_tip_ar", ""),
            })
    return correct, total, details


@reading_bp.route("/ar/exam/start", methods=["GET", "POST"])
@require_section_access("reading")
def ar_exam_start():
    sid = _student_id() or 0
    attempt_id = f"adapt_{sid}_{int(_time_mod.time())}"
    m1_ids = _pick_passages("tier69", count=2)

    _ADAPTIVE_CACHE[attempt_id] = {
        "student_id": sid,
        "user_id": sid,
        "started_at": datetime.now().isoformat(),
        "current_module": 1,
        "module1": {
            "passage_ids": m1_ids,
            "tier": "tier69",
            "answers": {},
            "score": None,
            "started_at": _time_mod.time(),
            "submitted": False,
        },
        "module2": None,
        "final_score": None,
    }
    from flask import redirect
    return redirect(f"/reading/ar/exam/module/{attempt_id}?user_id={sid}")


@reading_bp.route("/ar/exam/module/<attempt_id>")
@require_section_access("reading")
def ar_exam_module(attempt_id):
    state = _ADAPTIVE_CACHE.get(attempt_id)
    if not state:
        return "انتهت جلسة الامتحان. ابدأ من جديد.", 404

    mnum = state["current_module"]
    mkey = f"module{mnum}"
    mod = state[mkey]
    passages = _load_passages_full(mod["passage_ids"])
    elapsed = _time_mod.time() - mod["started_at"]
    remaining = max(0, MODULE_DURATION_SEC - int(elapsed))

    return render_template("reading/ar_exam.html",
        attempt_id=attempt_id,
        module_number=mnum,
        module_tier=mod["tier"],
        passages=passages,
        remaining_seconds=remaining,
        total_duration=MODULE_DURATION_SEC,
        user_id=_get_tg_id())


@reading_bp.route("/ar/exam/submit", methods=["POST"])
@require_section_access("reading")
def ar_exam_submit():
    data = _req.get_json() or {}
    attempt_id = data.get("attempt_id")
    answers = data.get("answers", {})

    state = _ADAPTIVE_CACHE.get(attempt_id)
    if not state:
        return jsonify({"ok": False, "error": "جلسة انتهت"}), 404

    mnum = state["current_module"]
    mkey = f"module{mnum}"
    mod = state[mkey]

    if mod["submitted"]:
        return jsonify({"ok": False, "error": "مُسلَّم بالفعل"}), 400

    passages = _load_passages_full(mod["passage_ids"])
    correct, total, details = _score_module(passages, answers)

    mod["answers"] = answers
    mod["score"] = {"correct": correct, "total": total, "details": details}
    mod["submitted"] = True
    mod["submitted_at"] = datetime.now().isoformat()

    if mnum == 1:
        next_tier = "tier90" if correct >= PASS_THRESHOLD else "tier59"
        m2_ids = _pick_passages(next_tier, count=2, exclude=mod["passage_ids"])
        state["module2"] = {
            "passage_ids": m2_ids,
            "tier": next_tier,
            "answers": {},
            "score": None,
            "started_at": _time_mod.time(),
            "submitted": False,
        }
        state["current_module"] = 2
        return jsonify({
            "ok": True,
            "next": "module2",
            "redirect": f"/reading/ar/exam/module/{attempt_id}?user_id=" + str(state.get("user_id","")),
            "module1_score": f"{correct}/{total}",
            "next_tier": next_tier,
        })
    else:
        m1 = state["module1"]["score"]
        m2 = state["module2"]["score"]
        m2_weight = 20 if state["module2"]["tier"] == "tier90" else 10
        m1_pts = (m1["correct"] / m1["total"]) * 10 if m1["total"] else 0
        m2_pts = (m2["correct"] / m2["total"]) * m2_weight if m2["total"] else 0
        final = round(m1_pts + m2_pts, 1)
        max_score = 10 + m2_weight
        state["final_score"] = {
            "raw": final,
            "max": max_score,
            "percent": round((final / max_score) * 100, 1),
            "m1_correct": m1["correct"], "m1_total": m1["total"],
            "m2_correct": m2["correct"], "m2_total": m2["total"],
            "m2_tier": state["module2"]["tier"],
        }
        state["finished_at"] = datetime.now().isoformat()
        return jsonify({
            "ok": True,
            "next": "result",
            "redirect": f"/reading/ar/exam/result/{attempt_id}?user_id=" + str(state.get("user_id","")),
        })


@reading_bp.route("/ar/exam/result/<attempt_id>")
@require_section_access("reading")
def ar_exam_result(attempt_id):
    state = _ADAPTIVE_CACHE.get(attempt_id)
    if not state or not state.get("final_score"):
        return "نتيجة غير متوفرة. أعد الامتحان.", 404

    all_mistakes = []
    for mkey in ["module1", "module2"]:
        mod = state[mkey]
        if mod and mod.get("score"):
            for d in mod["score"]["details"]:
                if not d["is_correct"]:
                    all_mistakes.append(d)

    return render_template("reading/ar_exam_result.html",
        attempt_id=attempt_id,
        final=state["final_score"],
        mistakes=all_mistakes,
        m1_details=state["module1"]["score"]["details"],
        m2_details=state["module2"]["score"]["details"],
        user_id=_get_tg_id())
