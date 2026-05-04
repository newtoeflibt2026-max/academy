"""
Yamen Academy – Flask API Server
"""
import os, json, sqlite3, asyncio, aiohttp, base64, random
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="webapp", static_url_path="")
CORS(app)

DB = "data/academy.db"
os.makedirs("data", exist_ok=True)

WRITING_KEYS = ['AIzaSyDkAuMCa9rBQGiFkqxIauUCL7eXQyP2aHw', 'AIzaSyDGRbeskDR64jlDFkC5UzSdfleMp_sUwKc', 'AIzaSyDFU5MAO20Hssq6SWS-F0TGGint3IZHcTU']
SPEAKING_KEYS = ['AIzaSyCBFNExYp5-9yFjHFrnaqUS-yZn_YqigSY', 'AIzaSyAXGja3hvzIo2SyTTQcuKBNa-yHZghHu8M', 'AIzaSyBWj39r49ORhKEpoDLhk6bpPiJLGrmohW0']
MODEL = "gemini-2.5-flash"

# ── DB Helpers ──
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

# ── Health ──
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

# ── Student ──
@app.route("/api/me")
def me():
    uid = request.args.get("user_id")
    if not uid: return jsonify({"error": "user_id required"}), 400
    row = query("SELECT * FROM students WHERE user_id=?", (uid,))
    return jsonify(dict(row[0]) if row else {"error": "not found"})

# ── Courses ──
@app.route("/api/courses")
def courses():
    uid = request.args.get("user_id")
    level = request.args.get("level", "")
    if level:
        rows = query("SELECT * FROM courses WHERE level=? ORDER BY id", (level,))
    else:
        rows = query("SELECT * FROM courses ORDER BY id")
    return jsonify(dict_rows(rows))

# ── Lessons ──
@app.route("/api/lessons")
def lessons():
    cid = request.args.get("course_id")
    rows = query("SELECT * FROM lessons WHERE course_id=? ORDER BY id", (cid,))
    return jsonify(dict_rows(rows))

# ── AI Writing ──
@app.route("/api/writing/evaluate", methods=["POST"])
def evaluate_writing():
    data = request.get_json(force=True)
    essay = data.get("essay", "")
    task_type = data.get("task_type", "task2")
    prompt = data.get("prompt", "")
    user_id = data.get("user_id")

    if len(essay.split()) < 150:
        return jsonify({"error": "Essay too short"}), 400

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

# ── AI Speaking ──
@app.route("/api/speaking/evaluate", methods=["POST"])
def evaluate_speaking():
    data = request.get_json(force=True)
    audio_b64 = data.get("audio_base64", "")
    prompt = data.get("prompt", "")
    part = data.get("part", "part1")
    duration = data.get("duration", 30)
    user_id = data.get("user_id")

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

# ── Admin ──
@app.route("/api/admin/stats")
def admin_stats():
    students = query("SELECT COUNT(*) as n FROM students")[0]["n"]
    active = query("SELECT COUNT(*) as n FROM subscriptions WHERE active=1")[0]["n"]
    pending = query("SELECT COUNT(*) as n FROM payments WHERE status='pending'")[0]["n"]
    return jsonify({"students": students, "active_subs": active, "pending_payments": pending})

@app.route("/api/admin/payments")
def admin_payments():
    rows = query("SELECT * FROM payments ORDER BY created_at DESC LIMIT 50")
    return jsonify(dict_rows(rows))

@app.route("/api/admin/approve", methods=["POST"])
def admin_approve():
    data = request.get_json(force=True)
    pid = data["payment_id"]
    execute("UPDATE payments SET status='approved' WHERE id=?", (pid,))
    p = query("SELECT * FROM payments WHERE id=?", (pid,))
    if p:
        p = dict(p[0])
        execute("INSERT INTO subscriptions (user_id,plan_name,course_id,start_date,end_date,active) VALUES (?,?,?,date('now'),date('now','+30 days'),1)",
                (p["user_id"], p.get("plan_name","default"), p.get("course_id",1)))
    return jsonify({"ok": True})

@app.route("/api/admin/reject", methods=["POST"])
def admin_reject():
    data = request.get_json(force=True)
    execute("UPDATE payments SET status='rejected' WHERE id=?", (data["payment_id"],))
    return jsonify({"ok": True})

# ── Static ──
@app.route("/")
def index():
    return send_from_directory("webapp", "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory("webapp", filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
