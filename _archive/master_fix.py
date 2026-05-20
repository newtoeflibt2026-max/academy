import sqlite3
conn = sqlite3.connect("academy.db")
c = conn.cursor()

# ── الجداول الناقصة ──────────────────────────────────────
c.executescript("""
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT '',
    title_ar TEXT DEFAULT '',
    description TEXT DEFAULT '',
    skill TEXT DEFAULT 'reading',
    phase INTEGER DEFAULT 1,
    order_num INTEGER DEFAULT 0,
    content TEXT DEFAULT '',
    media_url TEXT DEFAULT '',
    xp_reward INTEGER DEFAULT 10,
    timer_minutes INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscription_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT DEFAULT '',
    name_ar TEXT DEFAULT '',
    price REAL DEFAULT 0,
    currency TEXT DEFAULT 'JOD',
    duration_days INTEGER DEFAULT 30,
    description TEXT DEFAULT '',
    features TEXT DEFAULT '[]',
    is_active INTEGER DEFAULT 1,
    is_featured INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS placement_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_text TEXT NOT NULL DEFAULT '',
    option_a TEXT DEFAULT '',
    option_b TEXT DEFAULT '',
    option_c TEXT DEFAULT '',
    option_d TEXT DEFAULT '',
    correct_option TEXT DEFAULT 'a',
    skill TEXT DEFAULT 'grammar',
    difficulty TEXT DEFAULT 'medium',
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS essay_grading_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    criteria TEXT DEFAULT '',
    max_score INTEGER DEFAULT 10,
    description TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT DEFAULT '',
    message TEXT DEFAULT '',
    target TEXT DEFAULT 'all',
    target_user_id INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS student_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT DEFAULT '',
    full_name TEXT DEFAULT '',
    message TEXT DEFAULT '',
    is_read INTEGER DEFAULT 0,
    replied INTEGER DEFAULT 0,
    reply_text TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
""")

# ── إصلاح daily_missions: حذف عمود target_date من الاستعلامات ──
cols = [r[1] for r in c.execute("PRAGMA table_info(daily_missions)").fetchall()]
print("daily_missions cols:", cols)
for col, typ in {
    "mission_type": "TEXT DEFAULT 'quiz'",
    "target_count": "INTEGER DEFAULT 1",
    "xp_reward":    "INTEGER DEFAULT 20",
    "is_active":    "INTEGER DEFAULT 1",
}.items():
    if col not in cols:
        c.execute(f"ALTER TABLE daily_missions ADD COLUMN {col} {typ}")
        print("added:", col)

# ── إصلاح questions ──────────────────────────────────────
cols2 = [r[1] for r in c.execute("PRAGMA table_info(questions)").fetchall()]
for col, typ in {
    "option_a":      "TEXT DEFAULT ''",
    "option_b":      "TEXT DEFAULT ''",
    "option_c":      "TEXT DEFAULT ''",
    "option_d":      "TEXT DEFAULT ''",
    "correct_option":"TEXT DEFAULT 'a'",
    "timer_seconds": "INTEGER DEFAULT 30",
    "is_active":     "INTEGER DEFAULT 1",
    "explanation":   "TEXT DEFAULT ''",
}.items():
    if col not in cols2:
        c.execute(f"ALTER TABLE questions ADD COLUMN {col} {typ}")
        print("added to questions:", col)

# ── إصلاح phase_settings ─────────────────────────────────
cols3 = [r[1] for r in c.execute("PRAGMA table_info(phase_settings)").fetchall()]
for col, typ in {
    "phase_number":       "INTEGER DEFAULT 1",
    "phase_name":         "TEXT DEFAULT ''",
    "min_xp":             "INTEGER DEFAULT 0",
    "min_streak":         "INTEGER DEFAULT 0",
    "min_quiz_score":     "REAL DEFAULT 0",
    "min_attendance_days":"INTEGER DEFAULT 0",
    "description":        "TEXT DEFAULT ''",
}.items():
    if col not in cols3:
        c.execute(f"ALTER TABLE phase_settings ADD COLUMN {col} {typ}")
        print("added to phase_settings:", col)

