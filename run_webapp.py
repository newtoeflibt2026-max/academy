import os, sys, sqlite3, json, traceback
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory, redirect
from flask_cors import CORS

# ── استيراد الإعدادات ────────────────────────────────────────
try:
    from config import ADMIN_IDS, DATABASE_PATH, WEBAPP_PORT
except ImportError:
    ADMIN_IDS = [5602495831]
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yamen_academy.db")
    WEBAPP_PORT = int(os.environ.get("PORT", 8080))

app = Flask(__name__)
CORS(app)

# ════════════════════════════════════════════════════════════
# DB Helpers
# ════════════════════════════════════════════════════════════
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def q(query, args=(), one=False):
    conn = get_db()
    try:
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        conn.commit()
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(f"❌ DB: {e}")
        return None
    finally:
        conn.close()

def ex(query, args=()):
    conn = get_db()
    try:
        conn.execute(query, args)
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ EXEC: {e}")
        return False
    finally:
        conn.close()

# ════════════════════════════════════════════════════════════
# 🏠 الصفحات — Core Flow
# ════════════════════════════════════════════════════════════
@app.route("/")
def home():
    return redirect("/dashboard")

@app.route("/dashboard")
@app.route("/dashboard/<int:student_id>")
def dashboard(student_id=None):
    empty = {"student":{"first_name":"طالب","xp":0,"level":0,"streak":0,"id":0},
             "library":[],"skills":[],"leaderboard":[],"progress":{}}
    if student_id is None:
        return render_template("dashboard.html", **empty)
    try:
        s = q("SELECT * FROM students WHERE telegram_id=?",(student_id,),one=True)
        if not s:
            return render_template("dashboard.html", **empty), 200
        student = dict(s)
        student.setdefault("first_name", student.get("username") or "طالب")
        student.setdefault("xp",0); student.setdefault("level",0); student.setdefault("streak",0)
        
        # المكتبة
        library = q("SELECT * FROM library_items WHERE is_active=1 ORDER BY sort_order, id") or []
        # المهارات اليومية
        skills = q("SELECT * FROM daily_skills WHERE is_active=1 ORDER BY sort_order, id") or []
        # المتصدرين
        lb = q("SELECT * FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT 5") or []
        # التقدم
        progress_rows = q("SELECT * FROM user_progress WHERE user_id=?",(student_id,)) or []
        progress = {r["skill_type"]: dict(r) for r in progress_rows}
        
        return render_template("dashboard.html",
            student=student,
            library=[dict(r) for r in library],
            skills=[dict(r) for r in skills],
            leaderboard=[dict(r) for r in lb],
            progress=progress)
    except Exception as e:
        print(f"❌ Dashboard: {e}\n{traceback.format_exc()}")
        return render_template("dashboard.html", **empty), 200

@app.route("/admin")
def admin_panel():
    return render_template("admin.html")

# ════════════════════════════════════════════════════════════
# 📡 API — المكتبة
# ════════════════════════════════════════════════════════════
@app.route("/api/library")
def api_library():
    rows = q("SELECT * FROM library_items WHERE is_active=1 ORDER BY sort_order, id")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/library/add", methods=["POST"])
def api_library_add():
    d = request.get_json()
    title = d.get("title","").strip()
    item_type = d.get("type","pdf").strip()
    url = d.get("url","").strip()
    telegram_link = d.get("telegram_link","").strip()
    icon = d.get("icon","📄")
    category = d.get("category","general")
    if not title: return jsonify({"error":"العنوان مطلوب"}),400
    ex("INSERT INTO library_items (title,type,url,telegram_link,icon,category,is_active) VALUES (?,?,?,?,?,?,1)",
       (title, item_type, url, telegram_link, icon, category))
    return jsonify({"success":True,"message":f"تمت إضافة: {title}"})

@app.route("/api/library/delete/<int:item_id>", methods=["DELETE"])
def api_library_delete(item_id):
    ex("DELETE FROM library_items WHERE id=?",(item_id,))
    return jsonify({"success":True})

# ════════════════════════════════════════════════════════════
# 📡 API — المهارات اليومية (Dynamic)
# ════════════════════════════════════════════════════════════
@app.route("/api/skills")
def api_skills():
    rows = q("SELECT * FROM daily_skills WHERE is_active=1 ORDER BY sort_order, id")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/skills/add", methods=["POST"])
