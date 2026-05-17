import sqlite3, os
db_path = r"C:\Users\nelt2\yamen_academy\data\yamen_academy.db"
conn = sqlite3.connect(db_path)
try:
    conn.execute("ALTER TABLE questions ADD COLUMN image_url TEXT DEFAULT ''")
    conn.commit()
    print("تم اضافة عمود image_url")
except Exception as e:
    print("العمود موجود مسبقاً:", e)
conn.close()
