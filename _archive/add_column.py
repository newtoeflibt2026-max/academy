import sqlite3
conn = sqlite3.connect('academy.db')
try:
    conn.execute('ALTER TABLE lessons ADD COLUMN properties TEXT DEFAULT ""')
    print('✅ Column properties added')
except sqlite3.OperationalError as e:
    if 'duplicate' in str(e).lower():
        print('Column already exists')
    else:
        print(f'Error: {e}')
conn.commit()
conn.close()
