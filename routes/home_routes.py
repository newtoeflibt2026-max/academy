import json


# -*- coding: utf-8 -*-


"""


Home + Learning Path + Lesson Runner routes for Yamen Academy.


"""


import os, sqlite3, json


from datetime import datetime


from flask import Blueprint, render_template, request, jsonify, redirect, url_for





home_bp = Blueprint("home_bp", __name__)


DB_PATH = os.environ.get("DB_PATH", r"C:\Users\nelt2\yamen_academy\academy.db")





def _ar(*c): return "".join(chr(x) for x in c)





SECTION_META = {


    "reading":   {"title": _ar(0x627,0x644,0x642,0x631,0x627,0x621,0x629),         "class": "read"},


    "listening": {"title": _ar(0x627,0x644,0x627,0x633,0x62A,0x645,0x627,0x639),   "class": "listen"},


    "writing":   {"title": _ar(0x627,0x644,0x643,0x62A,0x627,0x628,0x629),         "class": "write"},


    "speaking":  {"title": _ar(0x627,0x644,0x62A,0x62D,0x62F,0x651,0x62B),         "class": "speak"},


}








def _conn():


    conn = sqlite3.connect(DB_PATH)


    conn.row_factory = sqlite3.Row


    return conn








def _get_student(user_id):


    try:


        c = _conn(); cur = c.cursor()


        cur.execute("SELECT * FROM students WHERE user_id=?", (user_id,))


        row = cur.fetchone()


        c.close()


        if row: return dict(row)


    except Exception as e:


        print(f"[home_routes] _get_student error: {e}")


    return {"user_id": user_id, "name": "Yamen Academy", "hearts": 5, "xp": 0,


            "streak_days": 0, "current_band": 0.0, "target_band": 6.5}








def _section_stats(user_id, section):


    try:


        c = _conn(); cur = c.cursor()


        # mini_lessons (lessons learning track)


        cur.execute("SELECT COUNT(*) FROM mini_lessons WHERE section=? AND is_active=1", (section,))


        total_lessons = cur.fetchone()[0] or 0


        cur.execute("""SELECT COUNT(*) FROM user_lesson_progress p


                       JOIN mini_lessons m ON m.id=p.mini_lesson_id


                       WHERE p.user_id=? AND m.section=? AND p.status='completed'""", (user_id, section))


        done_lessons = cur.fetchone()[0] or 0





        # Phase Speaking V2: override stats for "speaking" section


        if section == "speaking":


            try:


                cur.execute("SELECT COUNT(*) FROM speaking_v2_lessons")


                sp_total = cur.fetchone()[0] or 0


                cur.execute("""SELECT COUNT(*) FROM speaking_v2_progress


                               WHERE user_id=? AND status='completed'""", (str(user_id),))


                sp_done = cur.fetchone()[0] or 0


                c.close()


                pct = int(sp_done * 100 / sp_total) if sp_total else 0


                return {"total": sp_total, "done": sp_done, "pct": pct,


                        "lessons_done": sp_done, "lessons_total": sp_total,


                        "exams_done": 0, "exams_total": 0}


            except Exception as e:


                print(f"[home_routes] speaking_v2 stats error: {e}")





        # Phase 5.7: include reading_attempts for "reading" section


        attempts_done = 0


        attempts_total = 0


        if section == "reading":


            try:


                cur.execute("""SELECT COUNT(DISTINCT content_id) FROM reading_attempts


                               WHERE student_id=? AND status='completed'""", (user_id,))


                attempts_done = cur.fetchone()[0] or 0


                # total = number of content items available (estimated)


                try:


                    from services import content_loader as cl


                    items = [it for it in cl.load_all() if it.get("type") in ("daily_reading","complete_words","academic_reading")]


                    attempts_total = len(items)


                except Exception:


                    attempts_total = 0


            except Exception as e:


                print(f"[home_routes] reading_attempts stats error: {e}")





        c.close()


        total = total_lessons + attempts_total


        done = done_lessons + attempts_done


        pct = int(done * 100 / total) if total else 0


        return {"total": total, "done": done, "pct": pct,


                "lessons_done": done_lessons, "lessons_total": total_lessons,


                "exams_done": attempts_done, "exams_total": attempts_total}


    except Exception as e:


        print(f"[home_routes] _section_stats error: {e}")


        return {"total": 0, "done": 0, "pct": 0}








