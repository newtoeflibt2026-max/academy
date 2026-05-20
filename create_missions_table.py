import sqlite3
conn = sqlite3.connect("academy.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS missions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    mission_type TEXT DEFAULT 'daily',
    xp_reward INTEGER DEFAULT 20,
    target_date TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

cur.execute("PRAGMA table_info(missions)")
cols = cur.fetchall()
print(f"✅ جدول missions جاهز ({len(cols)} أعمدة):")
for c in cols:
    print(f"   - {c[1]} ({c[2]})")

conn.close()
