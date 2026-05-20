import sqlite3
conn = sqlite3.connect("academy.db")
c = conn.cursor()

# احذف كل الباقات القديمة
c.execute("DELETE FROM subscription_plans")

# أضف 3 باقات نظيفة
plans = [
    ("free",    "التجربة المجانية", 0,  "JOD", 7,  "جرّب الأكاديمية مجاناً لمدة أسبوع",        '["امتحان تحديد المستوى","درسان يومياً"]',           1, 0),
    ("basic",   "الباقة الأساسية",  25, "JOD", 30, "اشتراك شهري كامل بجميع المميزات",           '["جميع الدروس","مهام يومية","متابعة التقدم"]',       1, 1),
    ("premium", "الباقة المميزة",   45, "JOD", 90, "اشتراك ثلاثة أشهر مع دعم شخصي",            '["كل مزايا الأساسية","تصحيح مقالات","mock exam"]',  1, 0),
]
c.executemany("""INSERT INTO subscription_plans
    (name,name_ar,price,currency,duration_days,description,features,is_active,is_featured)
    VALUES (?,?,?,?,?,?,?,?,?)""", plans)

conn.commit()
print("plans:", c.execute("SELECT COUNT(*) FROM subscription_plans").fetchone()[0])

# تحقق من الطالب الموجود
student = c.execute("SELECT * FROM students LIMIT 1").fetchone()
if student:
    cols = [d[0] for d in c.execute("PRAGMA table_info(students)").fetchall()]
    print("student:", dict(zip(cols, student)))

conn.close()
print("DONE")
