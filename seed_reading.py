import sqlite3, os
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yamen_academy.db")
conn = sqlite3.connect(DB)
c = conn.cursor()
qs = [
    ("reading", "What is the main idea of a passage?", "The smallest detail", "The author's opinion only", "The overall point the author is making", "The first sentence of each paragraph", "C", "beginner"),
    ("reading", "Which word best describes a supporting detail?", "Contradicting evidence", "A piece of evidence that strengthens the main idea", "An unrelated fact", "The conclusion", "B", "beginner"),
    ("reading", "What does 'imply' mean in a reading context?", "To state directly", "To suggest without stating directly", "To argue against", "To summarize", "B", "intermediate"),
    ("reading", "Inference questions ask you to:", "Find a specific fact", "Understand the author's purpose", "Draw a conclusion not directly stated", "Memorize vocabulary", "C", "advanced"),
    ("reading", "A paragraph's topic sentence usually appears:", "In the middle", "At the very end", "At the beginning", "Only in the title", "C", "beginner"),
]
c.executemany("INSERT INTO questions (skill,question,option_a,option_b,option_c,option_d,correct_answer,difficulty) VALUES (?,?,?,?,?,?,?,?)", qs)
conn.commit(); conn.close()
print("5 Reading questions seeded")
