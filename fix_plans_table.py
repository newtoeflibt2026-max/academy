import sqlite3
conn = sqlite3.connect("academy.db")
c = conn.cursor()

# اعرض الوضع الحالي
cols = [r[1] for r in c.execute("PRAGMA table_info(subscription_plans)").fetchall()]
print("before:", cols)

# احذف وأعد الإنشاء
c.execute("DROP TABLE IF EXISTS subscription_plans")
c.execute("""CREATE TABLE subscription_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT DEFAULT '',
    name_ar TEXT DEFAULT '',
    price REAL DEFAULT 25000,
    currency TEXT DEFAULT 'IQD',
    duration_days INTEGER DEFAULT 30,
    description TEXT DEFAULT '',
    features TEXT DEFAULT '[]',
    is_active INTEGER DEFAULT 1,
    is_featured INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")

# أضف البيانات الافتراضية
plans = [
    ("basic",    "الباقة الأساسية",  25000, "IQD", 30, "اشتراك شهري",       '["امتحانات يومية","متابعة التقدم"]',                          1, 0),
    ("standard", "الباقة المميزة",   45000, "IQD", 60, "اشتراك شهرين",      '["كل مزايا الأساسية","تصحيح المقالات","امتحان mock"]',        1, 1),
    ("premium",  "الباقة الكاملة",   75000, "IQD", 90, "اشتراك ثلاثة أشهر",'["كل المزايا","دعم شخصي","شهادة إتمام"]',                     1, 0),
]
c.executemany("""INSERT INTO subscription_plans
    (name,name_ar,price,currency,duration_days,description,features,is_active,is_featured)
    VALUES (?,?,?,?,?,?,?,?,?)""", plans)

conn.commit()

# تحقق
cols2 = [r[1] for r in c.execute("PRAGMA table_info(subscription_plans)").fetchall()]
print("after:", cols2)
count = c.execute("SELECT COUNT(*) FROM subscription_plans").fetchone()[0]
print("rows:", count)
conn.close()
print("DONE")
