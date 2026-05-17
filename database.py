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


