# -*- coding: utf-8 -*-
"""
Foundation Path Routes - مسار التأسيس الشامل
المراحل F1-F6 مع نظام مجموعات الأسئلة (set 1/2/3) ودفتر الأخطاء.
"""
import sqlite3, json, os
from flask import Blueprint, request, render_template, jsonify, redirect
from subscription_helpers import require_section_access

foundation_bp = Blueprint("foundation", __name__)

# Use DB_PATH env (set by wsgi.py to /app/data/academy.db on Railway)
DB_PATH = os.environ.get("DB_PATH") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "academy.db")
print(f"[foundation] DB_PATH = {DB_PATH}", flush=True)

FOUNDATION_CODES = ["F1", "F2", "F3", "F4", "F5", "F6"]
STAGE_ICONS = {"F1": "📝", "F2": "📚", "F3": "🔨", "F4": "📖", "F5": "🎧", "F6": "✍️"}
STAGE_DESCS = {
    "F1": "أساسيات القواعد - الضمائر، الأفعال، الأزمنة",
    "F2": "مفردات أساسية + إملاء (400 كلمة عالية التكرار)",
    "F3": "بناء الجملة - من البسيط إلى المركب",
    "F4": "القراءة التأسيسية - الفكرة والتفاصيل",
    "F5": "الاستماع التأسيسي - أرقام، حوارات، محاضرات قصيرة",
    "F6": "الإنتاج - كتابة الإيميل والتحدث",
}

XP_SET1 = 25
XP_SET2 = 15
XP_SET3 = 10
XP_MISTAKE_RETRY = 5
PASS_PCT = 70


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_id(req):
    uid = req.args.get("user_id") or req.args.get("student_id") or "0"
    try:
        return int(uid)
    except:
        return 0


# =========================================================
# 1) GET /foundation - صفحة المراحل
# =========================================================
@foundation_bp.route("/foundation")
@require_section_access("foundation")
def foundation_home():
    user_id = get_user_id(request)
    conn = db(); cur = conn.cursor()

    # المراحل F1-F6
    cur.execute("SELECT id, code, name_ar FROM stages WHERE code IN ('F1','F2','F3','F4') ORDER BY code")
    raw_stages = cur.fetchall()

    stages = []
    prev_passed = True  # F1 always open
    for s in raw_stages:
        # عدد دروس المرحلة
        cur.execute("SELECT COUNT(*) FROM lessons WHERE stage_id=? AND is_active=1", (s["id"],))
        total = cur.fetchone()[0]
        # دروس مكتملة
        cur.execute("""SELECT COUNT(DISTINCT lesson_id) FROM lesson_attempts
                       WHERE telegram_id=? AND lesson_id IN (SELECT id FROM lessons WHERE stage_id=?) AND passed=1""",
                    (str(user_id), s["id"]))
        completed = cur.fetchone()[0]
        # هل اجتاز الـ gatekeeper؟
        cur.execute("SELECT gatekeeper_passed FROM stage_progress WHERE student_id=? AND stage_id=?", (user_id, s["id"]))
        gp = cur.fetchone()
        gk_passed = bool(gp and gp["gatekeeper_passed"])

        pct = int((completed / total) * 100) if total else 0
        locked = not prev_passed
        css = "locked" if locked else ("completed" if gk_passed else "current")
        stages.append({
            "id": s["id"], "code": s["code"], "name_ar": s["name_ar"],
            "desc_ar": STAGE_DESCS.get(s["code"], ""),
            "icon": STAGE_ICONS.get(s["code"], "📂"),
            "total": total, "completed": completed, "progress_pct": pct,
            "locked": locked, "css_class": css,
        })
        prev_passed = gk_passed

    # إحصائيات عامة
    cur.execute("""SELECT COUNT(DISTINCT lesson_id) FROM lesson_attempts WHERE telegram_id=? AND passed=1""", (str(user_id),))
    cl = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(xp),0) FROM students WHERE telegram_id=?", (user_id,))
    xp_row = cur.fetchone()
    total_xp = xp_row[0] if xp_row else 0
    cur.execute("SELECT COUNT(*) FROM error_bank WHERE user_id=? AND COALESCE(is_mastered,0)=0", (user_id,))
    mc = cur.fetchone()[0]
    conn.close()

    return render_template("foundation.html",
        stages=stages, user_id=user_id,
        stats={"completed_lessons": cl, "total_xp": total_xp, "mistakes_count": mc})


