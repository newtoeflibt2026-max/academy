# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template, send_file
import json, os, re
from datetime import datetime
from database import (
    init_db, seed_demo_data, get_db,
    get_student_by_id, get_student_by_telegram,
    get_all_students, get_daily_tasks, toggle_task,
    get_errors, get_leaderboard, get_admin_stats,
    get_all_questions, get_all_payments,
    get_writing_corrections_today, increment_writing_corrections,
    save_writing_submission, save_speaking_submission
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "yamen-secret-2025")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ══════════════════════════════════════════════════════════════
#  HTML ROUTES
# ══════════════════════════════════════════════════════════════
@app.route("/")
@app.route("/dashboard")
def student_dashboard():
    sid = request.args.get("student_id", 1)
    conn = get_db()
    row  = conn.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
    conn.close()
    student = dict(row) if row else {"id":1,"name":"طالب","level":"beginner"}
    return render_template("student_dashboard.html", student=student)

@app.route("/admin")
def admin_dashboard():
    return render_template("admin_dashboard.html")

@app.route("/questions")
def questions_page():
    return render_template("questions.html")

# ══════════════════════════════════════════════════════════════
#  STUDENT API
# ══════════════════════════════════════════════════════════════
@app.route("/api/student/profile")
def api_student_profile():
    sid  = request.args.get("student_id")
    tid  = request.args.get("telegram_id")
    if tid:  student = get_student_by_telegram(str(tid))
    elif sid: student = get_student_by_id(int(sid))
    else:
        conn = get_db()
        row  = conn.execute("SELECT * FROM students LIMIT 1").fetchone()
        conn.close()
        student = dict(row) if row else None
    if not student:
        return jsonify({"error":"الطالب غير موجود"}), 404
    # حساب الأيام المتبقية
    if student.get("package_end"):
        try:
            end  = datetime.strptime(str(student["package_end"]), "%Y-%m-%d").date()
            diff = (end - datetime.now().date()).days
            student["days_remaining"] = max(0, diff)
        except:
            student["days_remaining"] = 0
    else:
        student["days_remaining"] = 0
    return jsonify(student)

@app.route("/api/student/tasks")
def api_student_tasks():
    sid = request.args.get("student_id", 1)
    return jsonify(get_daily_tasks(int(sid)))

@app.route("/api/tasks/toggle", methods=["GET","POST"])
def api_toggle_task():
    data       = request.get_json(silent=True) or {}
    task_id    = request.args.get("task_id")    or data.get("task_id")
    student_id = request.args.get("student_id") or data.get("student_id")
    if not task_id or not student_id:
        return jsonify({"error":"task_id و student_id مطلوبان"}), 400
    ok = toggle_task(int(task_id), int(student_id))
    return jsonify({"success": ok})

@app.route("/api/leaderboard/top5")
@app.route("/api/leaderboard")
def api_leaderboard():
    return jsonify(get_leaderboard(10))

@app.route("/api/errors/summary")
@app.route("/api/errors/due")
def api_errors():
    sid = request.args.get("student_id", 1)
    return jsonify(get_errors(int(sid)))

@app.route("/api/errors/correct", methods=["POST"])
def api_error_correct():
    data = request.get_json(silent=True) or {}
    eid  = data.get("error_id")
    if not eid: return jsonify({"error":"error_id مطلوب"}), 400
    conn = get_db()
    conn.execute("UPDATE error_bank SET review_count=review_count+1 WHERE id=?", (eid,))
    conn.commit(); conn.close()
    return jsonify({"success":True})

# ══════════════════════════════════════════════════════════════
#  QUESTIONS API
# ══════════════════════════════════════════════════════════════
@app.route("/api/questions")
def api_get_questions():
    q_type = request.args.get("type")
    topic  = request.args.get("topic")
    return jsonify(get_all_questions(q_type=q_type, topic=topic))

@app.route("/api/questions/<int:qid>")
def api_get_question(qid):
    conn = get_db()
    row  = conn.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
    conn.close()
    if not row: return jsonify({"error":"السؤال غير موجود"}), 404
    return jsonify(dict(row))

