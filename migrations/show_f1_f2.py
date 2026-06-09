# -*- coding: utf-8 -*-
"""
Show F1 + F2 lessons and fix order_num.
Idempotent: safe to run on every deploy.
"""
import os, sqlite3

def show_and_order_f1_f2():
    db_path = os.environ.get("DB_PATH", "academy.db")
    print(f"[show_f1_f2] 🔍 DB: {db_path}")
    if not os.path.exists(db_path):
        print(f"[show_f1_f2] ⚠️  DB غير موجود")
        return
    
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    try:
        # 1) إظهار دروس F1 + F2
        cur.execute("UPDATE lessons SET is_active=1 WHERE stage_id IN (1,2) AND is_active=0")
        shown = cur.rowcount
        print(f"[show_f1_f2] ✅ تم إظهار {shown} درس")
        
        # 2) إصلاح order_num لـ F1, F2, F3
        for stage_id, lbl in [(1,"F1"),(2,"F2"),(3,"F3")]:
            cur.execute("SELECT id FROM lessons WHERE stage_id=? ORDER BY id", (stage_id,))
            ids = [r[0] for r in cur.fetchall()]
            for i, lid in enumerate(ids, start=1):
                cur.execute("UPDATE lessons SET order_num=? WHERE id=? AND (order_num IS NULL OR order_num!=?)",
                            (i, lid, i))
            print(f"[show_f1_f2] ✅ {lbl}: {len(ids)} درس مرتّب")
        
        # 3) تفعيل stages F1 + F2
        cur.execute("UPDATE stages SET is_active=1 WHERE id IN (1,2) AND is_active=0")
        st = cur.rowcount
        if st:
            print(f"[show_f1_f2] ✅ تم تفعيل {st} stage")
        
        con.commit()
        print("[show_f1_f2] ✅ اكتمل بنجاح")
    except Exception as e:
        print(f"[show_f1_f2] ❌ خطأ: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    show_and_order_f1_f2()