def _get_lesson_progress(user_id, section):


    c = _conn(); cur = c.cursor()


    cur.execute("""SELECT id, section, unit_number, lesson_number, title_ar, subtitle_ar,


                          lesson_type, quiz_pass_score, xp_reward, order_index


                   FROM mini_lessons WHERE section=? AND is_active=1


                   ORDER BY order_index, lesson_number""", (section,))


    lessons = [dict(r) for r in cur.fetchall()]


    if not lessons:


        c.close(); return []


    ids = [l["id"] for l in lessons]


    placeholders = ",".join("?" * len(ids))


    cur.execute(f"""SELECT mini_lesson_id, status, stars, best_score


                    FROM user_lesson_progress WHERE user_id=? AND mini_lesson_id IN ({placeholders})""",


                [user_id] + ids)


    prog_map = {r["mini_lesson_id"]: dict(r) for r in cur.fetchall()}


    c.close()


    prev_ok = True


    for l in lessons:


        p = prog_map.get(l["id"])


        if p and p["status"] == "completed":


            l["status"] = "completed"; l["stars"] = p.get("stars") or 0


            l["best_score"] = p.get("best_score") or 0; prev_ok = True


        else:


            if prev_ok:


                l["status"] = "available"; prev_ok = False


            else:


                l["status"] = "locked"


            l["stars"] = 0; l["best_score"] = 0


    return lessons











def _build_content_html(row):


    """يبني HTML غني من explanation_json بمفاتيحه الحقيقية المتنوعة."""


    import json as _json


    if not row:


        return ""


    keys = row.keys() if hasattr(row, "keys") else []


    parts = []





    title = (row["title_ar"] if "title_ar" in keys and row["title_ar"] else


             (row["title"] if "title" in keys else ""))


    if title:


        parts.append(f'<h2 style="color:#0066cc;margin:0 0 10px;font-weight:700">{title}</h2>')





    fp = row["focus_point"] if "focus_point" in keys else None


    if fp:


        parts.append(f'<div style="background:#e3f2fd;padding:10px 14px;border-radius:8px;margin:8px 0;font-weight:600">🎯 {fp}</div>')





    ex_raw = row["explanation_json"] if "explanation_json" in keys else None


    if ex_raw:


        try:


            ex = _json.loads(ex_raw)


        except Exception:


            ex = None





        def render_block(d, heading=None):


            out = []


            if heading:


                out.append(f'<h3 style="margin:18px 0 8px;color:#0d47a1">{heading}</h3>')


            if isinstance(d, dict):


                if d.get("ar"):


                    out.append(f'<div style="background:#f0f8ff;padding:14px;border-radius:10px;margin:10px 0;line-height:1.9;text-align:right">{d["ar"]}</div>')


                if d.get("key_rule"):


                    out.append(f'<div style="background:#fff3e0;padding:12px;border-right:4px solid #ff9800;border-radius:8px;margin:10px 0"><strong>⭐ القاعدة الذهبية:</strong> {d["key_rule"]}</div>')


                if d.get("text_types"):


                    out.append('<h4 style="margin:14px 0 6px">📑 أنواع النصوص:</h4><ul style="line-height:2;padding-right:20px">')


                    for t in d["text_types"]:


                        out.append(f"<li>{t}</li>")


                    out.append("</ul>")


                steps = d.get("solving_steps") or d.get("steps") or d.get("strategy")


                if steps:


                    out.append('<h4 style="margin:14px 0 6px">📋 خطوات الحل:</h4><ol style="line-height:2;padding-right:20px">')


                    for s in steps:


                        out.append(f"<li>{s}</li>")


                    out.append("</ol>")


                if d.get("signal_phrases"):


                    out.append('<h4 style="margin:14px 0 6px">🔑 العبارات الإشارية:</h4><ul style="line-height:2;padding-right:20px;font-family:Georgia,serif">')


                    for s in d["signal_phrases"]:


                        out.append(f"<li><code>{s}</code></li>")


                    out.append("</ul>")


                if d.get("tips"):


                    out.append('<div style="background:#fff8e1;padding:12px;border-right:4px solid #ffa726;border-radius:8px;margin:10px 0"><strong>💡 نصائح:</strong><ul style="margin:6px 0;padding-right:18px">')


                    for t in d["tips"]:


                        out.append(f"<li>{t}</li>")


                    out.append("</ul></div>")


            return "".join(out)





        if isinstance(ex, dict):


            top_level = render_block(ex)


            if top_level:


                parts.append(top_level)


            HEADINGS = {


                "factual": "📘 Factual Questions — أسئلة الحقائق",


                "negative_factual": "📕 Negative Factual — أسئلة الاستثناء",


                "inference": "🧠 Inference — أسئلة الاستنتاج",


                "vocabulary": "📖 Vocabulary — أسئلة المفردات",


                "rhetorical": "🎨 Rhetorical Purpose",


                "sentence_simplification": "✂️ Sentence Simplification",


                "main_idea": "💡 Main Idea — الفكرة الرئيسية",


                "summary": "📝 Summary — الملخص",


            }


            for k, heading in HEADINGS.items():


                if k in ex and isinstance(ex[k], dict):


                    parts.append(render_block(ex[k], heading))





    cont = row["content"] if "content" in keys else None


    if cont and len(str(cont)) > 60 and str(cont) not in "".join(parts):


        parts.append(f'<div style="margin-top:12px;color:#555">{cont}</div>')





    return chr(10).join(parts) if parts else ""