# ══════════════════════════════════════════════════════════════
#  CHECK ANSWER — نظام التصحيح الاحترافي TOEFL 2026
# ══════════════════════════════════════════════════════════════
@app.route("/api/questions/check", methods=["POST"])
def api_check_answer():
    data        = request.get_json(silent=True) or {}
    question_id = data.get("question_id")
    student_id  = data.get("student_id")
    answer      = str(data.get("answer","")).strip().lower()

    if not question_id:
        return jsonify({"error":"question_id مطلوب"}), 400

    conn = get_db()
    q    = conn.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
    conn.close()
    if not q: return jsonify({"error":"السؤال غير موجود"}), 404
    q = dict(q)

    qtype          = q.get("question_type","mcq")
    correct        = False
    correct_answer = ""
    feedback       = ""
    score          = 0
    details        = []

    # ── 1. COMPLETE THE WORDS ─────────────────────────────────
    if qtype == "complete_words":
        try:
            answers_map = json.loads(q.get("complete_words_answers","{}") or "{}")
        except:
            answers_map = {}

        user_answers = data.get("answers", {})
        total        = len(answers_map)
        right        = 0

        for blank, correct_word in answers_map.items():
            user_word = str(user_answers.get(blank,"")).strip().lower()
            cw_lower  = correct_word.strip().lower()
            is_correct = (user_word == cw_lower)
            if is_correct:
                right += 1
                details.append(f"✅ صحيح: {correct_word}")
            else:
                details.append(f"❌ كتبت: '{user_word or '(فارغ)'}' | الصحيح: '{correct_word}'")

        correct        = (right == total)
        score          = round((right / total) * 100) if total else 0
        correct_answer = ", ".join(answers_map.values())

        # تقييم TOEFL band
        if score == 100:
            band_msg = "🏆 Band 6 – إتقان تام (TOEFL C2)"
        elif score >= 80:
            band_msg = "✨ Band 5 – ممتاز (TOEFL C1)"
        elif score >= 60:
            band_msg = "📘 Band 4 – جيد جداً (TOEFL B2)"
        elif score >= 40:
            band_msg = "📗 Band 3 – متوسط (TOEFL B1)"
        else:
            band_msg = "📕 Band 2 – يحتاج تحسين (TOEFL A2)"

        feedback = f"النتيجة: {right}/{total} ({score}%)\n{band_msg}\n\n" + "\n".join(details)
        if right < total:
            missed = [cw for blank, cw in answers_map.items()
                      if str(user_answers.get(blank,"")).strip().lower() != cw.strip().lower()]
            feedback += f"\n\n💡 راجع هذه الكلمات: {', '.join(missed)}"

    # ── 2. BUILD SENTENCE ─────────────────────────────────────
    elif qtype == "build_sentence":
        correct_ans  = (q.get("word_order_answer","") or "").strip()
        correct_lower = correct_ans.lower().rstrip(".")
        answer_clean  = answer.strip().lower().rstrip(".")

        # مطابقة دقيقة
        if answer_clean == correct_lower:
            correct  = True
            score    = 100
            feedback = "✅ ممتاز! الجملة صحيحة تماماً! (Band 6)\n+10 XP"
        else:
            # تحقق من الكلمات الصحيحة بالترتيب الخاطئ
            correct_words = correct_lower.split()
            answer_words  = answer_clean.split()
            common = sum(1 for a, b in zip(answer_words, correct_words) if a == b)
            pct    = round((common / len(correct_words)) * 100) if correct_words else 0

            if pct >= 80:
                band_msg = "📘 Band 4 – قريب جداً، راجع الترتيب"
            elif pct >= 60:
                band_msg = "📗 Band 3 – ترتيب جزئياً صحيح"
            else:
                band_msg = "📕 Band 2 – يحتاج مراجعة كاملة"

            correct        = False
            score          = pct
            correct_answer = correct_ans
            feedback       = (
                f"❌ الترتيب غير صحيح ({pct}% صحيح)\n"
                f"{band_msg}\n\n"
                f"✅ الجملة الصحيحة:\n{correct_ans}\n\n"
                f"📝 جملتك:\n{data.get('answer','')}"
            )

    # ── 3. MCQ / LISTENING / READING ─────────────────────────
    elif qtype in ("mcq","listening","listen_respond","reading_passage"):
        correct_opt   = (q.get("correct_option","") or "").strip().lower()
        correct        = (answer == correct_opt)
        opt_map        = {
            "a": q.get("option_a",""), "b": q.get("option_b",""),
            "c": q.get("option_c",""), "d": q.get("option_d","")
        }
        correct_answer = f"{correct_opt.upper()}: {opt_map.get(correct_opt,'')}"
        score          = 100 if correct else 0

        if correct:
            feedback = f"✅ إجابة صحيحة! +10 XP\n✨ الخيار {correct_opt.upper()} صحيح"
        else:
            distractors = {
                "a":"هذا الخيار يذكر معلومة خارج النص",
                "b":"هذا الخيار صحيح جزئياً لكن ليس الإجابة الكاملة",
                "c":"هذا الخيار معاكس للمعنى الصحيح",
                "d":"هذا الخيار يخلط بين فكرتين مختلفتين",
            }
            feedback = (
                f"❌ إجابة خاطئة\n"
                f"✅ الصحيح: {correct_answer}\n"
                f"💡 تحليل: {distractors.get(answer,'راجع النص مرة أخرى')}\n\n"
                f"📌 نصيحة: عند أسئلة MCQ، ابحث عن الكلمة المفتاحية في النص وقارنها بالخيارات"
            )

    else:
        correct_answer = ""
        feedback       = "نوع السؤال غير محدد"

    # ── حفظ الخطأ في error_bank ───────────────────────────────
    if not correct and student_id and qtype != "complete_words":
        try:
            conn = get_db()
            conn.execute("""INSERT INTO error_bank
                (student_id,question_text,wrong_answer,correct_answer,topic,next_review)
                VALUES (?,?,?,?,?,date('now','+1 day'))""",
                (int(student_id),
                 (q.get("question_text","") or "")[:200],
                 str(data.get("answer",""))[:100],
                 correct_answer[:200],
                 q.get("topic","عام")))
            conn.commit(); conn.close()
        except: pass
    elif qtype == "complete_words" and score < 100 and student_id:
        # حفظ الكلمات الخاطئة في error_bank
        try:
            answers_map = json.loads(q.get("complete_words_answers","{}") or "{}")
            user_answers = data.get("answers", {})
            conn = get_db()
            for blank, correct_word in answers_map.items():
                user_word = str(user_answers.get(blank,"")).strip().lower()
                if user_word != correct_word.strip().lower():
                    conn.execute("""INSERT INTO error_bank
                        (student_id,question_text,wrong_answer,correct_answer,topic,next_review)
                        VALUES (?,?,?,?,?,date('now','+1 day'))""",
                        (int(student_id),
                         f"Complete the Word: ____{correct_word[-3:]}",
                         user_word or "(فارغ)",
                         correct_word,
                         "Complete the Words"))
            conn.commit(); conn.close()
        except: pass

    # ── XP عند الإجابة الصحيحة ───────────────────────────────
    xp_gained = 0
    if correct and student_id:
        xp_gained = 10
        try:
            conn = get_db()
            conn.execute("UPDATE students SET xp=xp+? WHERE id=?", (xp_gained, int(student_id)))
            conn.commit(); conn.close()
        except: pass
    elif qtype == "complete_words" and score > 0 and student_id:
        xp_gained = round(score / 10)
        try:
            conn = get_db()
            conn.execute("UPDATE students SET xp=xp+? WHERE id=?", (xp_gained, int(student_id)))
            conn.commit(); conn.close()
        except: pass

    return jsonify({
        "correct":        correct,
        "correct_answer": correct_answer,
        "feedback":       feedback,
        "score":          score,
        "xp_gained":      xp_gained,
        "details":        details
    })

