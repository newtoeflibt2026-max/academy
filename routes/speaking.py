# -*- coding: utf-8 -*-
"""
TOEFL Speaking Track - Flask Blueprint (v2)
Routes for: hub, stages, lessons, attempt API, progress.
Stage 0: Foundation (30 lessons - words/short/long sentences)
Stage 1: Listen & Repeat (8 topics × 7 sentences)
Pattern mirrors routes/listening.py for consistency.
"""
import os, json, sqlite3
from flask import Blueprint, render_template, request, jsonify
from subscription_helpers import require_section_access

speaking_bp = Blueprint("speaking", __name__)

DB_PATH = os.environ.get("DB_PATH", "academy.db")


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


def _is_admin(tg_id):
    try:
        from config import Settings
        return int(tg_id) in Settings.ADMIN_IDS
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════
# Helper: Compute lesson unlock status for a user
# ═══════════════════════════════════════════════════════════
def _get_lesson_states(conn, tg_id, stage_id):
    c = conn.cursor()
    lessons = c.execute("""
        SELECT id, code, title_ar, title_en, lesson_type, order_index,
               max_listen_count, pass_score,
               (SELECT COUNT(*) FROM speaking_v2_items WHERE lesson_id=l.id) AS items_count
        FROM speaking_v2_lessons l
        WHERE stage_id=? AND is_active=1
        ORDER BY order_index
    """, (stage_id,)).fetchall()

    prog = c.execute("""
        SELECT lesson_id, status, score, items_completed, items_correct
        FROM speaking_v2_progress
        WHERE user_id=?
    """, (str(tg_id),)).fetchall()
    prog_map = {p["lesson_id"]: dict(p) for p in prog}

    result = []
    prev_passed = True
    for l in lessons:
        d = dict(l)
        p = prog_map.get(d["id"])
        if p and p["status"] == "completed":
            d["status"] = "completed"
            d["score"] = p["score"]
            prev_passed = True
        elif prev_passed:
            d["status"] = "available"
            d["score"] = p["score"] if p else 0
            prev_passed = False
        else:
            d["status"] = "locked"
            d["score"] = 0
        result.append(d)
    return result


# ═══════════════════════════════════════════════════════════
# PAGE: Speaking Hub
# ═══════════════════════════════════════════════════════════
@speaking_bp.route("/speaking")
@require_section_access("speaking")
def speaking_hub():
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()

    stages = c.execute("""
        SELECT s.*,
            (SELECT COUNT(*) FROM speaking_v2_lessons WHERE stage_id=s.id AND is_active=1) AS lesson_count,
            (SELECT COUNT(*) FROM speaking_v2_progress p
               JOIN speaking_v2_lessons l ON l.id=p.lesson_id
               WHERE l.stage_id=s.id AND p.user_id=? AND p.status='completed') AS done_count
        FROM speaking_v2_stages s
        WHERE s.is_active=1
        ORDER BY s.order_index
    """, (str(tg_id),)).fetchall()

    stages_list = []
    for s in stages:
        sd = dict(s)
        denom = sd["lesson_count"] or 1
        sd["progress_pct"] = int((sd["done_count"] / denom) * 100) if denom else 0
        stages_list.append(sd)

    conn.close()
    return render_template("speaking/hub.html", stages=stages_list, user_id=tg_id)


# ═══════════════════════════════════════════════════════════
# PAGE: Stage detail
# ═══════════════════════════════════════════════════════════
@speaking_bp.route("/speaking/stage/<int:stage_id>")
@require_section_access("speaking")
def speaking_stage(stage_id):
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()

    stage = c.execute("SELECT * FROM speaking_v2_stages WHERE id=?", (stage_id,)).fetchone()
    if not stage:
        conn.close()
        return "Stage not found", 404

    lessons = _get_lesson_states(conn, tg_id, stage_id)
    conn.close()

    return render_template("speaking/stage.html",
                           stage=dict(stage), lessons=lessons, user_id=tg_id)


# ═══════════════════════════════════════════════════════════
# PAGE: Lesson (training screen)
# ═══════════════════════════════════════════════════════════
@speaking_bp.route("/speaking/lesson/<int:lesson_id>")
@require_section_access("speaking")
def speaking_lesson(lesson_id):
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()

    lesson = c.execute("""
        SELECT l.*, s.title_ar AS stage_title_ar, s.id AS stage_id, s.icon AS stage_icon
        FROM speaking_v2_lessons l
        JOIN speaking_v2_stages s ON s.id=l.stage_id
        WHERE l.id=?
    """, (lesson_id,)).fetchone()
    if not lesson:
        conn.close()
        return "Lesson not found", 404

    states = _get_lesson_states(conn, tg_id, lesson["stage_id"])
    current = next((x for x in states if x["id"] == lesson_id), None)
    if current and current["status"] == "locked" and not _is_admin(tg_id):
        conn.close()
        return render_template("speaking/locked.html", lesson=dict(lesson), user_id=tg_id), 403

    conn.close()
    return render_template("speaking/lesson.html", lesson=dict(lesson), user_id=tg_id)