@home_bp.route("/home")


def home():


    # DAY1_REDIRECT: unified dashboard


    from flask import redirect, request


    uid = request.args.get("user_id") or request.args.get("student_id") or ""


    return redirect("/student?student_id=" + str(uid))





    user_id = request.args.get("user_id")


    if not user_id: return "user_id required", 400


    student = _get_student(user_id)


    sections = {


        "reading":   _section_stats(user_id, "reading"),


        "listening": _section_stats(user_id, "listening"),


        "writing":   _section_stats(user_id, "writing"),


        "speaking":  _section_stats(user_id, "speaking"),


    }


        # WRITING_REAL_COUNT: compute real totals for writing + foundation from DB


    try:


        import sqlite3 as _sq


        _conn = _sq.connect("C:/app/data/academy.db")


        _conn.row_factory = _sq.Row


        _cc = _conn.cursor()





        # WRITING: lessons (stage1+stage2) + email scenarios + discussion scenarios + sb exercises


        _w_lessons = _cc.execute("SELECT COUNT(*) FROM writing_lessons WHERE is_exam=0").fetchone()[0]


        _w_emails  = _cc.execute("SELECT COUNT(*) FROM writing_email_scenarios WHERE is_active=1").fetchone()[0]


        _w_disc    = _cc.execute("SELECT COUNT(*) FROM writing_discussion_scenarios WHERE is_active=1").fetchone()[0]


        _w_sb      = _cc.execute("SELECT COUNT(*) FROM sentence_building_exercises WHERE is_active=1").fetchone()[0]


        _w_total = _w_lessons + _w_emails + _w_disc + _w_sb





        # WRITING done: progress (completed) + sb correct + submissions accepted


        _w_done_lesson = _cc.execute(


            "SELECT COUNT(*) FROM writing_progress WHERE telegram_id=? AND status='completed'",


            (str(user_id),)


        ).fetchone()[0]


        _w_done_sb = _cc.execute(


            "SELECT COUNT(DISTINCT exercise_id) FROM sentence_building_progress WHERE user_id=? AND is_correct=1",


            (str(user_id),)


        ).fetchone()[0]


        _w_done_sub = 0


        try:


            _w_done_sub = _cc.execute(


                "SELECT COUNT(*) FROM writing_submissions WHERE telegram_id=?",


                (str(user_id),)


            ).fetchone()[0]


        except Exception:


            pass


        _w_done = _w_done_lesson + _w_done_sb + _w_done_sub





        # FOUNDATION: 5 golden rules from sentence_foundation_lessons


        _f_total = _cc.execute("SELECT COUNT(*) FROM sentence_foundation_lessons WHERE is_active=1").fetchone()[0]





        _conn.close()





        if not isinstance(sections, dict):


            sections = {}


        sections["writing"] = {


            "done": _w_done,


            "total": _w_total,


            "pct": int((_w_done * 100) / _w_total) if _w_total else 0


        }


        sections["foundation"] = {


            "done": 0,


            "total": _f_total,


            "pct": 0


        }


    except Exception as _e:


        print(f"[WRITING_REAL_COUNT] warning: {_e}")





    # SECTIONS_GUARD: ensure all section keys exist (foundation/reading/listening/speaking/writing)


    _default = {"done": 0, "total": 0, "pct": 0}


    if not isinstance(sections, dict):


        sections = {}


    for _k in ("foundation", "reading", "listening", "speaking", "writing"):


        if _k not in sections or not isinstance(sections.get(_k), dict):


            sections[_k] = dict(_default)


        else:


            for _f in ("done", "total", "pct"):


                sections[_k].setdefault(_f, 0)


    return render_template("home.html", student=student, sections=sections, user_id=user_id)








@home_bp.route("/path/<section>")


