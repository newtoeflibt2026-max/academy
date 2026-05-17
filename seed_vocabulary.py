import sqlite3, os
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yamen_academy.db")
conn = sqlite3.connect(DB)
c = conn.cursor()
qs = [
    ("vocabulary", "What is a synonym for essential?", "Optional", "Unnecessary", "Crucial", "Minor", "C", "beginner"),
    ("vocabulary", "The word analyze means to:", "Ignore completely", "Examine in detail", "Summarize briefly", "Copy", "B", "intermediate"),
    ("vocabulary", "Ubiquitous most nearly means:", "Rare", "Everywhere", "Invisible", "Unique", "B", "advanced"),
]
c.executemany("INSERT INTO questions (skill,question,option_a,option_b,option_c,option_d,correct_answer,difficulty) VALUES (?,?,?,?,?,?,?,?)", qs)
conn.commit(); conn.close()
print("3 Vocabulary questions seeded")