# =========================================================
# 2) GET /foundation/stage/<id> - دروس المرحلة
# =========================================================
@foundation_bp.route("/foundation/stage/<int:stage_id>")
@require_section_access("foundation")
def foundation_stage(stage_id):
    user_id = get_user_id(request)
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT id, code, name_ar FROM stages WHERE id=?", (stage_id,))
    s = cur.fetchone()
    if not s:
        conn.close()
        return "Stage not found", 404
    stage = {"id": s["id"], "code": s["code"], "name_ar": s["name_ar"], "desc_ar": STAGE_DESCS.get(s["code"], "")}

    cur.execute("""SELECT id, title_ar, title, skill, xp_reward, order_index
                   FROM lessons WHERE stage_id=? AND is_active=1 ORDER BY order_index, id""", (stage_id,))
    raw = cur.fetchall()

    lessons = []
    prev_done = True
    for L in raw:
        cur.execute("SELECT MAX(passed) FROM lesson_attempts WHERE telegram_id=? AND lesson_id=?", (str(user_id), L["id"]))
        d = cur.fetchone()[0]
        done = bool(d)
        locked = not prev_done
        lessons.append({
            "id": L["id"], "title_ar": L["title_ar"] or L["title"],
            "skill": L["skill"] or "grammar", "xp_reward": L["xp_reward"] or 20,
            "done": done, "locked": locked,
            "css_class": "done" if done else ("locked" if locked else "current"),
        })
        prev_done = done

    gk_unlocked = all(L["done"] for L in lessons) and len(lessons) > 0
    conn.close()
    return render_template("foundation_stage.html", stage=stage, lessons=lessons, gk_unlocked=gk_unlocked, user_id=user_id)


# =========================================================
# 3) GET /foundation/lesson/<id> - شرح الدرس + ابدأ
# =========================================================
@foundation_bp.route("/foundation/lesson/<int:lesson_id>")
@require_section_access("foundation")
def foundation_lesson(lesson_id):
    user_id = get_user_id(request)
    conn = db(); cur = conn.cursor()
    cur.execute("""SELECT id, stage_id, title, title_ar, content, skill, xp_reward, timer_minutes, explanation_json
                   FROM lessons WHERE id=?""", (lesson_id,))
    L = cur.fetchone()
    if not L:
        conn.close()
        return "Lesson not found", 404

    # تحديد set التالي
    cur.execute("""SELECT MAX(set_number) FROM lesson_attempts WHERE telegram_id=? AND lesson_id=?""",
                (str(user_id), lesson_id))
    last_set = cur.fetchone()[0] or 0
    cur.execute("""SELECT passed FROM lesson_attempts WHERE telegram_id=? AND lesson_id=? ORDER BY id DESC LIMIT 1""",
                (str(user_id), lesson_id))
    last_row = cur.fetchone()
    next_set = 1
    if last_row and not last_row["passed"]:
        next_set = min(last_set + 1, 3)
    elif last_row and last_row["passed"]:
        next_set = 1  # الدرس مكتمل، إعادة من البداية إذا أراد

    # استخراج الأمثلة من explanation_json
    examples = []
    vocabulary = []
    content_html = L["content"] or ""
    try:
        if L["explanation_json"]:
            ej = json.loads(L["explanation_json"])
            examples = ej.get("examples", []) or []
            vocabulary = ej.get("vocabulary", []) or ej.get("vocab", []) or []
            if ej.get("content_html"):
                content_html = ej["content_html"]
    except:
        pass

    lesson = {
        "id": L["id"], "stage_id": L["stage_id"],
        "title_ar": L["title_ar"] or L["title"],
        "content_html": content_html,
        "skill": L["skill"] or "grammar",
        "xp_reward": L["xp_reward"] or 25,
        "timer_minutes": L["timer_minutes"] or 10,
    }
    conn.close()
    return render_template("foundation_lesson.html", lesson=lesson, examples=examples, next_set=next_set, user_id=user_id, vocabulary=vocabulary)


