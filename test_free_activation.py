import sqlite3
conn = sqlite3.connect("academy.db")
# نفذ نفس الـ UPDATE الذي يستخدمه payments.py للباقة المجانية
conn.execute("""UPDATE students 
                SET is_paid=1, is_active=1, 
                    subscription_type='مجانية', 
                    package_end=date('now','+7 days') 
                WHERE telegram_id=?""", ('5572314718',))
conn.commit()
# اعرض النتيجة
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT user_id, full_name, is_paid, subscription_type, package_end FROM students WHERE user_id=5572314718").fetchone()
print(dict(row))
conn.close()
