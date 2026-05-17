import sqlite3, os
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yamen_academy.db")
conn = sqlite3.connect(DB)
c = conn.cursor()
qs = [
    ("listening", "What should you focus on during a lecture?", "Every single word", "Key points and transitions", "Only the examples", "The speaker's accent", "B", "beginner"),
    ("listening", "Gist questions test your ability to:", "Understand specific numbers", "Get the overall meaning", "Repeat exact words", "Identify grammar mistakes", "B", "intermediate"),
    ("listening", "What is a common signal word for a contrast?", "Similarly", "In addition", "However", "For example", "C", "intermediate"),
]
c.executemany("INSERT INTO questions (skill,question,option_a,option_b,option_c,option_d,correct_answer,difficulty) VALUES (?,?,?,?,?,?,?,?)", qs)
conn.commit(); conn.close()
print("3 Listening questions seeded")
