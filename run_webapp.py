"""
Yamen Academy – WebApp + Admin Panel Server
"""
import os, sys, json, sqlite3, random
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

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

app = Flask(__name__, static_folder=None)
CORS(app)

# ─── SERVE ALL STATIC FILES FROM ROOT ───
STATIC_MAP = {}

def build_static_map():
    """Build a map of filename -> folder for all files in webapp/ and admin_panel/"""
    for folder in ["webapp", "admin_panel"]:
        if not os.path.exists(folder):
            continue
        for root, dirs, files in os.walk(folder):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), folder)
                STATIC_MAP[f] = (folder, rel)

build_static_map()

@app.route("/")
def webapp_index():
    return send_from_directory("webapp", "index.html")

@app.route("/admin")
def admin_index():
    return send_from_directory("admin_panel", "index.html")

@app.route("/<path:filename>")
def catch_all(filename):
    # Skip API routes
    if filename.startswith("api/"):
        return jsonify({"error": "not found"}), 404
    
    fname = os.path.basename(filename)
    if fname in STATIC_MAP:
        folder, rel = STATIC_MAP[fname]
        return send_from_directory(folder, rel)
    
    return jsonify({"error": "file not found", "path": filename}), 404

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
    rows = query("SELECT * FROM courses WHERE level=? ORDER BY id", (level,)) if level else query("SELECT * FROM courses ORDER BY id")
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
    return jsonify(dict_rows(query("SELECT * FROM placement_questions ORDER BY id")))

# ─── API: Spelling Words ───
@app.route("/api/spelling/words")
def spelling_words():
    level = request.args.get("level", "")
    rows = query("SELECT * FROM spelling_words WHERE level=? ORDER BY id", (level,)) if level else query("SELECT * FROM spelling_words ORDER BY id")
    return jsonify(dict_rows(rows))

# ─── API: Daily Challenge ───
@app.route("/api/daily/challenge")
def daily_challenge():
    today = __import__("datetime").date.today().isoformat()
    row = query("SELECT * FROM daily_challenges WHERE date=? ORDER BY id DESC LIMIT 1", (today,))
    if not row: row = query("SELECT * FROM daily_challenges ORDER BY id DESC LIMIT 1")
    return jsonify(dict(row[0]) if row else {"error": "no challenge"})

# ─── API: Leaderboard ───
@app.route("/api/leaderboard")
def leaderboard():
    return jsonify(dict_rows(query("SELECT user_id, full_name, level, xp FROM students ORDER BY xp DESC LIMIT 20")))

# ─── API: Student Progress ───
@app.route("/api/progress")
def progress():
    uid = request.args.get("user_id")
    if not uid: return jsonify({"error": "user_id required"}), 400
    student = query("SELECT * FROM students WHERE user_id=?", (uid,))
    if not student: return jsonify({"error": "not found"}), 404
    s = dict(student[0])
    return jsonify({"student": s, "stats": {
        "quizzes": query("SELECT COUNT(*) as c FROM quiz_attempts WHERE user_id=?", (uid,))[0]["c"],
        "writing": query("SELECT COUNT(*) as c FROM writing_submissions WHERE user_id=?", (uid,))[0]["c"],
        "speaking": query("SELECT COUNT(*) as c FROM speaking_sessions WHERE user_id=?", (uid,))[0]["c"],
        "words_practiced": query("SELECT COUNT(*) as c FROM word_reviews WHERE user_id=?", (uid,))[0]["c"]
    }})

# ─── API: Writing Evaluation ───
WRITING_KEYS = os.getenv("WRITING_KEYS", "").split(",")
SPEAKING_KEYS = os.getenv("SPEAKING_KEYS", "").split(",")
MODEL = "gemini-2.5-flash"