# =========================================================
# 4) GET /foundation/quiz/<id>?set=N - الأسئلة
# =========================================================
@foundation_bp.route("/foundation/quiz/<int:lesson_id>")
@require_section_access("foundation")
def foundation_quiz(lesson_id):
    user_id = get_user_id(request)
    try:
        set_number = int(request.args.get("set", "1"))
    except:
        set_number = 1
    set_number = max(1, min(set_number, 3))

    conn = db(); cur = conn.cursor()
    cur.execute("SELECT id, stage_id, title_ar, title FROM lessons WHERE id=?", (lesson_id,))
    L = cur.fetchone()
    if not L:
        conn.close()
        return "Lesson not found", 404

    cur.execute("""SELECT id, q_type, question, options_json, correct_answer, explanation,
                          explanation_ar, translation_ar, concept, tip,
                          why_a, why_b, why_c, why_d,
                          scrambled_words, expected_answer, blanks_json, passage_text, passage_ref
                   FROM lesson_questions
                   WHERE lesson_id=? AND COALESCE(set_number,1)=?
                   ORDER BY order_num, id""", (lesson_id, set_number))
    rows = cur.fetchall()

    # احتياطي: لو set N فارغ، استخدم set 1
    if not rows and set_number > 1:
        cur.execute("""SELECT id, q_type, question, options_json, correct_answer, explanation,
                              explanation_ar, translation_ar, concept, tip,
                              why_a, why_b, why_c, why_d,
                              scrambled_words, expected_answer, blanks_json, passage_text, passage_ref
                       FROM lesson_questions WHERE lesson_id=? AND COALESCE(set_number,1)=1
                       ORDER BY order_num, id""", (lesson_id,))
        rows = cur.fetchall()

    questions = []
    for r in rows:
        # options: قد تكون dict {"A":"x","B":"y"} أو list ["x","y"]
        opts_raw = r["options_json"]
        opts_list = []
        try:
            parsed = json.loads(opts_raw) if opts_raw else []
            if isinstance(parsed, dict):
                for LK in ["A","B","C","D","E"]:
                    if LK in parsed:
                        opts_list.append(parsed[LK])
            elif isinstance(parsed, list):
                opts_list = parsed
        except:
            opts_list = []

        # scrambled_words
        sw = []
        try:
            sw_raw = r["scrambled_words"] if "scrambled_words" in r.keys() else None
            if sw_raw:
                sw = json.loads(sw_raw)
        except:
            sw = []

        # blanks
        blanks = []
        try:
            b_raw = r["blanks_json"] if "blanks_json" in r.keys() else None
            if b_raw:
                blanks = json.loads(b_raw)
        except:
            blanks = []

        passage = ""
        try:
            passage = (r["passage_text"] if "passage_text" in r.keys() else "") or ""
        except:
            passage = ""

        questions.append({
            "id": r["id"],
            "q_type": r["q_type"] or "mcq",
            "question_text": r["question"] or "",
            "question": r["question"] or "",
            "options": opts_list,
            "correct_answer": r["correct_answer"] or "",
            "explanation": r["explanation"] or "",
            "explanation_ar": r["explanation_ar"] or r["explanation"] or "",
            "translation_ar": r["translation_ar"] or "",
            "concept_ar": r["concept"] or "",
            "tip": (r["tip"] if "tip" in r.keys() else "") or "",
            "why_a": (r["why_a"] if "why_a" in r.keys() else "") or "",
            "why_b": (r["why_b"] if "why_b" in r.keys() else "") or "",
            "why_c": (r["why_c"] if "why_c" in r.keys() else "") or "",
            "why_d": (r["why_d"] if "why_d" in r.keys() else "") or "",
            "scrambled_words": sw,
            "expected_answer": (r["expected_answer"] if "expected_answer" in r.keys() else "") or "",
            "blanks": blanks,
            "passage": passage,
        })
    conn.close()

    # L قد تكون tuple أو Row — نتعامل مع الحالتين
    try:
        l_id = L["id"]; l_stage = L["stage_id"]; l_title_ar = L["title_ar"]; l_title = L["title"]
    except (TypeError, IndexError):
        l_id, l_stage, l_title_ar, l_title = L[0], L[1], L[2], L[3]
    lesson = {"id": l_id, "stage_id": l_stage, "title_ar": l_title_ar or l_title}
    return render_template("foundation_quiz.html",
        lesson=lesson, questions=questions, questions_json=json.dumps(questions, ensure_ascii=False),
        total=len(questions), set_number=set_number, user_id=user_id)