# ── إصلاح system_settings ────────────────────────────────
cols4 = [r[1] for r in c.execute("PRAGMA table_info(system_settings)").fetchall()]
for col, typ in {
    "description": "TEXT DEFAULT ''",
    "updated_at":  "TEXT DEFAULT CURRENT_TIMESTAMP",
}.items():
    if col not in cols4:
        c.execute(f"ALTER TABLE system_settings ADD COLUMN {col} {typ}")
        print("added to system_settings:", col)

# ── إصلاح payments ───────────────────────────────────────
cols5 = [r[1] for r in c.execute("PRAGMA table_info(payments)").fetchall()]
for col, typ in {
    "user_id":     "INTEGER DEFAULT 0",
    "plan_id":     "INTEGER DEFAULT 1",
    "amount":      "REAL DEFAULT 0",
    "currency":    "TEXT DEFAULT 'JOD'",
    "status":      "TEXT DEFAULT 'pending'",
    "proof_file":  "TEXT DEFAULT ''",
    "notes":       "TEXT DEFAULT ''",
    "verified_at": "TEXT DEFAULT ''",
}.items():
    if col not in cols5:
        c.execute(f"ALTER TABLE payments ADD COLUMN {col} {typ}")
        print("added to payments:", col)

# ── إصلاح students ───────────────────────────────────────
cols6 = [r[1] for r in c.execute("PRAGMA table_info(students)").fetchall()]
for col, typ in {
    "is_paid":          "INTEGER DEFAULT 0",
    "is_active":        "INTEGER DEFAULT 1",
    "xp":               "INTEGER DEFAULT 0",
    "streak":           "INTEGER DEFAULT 0",
    "tasks_completed":  "INTEGER DEFAULT 0",
    "mock_score":       "REAL DEFAULT 0",
    "current_phase":    "INTEGER DEFAULT 1",
    "placement_done":   "INTEGER DEFAULT 0",
    "placement_score":  "REAL DEFAULT 0",
    "completed_lessons":"TEXT DEFAULT '[]'",
    "phone":            "TEXT DEFAULT ''",
    "level":            "TEXT DEFAULT 'beginner'",
}.items():
    if col not in cols6:
        c.execute(f"ALTER TABLE students ADD COLUMN {col} {typ}")
        print("added to students:", col)

# ── باقات افتراضية ───────────────────────────────────────
if c.execute("SELECT COUNT(*) FROM subscription_plans").fetchone()[0] == 0:
    c.executemany("""INSERT INTO subscription_plans
        (name,name_ar,price,currency,duration_days,description,is_active,is_featured)
        VALUES (?,?,?,?,?,?,?,?)""", [
        ("free",     "الباقة المجانية",  0,  "JOD", 7,  "تجربة مجانية لمدة أسبوع", 1, 0),
        ("basic",    "الباقة الأساسية",  25, "JOD", 30, "اشتراك شهري كامل",         1, 1),
        ("premium",  "الباقة المميزة",   45, "JOD", 90, "اشتراك ثلاثة أشهر",        1, 0),
    ])
    print("plans seeded")

# ── إعدادات النظام ────────────────────────────────────────
defaults = [
    ("subscription_currency", "JOD",        "عملة الاشتراك"),
    ("subscription_price",    "25",          "سعر الاشتراك الأساسي"),
    ("admin_phone",           "0798919150",  "رقم هاتف الأدمن"),
    ("graduation_min_xp",     "500",         "الحد الأدنى XP للتخرج"),
    ("graduation_min_tasks",  "50",          "الحد الأدنى مهام للتخرج"),
    ("graduation_min_streak", "7",           "الحد الأدنى streak للتخرج"),
    ("graduation_min_mock_score", "70",      "الحد الأدنى درجة mock"),
    ("question_timer_seconds","30",          "وقت السؤال بالثواني"),
    ("exam_timer_minutes",    "60",          "وقت الامتحان بالدقائق"),
    ("bot_welcome_message",   "مرحباً بك في أكاديمية يامن للتوفل! 🎓", "رسالة الترحيب"),
    ("paid_required_message", "هذه الميزة للمشتركين فقط. اضغط للاشتراك.", "رسالة الميزات المدفوعة"),
]
for key, value, desc in defaults:
    c.execute("""INSERT INTO system_settings (key,value,description)
        VALUES (?,?,?)
        ON CONFLICT(key) DO NOTHING""", (key, value, desc))

