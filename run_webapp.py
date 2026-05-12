"""
Yamen Academy – WebApp + Admin Panel Server
Entry point: python run_webapp.py
"""
import os, sys, json, sqlite3, random
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ─── DB Setup ───
DB = os.getenv("DB_PATH", "data/academy.db")
os.makedirs("data", exist_ok=True)

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def query(sql, params=()):
    return get_conn().execute(sql, params).fetchall()

def execute(sql, params=()):
    conn = get_conn()
    conn.execute(sql, params)
    conn.commit()
    conn.close()

def dict_rows(rows):
    return [dict(r) for r in rows]

# ─── Flask App ───
app = Flask(__name__)
CORS(app)

# ─── WebApp: serve index.html at root ───
@app.route("/")
def webapp_index():
    return send_from_directory("webapp", "index.html")

# ─── Static files: try webapp/ first, then admin_panel/ ───
@app.route("/<path:filename>")
def serve_static(filename):
    import os as _os
    # WebApp files
    webapp_path = _os.path.join("webapp", filename)
    if _os.path.exists(webapp_path):
        return send_from_directory("webapp", filename)
    # Admin Panel files
    admin_path = _os.path.join("admin_panel", filename)
    if _os.path.exists(admin_path):
        return send_from_directory("admin_panel", filename)
    return jsonify({"error": "file not found"}), 404

# ─── Admin Panel ───
@app.route("/admin")
def admin_index():
    return send_from_directory("admin_panel", "index.html")

@app.route("/admin/<path:filename>")
def admin_static(filename):
    return send_from_directory("admin_panel", filename)

# ─── API: Health ───
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "app": "yamen-academy"})

# ─── API: Student ───
@app.route("/api/me")
def me():
    uid = request.args.get("user_id")
    if not uid: return jsonify({"error": "user_id required"}), 400
    row = query("SELECT * FROM students WHERE user_id=?", (uid,))
    return jsonify(dict(row[0]) if row else {"error": "not found"})

# ─── API: Courses ───
@app.route("/api/courses")
def courses():
    level = request.args.get("level", "")
    if level:
        rows = query("SELECT * FROM courses WHERE level=? ORDER BY id", (level,))
    else:
        rows = query("SELECT * FROM courses ORDER BY id")
    return jsonify(dict_rows(rows))

# ─── API: Lessons ───
@app.route("/api/lessons")
def lessons():
    cid = request.args.get("course_id")
    rows = query("SELECT * FROM lessons WHERE course_id=? ORDER BY order_num", (cid,))
    return jsonify(dict_rows(rows))

# ─── API: Placement Questions ───
@app.route("/api/placement/questions")
def placement_questions():
    rows = query("SELECT * FROM placement_questions ORDER BY id")
    return jsonify(dict_rows(rows))

# ─── API: Spelling Words ───
@app.route("/api/spelling/words")
def spelling_words():
    level = request.args.get("level", "")
    if level:
        rows = query("SELECT * FROM spelling_words WHERE level=? ORDER BY id", (level,))
    else:
        rows = query("SELECT * FROM spelling_words ORDER BY id")
    return jsonify(dict_rows(rows))

# ─── API: Daily Challenge ───
@app.route("/api/daily/challenge")
def daily_challenge():
    today = __import__("datetime").date.today().isoformat()
    row = query("SELECT * FROM daily_challenges WHERE date=? ORDER BY id DESC LIMIT 1", (today,))
    if not row:
        row = query("SELECT * FROM daily_challenges ORDER BY id DESC LIMIT 1")
    return jsonify(dict(row[0]) if row else {"error": "no challenge"})

# ─── API: Leaderboard ───
@app.route("/api/leaderboard")
def leaderboard():
    rows = query("SELECT user_id, full_name, level, xp FROM students ORDER BY xp DESC LIMIT 20")
    return jsonify(dict_rows(rows))

