import sqlite3, os
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yamen_academy.db")
conn = sqlite3.connect(DB)
c = conn.cursor()
qs = [
    ("grammar", "Which sentence is grammatically correct?", "She don't like coffee.", "She doesn't likes coffee.", "She doesn't like coffee.", "She not like coffee.", "C", "beginner"),
    ("grammar", "I have been studying is an example of:", "Simple past", "Present perfect continuous", "Past perfect", "Future continuous", "B", "intermediate"),
    ("grammar", "Choose the correct conditional: If I ___ rich, I would travel.", "am", "was", "were", "been", "C", "advanced"),
]
c.executemany("INSERT INTO questions (skill,question,option_a,option_b,option_c,option_d,correct_answer,difficulty) VALUES (?,?,?,?,?,?,?,?)", qs)
conn.commit(); conn.close()
print("3 Grammar questions seeded")
