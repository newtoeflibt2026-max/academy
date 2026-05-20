import sqlite3
conn = sqlite3.connect('academy.db')
cols = [
    "media_type TEXT",
    "media_file_id TEXT",
    "action_type TEXT",
    "action_label TEXT"
]
for c in cols:
    try:
        conn.execute(f'ALTER TABLE lessons ADD COLUMN {c}')
        print(f'✅ Added: {c}')
    except Exception as e:
        print(f'⚠️  {e}')
conn.commit()
conn.close()
print('DONE')