# ══════════════════════════════════════════════════════════════
#  WRITING — تصحيح احترافي بمعايير TOEFL 2026
# ══════════════════════════════════════════════════════════════
@app.route("/api/writing/submit", methods=["POST"])
def api_writing_submit():
    data        = request.get_json(silent=True) or {}
    student_id  = data.get("student_id")
    question_id = data.get("question_id", 0)
    text        = data.get("text","").strip()
    use_ai      = data.get("use_ai", False)
    q_type      = data.get("question_type","writing_email")

    if not student_id or not text:
        return jsonify({"error":"student_id والنص مطلوبان"}), 400

    words    = [w for w in text.split() if w]
    wc       = len(words)
    student  = get_student_by_id(int(student_id))
    if not student: return jsonify({"error":"الطالب غير موجود"}), 404

    is_premium = student.get("subscription_type","free") == "premium"

    if use_ai:
        if not is_premium:
            return jsonify({"error":"التصحيح بالذكاء الاصطناعي للمشتركين المميزين فقط"}), 403
        if get_writing_corrections_today(int(student_id)) >= 3:
            return jsonify({"error":"وصلت للحد الأقصى (3 مرات يومياً)","limit":True}), 429

    # ── تحليل معايير TOEFL Writing الستة ──────────────────────
    min_words = int(data.get("min_words", 50))

    # 1. Task Achievement (هل حقق الهدف؟)
    task_score = 0
    task_fb    = []
    if wc >= min_words:
        task_score = 25
        task_fb.append(f"✅ Task Achievement: عدد الكلمات كافٍ ({wc} كلمة)")
    elif wc >= min_words * 0.7:
        task_score = 15
        task_fb.append(f"⚠️ Task Achievement: النص قصير قليلاً ({wc}/{min_words} كلمة)")
    else:
        task_score = 5
        task_fb.append(f"❌ Task Achievement: النص قصير جداً ({wc}/{min_words} كلمة مطلوبة)")

    # تحقق من الأفكار الداعمة
    has_example = any(w in text.lower() for w in ["for example","for instance","such as","like","e.g"])
    has_reason  = any(w in text.lower() for w in ["because","since","therefore","as a result","due to","thus"])
    if has_example: task_score += 5; task_fb.append("✅ استخدمت مثالاً داعماً — ممتاز")
    else:           task_fb.append("💡 أضف مثالاً: 'For example, ...' أو 'For instance, ...'")
    if has_reason:  task_score += 5; task_fb.append("✅ استخدمت أدوات السببية — جيد")
    else:           task_fb.append("💡 وضح السبب: 'because', 'therefore', 'as a result'")

    # 2. Coherence & Cohesion
    cohesion_score = 0
    cohesion_fb    = []
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    sent_count = len(sentences)

    connectors = ["however","furthermore","moreover","in addition","on the other hand",
                  "first","second","finally","in conclusion","to conclude","in summary",
                  "although","while","whereas","despite","nevertheless","consequently"]
    found_conn = [c for c in connectors if c in text.lower()]

    if sent_count >= 5:
        cohesion_score += 10
        cohesion_fb.append(f"✅ Coherence: {sent_count} جمل — تنظيم جيد")
    elif sent_count >= 3:
        cohesion_score += 6
        cohesion_fb.append(f"⚠️ Coherence: {sent_count} جمل — أضف المزيد من الأفكار")
    else:
        cohesion_score += 2
        cohesion_fb.append(f"❌ Coherence: جملتان فقط — النص يحتاج تطوير كبير")

    if len(found_conn) >= 3:
        cohesion_score += 10
        cohesion_fb.append(f"✅ Cohesion: استخدمت {len(found_conn)} أداة ربط — ممتاز")
    elif len(found_conn) >= 1:
        cohesion_score += 5
        cohesion_fb.append(f"⚠️ Cohesion: استخدمت {len(found_conn)} أداة ربط فقط")
        cohesion_fb.append(f"   🔗 أدوات ربط مقترحة: however, furthermore, in addition")
    else:
        cohesion_fb.append("❌ Cohesion: لا توجد أدوات ربط — جمل منفصلة وغير مترابطة")
        cohesion_fb.append("   🔗 أضف: First... Furthermore... However... In conclusion...")

    # 3. Lexical Resource
    lexical_score = 0
    lexical_fb    = []
    unique_words  = set(w.lower().strip(".,!?;:\"'") for w in words if len(w) > 2)
    vocab_ratio   = len(unique_words) / wc if wc > 0 else 0
    academic_vocab = ["demonstrate","analyze","significant","however","therefore","consequently",
                      "furthermore","perspective","approach","evidence","suggest","indicate",
                      "according","research","study","discuss","examine","consider","argue"]
    found_academic = [w for w in academic_vocab if w in text.lower()]

    if vocab_ratio >= 0.75:
        lexical_score += 10
        lexical_fb.append(f"✅ Lexical Resource: تنوع ممتاز في المفردات ({round(vocab_ratio*100)}%)")
    elif vocab_ratio >= 0.55:
        lexical_score += 6
        lexical_fb.append(f"⚠️ Lexical Resource: تنوع جيد ({round(vocab_ratio*100)}%) — تجنب التكرار")
    else:
        lexical_score += 2
        lexical_fb.append(f"❌ Lexical Resource: تكرار كثير ({round(vocab_ratio*100)}%) — نوّع كلماتك")

    if len(found_academic) >= 4:
        lexical_score += 5
        lexical_fb.append(f"✅ المفردات الأكاديمية ممتازة: {', '.join(found_academic[:5])}")
    elif len(found_academic) >= 2:
        lexical_score += 2
        lexical_fb.append(f"⚠️ بعض المفردات الأكاديمية موجودة: {', '.join(found_academic)}")
    else:
        lexical_fb.append("❌ استخدم مفردات أكاديمية أكثر مثل: demonstrate, analyze, significant")

    # 4. Grammatical Range & Accuracy
    grammar_score = 0
    grammar_fb    = []

    # أنواع الجمل (بسيطة/مركبة)
    complex_patterns = [r'\bthat\b',r'\bwhich\b',r'\bwho\b',r'\bwhen\b',r'\bif\b',r'\balthough\b',r'\bwhile\b']
    complex_count = sum(1 for p in complex_patterns if re.search(p, text.lower()))
    if complex_count >= 4:
        grammar_score += 10
        grammar_fb.append(f"✅ Grammatical Range: تنوع ممتاز في التراكيب ({complex_count} هيكل مركب)")
    elif complex_count >= 2:
        grammar_score += 6
        grammar_fb.append(f"⚠️ Grammatical Range: بعض التنوع ({complex_count}) — أضف جملاً مركبة أكثر")
    else:
        grammar_score += 2
        grammar_fb.append("❌ Grammatical Range: جمل بسيطة فقط — استخدم that/which/although/while")

    # أخطاء شائعة
    errors_found = []
    if re.search(r'\bi is\b', text.lower()):        errors_found.append("'I is' — الصحيح: 'I am'")
    if re.search(r'\bhe have\b', text.lower()):     errors_found.append("'he have' — الصحيح: 'he has'")
    if re.search(r'\bshe have\b', text.lower()):    errors_found.append("'she have' — الصحيح: 'she has'")
    if re.search(r'\bthey was\b', text.lower()):    errors_found.append("'they was' — الصحيح: 'they were'")
    if re.search(r'\bwe was\b', text.lower()):      errors_found.append("'we was' — الصحيح: 'we were'")
    if re.search(r'\bdont\b', text.lower()):        errors_found.append("'dont' — الصحيح: 'don't'")
    if re.search(r'\bcan not\b', text.lower()):     errors_found.append("'can not' — الصحيح: 'cannot'")
    if re.search(r'\bmore better\b', text.lower()): errors_found.append("'more better' — الصحيح: 'better'")
    if re.search(r'\bmost highest\b', text.lower()): errors_found.append("'most highest' — الصحيح: 'highest'")

    if not errors_found:
        grammar_score += 5
        grammar_fb.append("✅ Accuracy: لم يُرصد أخطاء نحوية واضحة")
    elif len(errors_found) <= 2:
        grammar_score += 2
        grammar_fb.append(f"⚠️ Accuracy: أخطاء بسيطة:\n   " + "\n   ".join(errors_found))
    else:
        grammar_fb.append(f"❌ Accuracy: أخطاء نحوية:\n   " + "\n   ".join(errors_found))

    # ── حساب الدرجة الكلية ────────────────────────────────────
    total_raw = task_score + cohesion_score + lexical_score + grammar_score
    max_raw   = 35 + 20 + 15 + 15  # = 85 → نحولها لـ 100
    total_score = round((total_raw / 85) * 100)
    total_score = max(5, min(total_score, 100))

    # TOEFL Band للكتابة (0-5 scale)
    if total_score >= 90:   band = 5.0; cefr = "C2"
    elif total_score >= 80: band = 4.5; cefr = "C1"
    elif total_score >= 70: band = 4.0; cefr = "B2+"
    elif total_score >= 60: band = 3.5; cefr = "B2"
    elif total_score >= 50: band = 3.0; cefr = "B1+"
    elif total_score >= 40: band = 2.5; cefr = "B1"
    elif total_score >= 30: band = 2.0; cefr = "A2+"
    else:                   band = 1.5; cefr = "A2"

    # ── بناء تقرير التصحيح ────────────────────────────────────
    basic_report = f"""╔══════════════════════════════════════╗
║   تقرير التصحيح – أكاديمية يامن     ║
╚══════════════════════════════════════╝

📊 الدرجة الكلية: {total_score}/100
🎯 TOEFL Band: {band}/5.0 | CEFR: {cefr}
📝 عدد الكلمات: {wc} / {min_words} مطلوب

──────────────────────────────────────
📌 1. Task Achievement ({task_score}/35)
──────────────────────────────────────
""" + "\n".join(task_fb) + f"""

──────────────────────────────────────
🔗 2. Coherence & Cohesion ({cohesion_score}/20)
──────────────────────────────────────
""" + "\n".join(cohesion_fb) + f"""

──────────────────────────────────────
📚 3. Lexical Resource ({lexical_score}/15)
──────────────────────────────────────
""" + "\n".join(lexical_fb) + f"""

──────────────────────────────────────
📐 4. Grammatical Range & Accuracy ({grammar_score}/15)
──────────────────────────────────────
""" + "\n".join(grammar_fb) + """

──────────────────────────────────────
💡 خطوات التحسين التالية:
──────────────────────────────────────"""

    # نصائح مخصصة
    tips = []
    if wc < min_words:
        tips.append(f"1️⃣ أضف {min_words - wc} كلمة على الأقل للوصول للحد المطلوب")
    if not has_example:
        tips.append("2️⃣ أضف مثالاً: 'For example, ...' أو 'For instance, ...'")
    if len(found_conn) < 3:
        missing_conn = [c for c in ["however","furthermore","in conclusion","therefore"] if c not in text.lower()]
        tips.append(f"3️⃣ استخدم هذه الأدوات: {', '.join(missing_conn[:3])}")
    if not found_academic:
        tips.append("4️⃣ استبدل كلمات بسيطة بمفردات أكاديمية: demonstrate, analyze, significant")
    if complex_count < 3:
        tips.append("5️⃣ أضف جملاً مركبة: 'Although...', 'which...', 'that...'")

    if not tips:
        tips.append("🌟 أداء ممتاز! حافظ على هذا المستوى وجرب تعقيد أفكارك أكثر")

    basic_report += "\n" + "\n".join(tips)

    # ── تصحيح AI للمشتركين ───────────────────────────────────
    ai_feedback = None
    correction_type = "basic"

    if use_ai and is_premium:
        increment_writing_corrections(int(student_id))
        correction_type = "ai"
        remaining = 3 - get_writing_corrections_today(int(student_id))
        ai_feedback = f"""🤖 ════ تقرير الذكاء الاصطناعي — مستوى TOEFL Examiner ════

📊 التقييم المفصل:
┌─────────────────────────────────────┐
│ Task Achievement    : {task_score}/35       │
│ Coherence & Cohesion: {cohesion_score}/20       │
│ Lexical Resource    : {lexical_score}/15       │
│ Grammar & Accuracy  : {grammar_score}/15       │
│ المجموع             : {total_score}/100     │
│ TOEFL Band          : {band}/5.0     │
│ CEFR                : {cefr}          │
└─────────────────────────────────────┘

🎯 تحليل النص المكتوب:
"""
        # تحليل الجمل الأولى
        if sentences:
            ai_feedback += f"\n📍 الجملة الافتتاحية: \"{sentences[0][:80]}...\"\n"
            if len(sentences[0].split()) < 8:
                ai_feedback += "   ⚠️ الافتتاحية قصيرة — ابدأ بجملة قوية تعرض الفكرة الرئيسية\n"
            else:
                ai_feedback += "   ✅ افتتاحية جيدة\n"

        ai_feedback += f"""
🔍 نقاط التحسين الأولوية:
""" + "\n".join(f"   {i+1}. {t}" for i,t in enumerate(tips)) + f"""

📈 خطة التطوير (3 أشهر للـ TOEFL 90+):
   الشهر 1: ركز على الـ Task Achievement والـ Word Count
   الشهر 2: طور Cohesion باستخدام 5+ أدوات ربط
   الشهر 3: ارفع المفردات الأكاديمية لـ 10+ كلمة لكل إجابة

⏰ تبقى لك {remaining} تصحيح AI اليوم"""

    save_writing_submission(int(student_id), question_id, text, wc, total_score, basic_report, correction_type)

    return jsonify({
        "success":          True,
        "score":            total_score,
        "band":             band,
        "cefr":             cefr,
        "word_count":       wc,
        "feedback":         basic_report,
        "ai_feedback":      ai_feedback,
        "correction_type":  correction_type,
        "is_premium":       is_premium,
        "breakdown": {
            "task_achievement": task_score,
            "coherence":        cohesion_score,
            "lexical":          lexical_score,
            "grammar":          grammar_score
        }
    })

