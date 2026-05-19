import sqlite3
conn = sqlite3.connect("academy.db")
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS placement_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_text TEXT NOT NULL,
    option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
    correct_option TEXT DEFAULT 'A',
    skill TEXT DEFAULT 'grammar',
    difficulty TEXT DEFAULT 'medium',
    is_active INTEGER DEFAULT 1
)""")

questions = [
    ("Choose the correct verb: She ___ to school every day.", "go", "goes", "going", "gone", "B", "grammar"),
    ("What is the synonym of 'happy'?", "sad", "angry", "joyful", "tired", "C", "vocabulary"),
    ("Choose the correct form: They ___ playing football now.", "is", "are", "was", "were", "B", "grammar"),
    ("Which word means the opposite of 'ancient'?", "old", "modern", "large", "small", "B", "vocabulary"),
    ("Choose the correct sentence:", "She don't like coffee", "She doesn't likes coffee", "She doesn't like coffee", "She not like coffee", "C", "grammar"),
    ("The word 'benevolent' means:", "cruel", "kind", "lazy", "clever", "B", "vocabulary"),
    ("Choose the correct preposition: She arrived ___ Monday.", "in", "on", "at", "by", "B", "grammar"),
    ("Which sentence is correct?", "I have went there", "I have gone there", "I have go there", "I went there yesterday", "B", "grammar"),
    ("What does 'eloquent' mean?", "silent", "well-spoken", "confused", "angry", "B", "vocabulary"),
    ("Choose the correct form: If I ___ rich, I would travel.", "am", "was", "were", "be", "C", "grammar"),
    ("The main idea of a paragraph is usually in the:", "last sentence", "middle sentence", "topic sentence", "conclusion", "C", "reading"),
    ("Choose the correct article: ___ apple a day keeps the doctor away.", "A", "An", "The", "No article", "B", "grammar"),
    ("What does 'meticulous' mean?", "careless", "very careful", "fast", "slow", "B", "vocabulary"),
    ("Choose the correct conjunction: I like tea ___ coffee.", "but", "or", "and", "so", "C", "grammar"),
    ("Which is a compound sentence?", "She runs.", "She runs fast.", "She runs and he walks.", "Running is fun.", "C", "grammar"),
    ("The word 'abundant' means:", "scarce", "plentiful", "expensive", "simple", "B", "vocabulary"),
    ("Choose the correct tense: By tomorrow, I ___ the report.", "finish", "finished", "will have finished", "have finished", "C", "grammar"),
    ("What is an inference?", "A direct quote", "A conclusion based on evidence", "A main idea", "A summary", "B", "reading"),
    ("Choose the correct form: Neither John nor his friends ___ coming.", "is", "are", "was", "were", "B", "grammar"),
    ("The word 'contemplate' means:", "ignore", "think about", "destroy", "create", "B", "vocabulary"),
]

for q in questions:
    c.execute("""INSERT OR IGNORE INTO placement_questions
        (question_text,option_a,option_b,option_c,option_d,correct_option,skill)
        VALUES (?,?,?,?,?,?,?)""", q)

conn.commit()
print("Added", len(questions), "questions")
conn.close()