# =========================================================
# 5) POST /api/foundation/quiz/answer - تسجيل إجابة
# =========================================================
@foundation_bp.route("/api/foundation/quiz/answer", methods=["POST"])
def api_quiz_answer():
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id", 0))
    except:
        user_id = 0
    lesson_id = int(data.get("lesson_id", 0) or 0)
    question_id = int(data.get("question_id", 0) or 0)
    is_correct = bool(data.get("correct", False))
    user_answer = str(data.get("user_answer", ""))[:200]
    correct_answer = str(data.get("correct_answer", ""))[:200]
    explanation_ar = str(data.get("explanation_ar", ""))[:1000]
    concept_ar = str(data.get("concept_ar", ""))[:200]

    if not user_id or not question_id:
        return jsonify({"ok": False, "error": "missing data"}), 400

    if not is_correct:
        conn = db(); cur = conn.cursor()
        # سجّل في error_bank فقط إذا غير موجود (لتجنّب التكرار)
        cur.execute("""SELECT id FROM error_bank WHERE user_id=? AND question_id=? AND COALESCE(is_mastered,0)=0""",
                    (user_id, question_id))
        existing = cur.fetchone()
        if not existing:
            cur.execute("""INSERT INTO error_bank
                (user_id, question_id, error_type, wrong_answer, correct_answer, created_at,
                 lesson_id, times_retried, times_correct_after, is_mastered, explanation_ar, concept_ar)
                VALUES (?, ?, 'quiz', ?, ?, datetime('now'), ?, 0, 0, 0, ?, ?)""",
                (user_id, question_id, user_answer, correct_answer, lesson_id, explanation_ar, concept_ar))
        conn.commit(); conn.close()
    return jsonify({"ok": True})


