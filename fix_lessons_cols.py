import sqlite3, sys

conn = sqlite3.connect("academy.db")
c = conn.cursor()

# ── إصلاح جدول lessons ──
cols = [r[1] for r in c.execute("PRAGMA table_info(lessons)").fetchall()]
print("lessons cols:", cols)

to_add = {
    "phase":         "INTEGER DEFAULT 1",
    "order_num":     "INTEGER DEFAULT 0",
    "title_ar":      "TEXT DEFAULT ''",
    "timer_minutes": "INTEGER DEFAULT 0",
    "media_url":     "TEXT DEFAULT ''",
    "content":       "TEXT DEFAULT ''",
}
for col, typ in to_add.items():
    if col not in cols:
        c.execute(f"ALTER TABLE lessons ADD COLUMN {col} {typ}")
        print("added:", col)

# ── إنشاء جدول essay_grading_rules ──
c.execute("""CREATE TABLE IF NOT EXISTS essay_grading_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    criteria TEXT NOT NULL DEFAULT '',
    max_score INTEGER DEFAULT 10,
    description TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")
print("essay_grading_rules OK")

conn.commit()
conn.close()
print("ALL DONE")
