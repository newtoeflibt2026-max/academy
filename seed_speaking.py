import sqlite3, os
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yamen_academy.db")
conn = sqlite3.connect(DB)
c = conn.cursor()
qs = [
    ("speaking", "TOEFL speaking task 1 usually asks you to:", "Read a passage", "Give your opinion on a familiar topic", "Summarize a lecture", "Write a response", "B", "beginner"),
    ("speaking", "What is fluency in speaking?", "Using complex vocabulary", "Speaking smoothly without long pauses", "Speaking very fast", "Having no accent", "B", "intermediate"),
    ("speaking", "In integrated speaking, you should include:", "Only your personal opinion", "Both the source material AND your opinion", "Only the source material", "Only facts, no opinions", "B", "advanced"),
]
c.executemany("INSERT INTO questions (skill,question,option_a,option_b,option_c,option_d,correct_answer,difficulty) VALUES (?,?,?,?,?,?,?,?)", qs)
conn.commit(); conn.close()
print("3 Speaking questions seeded")