# =========================================================
# 6) POST /api/foundation/quiz/finish - إنهاء وحساب النتيجة
# =========================================================
@foundation_bp.route("/api/foundation/quiz/finish", methods=["POST"])
def api_quiz_finish():
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id", 0))
    except:
        user_id = 0
    lesson_id = int(data.get("lesson_id", 0) or 0)
    set_number = int(data.get("set_number", 1) or 1)
    correct = int(data.get("correct", 0) or 0)
    total = int(data.get("total", 0) or 0)
    score = int(data.get("score", 0) or 0)
    answers_json = json.dumps(data.get("answers", []), ensure_ascii=False)

    passed = score >= PASS_PCT
    xp_awarded = 0
    next_action = "stage"
    message = ""

    conn = db(); cur = conn.cursor()
    # سجّل المحاولة
    cur.execute("""INSERT INTO lesson_attempts
        (telegram_id, lesson_id, started_at, finished_at, correct_count, total_questions, passed, score_percent, answers_json, set_number)
        VALUES (?, ?, datetime('now'), datetime('now'), ?, ?, ?, ?, ?, ?)""",
        (str(user_id), lesson_id, correct, total, 1 if passed else 0, score, answers_json, set_number))

    # === 🆕 تسجيل الأخطاء في error_bank مع التكرار الذكي ===
    wrong_answers = data.get("wrong_answers", []) or []
    saved_errors = 0
    for wa in wrong_answers:
        try:
            qid = int(wa.get("question_id", 0) or 0)
            if not qid: continue
            ua = str(wa.get("user_answer", "") or "")[:200]
            ca = str(wa.get("correct_answer", "") or "")[:200]
            
            # هل السؤال موجود في البنك مسبقاً وغير مُتقن؟
            cur.execute("""SELECT id, times_retried, times_correct_after, is_mastered 
                           FROM error_bank 
                           WHERE user_id=? AND question_id=? AND COALESCE(is_mastered,0)=0""",
                        (user_id, qid))
            existing = cur.fetchone()
            
            if existing:
                # موجود → أعد ضبط next_review +2 أيام، وصفّر times_correct_after
                cur.execute("""UPDATE error_bank 
                               SET wrong_answer=?, correct_answer=?, 
                                   next_review=date('now','+2 days'),
                                   times_correct_after=0,
                                   last_reviewed_at=datetime('now')
                               WHERE id=?""",
                            (ua, ca, existing[0]))
            else:
                # جديد → أدخل سجل جديد
                cur.execute("""INSERT INTO error_bank
                    (user_id, question_id, error_type, wrong_answer, correct_answer, created_at,
                     lesson_id, times_retried, times_correct_after, is_mastered, next_review)
                    VALUES (?, ?, 'foundation_exam', ?, ?, datetime('now'), ?, 0, 0, 0, date('now','+2 days'))""",
                    (user_id, qid, ua, ca, lesson_id))
            saved_errors += 1
        except Exception as e:
            print(f"[error_bank] skip qid={wa}: {e}")

    if passed:
        if set_number == 1: xp_awarded = XP_SET1
        elif set_number == 2: xp_awarded = XP_SET2
        else: xp_awarded = XP_SET3
        # امنح XP
        try:
            cur.execute("UPDATE students SET xp = COALESCE(xp,0) + ? WHERE telegram_id=?", (xp_awarded, user_id))
        except: pass
        message = f"🎉 ممتاز! نجحت بنسبة {score}% (set {set_number}). +{xp_awarded} XP"
        next_action = "stage"
    else:
        if set_number < 3:
            next_action = "next_set"
            message = f"⚠️ حصلت على {score}%. راجع الدرس جيداً ثم جرّب مجموعة جديدة (set {set_number+1})."
        else:
            next_action = "cooldown"
            message = f"📚 حصلت على {score}% في set 3. خذ استراحة وارجع لاحقاً مع تركيز أعلى."

    conn.commit(); conn.close()
    return jsonify({
        "ok": True, "passed": passed, "score": score,
        "xp_awarded": xp_awarded, "next_action": next_action, "message": message,
    })


# =========================================================
# 7) GET /mistakes - دفتر الأخطاء
# =========================================================
@foundation_bp.route("/mistakes")
def mistakes_page():
    user_id = get_user_id(request)
    conn = db(); cur = conn.cursor()
    cur.execute("""SELECT eb.id, eb.question_id, eb.wrong_answer, eb.correct_answer,
                          eb.created_at, COALESCE(eb.times_correct_after,0) AS times_correct_after,
                          COALESCE(eb.is_mastered,0) AS is_mastered,
                          eb.explanation_ar,
                          COALESCE(lq.question, q.question_text) AS question_text,
                          lq.options_json AS lq_opts,
                          q.option_a AS qa, q.option_b AS qb, q.option_c AS qc, q.option_d AS qd
                   FROM error_bank eb
                   LEFT JOIN lesson_questions lq ON lq.id = eb.question_id
                   LEFT JOIN questions q ON q.id = eb.question_id
                   WHERE eb.user_id=?
                     AND (lq.question IS NOT NULL OR q.question_text IS NOT NULL)
                   ORDER BY eb.is_mastered ASC, eb.created_at DESC LIMIT 100""", (user_id,))
    rows = cur.fetchall()
    mistakes = [dict(r) for r in rows]
    for m in mistakes:
        if not m.get("question_text"):
            m["question_text"] = "(السؤال غير متوفر)"
    cur.execute("""SELECT COUNT(*) FROM error_bank eb
                     LEFT JOIN lesson_questions lq ON lq.id = eb.question_id
                     LEFT JOIN questions q ON q.id = eb.question_id
                     WHERE eb.user_id=?
                       AND (lq.question IS NOT NULL OR q.question_text IS NOT NULL)""", (user_id,))
    total = cur.fetchone()[0]
    cur.execute("""SELECT COUNT(*) FROM error_bank eb
                     LEFT JOIN lesson_questions lq ON lq.id = eb.question_id
                     LEFT JOIN questions q ON q.id = eb.question_id
                     WHERE eb.user_id=? AND COALESCE(eb.is_mastered,0)=1
                       AND (lq.question IS NOT NULL OR q.question_text IS NOT NULL)""", (user_id,))
    mastered = cur.fetchone()[0]
    conn.close()
    return render_template("mistakes.html",
        mistakes=mistakes, user_id=user_id,
        stats={"total": total, "mastered": mastered, "active": total - mastered})


