import sqlite3, json
conn = sqlite3.connect("academy.db")
c = conn.cursor()

# أضف الأعمدة الناقصة
to_add = {
    "option_a":      "TEXT DEFAULT ''",
    "option_b":      "TEXT DEFAULT ''",
    "option_c":      "TEXT DEFAULT ''",
    "option_d":      "TEXT DEFAULT ''",
    "correct_option":"TEXT DEFAULT 'a'",
    "timer_seconds": "INTEGER DEFAULT 30",
    "is_active":     "INTEGER DEFAULT 1",
}
cols = [r[1] for r in c.execute("PRAGMA table_info(questions)").fetchall()]
for col, typ in to_add.items():
    if col not in cols:
        c.execute(f"ALTER TABLE questions ADD COLUMN {col} {typ}")
        print("added:", col)

# أضف الأسئلة التجريبية
questions = [
    ("What is the main idea of an academic passage?","To entertain","To inform and argue","To describe feelings","To tell stories","b","reading","medium",30),
    ("The word 'subsequent' most likely means:","Previous","Following","Important","Difficult","b","reading","medium",30),
    ("What does 'infer' mean in academic reading?","To state directly","To conclude from evidence","To memorize facts","To summarize","b","reading","easy",30),
    ("A 'thesis statement' in an essay is:","The conclusion","The main argument","A supporting detail","A question","b","reading","easy",30),
    ("Academic texts are best described as:","Casual writing","Formal and evidence-based","Personal journals","Creative fiction","b","reading","easy",30),
    ("Which sentence is grammatically correct?","She go to school","She goes to school","She going to school","She goed to school","b","writing","easy",30),
    ("An 'integrated essay' in TOEFL requires:","Only reading","Only listening","Both reading and listening","Personal opinion only","c","writing","medium",30),
    ("The best way to start a body paragraph is:","With a question","With a topic sentence","With a conclusion","With a quotation only","b","writing","easy",30),
    ("Which transition shows contrast?","Furthermore","In addition","However","Therefore","c","writing","medium",30),
    ("Academic writing should be:","Informal and casual","Formal and objective","Emotional and personal","Short and vague","b","writing","easy",30),
    ("In TOEFL listening, a lecture is given by:","A student","A professor","A librarian","A tourist","b","listening","easy",30),
    ("What does 'gist' mean in listening?","Specific detail","Main idea","New vocabulary","Background noise","b","listening","medium",30),
    ("When taking notes you should:","Write every word","Write key ideas only","Draw pictures only","Not write anything","b","listening","easy",30),
    ("Signal words like 'first, then, finally' indicate:","Contrast","Sequence","Cause and effect","Examples","b","listening","easy",30),
    ("A conversation in TOEFL listening involves:","One speaker","Two speakers","Three speakers","A narrator only","b","listening","medium",30),
    ("In TOEFL Speaking Task 1 you should:","Read a passage aloud","Express a personal opinion","Summarize a lecture","Write an essay","b","speaking","easy",30),
    ("Good TOEFL speaking responses are:","Long and detailed","Clear organized and fluent","Very fast with no pauses","Filled with complex vocabulary only","b","speaking","medium",30),
    ("The prep time for TOEFL Speaking Task 1 is:","10 seconds","15 seconds","30 seconds","60 seconds","b","speaking","medium",30),
    ("Which skill is most important in TOEFL speaking?","Accent","Coherence and fluency","Speed only","Loudness","b","speaking","easy",30),
    ("An integrated speaking task requires you to:","Only speak freely","Read listen then speak","Write and speak","Listen and write","b","speaking","medium",30),
]

c.executemany("""INSERT INTO questions
    (question_text,option_a,option_b,option_c,option_d,correct_option,skill,difficulty,timer_seconds,is_active)
    VALUES (?,?,?,?,?,?,?,?,?,1)""", questions)

conn.commit()
total = c.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
print(f"Total questions: {total}")
conn.close()
print("DONE")