def learning_path(section):


    if section not in SECTION_META: return "Unknown section", 404


    user_id = request.args.get("user_id")


    if not user_id: return "user_id required", 400


    student = _get_student(user_id)


    lessons = _get_lesson_progress(user_id, section)


    meta = SECTION_META[section]


    return render_template("learning_path.html",


                           student=student, lessons=lessons, user_id=user_id,


                           section=section, section_title=meta["title"], section_class=meta["class"])








# ============================================================


# LESSON RUNNER (FULL)


# ============================================================





# [REMOVED duplicate /lesson route - app.py serves it via lesson_view.html]





@home_bp.route("/api/lesson/submit", methods=["POST"])


def lesson_submit():


    data = request.get_json(silent=True) or {}


    user_id = int(data.get("user_id") or 0)


    lesson_id = int(data.get("lesson_id") or 0)


    correct = int(data.get("correct") or 0)


    total = int(data.get("total") or 1)


    passed = bool(data.get("passed", False))


    stars = int(data.get("stars") or 0)


    xp = int(data.get("xp") or 0)


    if not user_id or not lesson_id:


        return jsonify({"ok": False, "error": "user_id and lesson_id required"}), 400





    best_score = int(correct * 100 / total) if total else 0


    status = "completed" if passed else "available"


    now = datetime.now().isoformat(sep=" ", timespec="seconds")





    c = _conn(); cur = c.cursor()


    try:


        # Upsert into user_lesson_progress


        cur.execute("""SELECT id, best_score, stars, attempts FROM user_lesson_progress


                       WHERE user_id=? AND mini_lesson_id=?""", (user_id, lesson_id))


        existing = cur.fetchone()


        if existing:


            new_best = max(best_score, existing["best_score"] or 0)


            new_stars = max(stars, existing["stars"] or 0)


            new_attempts = (existing["attempts"] or 0) + 1


            cur.execute("""UPDATE user_lesson_progress


                           SET status=?, stars=?, best_score=?, attempts=?,


                               last_attempt_at=?, completed_at=CASE WHEN ?='completed' AND completed_at IS NULL THEN ? ELSE completed_at END


                           WHERE id=?""",


                        (status if passed or existing["best_score"] else "available",


                         new_stars, new_best, new_attempts, now, status, now, existing["id"]))


        else:


            cur.execute("""INSERT INTO user_lesson_progress


                           (user_id, mini_lesson_id, status, stars, best_score, attempts, last_attempt_at, completed_at)


                           VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",


                        (user_id, lesson_id, status, stars, best_score, now,


                         now if passed else None))





        # Award XP if passed


        if passed and xp > 0:


            try:


                cur.execute("UPDATE students SET xp = COALESCE(xp,0) + ? WHERE user_id=?", (xp, user_id))


                cur.execute("INSERT INTO xp_log (user_id, amount, reason, created_at) VALUES (?,?,?,?)",


                            (user_id, xp, f"lesson_{lesson_id}_passed", now))


            except Exception as e:


                print(f"[lesson_submit] XP update warning: {e}")





        c.commit()


        result = {"ok": True, "passed": passed, "stars": stars, "best_score": best_score, "xp_awarded": xp if passed else 0}


    except Exception as e:


        c.rollback()


        result = {"ok": False, "error": str(e)}


    finally:


        c.close()


    return jsonify(result)








# ============================================================


# HEARTS API


# ============================================================


def _hearts_api():


    try:


        from services import hearts_api


        return hearts_api


    except Exception as e:


        print(f"[home_routes] hearts_api import failed: {e}")


        return None








@home_bp.route("/api/hearts/status")


def hearts_status():


    user_id = request.args.get("user_id")


    if not user_id: return jsonify({"error": "user_id required"}), 400


    api = _hearts_api()


    if api: return jsonify(api.get_hearts_status(user_id))


    s = _get_student(user_id)


    return jsonify({"hearts": s.get("hearts", 5), "max": 5, "unlimited": False})








@home_bp.route("/api/hearts/lose", methods=["POST"])


def hearts_lose():


    data = request.get_json(silent=True) or {}


    user_id = int(data.get("user_id") or 0)


    if not user_id: return jsonify({"error": "user_id required"}), 400


    api = _hearts_api()


    if api: return jsonify(api.lose_heart(user_id))


    return jsonify({"ok": False, "error": "hearts_api not loaded"}), 500








@home_bp.route("/api/hearts/refill", methods=["POST"])


def hearts_refill():


    data = request.get_json(silent=True) or {}


    user_id = int(data.get("user_id") or 0)


    if not user_id: return jsonify({"error": "user_id required"}), 400


    api = _hearts_api()


    if api: return jsonify(api.refill_hearts(user_id))


    return jsonify({"ok": False, "error": "hearts_api not loaded"}), 500








# ============================================================


# PLACEHOLDER PAGES for tools (avoid 404s)


# ============================================================


def _placeholder(title_ar, desc_ar, user_id):


    back = _ar(0x631,0x62C,0x648,0x639)


    return f"""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8">


<title>{title_ar}</title>


<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap" rel="stylesheet">


<style>body{{font-family:'Tajawal',sans-serif;background:#f7f9fc;padding:60px 20px;text-align:center;margin:0}}


.card{{max-width:480px;margin:0 auto;background:#fff;padding:40px 30px;border-radius:24px;box-shadow:0 8px 32px rgba(0,0,0,.08)}}


.icon{{width:90px;height:90px;background:linear-gradient(135deg,#3b82f6,#2563eb);border-radius:24px;margin:0 auto 20px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:42px}}


h1{{font-size:24px;margin-bottom:10px;font-weight:900}}p{{color:#6b7a90;margin-bottom:24px;line-height:1.6}}


a{{display:inline-block;background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff;padding:14px 32px;border-radius:14px;text-decoration:none;font-weight:700;box-shadow:0 4px 0 #1e40af}}


.soon{{display:inline-block;background:#fef3c7;color:#92400e;padding:4px 12px;border-radius:12px;font-size:12px;font-weight:700;margin-bottom:12px}}


</style></head><body><div class="card">


<div class="icon">✨</div>


<div class="soon">""" + _ar(0x642,0x631,0x64A,0x628,0x627,0x64B) + """</div>


<h1>{title_ar}</h1><p>{desc_ar}</p>


<a href="/home?user_id={user_id}">{back}</a>


</div></body></html>"""








# REMOVED duplicate /mistakes route - kept in foundation.py





@home_bp.route("/daily")


def daily_page():


    uid = request.args.get("user_id", type=int) or 0


    return _placeholder(


        _ar(0x645,0x647,0x645,0x629,0x20,0x627,0x644,0x64A,0x648,0x645),


        _ar(0x62A,0x62D,0x62F,0x64A,0x627,0x62A,0x20,0x64A,0x648,0x645,0x64A,0x629,0x20,0x644,0x643,0x633,0x628,0x20,0x627,0x644,0x645,0x632,0x64A,0x62F,0x20,0x645,0x646,0x20,0x627,0x644,0x62E,0x628,0x631,0x629),


        uid)





@home_bp.route("/stages")


def stages_page():


    uid = request.args.get("user_id", type=int) or 0


    return _placeholder(


        _ar(0x627,0x644,0x645,0x631,0x627,0x62D,0x644),


        _ar(0x62E,0x631,0x64A,0x637,0x629,0x20,0x645,0x631,0x627,0x62D,0x644,0x20,0x631,0x62D,0x644,0x62A,0x643,0x20,0x646,0x62D,0x648,0x20,0x627,0x644,0x62A,0x62E,0x631,0x651,0x62C),


        uid)





@home_bp.route("/packages")


def packages_page():
    return render_template("packages.html")

@home_bp.route("/certificates")


def certificates_page():


    uid = request.args.get("user_id", type=int) or 0


    return _placeholder(


        _ar(0x634,0x647,0x627,0x62F,0x627,0x62A,0x64A),


        _ar(0x627,0x644,0x634,0x647,0x627,0x62F,0x627,0x62A,0x20,0x627,0x644,0x62A,0x64A,0x20,0x62D,0x635,0x644,0x62A,0x20,0x639,0x644,0x64A,0x647,0x627,0x20,0x645,0x646,0x20,0x64A,0x627,0x645,0x646,0x20,0x623,0x643,0x627,0x62F,0x64A,0x645,0x64A),


        uid)





@home_bp.route("/mock-exam")


def mock_exam_page():


    uid = request.args.get("user_id", type=int) or 0


    return _placeholder(


        _ar(0x628,0x648,0x651,0x627,0x628,0x629,0x20,0x627,0x644,0x62A,0x62E,0x631,0x651,0x62C),


        _ar(0x627,0x62E,0x62A,0x628,0x627,0x631,0x20,0x645,0x62D,0x627,0x643,0x627,0x629,0x20,0x643,0x627,0x645,0x644,0x20,0x644,0x644,0x62A,0x648,0x641,0x644,0x20,0x645,0x639,0x20,0x634,0x647,0x627,0x62F,0x629,0x20,0x631,0x633,0x645,0x64A,0x629),


        uid)






@home_bp.route("/landing")

@home_bp.route("/")

def landing_page():

    return render_template("landing.html")

