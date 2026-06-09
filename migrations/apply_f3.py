# -*- coding: utf-8 -*-
"""
migrations/apply_f3.py
يعمل عند بدء التطبيق على Railway.
- يفحص DB
- يضيف عمود next_review إلى error_bank إن لم يكن موجوداً
- يضيف دروس F3 وأسئلتها إن لم تكن موجودة
- آمن: لا يلمس بيانات الطلاب
"""
import os, sys, sqlite3, json

def apply_f3_migration(db_path=None):
    if not db_path:
        db_path = os.environ.get("DB_PATH", "academy.db")
    
    if not os.path.exists(db_path):
        print(f"[f3_migration] ⚠️ DB غير موجود: {db_path}", flush=True)
        return False
    
    print(f"[f3_migration] 🔍 فحص DB: {db_path}", flush=True)
    
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    # 1) إضافة عمود next_review لـ error_bank
    try:
        cur.execute("PRAGMA table_info(error_bank)")
        cols = [c[1] for c in cur.fetchall()]
        if "next_review" not in cols:
            cur.execute("ALTER TABLE error_bank ADD COLUMN next_review TEXT")
            cur.execute("UPDATE error_bank SET next_review = datetime('now', '+2 days') WHERE next_review IS NULL")
            print("[f3_migration] ✅ أُضيف عمود next_review", flush=True)
        if "last_reviewed_at" not in cols:
            cur.execute("ALTER TABLE error_bank ADD COLUMN last_reviewed_at TEXT")
            print("[f3_migration] ✅ أُضيف عمود last_reviewed_at", flush=True)
    except Exception as e:
        print(f"[f3_migration] ⚠️ خطأ في تعديل error_bank: {e}", flush=True)
    
    # 2) تحميل بيانات F3 من JSON
    json_path = os.path.join(os.path.dirname(__file__), "f3_data.json")
    if not os.path.exists(json_path):
        print(f"[f3_migration] ⚠️ ملف البيانات غير موجود: {json_path}", flush=True)
        con.commit(); con.close()
        return False
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    lessons = data["lessons"]
    questions = data["questions"]
    lesson_cols = data["lesson_columns"]
    question_cols = data["question_columns"]
    
    # 3) إضافة الدروس (INSERT OR IGNORE - لن يستبدل الموجود)
    lessons_added = 0
    for lesson in lessons:
        # تحقق إن كان الدرس موجوداً بنفس الـ id
        cur.execute("SELECT id FROM lessons WHERE id=?", (lesson["id"],))
        if cur.fetchone():
            continue  # موجود، نتخطى
        
        # احصل على الأعمدة الفعلية في DB
        cur.execute("PRAGMA table_info(lessons)")
        db_cols = [c[1] for c in cur.fetchall()]
        
        # احتفظ فقط بالأعمدة المشتركة
        filtered = {k: v for k, v in lesson.items() if k in db_cols}
        cols = ", ".join(filtered.keys())
        placeholders = ", ".join("?" * len(filtered))
        try:
            cur.execute(f"INSERT INTO lessons ({cols}) VALUES ({placeholders})", list(filtered.values()))
            lessons_added += 1
        except Exception as e:
            print(f"[f3_migration] ⚠️ خطأ في إضافة درس {lesson['id']}: {e}", flush=True)
    
    print(f"[f3_migration] ✅ دروس F3 المُضافة: {lessons_added}/{len(lessons)}", flush=True)
    
    # 4) إضافة الأسئلة
    questions_added = 0
    for q in questions:
        # تحقق إن كان السؤال موجوداً
        if q.get("id"):
            cur.execute("SELECT id FROM lesson_questions WHERE id=?", (q["id"],))
            if cur.fetchone():
                continue
        
        cur.execute("PRAGMA table_info(lesson_questions)")
        db_cols = [c[1] for c in cur.fetchall()]
        filtered = {k: v for k, v in q.items() if k in db_cols}
        cols = ", ".join(filtered.keys())
        placeholders = ", ".join("?" * len(filtered))
        try:
            cur.execute(f"INSERT INTO lesson_questions ({cols}) VALUES ({placeholders})", list(filtered.values()))
            questions_added += 1
        except Exception as e:
            print(f"[f3_migration] ⚠️ خطأ في إضافة سؤال {q.get('id')}: {e}", flush=True)
    
    print(f"[f3_migration] ✅ أسئلة F3 المُضافة: {questions_added}/{len(questions)}", flush=True)
    
    con.commit()
    con.close()
    print("[f3_migration] ✅ اكتمل بنجاح", flush=True)
    return True


if __name__ == "__main__":
    apply_f3_migration()