# ═══════════════════════════════════════════════════════════
# API: Get lesson items
# ═══════════════════════════════════════════════════════════
@speaking_bp.route("/api/speaking/lesson/<int:lesson_id>/items")
def api_lesson_items(lesson_id):
    conn = _db(); c = conn.cursor()
    lesson = c.execute("SELECT * FROM speaking_v2_lessons WHERE id=?", (lesson_id,)).fetchone()
    if not lesson:
        conn.close()
        return jsonify({"error": "Lesson not found"}), 404

    items = c.execute("""
        SELECT id, code, text_en, text_ar, audio_url, item_type,
               difficulty, ipa, stress_json, pauses_json, tip_ar, order_index
        FROM speaking_v2_items
        WHERE lesson_id=? AND is_active=1
        ORDER BY order_index
    """, (lesson_id,)).fetchall()

    items_list = []
    for it in items:
        d = dict(it)
        try:
            d["stress"] = json.loads(d.pop("stress_json")) if d.get("stress_json") else []
        except Exception:
            d["stress"] = []
        try:
            d["pauses"] = json.loads(d.pop("pauses_json")) if d.get("pauses_json") else []
        except Exception:
            d["pauses"] = []
        items_list.append(d)

    conn.close()
    return jsonify({
        "lesson": dict(lesson),
        "items": items_list,
        "max_listen_count": lesson["max_listen_count"],
    })


# ═══════════════════════════════════════════════════════════
# API: Record item attempt
# ═══════════════════════════════════════════════════════════
@speaking_bp.route("/api/speaking/attempt", methods=["POST"])
def api_attempt():
    tg_id = _get_tg_id()
    data = request.get_json(silent=True) or {}
    lesson_id = data.get("lesson_id")
    item_id = data.get("item_id")
    listen_count = int(data.get("listen_count", 1))
    self_assessment = int(data.get("self_assessment", 0))
    time_taken = int(data.get("time_taken_sec", 0))

    if not lesson_id or not item_id:
        return jsonify({"error": "Missing lesson_id or item_id"}), 400

    conn = _db(); c = conn.cursor()
    c.execute("""
        INSERT INTO speaking_v2_attempts
        (user_id, lesson_id, item_id, listen_count, self_assessment, time_taken_sec)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (str(tg_id), lesson_id, item_id, listen_count, self_assessment, time_taken))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════
# API: Complete lesson
# ═══════════════════════════════════════════════════════════
@speaking_bp.route("/api/speaking/lesson/<int:lesson_id>/complete", methods=["POST"])
def api_complete_lesson(lesson_id):
    data = request.get_json(silent=True) or {}
    tg_id = data.get("user_id") or _get_tg_id()
    items_correct = int(data.get("items_correct", 0))
    items_total = int(data.get("items_total", 0))

    if items_total <= 0:
        return jsonify({"error": "items_total must be > 0"}), 400

    score = round((items_correct / items_total) * 100)

    conn = _db(); c = conn.cursor()
    lesson = c.execute("SELECT pass_score, stage_id FROM speaking_v2_lessons WHERE id=?",
                       (lesson_id,)).fetchone()
    if not lesson:
        conn.close()
        return jsonify({"error": "Lesson not found"}), 404

    pass_score = lesson["pass_score"] or 70
    status = "completed" if score >= pass_score else "needs_practice"

    c.execute("""
        INSERT INTO speaking_v2_progress
        (user_id, lesson_id, status, items_completed, items_correct, score, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(user_id, lesson_id) DO UPDATE SET
            status=excluded.status,
            items_completed=excluded.items_completed,
            items_correct=excluded.items_correct,
            score=MAX(speaking_v2_progress.score, excluded.score),
            completed_at=CASE WHEN excluded.status='completed'
                              THEN excluded.completed_at
                              ELSE speaking_v2_progress.completed_at END
    """, (str(tg_id), lesson_id, status, items_total, items_correct, score))

    if status == "completed":
        try:
            existing = c.execute("SELECT id FROM user_skills_progress WHERE user_id=?",
                                 (str(tg_id),)).fetchone()
            if existing:
                c.execute("""UPDATE user_skills_progress
                             SET speaking_xp = COALESCE(speaking_xp,0) + 5,
                                 updated_at = datetime('now')
                             WHERE user_id=?""", (str(tg_id),))
            else:
                c.execute("""INSERT INTO user_skills_progress
                             (user_id, speaking_xp, updated_at)
                             VALUES (?, 5, datetime('now'))""", (str(tg_id),))
        except Exception:
            pass

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "score": score,
        "status": status,
        "pass_score": pass_score,
        "passed": status == "completed",
        "items_correct": items_correct,
        "items_total": items_total,
    })


# ═══════════════════════════════════════════════════════════
# API: User progress summary
# ═══════════════════════════════════════════════════════════
@speaking_bp.route("/api/speaking/progress")
def api_progress():
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()
    rows = c.execute("""
        SELECT s.id AS stage_id, s.code, s.title_ar,
               (SELECT COUNT(*) FROM speaking_v2_lessons WHERE stage_id=s.id AND is_active=1) AS total,
               (SELECT COUNT(*) FROM speaking_v2_progress p
                  JOIN speaking_v2_lessons l ON l.id=p.lesson_id
                  WHERE l.stage_id=s.id AND p.user_id=? AND p.status='completed') AS done
        FROM speaking_v2_stages s
        WHERE s.is_active=1
        ORDER BY s.order_index
    """, (str(tg_id),)).fetchall()

    conn.close()
    return jsonify({
        "user_id": str(tg_id),
        "stages": [dict(r) for r in rows]
    })
