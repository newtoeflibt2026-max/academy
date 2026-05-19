# -*- coding: utf-8 -*-
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")

def seed():
    conn = sqlite3.connect(DB_PATH)
       # إصلاح جدول lessons
    lesson_cols = [r[1] for r in conn.execute('PRAGMA table_info(lessons)').fetchall()]
    lesson_fixes = [
        ('description', 'TEXT'),
        ('skill_type', 'TEXT'),
        ('vocabulary', 'TEXT'),
        ('grammar_rule', 'TEXT'),
        ('audio_url', 'TEXT'),
        ('stage', 'INTEGER DEFAULT 1'),
        ('xp_reward', 'INTEGER DEFAULT 10'),
    ]
    for col, definition in lesson_fixes:
        if col not in lesson_cols:
            try:
                conn.execute(f'ALTER TABLE lessons ADD COLUMN {col} {definition}')
            except:
                pass
    conn.commit()
 
    # ══ إنشاء جدول placement_questions إن لم يكن موجوداً ══
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS placement_questions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text   TEXT NOT NULL,
        option_a        TEXT,
        option_b        TEXT,
        option_c        TEXT,
        option_d        TEXT,
        correct_option  TEXT,
        skill_type      TEXT DEFAULT 'general',
        is_active       INTEGER DEFAULT 1,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS subscription_plans (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_key        TEXT UNIQUE NOT NULL,
        plan_name       TEXT NOT NULL,
        price           REAL DEFAULT 0,
        days            INTEGER DEFAULT 30,
        speed           INTEGER DEFAULT 1,
        description     TEXT,
        emoji           TEXT DEFAULT '📦',
        is_active       INTEGER DEFAULT 1,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # ══ أسئلة تحديد المستوى ══
    questions = [
        ("Choose the correct sentence:",
         "The researcher explain the results clearly.",
         "The researcher explains the results clearly.",
         "The researcher explaining the results clearly.",
         "The researcher explaineds the results clearly.", "B", "grammar"),

        ("Choose the word closest in meaning to 'significant' in an academic context:",
         "minor", "important", "unclear", "temporary", "B", "vocabulary"),

        ("Complete the sentence: Many universities require students to submit their applications _____ the deadline.",
         "at", "in", "before", "during", "C", "grammar"),

        ("Read the sentence and answer:\nOnline learning has become increasingly popular because it allows students to access educational materials at their own pace and from any location.\nWhy has online learning become popular?",
         "It is cheaper than traditional learning in every case.",
         "It gives students flexibility in time and place.",
         "It replaces all classroom teachers.",
         "It is only used in universities.", "B", "reading"),

        ("Choose the best connector: The experiment was carefully designed; ______, the results were still inconclusive.",
         "therefore", "however", "for example", "similarly", "B", "grammar"),

        ("Read the passage:\nSome scientists believe that urban green spaces improve mental health. They argue that access to parks and gardens reduces stress and encourages physical activity.\nWhat is the main idea?",
         "Cities should remove unused land.",
         "Gardens are expensive to maintain.",
         "Green spaces may benefit psychological well-being.",
         "Scientists dislike urban environments.", "C", "reading"),

        ("Choose the sentence that best completes the idea: The professor's lecture was highly detailed; ______, many students needed additional time to review their notes.",
         "as a result", "in contrast", "for instance", "meanwhile", "A", "grammar"),

        ("Read the passage:\nAlthough the new policy was presented as a cost-saving measure, several faculty members expressed concern that it might reduce access to essential academic resources.\nWhat can be inferred?",
         "All faculty members supported the policy.",
         "The policy may have negative academic consequences.",
         "The policy immediately increased funding.",
         "Essential academic resources were already removed.", "B", "reading"),

        ("Read the sentence:\nThe author cautiously suggests that the findings may indicate a correlation, though further investigation is clearly necessary.\nWhat is the tone?",
         "emotional and exaggerated",
         "humorous and informal",
         "careful and academically reserved",
         "angry and critical", "C", "reading"),

        ("Read the passage:\nThe researcher acknowledges the limitations of the study but maintains that the overall trend in the data is too consistent to be dismissed as coincidence.\nWhich best describes the author's position?",
         "Completely uncertain and confused",
         "Skeptical but somewhat convinced by the evidence",
         "Entirely dismissive of the data",
         "Uninterested in the study's limitations", "B", "reading"),

        ("Choose the correct form: The data _____ been analyzed by the research team.",
         "has", "have", "is", "are", "A", "grammar"),

        ("Choose the word that does NOT belong: enhance, improve, deteriorate, strengthen",
         "enhance", "improve", "deteriorate", "strengthen", "C", "vocabulary"),

        ("The word 'ambiguous' most nearly means:",
         "clear", "uncertain", "important", "difficult", "B", "vocabulary"),

        ("Choose the correct sentence:",
         "Despite of the rain, the event continued.",
         "Despite the rain, the event continued.",
         "Despite that the rain, the event continued.",
         "Despite from the rain, the event continued.", "B", "grammar"),

        ("Read: Researchers found that students who slept at least 8 hours performed significantly better on cognitive tests than those who slept fewer hours.\nWhat conclusion can be drawn?",
         "Sleep has no effect on academic performance.",
         "Cognitive tests are unreliable.",
         "Adequate sleep may improve cognitive performance.",
         "Students should avoid cognitive tests.", "C", "reading"),

        ("Choose the academic connector: The study confirmed the hypothesis. ______, it opened new questions for future research.",
         "However", "Furthermore", "Therefore", "In contrast", "B", "vocabulary"),

        ("Which sentence uses the passive voice correctly?",
         "The committee decided the new policy.",
         "The new policy was decided by the committee.",
         "The committee was deciding the new policy.",
         "The new policy deciding by the committee.", "B", "grammar"),

        ("The word 'Subsequently' means:",
         "before", "at the same time", "after", "instead", "C", "vocabulary"),

        ("Read: While some economists argue that globalization increases inequality, others maintain that it creates opportunities for developing nations.\nWhat does the passage suggest?",
         "Globalization has only negative effects.",
         "There are opposing views on globalization's impact.",
         "Developing nations reject globalization.",
         "Economists agree on globalization's benefits.", "B", "reading"),

        ("Choose the correct sentence about academic writing:",
         "In my opinion I think that the results shows a clear pattern.",
         "The results indicate a clear pattern in the data.",
         "The results it shows a clear pattern obviously.",
         "Obviously the results are showing clear pattern.", "B", "grammar"),
    ]

    conn.execute("DELETE FROM placement_questions")
    conn.executemany(
        """INSERT INTO placement_questions
           (question_text, option_a, option_b, option_c, option_d,
            correct_option, skill_type)
           VALUES (?,?,?,?,?,?,?)""",
        questions
    )

    # ══ باقات الاشتراك ══
    plans = [
        ("flex_30", "المسار المرن 30 يوم", 25, 30, 1,
         "درس واحد يومياً - مناسب للمبتدئين", "🌱"),
        ("excellence_90", "مسار التفوق 90 يوم", 60, 90, 1,
         "المسار الأكاديمي الكامل من الصفر للاحتراف", "🎯"),
        ("emergency_30", "مسار الطوارئ المكثف", 80, 30, 4,
         "حتى 4 دروس يومياً للمتقدمين قبل الامتحان", "🚀"),
        ("vip_20h", "باقة VIP 20 ساعة برايفت", 400, 90, 4,
         "20 ساعة تدريب خاص + مسار الطوارئ مجاناً", "👑"),
    ]

    for plan in plans:
        conn.execute(
            """INSERT OR IGNORE INTO subscription_plans
               (plan_key, plan_name, price, days, speed, description, emoji)
               VALUES (?,?,?,?,?,?,?)""",
            plan
        )

    conn.commit()
    conn.close()
    print(f"✅ أضيف {len(questions)} سؤال placement")
    print("✅ أضيفت الباقات")
    print("DONE")

if __name__ == "__main__":
    seed()
