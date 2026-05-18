# -*- coding: utf-8 -*-
import sqlite3, os, json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "yamen_academy.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA encoding = 'UTF-8'")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT UNIQUE,
        name TEXT NOT NULL DEFAULT 'طالب',
        email TEXT, phone TEXT,
        level TEXT DEFAULT 'beginner',
        xp INTEGER DEFAULT 0,
        streak_days INTEGER DEFAULT 0,
        package TEXT DEFAULT 'مجاني',
        package_start DATE, package_end DATE,
        is_active INTEGER DEFAULT 1,
        completed_lessons INTEGER DEFAULT 0,
        accuracy INTEGER DEFAULT 0,
        subscription_type TEXT DEFAULT 'free',
        writing_corrections_today INTEGER DEFAULT 0,
        writing_corrections_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_type TEXT DEFAULT 'mcq',
        topic TEXT DEFAULT 'General',
        difficulty TEXT DEFAULT 'medium',
        question_text TEXT,
        passage_text  TEXT,
        audio_url     TEXT,
        audio_file_id TEXT,
        option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
        correct_option TEXT,
        complete_words_passage TEXT,
        complete_words_answers  TEXT,
        word_order_words  TEXT,
        word_order_answer TEXT,
        writing_prompt    TEXT,
        writing_min_words INTEGER DEFAULT 50,
        writing_sample    TEXT,
        speaking_prompt   TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS writing_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        question_id INTEGER,
        submitted_text TEXT,
        word_count INTEGER DEFAULT 0,
        basic_score INTEGER DEFAULT 0,
        basic_feedback TEXT,
        ai_score INTEGER,
        ai_feedback TEXT,
        correction_type TEXT DEFAULT 'basic',
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(question_id) REFERENCES questions(id)
    );

    CREATE TABLE IF NOT EXISTS speaking_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        question_id INTEGER,
        audio_file_path TEXT,
        duration_sec INTEGER,
        basic_score INTEGER DEFAULT 0,
        ai_feedback TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS daily_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        task_text TEXT NOT NULL,
        task_type TEXT DEFAULT 'study',
        xp_reward INTEGER DEFAULT 10,
        completed INTEGER DEFAULT 0,
        task_date DATE DEFAULT (date('now')),
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS error_bank (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        question_text TEXT,
        wrong_answer TEXT,
        correct_answer TEXT,
        topic TEXT,
        review_count INTEGER DEFAULT 0,
        next_review DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        level TEXT DEFAULT 'foundation',
        order_num INTEGER DEFAULT 1,
        content TEXT,
        min_score INTEGER DEFAULT 70,
        is_active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        amount REAL, package TEXT,
        duration_days INTEGER,
        status TEXT DEFAULT 'pending',
        payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_at TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS badges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        badge_key TEXT, badge_name TEXT,
        awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT
    );
    """)


def seed_demo_data():
    conn = get_db()
    c = conn.cursor()
    today = datetime.now().date()

    students = [
        ("احمد محمد","ahmed@demo.com","intermediate",2450,7,"باقة 90 يوم","premium",8,75),
        ("سارة علي","sara@demo.com","advanced",3200,12,"باقة 60 يوم","premium",22,88),
        ("محمد خالد","khalid@demo.com","beginner",980,3,"مجاني","free",15,60),
        ("نورة حسن","noura@demo.com","intermediate",1750,5,"باقة 90 يوم","premium",35,72),
        ("عمر عبدالله","omar@demo.com","advanced",4100,20,"باقة 60 يوم","premium",5,91),
    ]
    for s in students:
        name,email,level,xp,streak,pkg,sub_type,days_left,accuracy = s
        pkg_end   = today + timedelta(days=days_left)
        pkg_start = today - timedelta(days=90-days_left)
        if not c.execute("SELECT id FROM students WHERE email=?", (email,)).fetchone():
            c.execute("""INSERT INTO students
                (name,email,level,xp,streak_days,package,subscription_type,
                 package_start,package_end,is_active,completed_lessons,accuracy)
                VALUES (?,?,?,?,?,?,?,?,?,1,?,?)""",
                (name,email,level,xp,streak,pkg,sub_type,pkg_start,pkg_end,xp//200,accuracy))

    ahmed = c.execute("SELECT id FROM students WHERE email='ahmed@demo.com'").fetchone()
    if ahmed:
        sid = ahmed[0]
        c.execute("DELETE FROM daily_tasks WHERE student_id=? AND task_date=date('now')",(sid,))
        for text,ttype,xp_r,done in [
            ("مراجعة Complete the Words – الوحدة 3","reading",50,0),
            ("حل 10 أسئلة Listening Comprehension","listening",40,1),
            ("تمرين Build a Sentence (10 جمل)","writing",30,0),
            ("مراجعة كلمات اليوم (20 كلمة)","vocab",20,1),
            ("تسجيل Speaking – Interview Task","speaking",60,0),
        ]:
            c.execute("""INSERT INTO daily_tasks
                (student_id,task_text,task_type,xp_reward,completed,task_date)
                VALUES (?,?,?,?,?,date('now'))""",(sid,text,ttype,xp_r,done))

        if not c.execute("SELECT COUNT(*) FROM error_bank WHERE student_id=?",(sid,)).fetchone()[0]:
            for q,wrong,correct,topic in [
                ("Complete: 'The res_____ showed significant growth'","resent","results","Complete the Words"),
                ("Build Sentence: 'every/goes/She/day/to/school'","She every goes day","She goes to school every day","Build a Sentence"),
                ("Listening: What did the professor suggest?","Change the topic","Expand the scope","Listening"),
            ]:
                c.execute("""INSERT INTO error_bank
                    (student_id,question_text,wrong_answer,correct_answer,topic,next_review)
                    VALUES (?,?,?,?,?,date('now'))""",(sid,q,wrong,correct,topic))

    if not c.execute("SELECT COUNT(*) FROM questions").fetchone()[0]:
        questions = [
            # ── MCQ Reading ──────────────────────────────────────────────
            ("mcq","Reading","medium",
             "What is the main idea of the passage?",
             "The Industrial Revolution began in Britain in the late 18th century. It marked a major turning point in history, with almost every aspect of daily life influenced in some way.",
             None,None,
             "Economic decline","Industrial growth in Britain","Population decrease","Trade reduction","b",
             None,None,None,None,None,None,None,None),

            # ── Complete the Words (TOEFL 2026 نمط) ─────────────────────
            ("complete_words","Reading","medium",
             "Complete the Words – أكمل الكلمات الناقصة الحروف",
             None,None,None,
             None,None,None,None,None,
             "Scientists have long studied the mig_____ patterns of birds. Each autumn, millions of spe_____ travel thousands of miles to warmer cli_____. This phen_____ has fascinated res_____ for centuries.",
             '{"mig_____":"migration","spe_____":"species","cli_____":"climates","phen_____":"phenomenon","res_____":"researchers"}',
             None,None,None,None,None,None),

            ("complete_words","Reading","hard",
             "Complete the Words – Academic Text",
             None,None,None,
             None,None,None,None,None,
             "The human immune sys_____ is remarkably com_____. When path_____ enter the body, white blood cells pro_____ antibodies to neu_____ the threat. This def_____ mechanism has evo_____ over millions of years.",
             '{"sys_____":"system","com_____":"complex","path_____":"pathogens","pro_____":"produce","neu_____":"neutralize","def_____":"defense","evo_____":"evolved"}',
             None,None,None,None,None,None),

            # ── Listening MCQ ────────────────────────────────────────────
            ("listening","Listening","medium",
             "What is the main topic of the conversation?",
             None,
             "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
             None,
             "Technology impact on education","Climate change research","Campus library rules","Student exchange program","a",
             None,None,None,None,None,None,None,None),

            ("listening","Listening","easy",
             "What does the professor suggest the student should do?",
             None,
             "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
             None,
             "Change the topic completely","Reduce number of sources","Expand the scope of research","Focus on one aspect only","c",
             None,None,None,None,None,None,None,None),

            # ── Listen & Choose Response (TOEFL 2026) ────────────────────
            ("listen_respond","Listening","easy",
             "Listen to the sentence and choose the best response:",
             None,
             "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
             None,
             "Yes, a few minutes ago","No, I never heard that","Maybe tomorrow","I already left","a",
             None,None,None,None,None,None,None,None),

            # ── Build a Sentence (TOEFL 2026 Writing Task 1) ─────────────
            ("build_sentence","Writing","easy",
             "رتب الكلمات لتكوين جملة صحيحة:",
             None,None,None,
             None,None,None,None,None,
             None,None,
             "every / goes / She / day / school / to",
             "She goes to school every day.",
             None,None,None,None),

            ("build_sentence","Writing","medium",
             "رتب الكلمات لتكوين جملة صحيحة:",
             None,None,None,
             None,None,None,None,None,
             None,None,
             "been / have / three / studying / They / hours / for",
             "They have been studying for three hours.",
             None,None,None,None),

            ("build_sentence","Grammar","hard",
             "رتب الكلمات لتكوين جملة صحيحة:",
             None,None,None,
             None,None,None,None,None,
             None,None,
             "arrived / had / she / before / finished / he",
             "She had finished before he arrived.",
             None,None,None,None),

            # ── Writing Email ─────────────────────────────────────────────
            ("writing_email","Writing","medium",
             "Write an Email",
             None,None,None,
             None,None,None,None,None,
             None,None,None,None,
             "Write an email to your professor explaining why you missed the last class. Apologize and ask about the homework. (minimum 60 words)",
             60,
             "Dear Professor Smith,\n\nI am writing to apologize for missing your class yesterday. Unfortunately, I was not feeling well and had to visit the doctor.\n\nCould you please let me know what I missed and if there is any homework I need to complete?\n\nThank you for your understanding.\n\nBest regards,\nAhmed",
             None),

            # ── Writing Discussion ────────────────────────────────────────
            ("writing_discussion","Writing","hard",
             "Writing for Academic Discussion",
             "Professor: Do you think technology has improved or harmed human communication? Share your thoughts with examples.",
             None,None,
             None,None,None,None,None,
             None,None,None,None,
             "Write a post for the class discussion board responding to the professor's question. Support your opinion with at least one example. (minimum 100 words)",
             100,
             "In my opinion, technology has significantly improved human communication. For example, video calling applications like Zoom allow people to connect face-to-face regardless of distance. However, some argue that social media creates superficial relationships. Despite this, the overall impact is positive as technology breaks geographical barriers.",
             None),

            # ── Speaking ─────────────────────────────────────────────────
            ("speaking_interview","Speaking","medium",
             "Take an Interview – Answer the following question:",
             None,None,None,
             None,None,None,None,None,
             None,None,None,None,None,None,None,
             "Do you prefer studying in a group or alone? Explain why with examples from your experience. (45 seconds)"),

            ("speaking_repeat","Speaking","easy",
             "Listen and Repeat – استمع وكرر الجملة:",
             None,
             "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
             None,
             None,None,None,None,None,
             None,None,None,None,None,None,None,
             "The library opens at eight o'clock every morning."),
        ]
        for q in questions:
            c.execute("""INSERT INTO questions
                (question_type,topic,difficulty,question_text,passage_text,
                 audio_url,audio_file_id,option_a,option_b,option_c,option_d,correct_option,
                 complete_words_passage,complete_words_answers,
                 word_order_words,word_order_answer,
                 writing_prompt,writing_min_words,writing_sample,speaking_prompt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", q)

    for title,level,order,min_score in [
        ("مقدمة في اللغة الإنجليزية","foundation",1,60),
        ("الأفعال والأزمنة الأساسية","foundation",2,65),
        ("القراءة والاستيعاب – مستوى 1","toefl",3,70),
        ("Complete the Words – TOEFL 2026","toefl",4,70),
        ("Listening Comprehension","toefl",5,70),
        ("Build a Sentence","toefl",6,70),
        ("Writing Email & Discussion","advanced",7,75),
        ("Speaking Interview","advanced",8,80),
    ]:
        if not c.execute("SELECT id FROM lessons WHERE title=?",(title,)).fetchone():
            c.execute("INSERT INTO lessons (title,level,order_num,min_score) VALUES (?,?,?,?)",
                      (title,level,order,min_score))

    for key,val in [
        ("academy_name","أكاديمية يامن"),
        ("daily_xp_goal","200"),
        ("pass_score","70"),
        ("ai_corrections_per_day","3"),
        ("wallet_number","0798919150"),
    ]:
        c.execute("INSERT OR IGNORE INTO settings (key,value) VALUES (?,?)",(key,val))

    conn.commit()
    conn.close()
    print("البيانات التجريبية جاهزة")

def get_student_by_id(sid):
    conn=get_db(); row=conn.execute("SELECT * FROM students WHERE id=?",(sid,)).fetchone(); conn.close()
    return dict(row) if row else None

def get_student_by_telegram(tid):
    conn=get_db(); row=conn.execute("SELECT * FROM students WHERE telegram_id=?",(tid,)).fetchone(); conn.close()
    return dict(row) if row else None

def get_daily_tasks(sid):
    conn=get_db()
    rows=conn.execute("SELECT * FROM daily_tasks WHERE student_id=? AND task_date=date('now') ORDER BY completed ASC,id ASC",(sid,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def toggle_task(task_id, student_id):
    conn=get_db()
    task=conn.execute("SELECT * FROM daily_tasks WHERE id=? AND student_id=?",(task_id,student_id)).fetchone()
    if not task: conn.close(); return False
    new_s=0 if task["completed"] else 1
    conn.execute("UPDATE daily_tasks SET completed=? WHERE id=?",(new_s,task_id))
    if new_s==1: conn.execute("UPDATE students SET xp=xp+? WHERE id=?",(task["xp_reward"],student_id))
    else:        conn.execute("UPDATE students SET xp=MAX(0,xp-?) WHERE id=?",(task["xp_reward"],student_id))
    conn.commit(); conn.close(); return True

def get_leaderboard(limit=10):
    conn=get_db()
    rows=conn.execute("SELECT id,name,xp,streak_days,level FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT ?",(limit,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_errors(sid):
    conn=get_db()
    rows=conn.execute("SELECT * FROM error_bank WHERE student_id=? ORDER BY next_review ASC,created_at DESC",(sid,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_admin_stats():
    conn=get_db()
    s={"total_students":conn.execute("SELECT COUNT(*) FROM students").fetchone()[0],
       "active_students":conn.execute("SELECT COUNT(*) FROM students WHERE is_active=1").fetchone()[0],
       "total_questions":conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0],
       "pending_payments":conn.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0],
       "total_lessons":conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0],
       "tasks_today":conn.execute("SELECT COUNT(*) FROM daily_tasks WHERE task_date=date('now')").fetchone()[0]}
    conn.close(); return s

def get_all_students():
    conn=get_db(); rows=conn.execute("SELECT * FROM students ORDER BY xp DESC").fetchall(); conn.close()
    return [dict(r) for r in rows]

def get_all_questions(q_type=None,topic=None):
    conn=get_db()
    sql="SELECT * FROM questions WHERE 1=1"; args=[]
    if q_type: sql+=" AND question_type=?"; args.append(q_type)
    if topic:  sql+=" AND topic=?";         args.append(topic)
    rows=conn.execute(sql+" ORDER BY created_at DESC",args).fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_all_payments():
    conn=get_db()
    rows=conn.execute("""SELECT p.*,s.name as student_name FROM payments p
        LEFT JOIN students s ON p.student_id=s.id ORDER BY p.payment_date DESC""").fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_writing_corrections_today(sid):
    conn=get_db()
    row=conn.execute("SELECT writing_corrections_today,writing_corrections_date FROM students WHERE id=?",(sid,)).fetchone()
    conn.close()
    if not row: return 0
    if row["writing_corrections_date"]!=str(datetime.now().date()): return 0
    return row["writing_corrections_today"] or 0

def increment_writing_corrections(sid):
    today=str(datetime.now().date()); conn=get_db()
    row=conn.execute("SELECT writing_corrections_today,writing_corrections_date FROM students WHERE id=?",(sid,)).fetchone()
    if row and row["writing_corrections_date"]==today:
        conn.execute("UPDATE students SET writing_corrections_today=writing_corrections_today+1 WHERE id=?",(sid,))
    else:
        conn.execute("UPDATE students SET writing_corrections_today=1,writing_corrections_date=? WHERE id=?",(today,sid))
    conn.commit(); conn.close()

def save_writing_submission(sid,qid,text,wc,score,feedback,ctype):
    conn=get_db()
    conn.execute("""INSERT INTO writing_submissions
        (student_id,question_id,submitted_text,word_count,basic_score,basic_feedback,correction_type)
        VALUES (?,?,?,?,?,?,?)""",(sid,qid,text,wc,score,feedback,ctype))
    conn.commit(); conn.close()

def save_speaking_submission(sid,qid,file_path,duration):
    conn=get_db()
    conn.execute("""INSERT INTO speaking_submissions
        (student_id,question_id,audio_file_path,duration_sec,basic_score)
        VALUES (?,?,?,?,70)""",(sid,qid,file_path,duration))
    conn.commit(); conn.close()


# Mock Exam Tables
def init_mock_tables():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS mock_exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        target_score INTEGER DEFAULT 59,
        pass_score INTEGER DEFAULT 65,
        duration_minutes INTEGER DEFAULT 60,
        difficulty TEXT DEFAULT 'medium',
        is_active INTEGER DEFAULT 1,
        order_num INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS mock_exam_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mock_exam_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        section TEXT DEFAULT 'reading',
        order_num INTEGER DEFAULT 1,
        FOREIGN KEY(mock_exam_id) REFERENCES mock_exams(id),
        FOREIGN KEY(question_id) REFERENCES questions(id)
    );
    CREATE TABLE IF NOT EXISTS mock_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        mock_exam_id INTEGER NOT NULL,
        total_score INTEGER DEFAULT 0,
        reading_score INTEGER DEFAULT 0,
        listening_score INTEGER DEFAULT 0,
        writing_score INTEGER DEFAULT 0,
        speaking_score INTEGER DEFAULT 0,
        is_passed INTEGER DEFAULT 0,
        is_graduated INTEGER DEFAULT 0,
        answers_json TEXT,
        feedback TEXT,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(mock_exam_id) REFERENCES mock_exams(id)
    );
    """)
    conn.commit(); conn.close()

if __name__=="__main__":
    init_db(); seed_demo_data()
    print("قاعدة البيانات والبيانات التجريبية جاهزة!")


# ══════════════════════════════════════════════════════════════
#  دوال مساعدة للـ handlers (Bot compatibility layer)
# ══════════════════════════════════════════════════════════════

def _safe_exec(sql: str, params: tuple = ()):
    """تنفيذ SQL بأمان مع إرجاع cursor — مطلوب من handlers متعددة"""
    conn = get_db()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur
    except Exception as e:
        print(f"[DB] _safe_exec error: {e} | SQL: {sql[:80]}")
        # إرجاع cursor وهمي لا يكسر الكود
        class _EmptyCursor:
            def fetchone(self): return None
            def fetchall(self): return []
            lastrowid = None
        return _EmptyCursor()
    finally:
        conn.close()


def dict_rows(rows) -> list:
    """تحويل قائمة sqlite3.Row إلى قائمة dict"""
    return [dict(r) for r in rows] if rows else []


def dict_row(row) -> dict | None:
    """تحويل sqlite3.Row واحد إلى dict"""
    return dict(row) if row else None


# ── get_student بـ telegram_id (مطلوبة من handlers.courses و placement_test) ─
def get_student(telegram_id) -> dict | None:
    """جلب بيانات الطالب بـ telegram_id أو الـ id الداخلي"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM students WHERE telegram_id=?", (str(telegram_id),)
    ).fetchone()
    # إذا لم يوجد بـ telegram_id، جرّب كـ id داخلي
    if not row:
        try:
            row = conn.execute(
                "SELECT * FROM students WHERE id=?", (int(telegram_id),)
            ).fetchone()
        except Exception:
            pass
    conn.close()
    return dict(row) if row else None


# ── get_student_level ─────────────────────────────────────────
def get_student_level(telegram_id) -> str:
    """جلب مستوى الطالب"""
    s = get_student(telegram_id)
    return s.get("level", "A1") if s else "A1"


# ── add_xp ───────────────────────────────────────────────────
def add_xp(telegram_id, amount: int, reason: str = ""):
    """إضافة XP للطالب"""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE students SET xp=xp+? WHERE telegram_id=?",
            (amount, str(telegram_id))
        )
        conn.commit()
    except Exception as e:
        print(f"[DB] add_xp error: {e}")
    finally:
        conn.close()


