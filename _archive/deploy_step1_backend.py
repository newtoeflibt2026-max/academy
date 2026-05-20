import re, os

APP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
with open(APP_PATH, "r", encoding="utf-8") as f:
    code = f.read()

old_content = """@app.route("/api/admin/content/create", methods=["POST"])
def admin_create_content():
    return jsonify(create_lesson_from_admin(request.json))

@app.route("/api/admin/content/update", methods=["POST"])
def admin_update_content():
    return jsonify(update_lesson_from_admin(request.json))

@app.route("/api/admin/content/delete", methods=["POST"])
def admin_delete_content():
    return jsonify(delete_lesson_from_admin(request.json.get("lesson_id")))"""

if old_content in code:
    code = code.replace(old_content, "")

NEW_BLOCK = """

import sqlite3

def _db():
    conn = sqlite3.connect("data/yamen_academy.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/api/admin/content/create", methods=["POST"])
def admin_create_content():
    try:
        payload = request.get_json(force=True)
        result = create_lesson_from_admin(payload)
        return jsonify(result), 200 if result.get("status") == "ok" else 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/admin/content/update", methods=["POST"])
def admin_update_content():
    try:
        payload = request.get_json(force=True)
        result = update_lesson_from_admin(payload)
        return jsonify(result), 200 if result.get("status") == "ok" else 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/admin/content/delete", methods=["POST"])
def admin_delete_content():
    try:
        payload = request.get_json(force=True)
        lesson_id = payload.get("lesson_id")
        result = delete_lesson_from_admin(lesson_id)
        return jsonify(result), 200 if result.get("status") == "ok" else 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/admin/questions", methods=["GET"])
def admin_list_questions():
    try:
        conn = _db()
        rows = conn.execute("SELECT * FROM questions ORDER BY skill, id").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/questions/add", methods=["POST"])
def admin_add_question():
    try:
        data = request.get_json(force=True)
        required = ["skill", "question", "option_a", "option_b", "option_c", "option_d", "correct_answer"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400
        conn = _db()
        conn.execute(
            "INSERT INTO questions (skill,question,option_a,option_b,option_c,option_d,correct_answer,difficulty) VALUES (?,?,?,?,?,?,?,?)",
            (data["skill"], data["question"], data["option_a"], data["option_b"], data["option_c"], data["option_d"], data["correct_answer"].strip().upper(), data.get("difficulty", "beginner")),
        )
        conn.commit()
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return jsonify({"status": "ok", "id": new_id, "message": "Question added"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/questions/edit/<int:qid>", methods=["POST"])
def admin_edit_question(qid):
    try:
        data = request.get_json(force=True)
        fields, values = [], []
        for key in ["skill","question","option_a","option_b","option_c","option_d","correct_answer","difficulty"]:
            if key in data:
                fields.append(f"{key}=?")
                values.append(data[key])
        if not fields:
            return jsonify({"error": "No fields to update"}), 400
        fields.append("updated_at=datetime('now','localtime')")
        values.append(qid)
        conn = _db()
        conn.execute(f"UPDATE questions SET {','.join(fields)} WHERE id=?", values)
        conn.commit(); conn.close()
        return jsonify({"status": "ok", "message": f"Question {qid} updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/questions/delete/<int:qid>", methods=["POST"])
def admin_delete_question(qid):
    try:
        conn = _db()
        conn.execute("DELETE FROM questions WHERE id=?", (qid,))
        conn.commit(); conn.close()
        return jsonify({"status": "ok", "message": f"Question {qid} deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/placement/submit", methods=["POST"])
def placement_submit():
    try:
        data = request.get_json(force=True)
        student_id = data.get("student_id", session.get("student_id", 1))
        answers = data.get("answers", [])
        if not answers:
            return jsonify({"error": "No answers provided"}), 400
        total = len(answers)
        correct = 0
        conn = _db()
        for item in answers:
            qid = item.get("question_id")
            user_ans = item.get("answer", "").strip().upper()
            row = conn.execute("SELECT correct_answer FROM questions WHERE id=?", (qid,)).fetchone()
            if row and row["correct_answer"].strip().upper() == user_ans:
                correct += 1
        score_pct = round((correct / total) * 100, 1) if total > 0 else 0
        if score_pct < 50:
            band, level, label, path = "A1-A2", "beginner", "Weak", "foundations"
        elif score_pct <= 75:
            band, level, label, path = "B1-B2", "intermediate", "Intermediate", "core"
        else:
            band, level, label, path = "C1-C2", "advanced", "Advanced", "mastery"
        conn.execute("INSERT INTO placement_results (student_id,band,level,path,score_pct) VALUES (?,?,?,?,?)", (student_id,band,level,path,score_pct))
        try:
            conn.execute("UPDATE users SET level=? WHERE id=?", (level, student_id))
        except:
            pass
        conn.commit(); conn.close()
        session["student_id"] = student_id
        session["placement_level"] = level
        return jsonify({"status":"ok","score":score_pct,"correct":correct,"total":total,"band":band,"level":level,"label":label,"path":path,"message":f"Score: {score_pct}% - Level: {label} ({band})"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/placement/questions", methods=["GET"])
def placement_questions():
    try:
        conn = _db()
        rows = conn.execute("SELECT id, skill, question, option_a, option_b, option_c, option_d, difficulty FROM questions ORDER BY RANDOM()").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

"""

insert_before = 'if __name__ == "__main__":'
if insert_before in code:
    code = code.replace(insert_before, NEW_BLOCK + "\n" + insert_before)
    print("Backend injected into app.py!")
else:
    code += "\n" + NEW_BLOCK
    print("Backend appended to app.py!")

with open(APP_PATH, "w", encoding="utf-8") as f:
    f.write(code)
print("DONE - deploy_step1_backend.py complete")
