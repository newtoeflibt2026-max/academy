import sqlite3
conn = sqlite3.connect('academy.db')
cols = [r[1] for r in conn.execute('PRAGMA table_info(lessons)').fetchall()]
print('Before:', cols)

to_add = [
    ('description', 'TEXT'),
    ('skill_type', 'TEXT DEFAULT reading'),
    ('vocabulary', 'TEXT'),
    ('grammar_rule', 'TEXT'),
    ('audio_url', 'TEXT'),
    ('stage', 'INTEGER DEFAULT 1'),
    ('order_num', 'INTEGER DEFAULT 1'),
    ('xp_reward', 'INTEGER DEFAULT 10'),
]

for col, definition in to_add:
    if col not in cols:
        try:
            conn.execute(f'ALTER TABLE lessons ADD COLUMN {col} {definition}')
            print(f'Added: {col}')
        except Exception as e:
            print(f'Skip {col}: {e}')

conn.commit()
cols2 = [r[1] for r in conn.execute('PRAGMA table_info(lessons)').fetchall()]
print('After:', cols2)
conn.close()
print('DONE')
