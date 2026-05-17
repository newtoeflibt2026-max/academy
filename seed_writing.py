import sqlite3, os
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yamen_academy.db")
conn = sqlite3.connect(DB)
c = conn.cursor()
qs = [
    ("writing", "What is the first step in TOEFL integrated writing?", "Write your opinion immediately", "Take notes while reading and listening", "Copy the reading word-for-word", "Ignore the listening passage", "B", "beginner"),
    ("writing", "A strong thesis statement should be:", "Vague and general", "Specific and arguable", "A simple fact", "A question", "B", "intermediate"),
    ("writing", "In independent writing, you should spend the first 5 minutes:", "Writing the conclusion", "Checking grammar", "Brainstorming and outlining", "Counting words", "C", "intermediate"),
]
c.executemany("INSERT INTO questions (skill,question,option_a,option_b,option_c,option_d,correct_answer,difficulty) VALUES (?,?,?,?,?,?,?,?)", qs)
conn.commit(); conn.close()
print("3 Writing questions seeded")