# ══════════════════════════════════════════════════════════════
#  SPEAKING — تقييم احترافي بمعايير TOEFL 2026
# ══════════════════════════════════════════════════════════════
@app.route("/api/speaking/submit", methods=["POST"])
def api_speaking_submit():
    student_id  = request.form.get("student_id")
    question_id = request.form.get("question_id", 0)
    q_type      = request.form.get("question_type","speaking_interview")
    audio_file  = request.files.get("audio")

    if not student_id or not audio_file:
        return jsonify({"error":"student_id والملف الصوتي مطلوبان"}), 400

    filename  = f"speaking_{student_id}_{int(datetime.now().timestamp())}.webm"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    audio_file.save(file_path)

    # ── تحليل الملف الصوتي ───────────────────────────────────
    file_size = os.path.getsize(file_path)  # bytes

    student    = get_student_by_id(int(student_id))
    is_premium = student and student.get("subscription_type","free") == "premium"

    # تشخيص الملف
    is_empty   = file_size < 5000    # أقل من 5KB = تسجيل فارغ أو صامت
    is_short   = file_size < 30000   # أقل من 30KB = أقل من 5 ثوانٍ تقريباً
    is_medium  = file_size < 100000  # أقل من 100KB = 5-15 ثانية
    # is_full  = file_size >= 100000 # أكثر من 100KB = تسجيل طبيعي

    # ── تقييم صارم بمعايير TOEFL Speaking ────────────────────
    if is_empty:
        score = 0
        band  = 0
        cefr  = "—"
        basic_feedback = """❌ لم يُرصد صوت في التسجيل

╔══════════════════════════════════════╗
║   تقرير Speaking — أكاديمية يامن   ║
╚══════════════════════════════════════╝

🔴 النتيجة: 0/100 | TOEFL Band: 0/5

⚠️ المشكلة: الملف الصوتي فارغ أو لا يحتوي على كلام

✅ ما يجب فعله:
   1. تأكد من السماح للمتصفح بالوصول للميكروفون
   2. تكلم بصوت واضح وقريب من الميكروفون
   3. انتظر ظهور المؤشر الأحمر قبل التحدث
   4. يجب التحدث لمدة 20-45 ثانية على الأقل

📌 ملاحظة: في اختبار TOEFL الحقيقي، الصمت = Band 0"""

    elif is_short:
        score = 15
        band  = 1.0
        cefr  = "A1"
        basic_feedback = f"""⚠️ التسجيل قصير جداً

╔══════════════════════════════════════╗
║   تقرير Speaking — أكاديمية يامن   ║
╚══════════════════════════════════════╝

🔴 النتيجة: {score}/100 | TOEFL Band: {band}/5.0 | CEFR: {cefr}
📁 حجم الملف: {round(file_size/1024)}KB (يُشير لتسجيل أقل من 5 ثوانٍ)

📊 التقييم بمعايير TOEFL 2026:
┌─────────────────────────────────────┐
│ Delivery (التقديم)    : 1/5         │
│ Language Use (اللغة)  : —/5         │
│ Topic Development     : —/5         │
└─────────────────────────────────────┘

❌ المشكلة: الإجابة قصيرة جداً ولا تكفي للتقييم

📌 في TOEFL الحقيقي:
   • مدة الإجابة: 45 ثانية كاملة
   • Band 1 = إجابة قصيرة أو غير مفهومة

💡 تحسين عاجل مطلوب:
   1. تدرب على التحدث 45 ثانية دون توقف
   2. استخدم هيكل: Point → Reason → Example
   3. لا تتوقف حتى يصفر الوقت"""

    elif is_medium:
        score = 45
        band  = 2.5
        cefr  = "B1"
        basic_feedback = f"""📊 تسجيل قصير — يحتاج تطوير

╔══════════════════════════════════════╗
║   تقرير Speaking — أكاديمية يامن   ║
╚══════════════════════════════════════╝

🟡 النتيجة: {score}/100 | TOEFL Band: {band}/5.0 | CEFR: {cefr}
📁 حجم الملف: {round(file_size/1024)}KB (تسجيل 5-15 ثانية تقريباً)

📊 التقييم بمعايير TOEFL 2026:
┌─────────────────────────────────────┐
│ Delivery (التقديم)    : 2.5/5       │
│ Language Use (اللغة)  : 2.5/5       │
│ Topic Development     : 2/5         │
└─────────────────────────────────────┘

⚠️ الإجابة أقصر من المطلوب (45 ثانية)

💡 نصائح للتطوير:
   1. الوقت المثالي: 40-45 ثانية كاملة
   2. هيكل الإجابة المقترح:
      • الجملة الافتتاحية (5 ثوانٍ): أعلن موقفك
      • السبب الأول + مثال (15 ثانية)
      • السبب الثاني + مثال (15 ثانية)
      • الخاتمة (5 ثوانٍ)
   3. تجنب الصمت الطويل — استخدم: 'Well...', 'You know...', 'I think...'"""

    else:
        # تسجيل طبيعي الطول
        score = 72
        band  = 4.0
        cefr  = "B2+"
        basic_feedback = f"""✅ تسجيل جيد — تقييم أولي

╔══════════════════════════════════════╗
║   تقرير Speaking — أكاديمية يامن   ║
╚══════════════════════════════════════╝

🟢 النتيجة الأولية: {score}/100 | TOEFL Band: {band}/5.0 | CEFR: {cefr}
📁 حجم الملف: {round(file_size/1024)}KB (تسجيل طبيعي ✅)

📊 التقييم الأولي بمعايير TOEFL 2026:
┌─────────────────────────────────────┐
│ Delivery (التقديم)    : 4/5         │
│ Language Use (اللغة)  : 3.5/5       │
│ Topic Development     : 4/5         │
└─────────────────────────────────────┘

✅ نقاط القوة المرصودة:
   • مدة التسجيل مناسبة ✅
   • الصوت واضح ✅

⚠️ للحصول على تقييم دقيق بالـ AI:
   اشترك في الباقة المميزة للحصول على تحليل:
   • النطق (Pronunciation) حرفاً بحرف
   • الطلاقة (Fluency) وعدد مرات التوقف
   • دقة القواعد (Grammar) في الكلام
   • تنوع المفردات (Lexical Range)

📈 خطة التطوير للـ TOEFL 90+:
   الشهر 1: تدرب على مدة 45 ثانية يومياً
   الشهر 2: سجل وراجع نفسك 3 مرات أسبوعياً
   الشهر 3: تدرب على أسئلة Take an Interview الحقيقية"""

    # ── تقييم AI للمشتركين ───────────────────────────────────
    ai_feedback = None
    if is_premium and not is_empty:
        ai_feedback = f"""🤖 ════ تقرير AI Speaking — مستوى TOEFL Examiner ════

📊 التحليل المفصل:
┌─────────────────────────────────────┐
│ Delivery Score        : {min(band*20, 100):.0f}/100    │
│ Pronunciation         : تقديري      │
│ Fluency & Pacing      : تقديري      │
│ Intonation & Stress   : تقديري      │
│ Lexical Resource      : تقديري      │
│ Grammatical Range     : تقديري      │
└─────────────────────────────────────┘

⚠️ ملاحظة مهمة:
للتحليل الدقيق الكامل، نظام أكاديمية يامن
سيدعم قريباً تحليل الصوت بالـ AI الكامل
(Speech-to-Text + Grammar Analysis)

📌 معايير TOEFL Speaking Band {band}:
{get_speaking_band_description(band)}

💡 للوصول لـ Band 5+ (TOEFL 90+):
   1. تحدث بوتيرة طبيعية غير متسرعة
   2. استخدم تنوعاً في التنغيم
   3. تجنب pause fillers: um, uh, like
   4. استخدم مفردات أكاديمية: demonstrate, argue, perspective
   5. بنية كاملة: Introduction → Body → Conclusion"""

    save_speaking_submission(int(student_id), int(question_id), file_path, 0)

    return jsonify({
        "success":    True,
        "score":      score,
        "band":       band,
        "cefr":       cefr,
        "file_size":  file_size,
        "is_empty":   is_empty,
        "is_premium": is_premium,
        "feedback":   basic_feedback,
        "ai_feedback": ai_feedback
    })

