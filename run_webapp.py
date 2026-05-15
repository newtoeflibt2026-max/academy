import os, sqlite3, json
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory, redirect
from flask_cors import CORS

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH  = os.path.join(BASE_DIR, "data", "yamen_academy.db")
PORT           = int(os.environ.get("PORT", 5050))

app = Flask(__name__)
CORS(app)

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def query_db(query, args=(), one=False):
    conn = get_db()
    try:
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        conn.commit()
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(f"DB Error: {e}")
        return None
    finally:
        conn.close()

def execute_db(query, args=()):
    conn = get_db()
    try:
        conn.execute(query, args)
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Exec Error: {e}")
        return False
    finally:
        conn.close()

@app.route("/")
def home():
    return redirect("/dashboard")

@app.route("/dashboard")
@app.route("/dashboard/<int:student_id>")
def dashboard(student_id=None):
    empty = {"student":{"first_name":"طالب","xp":0,"level":0,"streak":0,"id":0},"courses":[],"error_count":0,"leaderboard":[]}
    if student_id is None: return render_template("dashboard.html", **empty)
    s = query_db("SELECT * FROM students WHERE telegram_id=?",(student_id,),one=True)
    if not s: return render_template("dashboard.html", **empty), 200
    student = dict(s)
    student.setdefault("first_name", student.get("username") or "طالب")
    student.setdefault("xp",0); student.setdefault("level",0); student.setdefault("streak",0)
    courses = query_db("SELECT * FROM courses WHERE is_active=1") or []
    err = query_db("SELECT COUNT(*) as cnt FROM error_bank WHERE user_id=?",(student_id,),one=True)
    lb = query_db("SELECT * FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT 5") or []
    return render_template("dashboard.html", student=student, courses=[dict(r) for r in courses], error_count=err["cnt"] if err else 0, leaderboard=[dict(r) for r in lb])

@app.route("/admin")
def admin_panel():
    return render_template("admin.html")

SKILLS_MAP = {
    "conversation":{"title":"محادثة 45s","icon":"💬","time":45},
    "word_completion":{"title":"إكمال كلمات","icon":"📝","time":60},
    "sentence_ordering":{"title":"ترتيب جمل","icon":"🧩","time":50},
    "email_writing":{"title":"كتابة إيميل","icon":"✉️","time":90},
    "listening":{"title":"استماع وتكرار","icon":"🎧","time":40},
    "reading":{"title":"قراءة متحررة","icon":"📖","time":70},
}

@app.route("/api/skills")
def api_get_skills():
    rows = query_db("SELECT * FROM courses WHERE is_active=1")
    active_skills = {r["skill_type"] for r in rows} if rows else set()
    skills = []
    for key,val in SKILLS_MAP.items():
        skills.append({"id":key,"title":val["title"],"icon":val["icon"],"time_limit":val["time"],"is_active":key in active_skills})
    return jsonify(skills)

@app.route("/api/skills/toggle", methods=["POST"])
def api_toggle_skill():
    data = request.get_json()
    skill_type = data.get("skill_type")
    if skill_type not in SKILLS_MAP: return jsonify({"error":"مهارة غير معروفة"}),400
    info = SKILLS_MAP[skill_type]
    existing = query_db("SELECT id,is_active FROM courses WHERE skill_type=?",(skill_type,),one=True)
    if existing:
        new_state = 0 if existing["is_active"] else 1
        execute_db("UPDATE courses SET is_active=? WHERE skill_type=?",(new_state,skill_type))
    else:
        execute_db("INSERT INTO courses (title,skill_type,time_limit,is_active) VALUES (?,?,?,1)",(info["title"],skill_type,info["time"]))
    return jsonify({"success":True,"skill_type":skill_type})

@app.route("/api/lessons", methods=["GET"])
def api_get_lessons():
    rows = query_db("SELECT * FROM lessons ORDER BY id DESC")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/lessons/add", methods=["POST"])
def api_add_lesson():
    data = request.get_json()
    title = data.get("title","").strip()
    lesson_type = data.get("type","video").strip()
    url = data.get("url","").strip()
    course_id = data.get("course_id",1)
    skill_type = data.get("skill_type","reading")
    if not title or not url: return jsonify({"error":"العنوان والرابط مطلوبان"}),400
    execute_db("INSERT INTO lessons (title,type,url,course_id,skill_type,is_active) VALUES (?,?,?,?,?,1)",(title,lesson_type,url,course_id,skill_type))
    return jsonify({"success":True,"message":f"تمت إضافة الدرس: {title}"})

