import sqlite3
conn = sqlite3.connect(r"C:\yamen_academy\data\academy.db")
try:
    conn.execute("ALTER TABLE subscriptions ADD COLUMN active INTEGER DEFAULT 1")
    print("✅ Added: active")
except Exception as e:
    if 'duplicate' in str(e).lower():
        print("Already exists: active")
    else:
        print(f"Error: {e}")
# Also add subscriptions_config table
conn.executescript("""
    CREATE TABLE IF NOT EXISTS subscription_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        key TEXT UNIQUE NOT NULL,
        price REAL NOT NULL,
        days INTEGER NOT NULL,
        active INTEGER DEFAULT 1
    );
""")
conn.commit()

# Seed default plans if empty
count = conn.execute("SELECT COUNT(*) FROM subscription_plans").fetchone()[0]
if count == 0:
    plans = [
        ("🥉 شهر واحد", "1month", 10, 30),
        ("🥈 3 شهور", "3months", 25, 90),
        ("🥇 سنة كاملة", "yearly", 80, 365),
    ]
    for name, key, price, days in plans:
        conn.execute("INSERT OR IGNORE INTO subscription_plans(name,key,price,days) VALUES(?,?,?,?)",
                     (name, key, price, days))
    print("✅ Seeded 3 plans")
conn.commit()
conn.close()
print("✅ DB fixed")