# ─── API: Student Progress ───
@app.route("/api/progress")
def progress():
    uid = request.args.get("user_id")
    if not uid: return jsonify({"error": "user_id required"}), 400
    student = query("SELECT * FROM students WHERE user_id=?", (uid,))
    if not student: return jsonify({"error": "not found"}), 404
    s = dict(student[0])
    quiz_count = query("SELECT COUNT(*) as c FROM quiz_attempts WHERE user_id=?", (uid,))[0]["c"]
    writing_count = query("SELECT COUNT(*) as c FROM writing_submissions WHERE user_id=?", (uid,))[0]["c"]
    speaking_count = query("SELECT COUNT(*) as c FROM speaking_sessions WHERE user_id=?", (uid,))[0]["c"]
    word_count = query("SELECT COUNT(*) as c FROM word_reviews WHERE user_id=?", (uid,))[0]["c"]
    return jsonify({
        "student": s,
        "stats": {
            "quizzes": quiz_count,
            "writing": writing_count,
            "speaking": speaking_count,
            "words_practiced": word_count
        }
    })

# ─── API: Writing Evaluation ───
WRITING_KEYS = os.getenv("WRITING_KEYS", "").split(",")
MODEL = "gemini-2.5-flash"

@app.route("/api/writing/evaluate", methods=["POST"])
def evaluate_writing():
    data = request.get_json(force=True)
    essay = data.get("essay", "")
    task_type = data.get("task_type", "task2")
    prompt = data.get("prompt", "")
    user_id = data.get("user_id")

    if len(essay.split()) < 50:
        return jsonify({"error": "Essay too short (minimum 50 words)"}), 400

    if not WRITING_KEYS or not WRITING_KEYS[0]:
        return jsonify({"error": "AI keys not configured"}), 500

    key = random.choice(WRITING_KEYS)
    system = """You are an IELTS examiner. Score this essay on:
Task Achievement, Coherence & Cohesion, Lexical Resource, Grammatical Range & Accuracy.
Reply ONLY in JSON: {"overall":6.5,"task_response":6,"coherence_cohesion":7,"lexical_resource":6.5,"grammatical_range":6.5,"feedback_ar":"detailed Arabic feedback","corrections":[]}"""

    url = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent?key=" + key
    body = {"contents":[{"parts":[{"text":system},{"text":"Task: "+task_type+"\nPrompt: "+prompt+"\nESSAY:\n\n"+essay}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":2048}}

    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = json.loads(resp.read())["candidates"][0]["content"]["parts"][0]["text"]
            raw = raw.strip().lstrip("```json").rstrip("```").strip()
            result = json.loads(raw)
            result.setdefault("overall", 6.0)
            result.setdefault("feedback_ar", "تم التقييم.")
            if user_id:
                execute("""INSERT INTO writing_submissions
                    (user_id,task_type,prompt,essay_text,word_count,band_score,task_response,coherence_cohesion,lexical_resource,grammatical_range,feedback_ar,corrections_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (int(user_id), task_type, prompt, essay, len(essay.split()),
                     result["overall"], result.get("task_response",6), result.get("coherence_cohesion",6),
                     result.get("lexical_resource",6), result.get("grammatical_range",6),
                     result["feedback_ar"], json.dumps(result.get("corrections",[]))))
            return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── API: Speaking Evaluation ───
SPEAKING_KEYS = os.getenv("SPEAKING_KEYS", "").split(",")

@app.route("/api/speaking/evaluate", methods=["POST"])
def evaluate_speaking():
    data = request.get_json(force=True)
    audio_b64 = data.get("audio_base64", "")
    prompt = data.get("prompt", "")
    part = data.get("part", "part1")
    duration = data.get("duration", 30)
    user_id = data.get("user_id")

    if not SPEAKING_KEYS or not SPEAKING_KEYS[0]:
        return jsonify({"error": "AI keys not configured"}), 500

    key = random.choice(SPEAKING_KEYS)
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent?key=" + key
    body = {"contents":[{"parts":[{"text":"IELTS Speaking "+part+". Prompt: "+prompt+". Duration: "+str(duration)+"s. Score on Fluency, Pronunciation, Lexical Resource, Grammar. Reply JSON: {\"overall\":6.5,\"fluency\":6,\"pronunciation\":7,\"lexical_resource\":6.5,\"grammatical_range\":6,\"feedback_ar\":\"...\",\"transcript\":\"...\"}"},{"inline_data":{"mime_type":"audio/ogg","data":audio_b64}}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":2048}}

    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = json.loads(resp.read())["candidates"][0]["content"]["parts"][0]["text"]
            raw = raw.strip().lstrip("```json").rstrip("```").strip()
            result = json.loads(raw)
            result.setdefault("overall", 6.0)
            result.setdefault("feedback_ar", "تم التقييم.")
            if user_id:
                execute("""INSERT INTO speaking_sessions
                    (user_id,prompt,transcript_text,audio_duration_sec,band_score,fluency,pronunciation,lexical_resource,grammatical_range,feedback_ar)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (int(user_id), prompt, result.get("transcript",""), duration,
                     result["overall"], result.get("fluency",6), result.get("pronunciation",6),
                     result.get("lexical_resource",6), result.get("grammatical_range",6),
                     result["feedback_ar"]))
            return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Admin API ───
@app.route("/api/admin/stats", methods=["GET", "POST"])
def admin_stats():
    students = query("SELECT COUNT(*) as n FROM students")[0]["n"]
    active = query("SELECT COUNT(*) as n FROM subscriptions WHERE active=1")[0]["n"]
    pending = query("SELECT COUNT(*) as n FROM payments WHERE status='pending'")[0]["n"]
    total_xp = query("SELECT COALESCE(SUM(xp),0) as n FROM students")[0]["n"]
    return jsonify({"total_students": students, "active_subs": active, "pending_payments": pending, "total_xp": total_xp})

@app.route("/api/admin/students", methods=["GET", "POST"])
def admin_students():
    rows = query("SELECT * FROM students ORDER BY created_at DESC")
    return jsonify({"students": dict_rows(rows)})

@app.route("/api/admin/payments", methods=["GET", "POST"])
def admin_payments():
    flt = request.json.get("filter", "pending") if request.method == "POST" else "pending"
    rows = query("SELECT * FROM payments WHERE status=? ORDER BY created_at DESC LIMIT 50", (flt,))
    return jsonify({"payments": dict_rows(rows)})

@app.route("/api/admin/approve_payment", methods=["POST"])
def admin_approve():
    data = request.get_json(force=True)
    pid = data["id"]
    execute("UPDATE payments SET status='approved' WHERE id=?", (pid,))
    p = query("SELECT * FROM payments WHERE id=?", (pid,))
    if p:
        p = dict(p[0])
        days = 30
        name = p.get("plan_name", "")
        if "VIP" in name: days = 60
        elif "Excellence" in name: days = 90
        execute("INSERT INTO subscriptions (user_id,plan_name,start_date,end_date,active) VALUES (?,?,datetime('now'),datetime('now','+"+str(days)+" days'),1)",
                (p["user_id"], name))
    return jsonify({"success": True})

@app.route("/api/admin/reject_payment", methods=["POST"])
def admin_reject():
    execute("UPDATE payments SET status='rejected' WHERE id=?", (request.json["id"],))
    return jsonify({"success": True})

# ─── Admin: Courses ───
@app.route("/api/admin/courses", methods=["GET", "POST"])
def admin_courses():
    rows = query("SELECT * FROM courses ORDER BY id")
    return jsonify({"courses": dict_rows(rows)})

@app.route("/api/admin/add_course", methods=["POST"])
def admin_add_course():
    d = request.json
    execute("INSERT INTO courses (name,level,description) VALUES (?,?,?)",
            (d["name"], d.get("level","A1"), d.get("description","")))
    return jsonify({"success": True})

@app.route("/api/admin/delete_course", methods=["POST"])
def admin_delete_course():
    execute("DELETE FROM courses WHERE id=?", (request.json["id"],))
    return jsonify({"success": True})

# ─── Admin: Settings ───
@app.route("/api/admin/settings", methods=["GET", "POST"])
def admin_settings():
    rows = query("SELECT * FROM admin_settings")
    settings = {r["key"]: r["value"] for r in rows}
    return jsonify(settings)

@app.route("/api/admin/save_setting", methods=["POST"])
def admin_save_setting():
    d = request.json
    execute("INSERT OR REPLACE INTO admin_settings (key, value) VALUES (?, ?)", (d["key"], str(d["value"])))
    return jsonify({"success": True})

# ─── Run ───
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Yamen Academy WebApp starting on port {port}")
    app.run(host="0.0.0.0", port=port)