def api_skills_add():
    d = request.get_json()
    title = d.get("title","").strip()
    skill_type = d.get("skill_type","reading").strip()
    icon = d.get("icon","📝")
    time_limit = d.get("time_limit",45)
    if not title: return jsonify({"error":"العنوان مطلوب"}),400
    ex("INSERT INTO daily_skills (title,skill_type,icon,time_limit,is_active) VALUES (?,?,?,?,1)",
       (title, skill_type, icon, time_limit))
    return jsonify({"success":True,"message":f"تمت إضافة المهارة: {title}"})

@app.route("/api/skills/toggle", methods=["POST"])
def api_skills_toggle():
    d = request.get_json()
    sid = d.get("id"); active = d.get("active",1)
    ex("UPDATE daily_skills SET is_active=? WHERE id=?",(active,sid))
    return jsonify({"success":True})

@app.route("/api/skills/delete/<int:skill_id>", methods=["DELETE"])
def api_skills_delete(skill_id):
    ex("DELETE FROM daily_skills WHERE id=?",(skill_id,))
    return jsonify({"success":True})

# ════════════════════════════════════════════════════════════
# 📡 API — الأسئلة + الامتحانات
# ════════════════════════════════════════════════════════════
@app.route("/api/question/next", methods=["POST"])
def api_next_question():
    d = request.get_json()
    skill_type = d.get("skill_type")
    student_id = d.get("student_id")
    last_qid = d.get("last_question_id",0)
    if not skill_type: return jsonify({"error":"نوع المهارة مطلوب"}),400
    row = q("SELECT * FROM questions WHERE skill_type=? AND is_active=1 AND id>? ORDER BY id ASC LIMIT 1",(skill_type,last_qid),one=True)
    if not row: row = q("SELECT * FROM questions WHERE skill_type=? AND is_active=1 ORDER BY id ASC LIMIT 1",(skill_type,),one=True)
    if not row: return jsonify({"error":"لا توجد أسئلة"}),404
    if student_id: ex("UPDATE students SET last_active=datetime('now') WHERE telegram_id=?",(student_id,))
    return jsonify({"question":dict(row),"has_timer":True,"time_limit":dict(row).get("time_limit",45)})

@app.route("/api/exam/start", methods=["POST"])
def api_exam_start():
    d = request.get_json()
    user_id = d.get("user_id"); section = d.get("section","reading")
    if not user_id: return jsonify({"error":"معرف مطلوب"}),400
    ex("INSERT INTO exam_sessions (user_id,section) VALUES (?,?)",(user_id,section))
    questions = q("SELECT * FROM questions WHERE skill_type=? AND is_active=1 ORDER BY RANDOM() LIMIT 5",(section,))
    return jsonify({"session_started":True,"questions":[dict(r) for r in questions] if questions else []})

@app.route("/api/exam/submit", methods=["POST"])
def api_exam_submit():
    d = request.get_json()
    user_id = d.get("user_id"); answers = d.get("answers",[])
    correct_count = sum(1 for a in answers if a.get("correct"))
    xp_earned = correct_count * 10
    ex("UPDATE exam_sessions SET correct=?,score=?,xp_earned=? WHERE user_id=? ORDER BY id DESC LIMIT 1",
       (correct_count, correct_count*20, xp_earned, user_id))
    ex("UPDATE students SET xp=COALESCE(xp,0)+? WHERE telegram_id=?",(xp_earned, user_id))
    return jsonify({"correct":correct_count,"total":len(answers),"xp_earned":xp_earned})

# ════════════════════════════════════════════════════════════
# 📡 API — AI Assessment
# ════════════════════════════════════════════════════════════
@app.route("/api/ai/submit_speaking", methods=["POST"])
def api_submit_speaking():
    """تقديم إجابة صوتية للتقييم"""
    d = request.get_json()
    user_id = d.get("user_id"); question_id = d.get("question_id")
    transcript = d.get("transcript",""); audio_url = d.get("audio_url","")
    if not user_id: return jsonify({"error":"معرف مطلوب"}),400
    
    # ⚡ تقييم AI بسيط (يمكن ربطه بـ OpenAI/Google API لاحقاً)
    score = min(5.0, max(1.0, len(transcript.split()) / 30 + 2.0))
    feedback = "نطق واضح، حاول تنويع المفردات" if score > 3 else "تحتاج مزيداً من التدريب على الطلاقة"
    
    ex("INSERT INTO speaking_submissions (user_id,question_id,audio_url,transcript,ai_score,ai_feedback) VALUES (?,?,?,?,?,?)",
       (user_id, question_id, audio_url, transcript, round(score,1), feedback))
    ex("UPDATE students SET xp=COALESCE(xp,0)+5 WHERE telegram_id=?",(user_id,))
    return jsonify({"score":round(score,1),"feedback":feedback,"xp_earned":5})

