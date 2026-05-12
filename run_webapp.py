"""
Yamen Academy v7 - ROOT ONLY + MMAP + WAL + SPA
"""
import os, json, sqlite3, random
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

DB = os.getenv("DB_PATH", "data/academy.db")
os.makedirs("data", exist_ok=True)

def get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA mmap_size=268435456")
    conn.execute("PRAGMA cache_size=-64000")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn

def query(sql, params=()):
    conn = get_conn()
    try: return conn.execute(sql, params).fetchall()
    finally: conn.close()

def execute(sql, params=()):
    conn = get_conn()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally: conn.close()

def dict_rows(rows): return [dict(r) for r in rows]

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:filename>")
def serve(filename):
    if filename.startswith("api/"): return jsonify({"error":"not found"}), 404
    if os.path.exists(filename) and os.path.isfile(filename):
        return send_from_directory(".", filename)
    for sub in ["icons","css","js"]:
        p = os.path.join(sub, os.path.basename(filename))
        if os.path.exists(p) and os.path.isfile(p):
            return send_from_directory(sub, os.path.basename(filename))
    return send_from_directory(".", "index.html")

@app.route("/admin")
def admin():
    if os.path.exists("admin_panel/index.html"):
        return send_from_directory("admin_panel", "index.html")
    return send_from_directory(".", "index.html")

@app.route("/api/health")
def health():
    try:
        query("SELECT 1")
        return jsonify({"status":"ok","db":True,"version":"7.0"})
    except: return jsonify({"status":"ok","db":False,"version":"7.0"})

@app.route("/api/me")
def me():
    uid = request.args.get("user_id")
    if not uid: return jsonify({"error":"user_id required"}), 400
    row = query("SELECT * FROM students WHERE user_id=?",(uid,))
    return jsonify(dict(row[0]) if row else {"error":"not found"})

@app.route("/api/courses")
def courses():
    lv = request.args.get("level","")
    rows = query("SELECT * FROM courses WHERE level=? ORDER BY id",(lv,)) if lv else query("SELECT * FROM courses ORDER BY id")
    return jsonify(dict_rows(rows))

@app.route("/api/lessons")
def lessons():
    cid = request.args.get("course_id")
    rows = query("SELECT * FROM lessons WHERE course_id=? ORDER BY order_num",(cid,)) if cid else query("SELECT * FROM lessons ORDER BY course_id, order_num")
    return jsonify(dict_rows(rows))

@app.route("/api/placement/questions")
def placement_q(): return jsonify(dict_rows(query("SELECT * FROM placement_questions ORDER BY id")))

@app.route("/api/spelling/words")
def spelling():
    lv = request.args.get("level","")
    rows = query("SELECT * FROM spelling_words WHERE level=? ORDER BY id",(lv,)) if lv else query("SELECT * FROM spelling_words ORDER BY id")
    return jsonify(dict_rows(rows))

@app.route("/api/daily/challenge")
def daily():
    today = __import__("datetime").date.today().isoformat()
    row = query("SELECT * FROM daily_challenges WHERE date=? ORDER BY id DESC LIMIT 1",(today,))
    if not row: row = query("SELECT * FROM daily_challenges ORDER BY id DESC LIMIT 1")
    return jsonify(dict(row[0]) if row else {"error":"no challenge"})

@app.route("/api/leaderboard")
def leaderboard():
    return jsonify(dict_rows(query("SELECT user_id,full_name,level,xp FROM students WHERE xp>0 ORDER BY xp DESC LIMIT 20")))

@app.route("/api/progress")
def progress():
    uid = request.args.get("user_id")
    if not uid: return jsonify({"error":"user_id required"}), 400
    s = query("SELECT * FROM students WHERE user_id=?",(uid,))
    if not s: return jsonify({"error":"not found"}), 404
    s = dict(s[0])
    return jsonify({"student":s,"stats":{"quizzes":query("SELECT COUNT(*) as c FROM quiz_attempts WHERE user_id=?",(uid,))[0]["c"],"writing":query("SELECT COUNT(*) as c FROM writing_submissions WHERE user_id=?",(uid,))[0]["c"],"speaking":query("SELECT COUNT(*) as c FROM speaking_sessions WHERE user_id=?",(uid,))[0]["c"],"words":query("SELECT COUNT(*) as c FROM word_reviews WHERE user_id=?",(uid,))[0]["c"]}})

WRITING_KEYS = os.getenv("WRITING_KEYS","").split(",")
SPEAKING_KEYS = os.getenv("SPEAKING_KEYS","").split(",")
MODEL = "gemini-2.5-flash"