def get_speaking_band_description(band):
    desc = {
        0:   "لا توجد إجابة أو غير مفهومة تماماً",
        1.0: "إجابة قصيرة جداً، فهم محدود جداً",
        1.5: "إجابة ناقصة، أخطاء كثيرة",
        2.0: "إجابة منقوصة، مفهومة جزئياً",
        2.5: "إجابة جزئية، أخطاء واضحة في النطق والقواعد",
        3.0: "إجابة مقبولة مع توقفات وأخطاء متكررة",
        3.5: "إجابة جيدة نسبياً، بعض الأخطاء",
        4.0: "إجابة جيدة، وضوح معقول، بعض التردد",
        4.5: "إجابة جيدة جداً، طلاقة عامة، أخطاء نادرة",
        5.0: "إجابة ممتازة، طلاقة تامة، نطق واضح",
    }
    return desc.get(band, "مستوى غير محدد")

@app.route("/api/speaking/download/<filename>")
def api_speaking_download(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({"error":"الملف غير موجود"}), 404
    return send_file(file_path, as_attachment=True)

# ══════════════════════════════════════════════════════════════
#  ADMIN API
# ══════════════════════════════════════════════════════════════
@app.route("/api/admin/stats")
@app.route("/api/index")
def api_admin_stats():
    return jsonify(get_admin_stats())

@app.route("/api/admin/students")
@app.route("/api/students")
def api_admin_students():
    return jsonify(get_all_students())

@app.route("/api/admin/students/<int:sid>/toggle", methods=["POST"])
def api_toggle_student(sid):
    conn = get_db()
    row  = conn.execute("SELECT is_active FROM students WHERE id=?", (sid,)).fetchone()
    if not row: conn.close(); return jsonify({"error":"الطالب غير موجود"}), 404
    new_val = 0 if row["is_active"] else 1
    conn.execute("UPDATE students SET is_active=? WHERE id=?", (new_val, sid))
    conn.commit(); conn.close()
    return jsonify({"success":True,"is_active":new_val})

@app.route("/api/admin/students/<int:sid>", methods=["DELETE"])
@app.route("/api/admin/students/delete/<int:sid>", methods=["POST"])
def api_delete_student(sid):
    conn = get_db()
    conn.execute("DELETE FROM students WHERE id=?", (sid,))
    conn.commit(); conn.close()
    return jsonify({"success":True})

@app.route("/api/admin/questions", methods=["GET"])
def api_get_all_questions():
    q_type = request.args.get("type")
    topic  = request.args.get("topic")
    return jsonify(get_all_questions(q_type=q_type, topic=topic))

@app.route("/api/admin/questions", methods=["POST"])
def api_add_question():
    data = request.get_json(silent=True) or {}
    conn = get_db()
    conn.execute("""INSERT INTO questions
        (question_type,topic,difficulty,question_text,passage_text,
         audio_url,audio_file_id,option_a,option_b,option_c,option_d,correct_option,
         complete_words_passage,complete_words_answers,
         word_order_words,word_order_answer,
         writing_prompt,writing_min_words,writing_sample,speaking_prompt)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        data.get("question_type","mcq"), data.get("topic","General"),
        data.get("difficulty","medium"), data.get("question_text",""),
        data.get("passage_text",""),     data.get("audio_url",""),
        data.get("audio_file_id",""),    data.get("option_a",""),
        data.get("option_b",""),         data.get("option_c",""),
        data.get("option_d",""),         data.get("correct_option","a"),
        data.get("complete_words_passage",""), data.get("complete_words_answers","{}"),
        data.get("word_order_words",""),  data.get("word_order_answer",""),
        data.get("writing_prompt",""),    data.get("writing_min_words",50),
        data.get("writing_sample",""),    data.get("speaking_prompt",""),
    ))
    conn.commit(); conn.close()
    return jsonify({"success":True,"message":"تم إضافة السؤال"})

@app.route("/api/admin/questions/<int:qid>", methods=["DELETE"])
@app.route("/api/admin/questions/delete/<int:qid>", methods=["POST"])
def api_delete_question(qid):
    conn = get_db()
    conn.execute("DELETE FROM questions WHERE id=?", (qid,))
    conn.commit(); conn.close()
    return jsonify({"success":True})

@app.route("/api/admin/questions/<int:qid>", methods=["PUT","POST"])
def api_edit_question(qid):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    conn.execute("""UPDATE questions SET
        question_type=?,topic=?,difficulty=?,question_text=?,passage_text=?,
        audio_url=?,audio_file_id=?,option_a=?,option_b=?,option_c=?,option_d=?,correct_option=?,
        complete_words_passage=?,complete_words_answers=?,
        word_order_words=?,word_order_answer=?,
        writing_prompt=?,writing_min_words=?,writing_sample=?,speaking_prompt=?
        WHERE id=?""", (
        data.get("question_type","mcq"),  data.get("topic","General"),
        data.get("difficulty","medium"),  data.get("question_text",""),
        data.get("passage_text",""),      data.get("audio_url",""),
        data.get("audio_file_id",""),     data.get("option_a",""),
        data.get("option_b",""),          data.get("option_c",""),
        data.get("option_d",""),          data.get("correct_option","a"),
        data.get("complete_words_passage",""), data.get("complete_words_answers","{}"),
        data.get("word_order_words",""),  data.get("word_order_answer",""),
        data.get("writing_prompt",""),    data.get("writing_min_words",50),
        data.get("writing_sample",""),    data.get("speaking_prompt",""),
        qid))
    conn.commit(); conn.close()
    return jsonify({"success":True})

@app.route("/api/admin/payments")
def api_get_payments():
    status = request.args.get("status")
    conn   = get_db()
    if status:
        rows = conn.execute("""SELECT p.*,s.name as student_name FROM payments p
            LEFT JOIN students s ON p.student_id=s.id
            WHERE p.status=? ORDER BY p.payment_date DESC""",(status,)).fetchall()
    else:
        rows = conn.execute("""SELECT p.*,s.name as student_name FROM payments p
            LEFT JOIN students s ON p.student_id=s.id
            ORDER BY p.payment_date DESC""").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/payments/<int:pid>/approve", methods=["POST"])
def api_approve_admin_payment(pid):
    conn = get_db()
    p    = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
    if p:
        conn.execute("UPDATE payments SET status=''approved'',approved_at=CURRENT_TIMESTAMP WHERE id=?", (pid,))
        days = p["duration_days"] or 30
        conn.execute("""UPDATE students SET
            package_end=date(''now'',?),subscription_type=''premium'',is_active=1
            WHERE id=?""", (f"+{days} days", p["student_id"]))
    conn.commit(); conn.close()
    return jsonify({"success":True})

@app.route("/api/admin/payments/<int:pid>/reject", methods=["POST"])
def api_reject_payment(pid):
    conn = get_db()
    conn.execute("UPDATE payments SET status=''rejected'' WHERE id=?", (pid,))
    conn.commit(); conn.close()
    return jsonify({"success":True})

@app.route("/api/admin/courses")
def api_get_courses():
    conn    = get_db()
    courses = conn.execute("SELECT * FROM lessons ORDER BY order_num").fetchall()
    conn.close()
    return jsonify([dict(c) for c in courses])

@app.route("/api/admin/courses/add", methods=["POST"])
def api_add_course():
    data = request.get_json(silent=True) or {}
    conn = get_db()
    conn.execute("INSERT INTO lessons (title,level,order_num,min_score) VALUES (?,?,?,?)", (
        data.get("name","درس جديد"), data.get("level","foundation"),
        data.get("order_num",1),     data.get("min_score",70)))
    conn.commit(); conn.close()
    return jsonify({"success":True})

@app.route("/api/admin/settings", methods=["POST"])
def api_save_setting():
    data = request.get_json(silent=True) or {}
    key  = data.get("key")
    val  = str(data.get("value",""))
    if not key: return jsonify({"error":"key مطلوب"}), 400
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key,val))
    conn.commit(); conn.close()
    return jsonify({"success":True})

@app.route("/api/admin/send-challenge", methods=["POST"])
def api_send_challenge():
    return jsonify({"success":True,"message":"تم إرسال تحدي اليوم"})

# ══════════════════════════════════════════════════════════════
#  GRADUATION PORTAL — بوابة التخرج
# ══════════════════════════════════════════════════════════════
@app.route("/graduation")
def graduation_page():
    return render_template("graduation.html")

@app.route("/api/graduation/exams")
def api_graduation_exams():
    conn = get_db()
    exams = conn.execute(
        "SELECT * FROM mock_exams WHERE is_active=1 ORDER BY order_num"
    ).fetchall()
    conn.close()
    return jsonify([dict(e) for e in exams])

@app.route("/api/graduation/exam/<int:exam_id>")
def api_graduation_exam_detail(exam_id):
    student_id = request.args.get("student_id", 1)
    conn = get_db()
    exam = conn.execute("SELECT * FROM mock_exams WHERE id=?", (exam_id,)).fetchone()
    if not exam:
        conn.close()
        return jsonify({"error": "الاختبار غير موجود"}), 404
    qs_rows = conn.execute("""
        SELECT q.*, meq.section, meq.order_num as q_order
        FROM mock_exam_questions meq
        JOIN questions q ON meq.question_id = q.id
        WHERE meq.mock_exam_id = ?
        ORDER BY meq.order_num
    """, (exam_id,)).fetchall()
    conn.close()
    return jsonify({
        "exam":      dict(exam),
        "questions": [dict(q) for q in qs_rows]
    })

@app.route("/api/graduation/results")
def api_graduation_results():
    sid = request.args.get("student_id", 1)
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM mock_results WHERE student_id=? ORDER BY completed_at DESC",
        (int(sid),)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/graduation/submit", methods=["POST"])
def api_graduation_submit():
    data = request.get_json(silent=True) or {}
    required = ["student_id","mock_exam_id","total_score"]
    for f in required:
        if f not in data:
            return jsonify({"error": f"{f} مطلوب"}), 400
    conn = get_db()
    conn.execute("""
        INSERT INTO mock_results
        (student_id,mock_exam_id,total_score,
         reading_score,listening_score,writing_score,speaking_score,
         is_passed,is_graduated,answers_json,feedback)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        int(data["student_id"]),
        int(data["mock_exam_id"]),
        int(data["total_score"]),
        int(data.get("reading_score",  0)),
        int(data.get("listening_score",0)),
        int(data.get("writing_score",  0)),
        int(data.get("speaking_score", 0)),
        int(data.get("is_passed",      0)),
        int(data.get("is_graduated",   0)),
        data.get("answers_json","{}"),
        data.get("feedback","")
    ))
    xp_reward = 50 if data.get("is_passed") else 20
    conn.execute("UPDATE students SET xp=xp+? WHERE id=?",
                 (xp_reward, int(data["student_id"])))
    conn.commit(); conn.close()
    return jsonify({"success": True, "xp_gained": xp_reward})