# =========================================================
# 8) POST /api/mistakes/<id>/retry - مراجعة خطأ
# =========================================================
@foundation_bp.route("/api/mistakes/<int:mid>/retry", methods=["POST"])
def api_mistake_retry(mid):
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get("user_id", 0))
    except:
        user_id = 0
    user_answer = str(data.get("user_answer", "")).strip()

    conn = db(); cur = conn.cursor()
    cur.execute("""SELECT eb.id, eb.user_id, eb.correct_answer, eb.times_correct_after, eb.is_mastered
                   FROM error_bank eb WHERE eb.id=? AND eb.user_id=?""", (mid, user_id))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "not found"}), 404

    is_correct = user_answer.lower() == str(row["correct_answer"]).lower().strip()
    new_count = (row["times_correct_after"] or 0) + (1 if is_correct else 0)
    mastered = 1 if new_count >= 3 else 0
    cur.execute("""UPDATE error_bank SET times_retried = COALESCE(times_retried,0)+1,
                   times_correct_after=?, is_mastered=? WHERE id=?""",
                (new_count, mastered, mid))
    if is_correct:
        try:
            cur.execute("UPDATE students SET xp = COALESCE(xp,0) + ? WHERE telegram_id=?", (XP_MISTAKE_RETRY, user_id))
        except: pass
    conn.commit(); conn.close()
    return jsonify({
        "ok": True, "correct": is_correct, "correct_answer": row["correct_answer"],
        "times_correct_after": new_count, "mastered": bool(mastered),
        "xp_awarded": XP_MISTAKE_RETRY if is_correct else 0,
    })


# ============================================================
# GATEKEEPER - ?????? ????? ???????
# ============================================================
import random as _random

@foundation_bp.route("/foundation/gatekeeper/<int:stage_id>")
@require_section_access("foundation")
def gatekeeper_start(stage_id):
    user_id = get_user_id(request)
    conn = db(); cur = conn.cursor()

    # ???? ?? ???????
    cur.execute("SELECT id, code, name_ar FROM stages WHERE id=?", (stage_id,))
    st = cur.fetchone()
    if not st:
        conn.close()
        return "Stage not found", 404

    # ???? ?? ?????? ???? ???? ???????
    cur.execute("SELECT COUNT(*) FROM lessons WHERE stage_id=? AND is_active=1", (stage_id,))
    total_lessons = cur.fetchone()[0]
    cur.execute("""SELECT COUNT(DISTINCT lesson_id) FROM lesson_attempts
                   WHERE telegram_id=? AND passed=1
                   AND lesson_id IN (SELECT id FROM lessons WHERE stage_id=?)""",
                (str(user_id), stage_id))
    done_lessons = cur.fetchone()[0]

    if total_lessons == 0 or done_lessons < total_lessons:
        conn.close()
        return render_template("gatekeeper_locked.html",
            stage={"id": st["id"], "code": st["code"], "name_ar": st["name_ar"]},
            done=done_lessons, total=total_lessons, user_id=user_id)

    # ???? 10 ????? ??????? ?? ????? ???? ???????
    cur.execute("""SELECT id, question, options_json, correct_answer, explanation_ar, explanation, translation_ar
                   FROM lesson_questions
                   WHERE lesson_id IN (SELECT id FROM lessons WHERE stage_id=? AND is_active=1)
                   AND question IS NOT NULL AND question != ''
                   ORDER BY RANDOM() LIMIT 10""", (stage_id,))
    raw = cur.fetchall()
    conn.close()

    if not raw:
        return f"<h2>?? ???? ????? ????? ??????? {st['code']}</h2><a href='/foundation?user_id={user_id}'>????</a>", 200

    import json as _json
    questions = []
    for q in raw:
        opts = []
        try:
            opts = _json.loads(q["options_json"]) if q["options_json"] else []
        except Exception:
            opts = []
        questions.append({
            "id": q["id"],
            "question": q["question"],
            "options": opts,
            "correct": q["correct_answer"],
            "explanation": q["explanation_ar"] or q["explanation"] or "",
            "translation": q["translation_ar"] or "",
        })

    return render_template("gatekeeper.html",
        stage={"id": st["id"], "code": st["code"], "name_ar": st["name_ar"]},
        questions=questions, user_id=user_id, pass_threshold=80)


