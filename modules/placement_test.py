"""
placement_test.py v17.0 — محرك امتحان تحديد المستوى
- MCQ فقط لضمان دقة التصحيح
- مؤقت تنازلي (Time-Limited)
- تصحيح فوري وتصنيف (مبتدئ/متوسط/متقدم)
- قفل Dashboard حتى إنهاء الامتحان
"""
from flask import Blueprint, jsonify, request, render_template
from modules.models import query_db, execute_db
import random

placement_bp = Blueprint("placement", __name__, url_prefix="/placement")

@placement_bp.route("/")
def placement_page():
    """صفحة امتحان المستوى"""
    return render_template("placement.html")

@placement_bp.route("/api/questions")
def api_placement_questions():
    """جلب 10 أسئلة عشوائية لامتحان المستوى"""
    rows = query_db("SELECT * FROM placement_questions WHERE is_active=1 ORDER BY RANDOM() LIMIT 10")
    if not rows:
        # أسئلة احتياطية
        return jsonify({"questions": [
            {"id":0,"question_text":"What is the synonym of 'rapid'?","option_a":"Slow","option_b":"Fast","option_c":"Heavy","option_d":"Bright","time_limit_seconds":45},
            {"id":0,"question_text":"Choose correct: He ___ to school","option_a":"go","option_b":"goes","option_c":"going","option_d":"gone","time_limit_seconds":45},
            {"id":0,"question_text":"The word 'ubiquitous' means:","option_a":"Rare","option_b":"Everywhere","option_c":"Underground","option_d":"Unique","time_limit_seconds":60},
            {"id":0,"question_text":"What is TOEFL for?","option_a":"Math","option_b":"English proficiency","option_c":"Science","option_d":"History","time_limit_seconds":30},
            {"id":0,"question_text":"'To kill two birds' means:","option_a":"Be cruel","option_b":"Achieve two things","option_c":"Fail","option_d":"Hunt","time_limit_seconds":45},
        ], "total_time": 600})

    questions = []
    for r in rows:
        questions.append({
            "id": r["id"],
            "question_text": r["question_text"],
            "option_a": r["option_a"],
            "option_b": r["option_b"],
            "option_c": r["option_c"],
            "option_d": r["option_d"],
            "time_limit_seconds": r["time_limit_seconds"],
        })

    return jsonify({"questions": questions, "total_time": 600})

@placement_bp.route("/api/submit", methods=["POST"])
def api_placement_submit():
    """
    استقبال إجابات الطالب وتصحيحها فورياً
    body: {user_id, answers: [{question_id, selected_option}]}
    """
    d = request.get_json()
    user_id = d.get("user_id")
    answers = d.get("answers", [])

    if not user_id:
        return jsonify({"error": "معرف الطالب مطلوب"}), 400

    # تصحيح الإجابات
    total = len(answers)
    correct = 0
    skill_scores = {}

    for ans in answers:
        qid = ans.get("question_id")
        selected = ans.get("selected_option", "").strip().upper()

        row = query_db("SELECT correct_option, skill_area, difficulty FROM placement_questions WHERE id=?", (qid,), one=True)
        if row:
            is_correct = (selected == row["correct_option"].strip().upper())
            if is_correct:
                correct += 1

            area = row["skill_area"] or "general"
            if area not in skill_scores:
                skill_scores[area] = {"correct": 0, "total": 0}
            skill_scores[area]["total"] += 1
            if is_correct:
                skill_scores[area]["correct"] += 1

    score_percent = round((correct / total) * 100, 1) if total > 0 else 0

    # تصنيف المستوى
    if score_percent >= 80:
        level = "متقدم Advanced"
    elif score_percent >= 50:
        level = "متوسط Intermediate"
    else:
        level = "مبتدئ Beginner"

    # حفظ النتيجة
    execute_db(
        """INSERT INTO placement_results (user_id, total_questions, correct_count, score_percent, level, skill_breakdown)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, total, correct, score_percent, level, str(skill_scores)))

    # تحديث الطالب
    execute_db(
        "UPDATE students SET placement_done=1, placement_level=?, level=?, xp=COALESCE(xp,0)+?, last_active=CURRENT_TIMESTAMP WHERE telegram_id=?",
        (level, {"متقدم Advanced": 3, "متوسط Intermediate": 2, "مبتدئ Beginner": 1}.get(level, 1),
         correct * 5, user_id))

    # تسجيل نشاط
    execute_db(
        "INSERT INTO activity_log (user_id, action, details, xp_change) VALUES (?,?,?,?)",
        (user_id, "placement_complete", f"Level: {level} | Score: {score_percent}%", correct * 5))

    return jsonify({
        "success": True,
        "total": total,
        "correct": correct,
        "score_percent": score_percent,
        "level": level,
        "level_number": {"متقدم Advanced": 3, "متوسط Intermediate": 2, "مبتدئ Beginner": 1}.get(level, 1),
        "xp_earned": correct * 5,
        "skill_breakdown": skill_scores
    })

@placement_bp.route("/api/status/<int:user_id>")
def api_placement_status(user_id):
    """هل أنهى الطالب امتحان المستوى؟"""
    row = query_db("SELECT placement_done, placement_level FROM students WHERE telegram_id=?", (user_id,), one=True)
    if row:
        return jsonify({
            "placement_done": bool(row["placement_done"]),
            "level": row["placement_level"]
        })
    return jsonify({"placement_done": False, "level": None})