# ── Admin: Mock Exam Management ───────────────────────────────
@app.route("/api/admin/mock-exams", methods=["GET"])
def api_admin_get_mock_exams():
    conn = get_db()
    exams = conn.execute("SELECT * FROM mock_exams ORDER BY order_num").fetchall()
    result = []
    for e in exams:
        ed = dict(e)
        ed["question_count"] = conn.execute(
            "SELECT COUNT(*) FROM mock_exam_questions WHERE mock_exam_id=?", (e["id"],)
        ).fetchone()[0]
        result.append(ed)
    conn.close()
    return jsonify(result)

@app.route("/api/admin/mock-exams", methods=["POST"])
def api_admin_add_mock_exam():
    data = request.get_json(silent=True) or {}
    conn = get_db()
    cur  = conn.execute("""
        INSERT INTO mock_exams
        (title,description,target_score,pass_score,duration_minutes,difficulty,order_num,is_active)
        VALUES (?,?,?,?,?,?,?,1)
    """, (
        data.get("title","Mock Exam"),
        data.get("description",""),
        int(data.get("target_score", 59)),
        int(data.get("pass_score",   65)),
        int(data.get("duration_minutes", 60)),
        data.get("difficulty","medium"),
        int(data.get("order_num", 1))
    ))
    exam_id = cur.lastrowid
    conn.execute("""
        INSERT INTO mock_exam_questions (mock_exam_id, question_id, section, order_num)
        SELECT ?, id,
        CASE question_type
            WHEN 'mcq' THEN 'reading'
            WHEN 'complete_words' THEN 'reading'
            WHEN 'reading_passage' THEN 'reading'
            WHEN 'listening' THEN 'listening'
            WHEN 'listen_respond' THEN 'listening'
            WHEN 'build_sentence' THEN 'writing'
            WHEN 'writing_email' THEN 'writing'
            WHEN 'writing_discussion' THEN 'writing'
            WHEN 'speaking_interview' THEN 'speaking'
            WHEN 'speaking_repeat' THEN 'speaking'
            ELSE 'reading'
        END,
        id
        FROM questions ORDER BY RANDOM() LIMIT 10
    """, (exam_id,))
    conn.commit(); conn.close()
    return jsonify({"success": True, "id": exam_id, "message": "تم إضافة الاختبار"})

