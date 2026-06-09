# -*- coding: utf-8 -*-
"""
migrations/ensure_admin_subscriptions.py
يفعّل اشتراك تجريبي للأدمنز (من ADMIN_IDS env)
وأي معرّفات يدوية في القائمة أدناه.
"""
import os, sqlite3, datetime

# معرّفات الطلاب التجريبيين (للاختبار)
TEST_USERS = [
    5572314718,  # المالك
]

def ensure_admin_subscriptions(db_path=None):
    if not db_path:
        db_path = os.environ.get("DB_PATH", "academy.db")
    
    if not os.path.exists(db_path):
        print(f"[admin_sub] ⚠️ DB غير موجود: {db_path}", flush=True)
        return False
    
    print(f"[admin_sub] 🔍 فحص DB: {db_path}", flush=True)
    
    # اجمع كل المعرّفات (test + admins)
    all_ids = set(TEST_USERS)
    admin_ids_env = os.environ.get("ADMIN_IDS", "")
    for x in admin_ids_env.replace(" ", "").split(","):
        if x.isdigit():
            all_ids.add(int(x))
    
    if not all_ids:
        print("[admin_sub] لا معرّفات للمعالجة", flush=True)
        return True
    
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    # فحص بنية subscriptions
    cur.execute("PRAGMA table_info(subscriptions)")
    cols = [c[1] for c in cur.fetchall()]
    
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=180)
    
    for tg_id in all_ids:
        # تحقق من وجود اشتراك نشط
        try:
            cur.execute("""
                SELECT id FROM subscriptions 
                WHERE telegram_id=? AND is_active=1
                AND (end_date IS NULL OR end_date >= ?)
            """, (tg_id, today.isoformat()))
            existing = cur.fetchone()
            
            if existing:
                print(f"[admin_sub] ℹ️ {tg_id}: اشتراك نشط موجود", flush=True)
                continue
            
            # تأكد من وجود الطالب في students
            cur.execute("SELECT id FROM students WHERE telegram_id=?", (tg_id,))
            student = cur.fetchone()
            if not student:
                print(f"[admin_sub] ⚠️ {tg_id}: ليس في students - تخطّي", flush=True)
                continue
            
            # حدّث is_paid=1
            try:
                cur.execute("UPDATE students SET is_paid=1 WHERE telegram_id=?", (tg_id,))
            except: pass
            
            # أدخل اشتراك
            cur.execute("""
                INSERT INTO subscriptions (telegram_id, plan_name, start_date, end_date, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (tg_id, "foundation_full", today.isoformat(), end_date.isoformat()))
            
            print(f"[admin_sub] ✅ {tg_id}: اشتراك مُفعّل (180 يوم)", flush=True)
        
        except Exception as e:
            print(f"[admin_sub] ⚠️ {tg_id}: {e}", flush=True)
    
    con.commit()
    con.close()
    print("[admin_sub] ✅ اكتمل", flush=True)
    return True


if __name__ == "__main__":
    ensure_admin_subscriptions()