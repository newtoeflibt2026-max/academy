import sqlite3, json

conn = sqlite3.connect("academy.db")
c = conn.cursor()

# ── إصلاح جدول questions ──
cols = [r[1] for r in c.execute("PRAGMA table_info(questions)").fetchall()]
for col, typ in {
    "option_a":"TEXT DEFAULT ''","option_b":"TEXT DEFAULT ''",
    "option_c":"TEXT DEFAULT ''","option_d":"TEXT DEFAULT ''",
    "correct_option":"TEXT DEFAULT 'a'",
    "timer_seconds":"INTEGER DEFAULT 30","is_active":"INTEGER DEFAULT 1"
}.items():
    if col not in cols:
        c.execute(f"ALTER TABLE questions ADD COLUMN {col} {typ}")
        print("added to questions:", col)

# ── إنشاء essay_grading_rules ──
c.execute("""CREATE TABLE IF NOT EXISTS essay_grading_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    criteria TEXT NOT NULL DEFAULT '',
    max_score INTEGER DEFAULT 10,
    description TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")

# ── إصلاح phase_settings ──
cols2 = [r[1] for r in c.execute("PRAGMA table_info(phase_settings)").fetchall()]
for col, typ in {
    "phase_number":"INTEGER","phase_name":"TEXT DEFAULT ''",
    "min_xp":"INTEGER DEFAULT 0","min_streak":"INTEGER DEFAULT 0",
    "min_quiz_score":"REAL DEFAULT 0","min_attendance_days":"INTEGER DEFAULT 0",
    "description":"TEXT DEFAULT ''","updated_at":"TEXT DEFAULT CURRENT_TIMESTAMP"
}.items():
    if col not in cols2:
        c.execute(f"ALTER TABLE phase_settings ADD COLUMN {col} {typ}")
        print("added to phase_settings:", col)

# ── إضافة مراحل افتراضية ──
if c.execute("SELECT COUNT(*) FROM phase_settings").fetchone()[0] == 0:
    c.executemany("""INSERT INTO phase_settings
        (phase_number,phase_name,min_xp,min_streak,min_quiz_score,min_attendance_days,description)
        VALUES (?,?,?,?,?,?,?)""", [
        (1,"المبتدئ",0,0,0,0,"المرحلة الأولى"),
        (2,"المتوسط",200,2,60,7,"المرحلة الثانية"),
        (3,"المتقدم",500,5,75,14,"المرحلة الثالثة"),
    ])
    print("phases seeded")

# ── أسئلة تجريبية ──
existing = c.execute("SELECT COUNT(*) FROM questions WHERE option_a != ''").fetchone()[0]
if existing == 0:
    questions = [
        ("What is the main idea of an academic passage?","To entertain","To inform and argue","To describe feelings","To tell stories","b","reading","medium",30),
        ("The word 'subsequent' most likely means:","Previous","Following","Important","Difficult","b","reading","medium",30),
        ("What does 'infer' mean in academic reading?","To state directly","To conclude from evidence","To memorize facts","To summarize","b","reading","easy",30),
        ("A 'thesis statement' is:","The conclusion","The main argument","A supporting detail","A question","b","reading","easy",30),
        ("Academic texts are best described as:","Casual writing","Formal and evidence-based","Personal journals","Creative fiction","b","reading","easy",30),
        ("Which sentence is correct?","She go to school","She goes to school","She going to school","She goed to school","b","writing","easy",30),
        ("Integrated TOEFL essay requires:","Only reading","Only listening","Both reading and listening","Personal opinion only","c","writing","medium",30),
        ("Start a body paragraph with:","A question","A topic sentence","A conclusion","A quotation only","b","writing","easy",30),
        ("Which transition shows contrast?","Furthermore","In addition","However","Therefore","c","writing","medium",30),
        ("Academic writing should be:","Informal","Formal and objective","Emotional","Vague","b","writing","easy",30),
        ("TOEFL listening lecture is given by:","A student","A professor","A librarian","A tourist","b","listening","easy",30),
        ("'Gist' in listening means:","Specific detail","Main idea","New vocabulary","Background noise","b","listening","medium",30),
        ("When taking notes you should:","Write every word","Write key ideas only","Draw pictures","Not write anything","b","listening","easy",30),
        ("'First then finally' indicates:","Contrast","Sequence","Cause and effect","Examples","b","listening","easy",30),
        ("TOEFL listening conversation involves:","One speaker","Two speakers","Three speakers","A narrator only","b","listening","medium",30),
        ("TOEFL Speaking Task 1 requires:","Reading aloud","Personal opinion","Summarizing a lecture","Writing an essay","b","speaking","easy",30),
        ("Good speaking responses are:","Very long","Clear organized fluent","Very fast","Complex vocabulary only","b","speaking","medium",30),
        ("Prep time for Speaking Task 1:","10 seconds","15 seconds","30 seconds","60 seconds","b","speaking","medium",30),
        ("Most important in TOEFL speaking:","Accent","Coherence and fluency","Speed","Loudness","b","speaking","easy",30),
        ("Integrated speaking requires:","Free speaking","Read listen then speak","Write and speak","Listen and write","b","speaking","medium",30),
    ]
    c.executemany("""INSERT INTO questions
        (question_text,option_a,option_b,option_c,option_d,correct_option,skill,difficulty,timer_seconds,is_active)
        VALUES (?,?,?,?,?,?,?,?,?,1)""", questions)
    print(f"added {len(questions)} questions")

conn.commit()
conn.close()
print("ALL DONE")