@app.route("/api/lessons/delete/<int:lesson_id>", methods=["DELETE"])
def api_delete_lesson(lesson_id):
    execute_db("DELETE FROM lessons WHERE id=?",(lesson_id,))
    return jsonify({"success":True})

@app.route("/api/question/next", methods=["POST"])
def api_next_question():
    data = request.get_json()
    skill_type = data.get("skill_type")
    student_id = data.get("student_id")
    last_qid = data.get("last_question_id",0)
    if not skill_type: return jsonify({"error":"نوع المهارة مطلوب"}),400
    q = query_db("SELECT * FROM questions WHERE skill_type=? AND is_active=1 AND id>? ORDER BY id ASC LIMIT 1",(skill_type,last_qid),one=True)
    if not q: q = query_db("SELECT * FROM questions WHERE skill_type=? AND is_active=1 ORDER BY id ASC LIMIT 1",(skill_type,),one=True)
    if not q: return jsonify({"error":"لا توجد أسئلة متاحة لهذه المهارة"}),404
    qd = dict(q)
    if student_id: execute_db("UPDATE students SET last_active=datetime('now') WHERE telegram_id=?",(student_id,))
    return jsonify({"question":qd,"has_timer":True,"time_limit":qd.get("time_limit",45)})

@app.route("/api/student/xp", methods=["POST"])
def api_update_xp():
    d = request.get_json()
    sid = d.get("student_id"); xp = d.get("xp_gain",10)
    if not sid: return jsonify({"error":"معرف الطالب مطلوب"}),400
    execute_db("UPDATE students SET xp=COALESCE(xp,0)+?, last_active=datetime('now') WHERE telegram_id=?",(xp,sid))
    row = query_db("SELECT xp,level FROM students WHERE telegram_id=?",(sid,),one=True)
    return jsonify({"xp":row["xp"],"level":row["level"]}) if row else jsonify({"error":"طالب غير موجود"}),404

@app.route("/api/leaderboard")
def api_leaderboard():
    rows = query_db("SELECT telegram_id,first_name,username,xp,level FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT 10")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/error_bank/<int:user_id>")
def api_error_bank(user_id):
    rows = query_db("SELECT * FROM error_bank WHERE user_id=?",(user_id,))
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/error_bank/add", methods=["POST"])
def api_error_bank_add():
    d = request.get_json()
    execute_db("INSERT OR IGNORE INTO error_bank (user_id,question_id,skill_type,correct_count) VALUES (?,?,?,0)",(d.get("user_id"),d.get("question_id"),d.get("skill_type")))
    return jsonify({"success":True})

@app.route("/api/error_bank/correct", methods=["POST"])
def api_error_correct():
    d = request.get_json()
    qid=d.get("question_id"); uid=d.get("user_id")
    if not qid or not uid: return jsonify({"error":"Missing"}),400
    execute_db("UPDATE error_bank SET correct_count=COALESCE(correct_count,0)+1 WHERE question_id=? AND user_id=?",(qid,uid))
    row = query_db("SELECT correct_count FROM error_bank WHERE question_id=? AND user_id=?",(qid,uid),one=True)
    if row and row["correct_count"]>=2: execute_db("DELETE FROM error_bank WHERE question_id=? AND user_id=?",(qid,uid))
    return jsonify({"success":True})

@app.route("/api/health")
def health():
    return jsonify({"status":"healthy","app":"يامن أكاديمي","timestamp":str(datetime.now())})

@app.route("/api/admin/stats")
def admin_stats():
    sc=query_db("SELECT COUNT(*) as c FROM students",one=True)
    cc=query_db("SELECT COUNT(*) as c FROM courses",one=True)
    lc=query_db("SELECT COUNT(*) as c FROM lessons",one=True)
    qc=query_db("SELECT COUNT(*) as c FROM questions",one=True)
    return jsonify({"students":sc["c"] if sc else 0,"courses":cc["c"] if cc else 0,"lessons":lc["c"] if lc else 0,"questions":qc["c"] if qc else 0})

@app.route("/api/admin/students")
def admin_students():
    rows = query_db("SELECT * FROM students ORDER BY xp DESC")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/style.css")
def serve_css(): return send_from_directory("static","style.css")
@app.route("/app.js")
def serve_js(): return send_from_directory("static","app.js")

if __name__=="__main__":
    os.makedirs(os.path.join(BASE_DIR,"data"),exist_ok=True)
    app.run(host="0.0.0.0",port=PORT,debug=False)