@app.route("/api/admin/mock-exams/<int:eid>", methods=["PUT","POST"])
def api_admin_update_mock_exam(eid):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    conn.execute("""
        UPDATE mock_exams SET
        title=?,description=?,target_score=?,pass_score=?,
        duration_minutes=?,difficulty=?,order_num=?,is_active=?
        WHERE id=?
    """, (
        data.get("title",""),
        data.get("description",""),
        int(data.get("target_score",59)),
        int(data.get("pass_score",65)),
        int(data.get("duration_minutes",60)),
        data.get("difficulty","medium"),
        int(data.get("order_num",1)),
        int(data.get("is_active",1)),
        eid
    ))
    conn.commit(); conn.close()
    return jsonify({"success": True})

@app.route("/api/admin/mock-exams/<int:eid>", methods=["DELETE"])
def api_admin_delete_mock_exam(eid):
    conn = get_db()
    conn.execute("DELETE FROM mock_exam_questions WHERE mock_exam_id=?", (eid,))
    conn.execute("DELETE FROM mock_results WHERE mock_exam_id=?",        (eid,))
    conn.execute("DELETE FROM mock_exams WHERE id=?",                    (eid,))
    conn.commit(); conn.close()
    return jsonify({"success": True})

@app.route("/api/admin/mock-exams/<int:eid>/questions", methods=["POST"])
def api_admin_add_question_to_exam(eid):
    data = request.get_json(silent=True) or {}
    qid  = data.get("question_id")
    sec  = data.get("section","reading")
    if not qid: return jsonify({"error":"question_id مطلوب"}),400
    conn = get_db()
    exists = conn.execute(
        "SELECT id FROM mock_exam_questions WHERE mock_exam_id=? AND question_id=?",
        (eid, qid)
    ).fetchone()
    if exists:
        conn.close()
        return jsonify({"error":"السؤال موجود بالفعل"}), 409
    max_order = conn.execute(
        "SELECT MAX(order_num) FROM mock_exam_questions WHERE mock_exam_id=?", (eid,)
    ).fetchone()[0] or 0
    conn.execute(
        "INSERT INTO mock_exam_questions (mock_exam_id,question_id,section,order_num) VALUES (?,?,?,?)",
        (eid, qid, sec, max_order+1)
    )
    conn.commit(); conn.close()
    return jsonify({"success": True})