@app.route("/api/writing/evaluate", methods=["POST"])
def eval_writing():
    d = request.get_json(force=True)
    essay = d.get("essay","")
    if len(essay.split()) < 50: return jsonify({"error":"Essay too short"}), 400
    keys = [k for k in WRITING_KEYS if k.strip()]
    if not keys: return jsonify({"error":"AI keys not configured"}), 500
    key = random.choice(keys)
    sp = 'You are an IELTS examiner. Reply ONLY in JSON: {"overall":6.5,"task_response":6,"coherence_cohesion":7,"lexical_resource":6.5,"grammatical_range":6.5,"feedback_ar":"Arabic","corrections":[]}'
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}"
    body = {"contents":[{"parts":[{"text":sp},{"text":f"Task: {d.get('task_type','task2')}\nPrompt: {d.get('prompt','')}\nESSAY:\n\n{essay}"}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":2048}}
    import urllib.request as ur
    req = ur.Request(url, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    try:
        with ur.urlopen(req, timeout=60) as r:
            t = json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"].strip().lstrip("```json").rstrip("```").strip()
            rj = json.loads(t)
            rj.setdefault("overall",6.0); rj.setdefault("feedback_ar","تم التقييم.")
            uid = d.get("user_id")
            if uid: execute("INSERT INTO writing_submissions (user_id,task_type,prompt,essay_text,word_count,band_score,task_response,coherence_cohesion,lexical_resource,grammatical_range,feedback_ar,corrections_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",(int(uid),d.get("task_type","task2"),d.get("prompt",""),essay,len(essay.split()),rj["overall"],rj.get("task_response",6),rj.get("coherence_cohesion",6),rj.get("lexical_resource",6),rj.get("grammatical_range",6),rj["feedback_ar"],json.dumps(rj.get("corrections",[]))))
            return jsonify(rj)
    except Exception as e: return jsonify({"error":str(e)}), 500

@app.route("/api/speaking/evaluate", methods=["POST"])
def eval_speaking():
    d = request.get_json(force=True)
    keys = [k for k in SPEAKING_KEYS if k.strip()]
    if not keys: return jsonify({"error":"AI keys not configured"}), 500
    key = random.choice(keys)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}"
    body = {"contents":[{"parts":[{"text":f"IELTS Speaking {d.get('part','part1')}. Prompt: {d.get('prompt','')}. Duration: {d.get('duration',30)}s. Score JSON: {{\"overall\":6.5,\"fluency\":6,\"pronunciation\":7,\"lexical_resource\":6.5,\"grammatical_range\":6,\"feedback_ar\":\"...\",\"transcript\":\"...\"}}"},{"inline_data":{"mime_type":"audio/ogg","data":d.get("audio_base64","")}}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":2048}}
    import urllib.request as ur
    req = ur.Request(url, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    try:
        with ur.urlopen(req, timeout=90) as r:
            t = json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"].strip().lstrip("```json").rstrip("```").strip()
            rj = json.loads(t)
            rj.setdefault("overall",6.0); rj.setdefault("feedback_ar","تم التقييم.")
            uid = d.get("user_id")
            if uid: execute("INSERT INTO speaking_sessions (user_id,prompt,transcript_text,audio_duration_sec,band_score,fluency,pronunciation,lexical_resource,grammatical_range,feedback_ar) VALUES (?,?,?,?,?,?,?,?,?,?)",(int(uid),d.get("prompt",""),rj.get("transcript",""),d.get("duration",30),rj["overall"],rj.get("fluency",6),rj.get("pronunciation",6),rj.get("lexical_resource",6),rj.get("grammatical_range",6),rj["feedback_ar"]))
            return jsonify(rj)
    except Exception as e: return jsonify({"error":str(e)}), 500

@app.route("/api/admin/stats")
def admin_stats(): return jsonify({"total_students":query("SELECT COUNT(*) as n FROM students")[0]["n"],"active_subs":query("SELECT COUNT(*) as n FROM subscriptions WHERE active=1")[0]["n"],"pending_payments":query("SELECT COUNT(*) as n FROM payments WHERE status='pending'")[0]["n"],"total_xp":query("SELECT COALESCE(SUM(xp),0) as n FROM students")[0]["n"]})

@app.route("/api/admin/students")
def admin_students(): return jsonify({"students":dict_rows(query("SELECT * FROM students ORDER BY created_at DESC"))})

@app.route("/api/admin/payments", methods=["GET","POST"])
def admin_payments():
    flt = request.json.get("filter","pending") if request.method=="POST" else "pending"
    return jsonify({"payments":dict_rows(query("SELECT * FROM payments WHERE status=? ORDER BY created_at DESC LIMIT 50",(flt,)))})

@app.route("/api/admin/approve_payment", methods=["POST"])
def admin_approve():
    d = request.get_json(force=True)
    execute("UPDATE payments SET status='approved' WHERE id=?",(d["id"],))
    p = query("SELECT * FROM payments WHERE id=?",(d["id"],))
    if p:
        p = dict(p[0]); days = 90 if "Excellence" in p.get("plan_name","") else (60 if "VIP" in p.get("plan_name","") else 30)
        execute(f"INSERT INTO subscriptions (user_id,plan_name,start_date,end_date,active) VALUES (?,?,datetime('now'),datetime('now','+{days} days'),1)",(p["user_id"],p.get("plan_name","")))
    return jsonify({"success":True})

@app.route("/api/admin/reject_payment", methods=["POST"])
def admin_reject(): execute("UPDATE payments SET status='rejected' WHERE id=?",(request.json["id"],)); return jsonify({"success":True})

@app.route("/api/admin/courses")
def admin_courses(): return jsonify({"courses":dict_rows(query("SELECT * FROM courses ORDER BY id"))})

@app.route("/api/admin/add_course", methods=["POST"])
def admin_add_course():
    d = request.json
    execute("INSERT INTO courses (name,level,description) VALUES (?,?,?)",(d["name"],d.get("level","A1"),d.get("description","")))
    return jsonify({"success":True})

@app.route("/api/admin/delete_course", methods=["POST"])
def admin_delete_course(): execute("DELETE FROM courses WHERE id=?",(request.json["id"],)); return jsonify({"success":True})

@app.route("/api/admin/settings")
def admin_settings(): return jsonify({r["key"]:r["value"] for r in query("SELECT * FROM admin_settings")})

@app.route("/api/admin/save_setting", methods=["POST"])
def admin_save_setting():
    d = request.json
    execute("INSERT OR REPLACE INTO admin_settings (key,value) VALUES (?,?)",(d["key"],str(d["value"])))
    return jsonify({"success":True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Yamen Academy v7.0 [UNSTUCK] on port {port}")
    app.run(host="0.0.0.0", port=port)