@foundation_bp.route("/foundation/gatekeeper/<int:stage_id>/submit", methods=["POST"])
def gatekeeper_submit(stage_id):
    user_id = get_user_id(request)
    data = request.get_json(silent=True) or {}
    answers = data.get("answers", {})  # {qid: "A"/"B"/...}

    conn = db(); cur = conn.cursor()
    qids = [int(k) for k in answers.keys() if str(k).isdigit()]
    if not qids:
        conn.close()
        return jsonify({"ok": False, "error": "no answers"}), 400

    placeholders = ",".join(["?"] * len(qids))
    cur.execute(f"SELECT id, correct_answer FROM lesson_questions WHERE id IN ({placeholders})", qids)
    correct_map = {r["id"]: (r["correct_answer"] or "").strip() for r in cur.fetchall()}

    correct = 0
    total = len(qids)
    details = []
    for qid in qids:
        user_ans = (answers.get(str(qid)) or "").strip()
        right = correct_map.get(qid, "")
        is_right = user_ans.upper() == right.upper()
        if is_right: correct += 1
        details.append({"qid": qid, "user": user_ans, "correct": right, "is_correct": is_right})

    score_pct = int((correct / total) * 100) if total else 0
    passed = 1 if score_pct >= 80 else 0

    # ??? ?? stage_progress
    cur.execute("SELECT id, gatekeeper_attempts, gatekeeper_best_score FROM stage_progress WHERE student_id=? AND stage_id=?",
                (user_id, stage_id))
    sp = cur.fetchone()
    if sp:
        new_attempts = (sp["gatekeeper_attempts"] or 0) + 1
        new_best = max(sp["gatekeeper_best_score"] or 0, score_pct)
        cur.execute("""UPDATE stage_progress SET gatekeeper_attempts=?, gatekeeper_best_score=?,
                       gatekeeper_passed=CASE WHEN ?>=80 THEN 1 ELSE gatekeeper_passed END,
                       completed_at=CASE WHEN ?>=80 THEN CURRENT_TIMESTAMP ELSE completed_at END
                       WHERE id=?""",
                    (new_attempts, new_best, score_pct, score_pct, sp["id"]))
    else:
        cur.execute("""INSERT INTO stage_progress (student_id, stage_id, status, gatekeeper_attempts,
                       gatekeeper_best_score, gatekeeper_passed, started_at, completed_at)
                       VALUES (?, ?, 'in_progress', 1, ?, ?, CURRENT_TIMESTAMP,
                       CASE WHEN ?>=80 THEN CURRENT_TIMESTAMP ELSE NULL END)""",
                    (user_id, stage_id, score_pct, passed, score_pct))
    conn.commit()
    conn.close()

    return jsonify({
        "ok": True, "score_pct": score_pct, "correct": correct, "total": total,
        "passed": bool(passed), "details": details
    })

