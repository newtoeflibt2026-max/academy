# -*- coding: utf-8 -*-
"""
migrations/hide_old_f1_f2.py
يُخفي دروس F1 + F2 القديمة (التي لم نبنِها معاً)
سيُعاد بناؤها لاحقاً.
آمن: لا يحذف شيء، فقط is_active=0
"""
import os, sqlite3

def hide_old_f1_f2(db_path=None):
    if not db_path:
        db_path = os.environ.get("DB_PATH", "academy.db")
    
    if not os.path.exists(db_path):
        print(f"[hide_old] ⚠️ DB غير موجود: {db_path}", flush=True)
        return False
    
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    try:
        # إخفاء دروس F1 + F2 القديمة فقط
        cur.execute("UPDATE lessons SET is_active=0 WHERE stage_id IN (1, 2) AND COALESCE(is_active,1)=1")
        hidden = cur.rowcount
        if hidden > 0:
            print(f"[hide_old] ✅ أُخفي {hidden} درس من F1 + F2 القديمة", flush=True)
        else:
            print(f"[hide_old] ℹ️ F1 + F2 مُخفاة مسبقاً", flush=True)
        
        # تأكد ظهور F3
        cur.execute("UPDATE lessons SET is_active=1 WHERE stage_id=3 AND COALESCE(is_active,0)=0")
        if cur.rowcount > 0:
            print(f"[hide_old] ✅ أُعيد إظهار {cur.rowcount} درس F3", flush=True)
        
        # إخفاء stages F1, F2 (لا تظهر كأقسام)
        cur.execute("UPDATE stages SET is_active=0 WHERE code IN ('F1', 'F2') AND is_active=1")
        if cur.rowcount > 0:
            print(f"[hide_old] ✅ أُخفيت stages F1, F2", flush=True)
        
        # تأكد ظهور F3
        cur.execute("UPDATE stages SET is_active=1 WHERE code='F3' AND is_active=0")
        if cur.rowcount > 0:
            print(f"[hide_old] ✅ أُعيد إظهار stage F3", flush=True)
        
        con.commit()
    except Exception as e:
        print(f"[hide_old] ⚠️ خطأ: {e}", flush=True)
    
    con.close()
    print("[hide_old] ✅ اكتمل", flush=True)
    return True


if __name__ == "__main__":
    hide_old_f1_f2()