# ── Subscription check ────────────────────────────────────────
def has_active_subscription(telegram_id) -> bool:
    """هل الطالب لديه اشتراك فعّال؟"""
    s = get_student(telegram_id)
    if not s:
        return False
    if s.get("subscription_type") == "premium":
        return True
    if s.get("package_end"):
        try:
            from datetime import date
            end_date = datetime.strptime(str(s["package_end"]), "%Y-%m-%d").date()
            return end_date >= date.today()
        except Exception:
            pass
    return False


# ── Courses & Lessons ─────────────────────────────────────────
def get_courses_by_level(level: str) -> list:
    """جلب الكورسات حسب المستوى"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM lessons WHERE level=? AND is_active=1 ORDER BY order_num",
        (level,)
    ).fetchall()
    # إذا لم توجد بمستوى محدد، أرجع كل الدروس النشطة
    if not rows:
        rows = conn.execute(
            "SELECT * FROM lessons WHERE is_active=1 ORDER BY order_num LIMIT 20"
        ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d.setdefault("name", d.get("title", ""))
        result.append(d)
    return result


def get_lessons_by_course(course_id: int) -> list:
    """جلب دروس كورس معين"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM lessons WHERE id=? OR order_num=? ORDER BY order_num",
        (course_id, course_id)
    ).fetchall()
    conn.close()
    return dict_rows(rows)


