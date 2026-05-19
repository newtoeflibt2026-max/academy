# -*- coding: utf-8 -*-
import sqlite3, os, json

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")

def fix_all():
    conn = sqlite3.connect(DB_PATH)

    print("=" * 50)
    print("بدء الاصلاح الشامل")
    print("=" * 50)

    # 1. إصلاح جدول students
    student_cols = [r[1] for r in conn.execute("PRAGMA table_info(students)").fetchall()]
    student_fixes = [
        ("is_paid", "INTEGER DEFAULT 0"),
        ("level", "TEXT DEFAULT 'beginner'"),
        ("placement_done", "INTEGER DEFAULT 0"),
        ("placement_score", "REAL DEFAULT 0"),
        ("xp", "INTEGER DEFAULT 0"),
        ("streak", "INTEGER DEFAULT 0"),
        ("last_active", "TEXT"),
        ("phone", "TEXT"),
        ("mock_exam_score", "REAL DEFAULT 0"),
        ("missions_completed", "INTEGER DEFAULT 0"),
        ("total_xp", "INTEGER DEFAULT 0"),
        ("stage", "INTEGER DEFAULT 1"),
        ("registered_at", "TEXT"),
        ("full_name", "TEXT"),
    ]
    for col, defn in student_fixes:
        if col not in student_cols:
            try:
                conn.execute("ALTER TABLE students ADD COLUMN " + col + " " + defn)
                print("students." + col + " added")
            except Exception as e:
                print("skip students." + col + ": " + str(e))

    # 2. إصلاح جدول lessons
    lesson_cols = [r[1] for r in conn.execute("PRAGMA table_info(lessons)").fetchall()]
    lesson_fixes = [
        ("description", "TEXT DEFAULT ''"),
        ("skill_type", "TEXT DEFAULT 'reading'"),
        ("vocabulary", "TEXT DEFAULT ''"),
        ("grammar_rule", "TEXT DEFAULT ''"),
        ("audio_url", "TEXT DEFAULT ''"),
        ("stage", "INTEGER DEFAULT 1"),
        ("xp_reward", "INTEGER DEFAULT 20"),
        ("is_active", "INTEGER DEFAULT 1"),
        ("unlock_day", "INTEGER DEFAULT 1"),
        ("quiz_json", "TEXT DEFAULT '[]'"),
        ("order_num", "INTEGER DEFAULT 1"),
    ]
    for col, defn in lesson_fixes:
        if col not in lesson_cols:
            try:
                conn.execute("ALTER TABLE lessons ADD COLUMN " + col + " " + defn)
                print("lessons." + col + " added")
            except Exception as e:
                print("skip lessons." + col + ": " + str(e))

    # 3. جدول essay_grading_rules
    conn.execute(
        "CREATE TABLE IF NOT EXISTS essay_grading_rules ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "topic TEXT NOT NULL,"
        "target_keywords TEXT DEFAULT '[]',"
        "academic_connectors TEXT DEFAULT '[]',"
        "forbidden_words TEXT DEFAULT '[]',"
        "points_per_keyword INTEGER DEFAULT 2,"
        "points_per_connector INTEGER DEFAULT 3,"
        "penalty_per_forbidden INTEGER DEFAULT 1,"
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP"
        ")"
    )
    print("essay_grading_rules table ready")

    # 4. جدول user_skills_progress
    conn.execute(
        "CREATE TABLE IF NOT EXISTS user_skills_progress ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "telegram_id TEXT NOT NULL,"
        "reading_xp INTEGER DEFAULT 0,"
        "listening_xp INTEGER DEFAULT 0,"
        "speaking_xp INTEGER DEFAULT 0,"
        "writing_xp INTEGER DEFAULT 0,"
        "updated_at TEXT DEFAULT CURRENT_TIMESTAMP"
        ")"
    )

    # 5. جدول daily_missions
    conn.execute(
        "CREATE TABLE IF NOT EXISTS daily_missions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "title TEXT NOT NULL,"
        "description TEXT,"
        "mission_type TEXT DEFAULT 'general',"
        "skill_type TEXT DEFAULT 'reading',"
        "xp_reward INTEGER DEFAULT 20,"
        "target_date TEXT,"
        "is_active INTEGER DEFAULT 1,"
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP"
        ")"
    )

    # 6. جدول system_settings
    conn.execute(
        "CREATE TABLE IF NOT EXISTS system_settings ("
        "key TEXT PRIMARY KEY,"
        "value TEXT,"
        "updated_at TEXT DEFAULT CURRENT_TIMESTAMP"
        ")"
    )

    # 7. جدول placement_questions
    conn.execute(
        "CREATE TABLE IF NOT EXISTS placement_questions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "question_text TEXT NOT NULL,"
        "option_a TEXT,"
        "option_b TEXT,"
        "option_c TEXT,"
        "option_d TEXT,"
        "correct_option TEXT NOT NULL,"
        "skill_type TEXT DEFAULT 'reading',"
        "difficulty TEXT DEFAULT 'medium',"
        "is_active INTEGER DEFAULT 1"
        ")"
    )
    print("all tables ready")

    # 8. الإعدادات الافتراضية
    settings = [
        ("required_score", "59"),
        ("mock_exam_threshold", "69"),
        ("graduation_xp", "500"),
        ("graduation_missions", "10"),
        ("graduation_streak", "3"),
        ("academy_name", "أكاديمية يامن للتوفل"),
        ("channel_id", "@YamenToeflIelts"),
        ("daily_lesson_time", "09:00"),
        ("inactivity_penalty_hours", "48"),
        ("inactivity_xp_penalty", "15"),
    ]
    for k, v in settings:
        conn.execute(
            "INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)", (k, v)
        )
    print("settings seeded")

    # 9. أسئلة اختبار تحديد المستوى
    count = conn.execute("SELECT COUNT(*) FROM placement_questions").fetchone()[0]
    if count < 10:
        questions = [
            ("The professor _____ the experiment three times before getting results.",
             "repeated", "repeating", "has repeated", "repeat", "A", "grammar"),
            ("Choose the word closest in meaning to 'ubiquitous':",
             "rare", "everywhere present", "dangerous", "hidden", "B", "vocabulary"),
            ("The graph _____ a steady increase in global temperatures.",
             "indicate", "indicates", "indicating", "indicated", "B", "grammar"),
            ("Which sentence is grammatically correct?",
             "She don't know the answer.",
             "She doesn't knows the answer.",
             "She doesn't know the answer.",
             "She not know the answer.", "C", "grammar"),
            ("The word 'benevolent' means:",
             "cruel", "kind and generous", "intelligent", "lazy", "B", "vocabulary"),
            ("The study _____ that sleep affects cognitive performance.",
             "suggest", "suggesting", "suggests", "suggested", "C", "grammar"),
            ("Choose the correct word: The results were _____ surprising.",
             "extreme", "extremely", "extremeness", "extremed", "B", "grammar"),
            ("What does 'ambiguous' mean?",
             "clear and obvious", "having two different meanings",
             "very large", "fast-moving", "B", "vocabulary"),
            ("The researchers _____ their findings at the conference last week.",
             "present", "presents", "presented", "presenting", "C", "grammar"),
            ("Which transition word shows contrast?",
             "Furthermore", "Therefore", "However", "Additionally", "C", "vocabulary"),
            ("By the time she graduated, she _____ four research papers.",
             "wrote", "has written", "had written", "writes", "C", "grammar"),
            ("The word 'mitigate' means to:",
             "worsen", "make less severe", "celebrate", "ignore", "B", "vocabulary"),
            ("_____ the heavy rain, the outdoor event continued as planned.",
             "Although", "Despite", "However", "Because", "B", "grammar"),
            ("Choose the word that does NOT belong:",
             "analyze", "examine", "scrutinize", "ignore", "D", "vocabulary"),
            ("The passive voice of 'Scientists discovered a new planet' is:",
             "A new planet discovered by scientists.",
             "A new planet was discovered by scientists.",
             "A new planet has discovered by scientists.",
             "Scientists was discovered a new planet.", "B", "grammar"),
            ("What does 'corroborate' mean?",
             "to contradict", "to confirm or support",
             "to ignore", "to question", "B", "vocabulary"),
            ("If she _____ harder, she would have passed the exam.",
             "studied", "had studied", "studies", "study", "B", "grammar"),
            ("The word 'prevalent' is closest in meaning to:",
             "rare", "ancient", "widespread", "dangerous", "C", "vocabulary"),
            ("Choose the correct sentence:",
             "Neither the students nor the teacher were ready.",
             "Neither the students nor the teacher was ready.",
             "Neither the students nor the teacher are ready.",
             "Neither the students nor the teacher is ready.", "B", "grammar"),
            ("Academic writing should be:",
             "emotional and personal", "objective and formal",
             "simple and childlike", "short and informal", "B", "vocabulary"),
        ]
        for q in questions:
            conn.execute(
                "INSERT INTO placement_questions "
                "(question_text, option_a, option_b, option_c, option_d, correct_option, skill_type, is_active) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
                q
            )
        print(str(len(questions)) + " questions added")
    else:
        print("questions already exist: " + str(count))

        # 10. subscription_plans - الأعمدة الحقيقية: plan_key, plan_name, price, days, speed
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]

    if "subscription_plans" not in tables:
        conn.execute(
            "CREATE TABLE subscription_plans ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "plan_key TEXT UNIQUE NOT NULL,"
            "plan_name TEXT NOT NULL,"
            "price INTEGER NOT NULL,"
            "days INTEGER NOT NULL,"
            "speed INTEGER DEFAULT 1,"
            "description TEXT,"
            "emoji TEXT DEFAULT 'P',"
            "is_active INTEGER DEFAULT 1,"
            "created_at TEXT DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        print("subscription_plans table created")

    # أضف plan_id كـ alias إذا لم يكن موجوداً (للتوافق مع الكود القديم)
    sp_cols = [r[1] for r in conn.execute(
        "PRAGMA table_info(subscription_plans)"
    ).fetchall()]
    if "plan_id" not in sp_cols:
        try:
            conn.execute("ALTER TABLE subscription_plans ADD COLUMN plan_id TEXT")
            conn.execute("UPDATE subscription_plans SET plan_id = plan_key")
            print("Added plan_id alias column")
        except Exception as e:
            print("plan_id skip: " + str(e))

    plans_data = [
        ("flex_30",       "الباقة المرنة 30 يوم",  25000,  30, 1, "درس يومي"),
        ("excellence_90", "باقة التميز 90 يوم",    60000,  90, 1, "90 يوما"),
        ("emergency_30",  "باقة الطوارئ 30 يوم",   45000,  30, 4, "مكثف"),
        ("vip_20h",       "VIP 20 ساعة خاصة",     400000,  60, 1, "خاص"),
    ]

    for pid, name, price, days, speed, desc in plans_data:
        existing = conn.execute(
            "SELECT id FROM subscription_plans WHERE plan_key=?", (pid,)
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO subscription_plans (plan_key, plan_name, price, days, speed, description) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (pid, name, price, days, speed, desc)
            )
            print("Plan added: " + pid)
        else:
            conn.execute(
                "UPDATE subscription_plans SET plan_name=?, price=?, days=?, speed=?, description=? "
                "WHERE plan_key=?",
                (name, price, days, speed, desc, pid)
            )
            print("Plan updated: " + pid)

    conn.commit()
    conn.close()
    print("=" * 50)
    print("DONE - all fixed!")
    print("=" * 50)


if __name__ == "__main__":
    fix_all()
