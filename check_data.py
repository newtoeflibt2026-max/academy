import sqlite3, os
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")
conn = sqlite3.connect(DB)
print("subscription_plans rows:", conn.execute("SELECT COUNT(*) FROM subscription_plans").fetchone()[0])
print("lessons rows:", conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0])
print("placement_questions rows:", conn.execute("SELECT COUNT(*) FROM placement_questions").fetchone()[0])
print("daily_missions cols:", [r[1] for r in conn.execute("PRAGMA table_info(daily_missions)").fetchall()])
conn.close()