def get_lesson(lesson_id: int) -> dict | None:
    """جلب درس واحد"""
    conn = get_db()
    row = conn.execute("SELECT * FROM lessons WHERE id=?", (lesson_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Quiz ──────────────────────────────────────────────────────
def get_quiz_by_lesson_id(lesson_id: int) -> dict | None:
    """جلب كويز مرتبط بدرس (نستخدم questions كبديل)"""
    conn = get_db()
    # أول سؤال MCQ مرتبط بهذا الدرس (تقريبي)
    row = conn.execute(
        "SELECT * FROM questions WHERE question_type='mcq' ORDER BY RANDOM() LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["id"] = d.get("id", lesson_id)
        return d
    return None


def get_quiz_questions(quiz_id: int) -> list:
    """جلب أسئلة كويز"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM questions WHERE question_type IN ('mcq','listening','reading_passage') ORDER BY RANDOM() LIMIT 10"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        # توحيد الأعمدة مع ما تتوقعه handlers
        d.setdefault("question_text", d.get("question_text", ""))
        import json as _json
        options = [d.get("option_a",""), d.get("option_b",""),
                   d.get("option_c",""), d.get("option_d","")]
        d["options"] = _json.dumps([o for o in options if o], ensure_ascii=False)
        d["correct_answer"] = d.get("correct_option", "a")
        d["question_type"] = "mcq"
        result.append(d)
    return result


def add_quiz_attempt(user_id, quiz_id, answers: list, score: int):
    """حفظ محاولة كويز"""
    import json as _json
    _safe_exec(
        """INSERT OR IGNORE INTO error_bank
           (student_id, question_text, wrong_answer, correct_answer, topic, next_review)
           VALUES (?, ?, ?, ?, ?, date('now','+1 day'))""",
        (str(user_id), f"Quiz #{quiz_id}", str(score), str(len(answers)), "Mock Exam")
    )


# ── Placement Test ────────────────────────────────────────────
def get_placement_questions(limit: int = 10) -> list:
    """جلب أسئلة اختبار تحديد المستوى"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM questions WHERE question_type='mcq' ORDER BY RANDOM() LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["question"]     = d.get("question_text", "")
        d["option_a"]     = d.get("option_a", "A")
        d["option_b"]     = d.get("option_b", "B")
        d["option_c"]     = d.get("option_c", "C")
        d["option_d"]     = d.get("option_d", "D")
        # correct_option → int index (a=0, b=1, c=2, d=3)
        opt_map = {"a": 0, "b": 1, "c": 2, "d": 3}
        d["correct_option"] = opt_map.get(
            str(d.get("correct_option", "a")).lower(), 0
        )
        d.setdefault("placement_done", False)
        result.append(d)
    return result


def set_student_level(telegram_id, level: str):
    """تحديث مستوى الطالب"""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE students SET level=? WHERE telegram_id=?",
            (level, str(telegram_id))
        )
        conn.commit()
    finally:
        conn.close()


def set_placement_done(telegram_id):
    """تسجيل أن الطالب أتم اختبار تحديد المستوى"""
    # نستخدم حقل موجود لتخزين هذا (metadata في الـ settings مثلاً)
    _safe_exec(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (f"placement_done_{telegram_id}", "1")
    )


# ── Spelling / SRS (Spaced Repetition System) ─────────────────
def get_spelling_words(level: str = "A1", limit: int = 5) -> list:
    """جلب كلمات للتهجئة حسب المستوى"""
    conn = get_db()
    # محاولة جلب من جدول spelling_words إن وجد، وإلا من questions
    try:
        rows = conn.execute(
            "SELECT * FROM spelling_words WHERE level=? ORDER BY RANDOM() LIMIT ?",
            (level, limit)
        ).fetchall()
    except Exception:
        rows = []
    if not rows:
        # جلب كلمات من جدول questions كبديل
        rows = conn.execute(
            "SELECT id, word_order_answer as word, 'Vocabulary' as level, "
            "'Practice word' as definition, 'Practice this word.' as example_sentence "
            "FROM questions WHERE word_order_answer IS NOT NULL "
            "ORDER BY RANDOM() LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d.setdefault("word", d.get("word", "example"))
        d.setdefault("definition", d.get("definition", "A word to spell"))
        d.setdefault("example_sentence", d.get("example_sentence", "Use the word correctly."))
        d.setdefault("id", d.get("id", 0))
        result.append(d)
    return result


def get_all_spelling_words() -> list:
    """جلب كل كلمات التهجئة"""
    return get_spelling_words(limit=100)


def get_or_create_review(telegram_id, word_id: int) -> dict:
    """إنشاء أو جلب سجل مراجعة SRS"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM spelling_reviews WHERE user_id=? AND word_id=?",
            (str(telegram_id), word_id)
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO spelling_reviews (user_id, word_id, next_review, interval_days, ease_factor, repetitions) "
                "VALUES (?, ?, date('now'), 1, 2.5, 0)",
                (str(telegram_id), word_id)
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM spelling_reviews WHERE user_id=? AND word_id=?",
                (str(telegram_id), word_id)
            ).fetchone()
        return dict(row) if row else {}
    except Exception:
        # الجدول غير موجود — أنشئه ثم أعد المحاولة
        conn.execute("""CREATE TABLE IF NOT EXISTS spelling_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            word_id INTEGER NOT NULL,
            next_review DATE DEFAULT (date('now')),
            interval_days INTEGER DEFAULT 1,
            ease_factor REAL DEFAULT 2.5,
            repetitions INTEGER DEFAULT 0,
            UNIQUE(user_id, word_id)
        )""")
        conn.commit()
        return {}
    finally:
        conn.close()


def get_due_reviews(telegram_id, limit: int = 10) -> list:
    """جلب الكلمات المستحقة للمراجعة اليوم"""
    conn = get_db()
    try:
        # محاولة جدول spelling_reviews + spelling_words
        rows = conn.execute(
            """SELECT sr.*, sw.word, sw.definition, sw.example_sentence, sr.id as review_id, sw.id as word_id
               FROM spelling_reviews sr
               JOIN spelling_words sw ON sr.word_id = sw.id
               WHERE sr.user_id=? AND sr.next_review <= date('now')
               ORDER BY sr.next_review ASC LIMIT ?""",
            (str(telegram_id), limit)
        ).fetchall()
    except Exception:
        rows = []
    conn.close()
    return dict_rows(rows)


def update_review(telegram_id, word_id: int, quality: int, elapsed_sec: float):
    """تحديث سجل مراجعة SRS بعد الإجابة (خوارزمية SM-2 مبسطة)"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM spelling_reviews WHERE user_id=? AND word_id=?",
            (str(telegram_id), word_id)
        ).fetchone()
        if not row:
            conn.close()
            return
        r = dict(row)
        ef   = max(1.3, r["ease_factor"] + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        reps = r["repetitions"] + 1
        if quality < 3:
            interval = 1
        elif reps == 1:
            interval = 1
        elif reps == 2:
            interval = 6
        else:
            interval = round(r["interval_days"] * ef)
        conn.execute(
            "UPDATE spelling_reviews SET ease_factor=?, repetitions=?, interval_days=?, "
            "next_review=date('now', ?) WHERE user_id=? AND word_id=?",
            (ef, reps, interval, f"+{interval} days", str(telegram_id), word_id)
        )
        conn.commit()
    except Exception as e:
        print(f"[DB] update_review error: {e}")
    finally:
        conn.close()


def add_to_error_bank(telegram_id, word_id: int, misspelled_as: str):
    """إضافة كلمة خاطئة لبنك الأخطاء"""
    _safe_exec(
        """INSERT OR IGNORE INTO error_bank
           (student_id, question_text, wrong_answer, correct_answer, topic, next_review)
           VALUES (?, ?, ?, ?, 'Spelling', date('now'))""",
        (str(telegram_id), f"word_id:{word_id}", misspelled_as, str(word_id))
    )


def get_error_bank(telegram_id, limit: int = 8) -> list:
    """جلب أخطاء التهجئة للطالب"""
    conn = get_db()
    rows = conn.execute(
        "SELECT *, wrong_answer as misspelled_as, correct_answer as word, "
        "'Spelling error' as definition "
        "FROM error_bank WHERE student_id=? AND topic='Spelling' ORDER BY created_at DESC LIMIT ?",
        (str(telegram_id), limit)
    ).fetchall()
    conn.close()
    return dict_rows(rows)


def mark_error_mastered(telegram_id, error_id: int):
    """حذف خطأ من بنك الأخطاء بعد إتقانه"""
    conn = get_db()
    conn.execute(
        "DELETE FROM error_bank WHERE id=? AND student_id=?",
        (error_id, str(telegram_id))
    )
    conn.commit()
    conn.close()


def quality_from_answer(is_correct: bool, elapsed_sec: float) -> int:
    """حساب جودة الإجابة (0-5) للـ SM-2"""
    if not is_correct:
        return 2
    if elapsed_sec < 5:
        return 5   # سريع وصحيح
    if elapsed_sec < 15:
        return 4
    return 3


# ── Daily Challenge ───────────────────────────────────────────
def get_today_challenge() -> dict | None:
    """جلب تحدي اليوم من قاعدة البيانات أو إنشاء واحد"""
    conn = get_db()
    try:
        # محاولة جدول daily_challenges المخصص
        row = conn.execute(
            "SELECT * FROM daily_challenges WHERE challenge_date=date('now') LIMIT 1"
        ).fetchone()
        if row:
            conn.close()
            return dict(row)
    except Exception:
        pass
    # توليد تحدي يومي من جدول questions
    try:
        row = conn.execute(
            "SELECT id, question_text as question, correct_option as answer, 15 as xp_reward "
            "FROM questions WHERE question_type='mcq' ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        if row:
            d = dict(row)
            d["question"] = d.get("question", "ما معنى كلمة 'Eloquent'؟")
            d["answer"]   = str(d.get("answer", "articulate"))
            d["xp_reward"] = 15
            conn.close()
            return d
    except Exception:
        pass
    conn.close()
    # تحدي افتراضي إذا لم توجد أسئلة
    return {
        "id": 1,
        "question": "ما معنى كلمة 'Perseverance' بالعربية؟",
        "answer": "المثابرة",
        "xp_reward": 15,
    }