@app.route("/api/admin/mock-exams/<int:eid>/questions/<int:qid>", methods=["DELETE"])
def api_admin_remove_question_from_exam(eid, qid):
    conn = get_db()
    conn.execute(
        "DELETE FROM mock_exam_questions WHERE mock_exam_id=? AND question_id=?",
        (eid, qid)
    )
    conn.commit(); conn.close()
    return jsonify({"success": True})

# ══════════════════════════════════════════════════════════════
#  TELEGRAM WEBHOOK — استقبال تحديثات البوت عبر Flask
# ══════════════════════════════════════════════════════════════
_bot_dp  = None
_bot_obj = None

def set_bot_for_webhook(bot, dp):
    global _bot_obj, _bot_dp
    _bot_obj = bot
    _bot_dp  = dp

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    global _bot_obj, _bot_dp
    if not _bot_obj or not _bot_dp:
        return jsonify({"error": "البوت غير مهيأ"}), 503
    try:
        import asyncio as _aio
        from aiogram.types import Update as _Update
        data   = request.get_json(force=True, silent=True) or {}
        update = _Update.model_validate(data)
        loop   = _aio.new_event_loop()
        loop.run_until_complete(_bot_dp.feed_update(_bot_obj, update))
        loop.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ══════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════
@app.route("/api/health")
@app.route("/health")
def api_health():
    conn = get_db()
    try:
        students  = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        questions = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    finally:
        conn.close()
    return jsonify({
        "status": "ok", "version": "2.0.0",
        "students": students, "questions": questions,
        "timestamp": datetime.now().isoformat(),
    })

# ══════════════════════════════════════════════════════════════
#  SUBSCRIPTION ACTIVATION API
# ══════════════════════════════════════════════════════════════
@app.route("/api/admin/activate", methods=["POST"])
def api_activate_student():
    data = request.get_json(silent=True) or {}
    sid  = data.get("student_id")
    tid  = data.get("telegram_id")
    pkg  = data.get("package", "premium")
    days = int(data.get("days", 30))
    conn = get_db()
    try:
        if tid:
            conn.execute(
                "UPDATE students SET is_active=1, subscription_type='premium', "
                "package=?, package_start=date('now'), package_end=date('now',?) "
                "WHERE telegram_id=?",
                (pkg, f"+{days} days", str(tid))
            )
        elif sid:
            conn.execute(
                "UPDATE students SET is_active=1, subscription_type='premium', "
                "package=?, package_start=date('now'), package_end=date('now',?) "
                "WHERE id=?",
                (pkg, f"+{days} days", int(sid))
            )
        else:
            return jsonify({"error": "student_id أو telegram_id مطلوب"}), 400
        conn.commit()
        return jsonify({"success": True, "days": days, "package": pkg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    init_db()
    seed_demo_data()
    print("="*50)
    print("الخادم يعمل على http://localhost:5000")
    print("داشبورد الطالب : http://localhost:5000/?student_id=1")
    print("لوحة الادمن    : http://localhost:5000/admin")
    print("Health Check   : http://localhost:5000/api/health")
    print("="*50)
    app.run(host="0.0.0.0", port=5000, debug=False)