@app.route("/api/ai/submit_writing", methods=["POST"])
def api_submit_writing():
    """تقديم إجابة كتابية للتقييم"""
    d = request.get_json()
    user_id = d.get("user_id"); question_id = d.get("question_id")
    essay = d.get("essay","")
    if not user_id or not essay: return jsonify({"error":"مطلوب"}),400
    
    word_count = len(essay.split())
    # تقييم بسيط
    score = min(5.0, max(1.0, word_count / 40 + 2.0))
    feedback = "كتابة جيدة، اهتم بعلامات الترقيم" if score > 3 else "حاول توسيع أفكارك"
    
    ex("INSERT INTO writing_submissions (user_id,question_id,essay_text,ai_score,ai_feedback,word_count) VALUES (?,?,?,?,?,?)",
       (user_id, question_id, essay, round(score,1), feedback, word_count))
    ex("UPDATE students SET xp=COALESCE(xp,0)+10 WHERE telegram_id=?",(user_id,))
    return jsonify({"score":round(score,1),"feedback":feedback,"word_count":word_count,"xp_earned":10})

@app.route("/api/ai/config", methods=["GET"])
def api_ai_config():
    rows = q("SELECT * FROM ai_config ORDER BY id")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/ai/config/update", methods=["POST"])
def api_ai_config_update():
    d = request.get_json()
    key = d.get("config_key"); val = d.get("config_value")
    if not key: return jsonify({"error":"مطلوب"}),400
    ex("UPDATE ai_config SET config_value=?, updated_at=datetime('now') WHERE config_key=?",(val,key))
    return jsonify({"success":True})

# ════════════════════════════════════════════════════════════
# 📡 API — متفرقات
# ════════════════════════════════════════════════════════════
@app.route("/api/student/xp", methods=["POST"])
def api_update_xp():
    d = request.get_json()
    sid = d.get("student_id"); xp = d.get("xp_gain",10)
    ex("UPDATE students SET xp=COALESCE(xp,0)+?, last_active=datetime('now') WHERE telegram_id=?",(xp,sid))
    row = q("SELECT xp,level FROM students WHERE telegram_id=?",(sid,),one=True)
    return jsonify({"xp":row["xp"],"level":row["level"]}) if row else jsonify({"error":"غير موجود"}),404

@app.route("/api/leaderboard")
def api_leaderboard():
    rows = q("SELECT telegram_id,first_name,username,xp,level FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT 10")
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/error_bank/<int:user_id>")
def api_error_bank(user_id):
    rows = q("SELECT * FROM error_bank WHERE user_id=?",(user_id,))
    return jsonify([dict(r) for r in rows] if rows else [])

@app.route("/api/health")
def health():
    return jsonify({"status":"online","app":"يامن أكاديمي — TOEFL Platform","timestamp":str(datetime.now())})

@app.route("/api/admin/stats")
def admin_stats():
    sc=q("SELECT COUNT(*) as c FROM students",one=True)
    lc=q("SELECT COUNT(*) as c FROM library_items",one=True)
    kc=q("SELECT COUNT(*) as c FROM daily_skills",one=True)
    qc=q("SELECT COUNT(*) as c FROM questions",one=True)
    return jsonify({"students":sc["c"]if sc else 0,"library":lc["c"]if lc else 0,"skills":kc["c"]if kc else 0,"questions":qc["c"]if qc else 0})

# ════════════════════════════════════════════════════════════
# 📁 Static Files + Audio
# ════════════════════════════════════════════════════════════
@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

@app.route("/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory("static/audio", filename, mimetype="audio/mpeg")

# ════════════════════════════════════════════════════════════
# سجل المسارات
# ════════════════════════════════════════════════════════════
with app.app_context():
    print("\n" + "="*60)
    print("🛣️  يامن أكاديمي — TOEFL Routes:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if not rule.rule.startswith('/static'):
            methods = ','.join(sorted(rule.methods - {'HEAD','OPTIONS'}))
            print(f"   {methods:8s} → {rule.rule}")
    print("="*60 + "\n")

if __name__ == "__main__":
    from database import init_db
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    init_db()
    app.run(host="0.0.0.0", port=WEBAPP_PORT, debug=False)
