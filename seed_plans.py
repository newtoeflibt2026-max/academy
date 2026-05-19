import sqlite3
conn = sqlite3.connect('academy.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS subscription_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    name_ar TEXT NOT NULL,
    price REAL NOT NULL,
    currency TEXT DEFAULT "IQD",
    duration_days INTEGER DEFAULT 30,
    description TEXT,
    features TEXT DEFAULT "[]",
    is_active INTEGER DEFAULT 1,
    is_featured INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime("now")),
    updated_at TEXT DEFAULT (datetime("now"))
)''')

# باقات افتراضية
plans = [
    ("basic", "الباقة الأساسية", 25000, "IQD", 30,
     "مناسبة للمبتدئين",
     '["الوصول للدروس الأساسية","المهام اليومية","تتبع التقدم"]',
     1, 0),
    ("standard", "الباقة المتوسطة", 45000, "IQD", 60,
     "للطلاب الجادين",
     '["جميع مميزات الأساسية","Mock Exam","تصحيح الكتابة","دعم أولوية"]',
     1, 1),
    ("premium", "الباقة المتقدمة", 75000, "IQD", 90,
     "للتحضير الكامل",
     '["جميع المميزات","جلسات خاصة","شهادة إتمام","دعم 24/7"]',
     1, 0),
]
for p in plans:
    c.execute('''INSERT OR IGNORE INTO subscription_plans
        (name,name_ar,price,currency,duration_days,description,features,is_active,is_featured)
        VALUES (?,?,?,?,?,?,?,?,?)''', p)

conn.commit()
conn.close()
print("ALL DONE")
