# -*- coding: utf-8 -*-
"""
F1 Migration: adds missing F1 lessons to production DB.
Idempotent: uses INSERT OR IGNORE pattern.
Preserves student data.
"""
import os, sqlite3, json

def apply_f1_migration():
    db = os.environ.get("DB_PATH", "academy.db")
    print(f"[f1_migration] 🔍 DB: {db}")
    if not os.path.exists(db):
        print(f"[f1_migration] ⚠️  DB not found")
        return
    
    here = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(here, "f1_data.json")
    if not os.path.exists(data_file):
        print(f"[f1_migration] ⚠️  data file not found: {data_file}")
        return
    
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    lessons = data["lessons"]
    questions = data["questions"]
    lq_columns = data["lq_columns"]
    
    con = sqlite3.connect(db)
    cur = con.cursor()
    
    try:
        # 1) أعمدة جدول lessons الفعلية في DB الإنتاج
        cur.execute("PRAGMA table_info(lessons)")
        prod_lesson_cols = {c[1] for c in cur.fetchall()}
        
        cur.execute("PRAGMA table_info(lesson_questions)")
        prod_lq_cols = {c[1] for c in cur.fetchall()}
        
        # 2) إضافة الدروس المفقودة
        lessons_added = 0
        for lesson in lessons:
            lid = lesson["id"]
            
            # هل الدرس موجود؟
            cur.execute("SELECT id FROM lessons WHERE id=?", (lid,))
            if cur.fetchone():
                # موجود - تحقق هل محتواه فارغ (دروس قديمة بدون content)
                cur.execute("SELECT LENGTH(COALESCE(content,'')) FROM lessons WHERE id=?", (lid,))
                clen = cur.fetchone()[0]
                if clen < 500:  # محتوى ناقص أو فارغ → نُحدّثه
                    # نُحدّث الحقول المهمة فقط
                    update_fields = []
                    update_values = []
                    for col in ["title", "title_ar", "content", "lesson_code", "stage_id",
                                "explanation_json", "skill", "xp_reward", "timer_minutes",
                                "order_num", "is_active", "pass_score"]:
                        if col in prod_lesson_cols and col in lesson and lesson[col] is not None:
                            update_fields.append(f"{col}=?")
                            update_values.append(lesson[col])
                    if update_fields:
                        update_values.append(lid)
                        cur.execute(
                            f"UPDATE lessons SET {', '.join(update_fields)} WHERE id=?",
                            update_values
                        )
                        print(f"[f1_migration] 🔄 درس ID:{lid} محدّث ({lesson['title'][:40]})")
                continue
            
            # غير موجود - أضِفه
            cols = [c for c in lesson.keys() if c in prod_lesson_cols]
            vals = [lesson[c] for c in cols]
            placeholders = ",".join(["?"] * len(cols))
            cur.execute(
                f"INSERT INTO lessons ({','.join(cols)}) VALUES ({placeholders})",
                vals
            )
            lessons_added += 1
            print(f"[f1_migration] ✅ درس مضاف ID:{lid} ({lesson['title'][:40]})")
        
        print(f"[f1_migration] ✅ دروس F1 المُضافة: {lessons_added}/{len(lessons)}")
        
        # 3) إضافة الأسئلة المفقودة
        questions_added = 0
        questions_total = 0
        for lid_str, qs in questions.items():
            lid = int(lid_str)
            for q in qs:
                questions_total += 1
                qid = q.get("id")
                # هل السؤال موجود؟
                cur.execute("SELECT id FROM lesson_questions WHERE id=?", (qid,))
                if cur.fetchone():
                    continue
                
                cols = [c for c in q.keys() if c in prod_lq_cols]
                vals = [q[c] for c in cols]
                placeholders = ",".join(["?"] * len(cols))
                try:
                    cur.execute(
                        f"INSERT INTO lesson_questions ({','.join(cols)}) VALUES ({placeholders})",
                        vals
                    )
                    questions_added += 1
                except Exception as e:
                    print(f"[f1_migration] ⚠️  failed Q:{qid}: {e}")
        
        print(f"[f1_migration] ✅ أسئلة F1 المُضافة: {questions_added}/{questions_total}")
        
        con.commit()
        print("[f1_migration] ✅ اكتمل بنجاح")
    except Exception as e:
        print(f"[f1_migration] ❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
    finally:
        con.close()

if __name__ == "__main__":
    apply_f1_migration()