# -*- coding: utf-8 -*-
"""
startup_seed.py
يُشغَّل تلقائياً عند كل بدء تشغيل على Railway
يضمن وجود الجداول والبيانات الأساسية دائماً
"""
import sqlite3, os, logging

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")
)


def seed():
    conn = sqlite3.connect(DB_PATH)

    # ── الجداول الأساسية ──────────────────────────────────
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            level TEXT DEFAULT 'beginner',
            xp INTEGER DEFAULT 0,
            total_xp INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            last_active TEXT,
            is_paid INTEGER DEFAULT 0,
            placement_done INTEGER DEFAULT 0,
            placement_score REAL DEFAULT 0,
            stage INTEGER DEFAULT 1,
            missions_completed INTEGER DEFAULT 0,
            mock_exam_score REAL DEFAULT 0,
            registered_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            content TEXT DEFAULT '',
            skill_type TEXT DEFAULT 'reading',
            vocabulary TEXT DEFAULT '',
            grammar_rule TEXT DEFAULT '',
            audio_url TEXT DEFAULT '',
            stage INTEGER DEFAULT 1,
            order_num INTEGER DEFAULT 1,
            xp_reward INTEGER DEFAULT 20,
            is_active INTEGER DEFAULT 1,
            unlock_day INTEGER DEFAULT 1,
            quiz_json TEXT DEFAULT '[]',
            course_id INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS placement_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_option TEXT NOT NULL,
            skill_type TEXT DEFAULT 'reading',
            difficulty TEXT DEFAULT 'medium',
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS subscription_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_key TEXT UNIQUE NOT NULL,
            plan_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            days INTEGER NOT NULL,
            speed INTEGER DEFAULT 1,
            description TEXT DEFAULT '',
            emoji TEXT DEFAULT 'P',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT,
            user_id TEXT,
            plan_name TEXT,
            plan_key TEXT,
            start_date TEXT DEFAULT CURRENT_TIMESTAMP,
            end_date TEXT,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS essay_grading_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            target_keywords TEXT DEFAULT '[]',
            academic_connectors TEXT DEFAULT '[]',
            forbidden_words TEXT DEFAULT '[]',
            points_per_keyword INTEGER DEFAULT 2,
            points_per_connector INTEGER DEFAULT 3,
            penalty_per_forbidden INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS daily_missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            mission_type TEXT DEFAULT 'general',
            skill_type TEXT DEFAULT 'reading',
            xp_reward INTEGER DEFAULT 20,
            target_date TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_skills_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT NOT NULL,
            reading_xp INTEGER DEFAULT 0,
            listening_xp INTEGER DEFAULT 0,
            speaking_xp INTEGER DEFAULT 0,
            writing_xp INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT,
            plan_key TEXT,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            receipt_file_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS xp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT,
            xp_amount INTEGER,
            skill_type TEXT,
            reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ── أضف الأعمدة الناقصة في students (للتوافق مع القديم) ──
    student_cols = [r[1] for r in conn.execute(
        "PRAGMA table_info(students)"
    ).fetchall()]
    for col, defn in [
        ("user_id", "TEXT"),
        ("tasks_completed", "INTEGER DEFAULT 0"),
        ("grammar_xp", "INTEGER DEFAULT 0"),
        ("vocabulary_xp", "INTEGER DEFAULT 0"),
    ]:
        if col not in student_cols:
            try:
                conn.execute(
                    "ALTER TABLE students ADD COLUMN " + col + " " + defn
                )
            except Exception:
                pass

    conn.commit()

    # ── باقات الاشتراك ────────────────────────────────────
    for pk, pn, price, days, speed, desc, emoji in [
        ("flex_30",       "الباقة المرنة 30 يوم",  25000,  30, 1,
         "درس يومي + تصحيح كتابي + تتبع التقدم", "M"),
        ("excellence_90", "باقة التميز 90 يوم",    60000,  90, 1,
         "90 يوماً من التدريب المكثف + شهادة", "T"),
        ("emergency_30",  "باقة الطوارئ 30 يوم",   45000,  30, 4,
         "تدريب مكثف 4 دروس يومياً", "E"),
        ("vip_20h",       "VIP 20 ساعة خاصة",     400000,  60, 1,
         "20 ساعة تدريس خاص مع المدرب", "V"),
    ]:
        exists = conn.execute(
            "SELECT id FROM subscription_plans WHERE plan_key=?", (pk,)
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO subscription_plans "
                "(plan_key, plan_name, price, days, speed, description, emoji, is_active) "
                "VALUES (?,?,?,?,?,?,?,1)",
                (pk, pn, price, days, speed, desc, emoji)
            )
    conn.commit()

    # ── أسئلة الـ Placement Test ──────────────────────────
    q_count = conn.execute(
        "SELECT COUNT(*) FROM placement_questions"
    ).fetchone()[0]

    if q_count < 10:
        questions = [
            ("The professor _____ the experiment three times.",
             "repeated","repeating","has repeated","repeat","A","grammar"),
            ("Choose the word closest in meaning to 'ubiquitous':",
             "rare","everywhere present","dangerous","hidden","B","vocabulary"),
            ("The graph _____ a steady increase in temperatures.",
             "indicate","indicates","indicating","indicated","B","grammar"),
            ("Which sentence is grammatically correct?",
             "She don't know.","She doesn't knows.","She doesn't know.","She not know.","C","grammar"),
            ("The word 'benevolent' means:",
             "cruel","kind and generous","intelligent","lazy","B","vocabulary"),
            ("The study _____ that sleep affects performance.",
             "suggest","suggesting","suggests","suggested","C","grammar"),
            ("The results were _____ surprising.",
             "extreme","extremely","extremeness","extremed","B","grammar"),
            ("What does 'ambiguous' mean?",
             "clear","two different meanings","very large","fast","B","vocabulary"),
            ("The researchers _____ findings at the conference last week.",
             "present","presents","presented","presenting","C","grammar"),
            ("Which word shows contrast?",
             "Furthermore","Therefore","However","Additionally","C","vocabulary"),
            ("By graduation, she _____ four papers.",
             "wrote","has written","had written","writes","C","grammar"),
            ("The word 'mitigate' means to:",
             "worsen","make less severe","celebrate","ignore","B","vocabulary"),
            ("_____ the heavy rain, the event continued.",
             "Although","Despite","However","Because","B","grammar"),
            ("Choose the word that does NOT belong:",
             "analyze","examine","scrutinize","ignore","D","vocabulary"),
            ("Passive of 'Scientists discovered a planet':",
             "A planet discovered.","A planet was discovered.","A planet has discovered.","Scientists was discovered.","B","grammar"),
            ("What does 'corroborate' mean?",
             "contradict","confirm or support","ignore","question","B","vocabulary"),
            ("If she _____ harder, she would have passed.",
             "studied","had studied","studies","study","B","grammar"),
            ("The word 'prevalent' means:",
             "rare","ancient","widespread","dangerous","C","vocabulary"),
            ("Correct sentence about neither/nor:",
             "Neither student were ready.","Neither student was ready.",
             "Neither student are ready.","Neither student is ready.","B","grammar"),
            ("Academic writing should be:",
             "emotional","objective and formal","childlike","informal","B","vocabulary"),
        ]
        for q in questions:
            conn.execute(
                "INSERT INTO placement_questions "
                "(question_text,option_a,option_b,option_c,option_d,"
                "correct_option,skill_type,is_active) "
                "VALUES (?,?,?,?,?,?,?,1)",
                q
            )
        conn.commit()
        logger.info("placement questions seeded: " + str(len(questions)))

    # ── دروس القراءة الـ 12 ───────────────────────────────
    l_count = conn.execute(
        "SELECT COUNT(*) FROM lessons"
    ).fetchone()[0]

    if l_count < 5:
        lessons = [
            (1, 1, "Lesson 1: Finding the Main Idea", "reading",
             "The main idea is the central point of a passage. It is usually stated in the topic sentence.",
             "main idea, topic sentence, central point, passage, paragraph",
             "A topic sentence introduces the main idea of a paragraph.", 20),

            (1, 2, "Lesson 2: Supporting Details", "reading",
             "Supporting details provide evidence, examples, or explanations that back up the main idea.",
             "supporting details, evidence, examples, explanation, facts",
             "Use 'for example', 'such as', 'in addition' to introduce details.", 20),

            (1, 3, "Lesson 3: Vocabulary in Context", "reading",
             "When you encounter an unknown word, use context clues from surrounding sentences.",
             "context clues, definition, synonym, antonym, inference",
             "Look for signal words: 'means', 'refers to', 'known as'.", 20),

            (1, 4, "Lesson 4: Making Inferences", "reading",
             "An inference is a conclusion drawn from evidence. It is not directly stated in the text.",
             "inference, conclusion, imply, suggest, evidence",
             "Use 'It can be inferred that...' or 'The author implies...'", 25),

            (1, 5, "Lesson 5: Author's Purpose", "reading",
             "Authors write to inform, persuade, or entertain. Identifying the purpose helps comprehension.",
             "inform, persuade, entertain, purpose, tone",
             "Signal words for persuasion: should, must, need to, clearly.", 25),

            (2, 1, "Lesson 6: Cause and Effect", "reading",
             "Cause and effect passages explain why something happened and what resulted from it.",
             "cause, effect, result, therefore, consequently, because",
             "Use 'because' for cause, 'therefore/consequently' for effect.", 25),

            (2, 2, "Lesson 7: Compare and Contrast", "reading",
             "Comparison shows similarities; contrast shows differences between two subjects.",
             "similar, different, both, however, whereas, on the other hand",
             "Use 'whereas' and 'on the other hand' for contrast.", 25),

            (2, 3, "Lesson 8: Paragraph Organization", "reading",
             "Well-organized paragraphs have a topic sentence, body sentences, and a concluding sentence.",
             "topic sentence, body, conclusion, transition, coherence",
             "Transition words: first, then, finally, in conclusion.", 30),

            (2, 4, "Lesson 9: Reading Charts and Graphs", "reading",
             "TOEFL often includes passages with visual data. Learn to extract key information quickly.",
             "data, trend, increase, decrease, percentage, comparison",
             "Use 'According to the graph/chart...' in your response.", 30),

            (2, 5, "Lesson 10: Academic Vocabulary", "reading",
             "Academic vocabulary appears frequently in TOEFL passages. Master these high-frequency words.",
             "analyze, evaluate, significant, contribute, indicate, establish",
             "These words often replace simple words: show=indicate, important=significant.", 30),

            (3, 1, "Lesson 11: Integrated Reading Strategy", "reading",
             "Combine skimming, scanning, and detailed reading for maximum efficiency.",
             "skimming, scanning, detailed reading, strategy, efficiency",
             "Skim for main idea, scan for details, read closely for inference.", 35),

            (3, 2, "Lesson 12: TOEFL Reading Practice", "reading",
             "Full TOEFL reading passages are 600-700 words with multiple question types.",
             "passage, question types, time management, elimination, re-reading",
             "Eliminate wrong answers first, then choose the best remaining option.", 40),
        ]
        for stage, order_num, title, skill, content, vocab, grammar, xp in lessons:
            conn.execute(
                "INSERT INTO lessons "
                "(stage, order_num, title, skill_type, content, vocabulary, "
                "grammar_rule, xp_reward, is_active, description) "
                "VALUES (?,?,?,?,?,?,?,?,1,?)",
                (stage, order_num, title, skill, content, vocab, grammar, xp, content[:100])
            )
        conn.commit()
        logger.info("12 lessons seeded")

    # ── الإعدادات الافتراضية ──────────────────────────────
    for k, v in [
        ("required_score",           "59"),
        ("mock_exam_threshold",      "69"),
        ("graduation_xp",            "500"),
        ("graduation_missions",      "10"),
        ("graduation_streak",        "3"),
        ("academy_name",             "أكاديمية يامن للتوفل"),
        ("channel_id",               "@YamenToeflIelts"),
        ("daily_lesson_time",        "09:00"),
        ("inactivity_penalty_hours", "48"),
        ("bot_welcome_message",
         "مرحباً بك في أكاديمية يامن للتوفل! 🎓\nطور مهاراتك وحقق هدفك!"),
        ("paid_required_message",
         "هذه الميزة مخصصة للمشتركين فقط.\nتواصل مع الأدمن لتفعيل اشتراكك."),
    ]:
        conn.execute(
            "INSERT OR IGNORE INTO system_settings (key, value) VALUES (?,?)",
            (k, v)
        )
    conn.commit()
    conn.close()
    logger.info("startup_seed completed successfully")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed()
    print("DONE")