@app.route("/api/writing/evaluate", methods=["POST"])
def evaluate_writing():
    data = request.get_json(force=True)
    essay = data.get("essay", "")
    if len(essay.split()) < 50: return jsonify({"error": "Essay too short"}), 400
    if not WRITING_KEYS or not WRITING_KEYS[0]: return jsonify({"error": "AI keys not configured"}), 500
    key = random.choice(WRITING_KEYS)
    system = 'You are an IELTS examiner. Reply ONLY in JSON: {"overall":6.5,"task_response":6,"coherence_cohesion":7,"lexical_resource":6.5,"grammatical_range":6.5,"feedback_ar":"Arabic feedback","corrections":[]}'
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}"
    body = {"contents":[{"parts":[{"text":system},{"text":f"Task: {data.get('task_type','task2')}\nPrompt: {data.get('prompt','')}\nESSAY:\n\n{essay}"}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":2048}}
    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = json.loads(resp.read())["candidates"][0]["content"]["parts"][0]["text"]
            raw = raw.strip().lstrip("```json").rstrip("```").strip()
            result = json.loads(raw)
            result.setdefault("overall", 6.0)
            result.setdefault("feedback_ar", "تم التقييم.")
            uid = data.get("user_id")
            if uid:
                execute("INSERT INTO writing_submissions (user_id,task_type,prompt,essay_text,word_count,band_score,task_response,coherence_cohesion,lexical_resource,grammatical_range,feedback_ar,corrections_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (int(uid), data.get("task_type","task2"), data.get("prompt",""), essay, len(essay.split()), result["overall"], result.get("task_response",6), result.get("coherence_cohesion",6), result.get("lexical_resource",6), result.get("grammatical_range",6), result["feedback_ar"], json.dumps(result.get("corrections",[]))))
            return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── API: Speaking Evaluation ───
@app.route("/api/speaking/evaluate", methods=["POST"])
def evaluate_speaking():
    data = request.get_json(force=True)
    if not SPEAKING_KEYS or not SPEAKING_KEYS[0]: return jsonify({"error": "AI keys not configured"}), 500
    key = random.choice(SPEAKING_KEYS)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}"
    body = {"contents":[{"parts":[{"text":f"IELTS Speaking {data.get('part','part1')}. Prompt: {data.get('prompt','')}. Duration: {data.get('duration',30)}s. Score on Fluency, Pronunciation, Lexical Resource, Grammar. Reply JSON: {{\"overall\":6.5,\"fluency\":6,\"pronunciation\":7,\"lexical_resource\":6.5,\"grammatical_range\":6,\"feedback_ar\":\"...\",\"transcript\":\"...\"}}"},{"inline_data":{"mime_type":"audio/ogg","data":data.get("audio_base64","")}}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":2048}}
    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = json.loads(resp.read())["candidates"][0]["content"]["parts"][0]["text"]
            raw = raw.strip().lstrip("```json").rstrip("```").strip()
            result = json.loads(raw)
            result.setdefault("overall", 6.0)
            result.setdefault("feedback_ar", "تم التقييم.")
            uid = data.get("user_id")
            if uid:
                execute("INSERT INTO speaking_sessions (user_id,prompt,transcript_text,audio_duration_sec,band_score,fluency,pronunciation,lexical_resource,grammatical_range,feedback_ar) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (int(uid), data.get("prompt",""), result.get("transcript",""), data.get("duration",30), result["overall"], result.get("fluency",6), result.get("pronunciation",6), result.get("lexical_resource",6), result.get("grammatical_range",6), result["feedback_ar"]))
            return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Admin API ───
@app.route("/api/admin/stats", methods=["GET", "POST"])
def admin_stats():
    return jsonify({"total_students": query("SELECT COUNT(*) as n FROM students")[0]["n"], "active_subs": query("SELECT COUNT(*) as n FROM subscriptions WHERE active=1")[0]["n"], "pending_payments": query("SELECT COUNT(*) as n FROM payments WHERE status='pending'")[0]["n"], "total_xp": query("SELECT COALESCE(SUM(xp),0) as n FROM students")[0]["n"]})

@app.route("/api/admin/students", methods=["GET", "POST"])
def admin_students():
    return jsonify({"students": dict_rows(query("SELECT * FROM students ORDER BY created_at DESC"))})

@app.route("/api/admin/payments", methods=["GET", "POST"])
def admin_payments():
    flt = request.json.get("filter", "pending") if request.method == "POST" else "pending"
    return jsonify({"payments": dict_rows(query("SELECT * FROM payments WHERE status=? ORDER BY created_at DESC LIMIT 50", (flt,)))})

@app.route("/api/admin/approve_payment", methods=["POST"])
def admin_approve():
    data = request.get_json(force=True)
    execute("UPDATE payments SET status='approved' WHERE id=?", (data["id"],))
    p = query("SELECT * FROM payments WHERE id=?", (data["id"],))
    if p:
        p = dict(p[0])
        days = 90 if "Excellence" in p.get("plan_name","") else (60 if "VIP" in p.get("plan_name","") else 30)
        execute(f"INSERT INTO subscriptions (user_id,plan_name,start_date,end_date,active) VALUES (?,?,datetime('now'),datetime('now','+{days} days'),1)", (p["user_id"], p.get("plan_name","")))
    return jsonify({"success": True})

@app.route("/api/admin/reject_payment", methods=["POST"])
def admin_reject():
    execute("UPDATE payments SET status='rejected' WHERE id=?", (request.json["id"],))
    return jsonify({"success": True})

@app.route("/api/admin/courses", methods=["GET", "POST"])
def admin_courses():
    return jsonify({"courses": dict_rows(query("SELECT * FROM courses ORDER BY id"))})

@app.route("/api/admin/add_course", methods=["POST"])
def admin_add_course():
    d = request.json
    execute("INSERT INTO courses (name,level,description) VALUES (?,?,?)", (d["name"], d.get("level","A1"), d.get("description","")))
    return jsonify({"success": True})

@app.route("/api/admin/delete_course", methods=["POST"])
def admin_delete_course():
    execute("DELETE FROM courses WHERE id=?", (request.json["id"],))
    return jsonify({"success": True})

@app.route("/api/admin/settings", methods=["GET", "POST"])
def admin_settings():
    return jsonify({r["key"]: r["value"] for r in query("SELECT * FROM admin_settings")})

@app.route("/api/admin/save_setting", methods=["POST"])
def admin_save_setting():
    d = request.json
    execute("INSERT OR REPLACE INTO admin_settings (key, value) VALUES (?, ?)", (d["key"], str(d["value"])))
    return jsonify({"success": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Yamen Academy WebApp starting on port {port}")
    app.run(host="0.0.0.0", port=port)