# =========================================================
# POST /foundation/quiz/<lesson_id>/submit - ??? ??????? + ????? ??????
# =========================================================
@foundation_bp.route("/foundation/quiz/<int:lesson_id>/submit", methods=["POST"])
def foundation_quiz_submit(lesson_id):
    from flask import jsonify
    data = request.get_json(silent=True) or {}
    user_id = str(data.get("user_id") or get_user_id(request) or "")
    try:
        score   = float(data.get("score", 0))
        correct = int(data.get("correct", 0))
        total   = int(data.get("total", 0))
        set_n   = int(data.get("set_number", 1))
    except Exception:
        score, correct, total, set_n = 0.0, 0, 0, 1
    passed = 1 if score >= 70 else 0

    conn = db(); cur = conn.cursor()
    # ???? ????????
    now = __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""INSERT INTO lesson_attempts
                   (telegram_id, lesson_id, started_at, finished_at,
                    correct_count, total_questions, passed, score_percent, set_number)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (user_id, lesson_id, now, now, correct, total, passed, score, set_n))

    # ???? XP ??? ??????
    if passed:
        try:
            cur.execute("UPDATE students SET xp = COALESCE(xp,0) + 20 WHERE telegram_id=?", (user_id,))
        except Exception:
            pass

    # ???? ????? ?????? ?? ??? ???????
    next_lesson_id = None
    cur.execute("SELECT stage_id, order_index FROM lessons WHERE id=?", (lesson_id,))
    cur_lesson = cur.fetchone()
    if cur_lesson:
        cur.execute("""SELECT id FROM lessons
                       WHERE stage_id=? AND is_active=1
                         AND (order_index > ? OR (order_index = ? AND id > ?))
                       ORDER BY order_index, id LIMIT 1""",
                    (cur_lesson["stage_id"], cur_lesson["order_index"] or 0,
                     cur_lesson["order_index"] or 0, lesson_id))
        nxt = cur.fetchone()
        if nxt:
            next_lesson_id = nxt["id"]

    conn.commit(); conn.close()
    return jsonify({
        "ok": True, "passed": bool(passed), "score": score,
        "next_lesson_id": next_lesson_id, "stage_id": cur_lesson["stage_id"] if cur_lesson else None
    })


# ============ بوابة التأسيس - الامتحان الرسمي ============
@foundation_bp.route("/foundation/exam/<int:lesson_id>")
@require_section_access("foundation")
def foundation_exam(lesson_id):
    """امتحان رسمي للدرس 70 (بوابة التأسيس) - بدون كشف إجابات أثناء الاختبار"""
    user_id = get_user_id(request)
    
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT id, stage_id, title_ar, title FROM lessons WHERE id=?", (lesson_id,))
    L = cur.fetchone()
    if not L:
        conn.close()
        return "Lesson not found", 404
    
    cur.execute("""SELECT id, q_type, question, options_json, correct_answer,
                          why_a, why_b, why_c, why_d, tip
                   FROM lesson_questions
                   WHERE lesson_id=? AND COALESCE(set_number,1)=1
                   ORDER BY order_num, id""", (lesson_id,))
    rows = cur.fetchall()
    
    import json as _json
    questions = []
    for r in rows:
        opts_raw = r["options_json"]
        opts_list = []
        try:
            parsed = _json.loads(opts_raw) if opts_raw else []
            if isinstance(parsed, dict):
                for LK in ["A","B","C","D","E"]:
                    if LK in parsed:
                        opts_list.append({"letter": LK, "text": parsed[LK]})
            elif isinstance(parsed, list):
                letters = ["A","B","C","D","E"]
                for i, t in enumerate(parsed):
                    opts_list.append({"letter": letters[i], "text": t})
        except:
            opts_list = []
        
        questions.append({
            "id": r["id"],
            "question_text": r["question"] or "",
            "options": opts_list,
            "correct_answer": r["correct_answer"] or "",
            "why_a": r["why_a"] or "",
            "why_b": r["why_b"] or "",
            "why_c": r["why_c"] or "",
            "why_d": r["why_d"] or "",
            "tip": r["tip"] or "",
        })
    
    conn.close()
    
    lesson_dict = {"id": L["id"], "stage_id": L["stage_id"], 
                   "title": L["title"], "title_ar": L["title_ar"]}
    
    return render_template("foundation_exam.html",
                           lesson=lesson_dict,
                           questions=questions,
                           questions_json=_json.dumps(questions, ensure_ascii=False),
                           user_id=user_id,
                           exam_minutes=15)