# ── مراحل افتراضية ───────────────────────────────────────
if c.execute("SELECT COUNT(*) FROM phase_settings").fetchone()[0] == 0:
    c.executemany("""INSERT INTO phase_settings
        (phase_number,phase_name,min_xp,min_streak,min_quiz_score,min_attendance_days,description)
        VALUES (?,?,?,?,?,?,?)""", [
        (1, "المبتدئ",  0,   0, 0,  0,  "المرحلة الأولى"),
        (2, "المتوسط",  200, 2, 60, 7,  "المرحلة الثانية"),
        (3, "المتقدم",  500, 5, 75, 14, "المرحلة الثالثة"),
    ])
    print("phases seeded")

# ── أسئلة placement افتراضية ─────────────────────────────
if c.execute("SELECT COUNT(*) FROM placement_questions").fetchone()[0] == 0:
    pqs = [
        ("Choose the correct verb: She ___ to school every day.", "go", "goes", "going", "gone", "b", "grammar", "easy"),
        ("What is the opposite of 'ancient'?", "Old", "Modern", "Huge", "Tiny", "b", "vocabulary", "easy"),
        ("The lecture was about climate ___.", "change", "changed", "changes", "changing", "a", "grammar", "medium"),
        ("Choose the correct sentence:", "He don't like coffee", "He doesn't likes coffee", "He doesn't like coffee", "He not like coffee", "c", "grammar", "easy"),
        ("'Subsequent' means:", "Before", "After", "During", "Without", "b", "vocabulary", "medium"),
        ("The passive form of 'They built the bridge' is:", "The bridge builds", "The bridge was built", "The bridge is build", "The bridge built", "b", "grammar", "medium"),
        ("Which word means 'to make better'?", "Worsen", "Improve", "Ignore", "Reduce", "b", "vocabulary", "easy"),
        ("Choose the correct preposition: She is interested ___ music.", "on", "at", "in", "of", "c", "grammar", "easy"),
        ("'Ambiguous' means:", "Clear", "Having two meanings", "Simple", "Accurate", "b", "vocabulary", "hard"),
        ("The students ___ studying when the teacher arrived.", "was", "were", "are", "is", "b", "grammar", "medium"),
    ]
    c.executemany("""INSERT INTO placement_questions
        (question_text,option_a,option_b,option_c,option_d,correct_option,skill,difficulty)
        VALUES (?,?,?,?,?,?,?,?)""", pqs)
    print("placement questions seeded")

# ── أسئلة عامة ───────────────────────────────────────────
if c.execute("SELECT COUNT(*) FROM questions WHERE option_a != ''").fetchone()[0] == 0:
    qs = [
        ("What is the main idea of an academic passage?","To entertain","To inform and argue","To describe feelings","To tell stories","b","reading","medium",30),
        ("The word 'subsequent' most likely means:","Previous","Following","Important","Difficult","b","reading","medium",30),
        ("What does 'infer' mean in reading?","State directly","Conclude from evidence","Memorize facts","Summarize","b","reading","easy",30),
        ("A thesis statement is:","The conclusion","The main argument","A supporting detail","A question","b","reading","easy",30),
        ("Which sentence is correct?","She go to school","She goes to school","She going","She goed","b","writing","easy",30),
        ("Integrated TOEFL essay requires:","Only reading","Only listening","Both reading and listening","Opinion only","c","writing","medium",30),
        ("Which transition shows contrast?","Furthermore","In addition","However","Therefore","c","writing","medium",30),
        ("TOEFL listening lecture is given by:","A student","A professor","A librarian","A tourist","b","listening","easy",30),
        ("'Gist' in listening means:","Specific detail","Main idea","New vocabulary","Background noise","b","listening","medium",30),
        ("TOEFL Speaking Task 1 requires:","Reading aloud","Personal opinion","Summarizing","Writing","b","speaking","easy",30),
    ]
    c.executemany("""INSERT INTO questions
        (question_text,option_a,option_b,option_c,option_d,correct_option,skill,difficulty,timer_seconds,is_active)
        VALUES (?,?,?,?,?,?,?,?,?,1)""", qs)
    print("questions seeded")

conn.commit()
conn.close()
print("\n✅ ALL DONE - Database fully initialized")
