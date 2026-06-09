# -*- coding: utf-8 -*-
"""
migrations/ensure_schema.py
يضمن وجود كل الأعمدة المطلوبة في جميع الجداول.
يعمل في كل deploy على Railway.
"""
import os, sys, sqlite3

def ensure_schema(db_path=None):
    if not db_path:
        db_path = os.environ.get("DB_PATH", "academy.db")
    
    if not os.path.exists(db_path):
        print(f"[ensure_schema] ⚠️ DB غير موجود: {db_path}", flush=True)
        return False
    
    print(f"[ensure_schema] 🔍 فحص DB: {db_path}", flush=True)
    
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    # تعريف الأعمدة المطلوبة لكل جدول
    required_columns = {
        "error_bank": [
            ("next_review", "TEXT"),
            ("last_reviewed_at", "TEXT"),
            ("times_retried", "INTEGER DEFAULT 0"),
            ("times_correct_after", "INTEGER DEFAULT 0"),
            ("is_mastered", "INTEGER DEFAULT 0"),
            ("explanation_ar", "TEXT"),
            ("concept_ar", "TEXT"),
            ("lesson_id", "INTEGER"),
        ],
        "lesson_questions": [
            ("concept", "TEXT"),
            ("set_number", "INTEGER"),
            ("explanation_ar", "TEXT"),
            ("translation_ar", "TEXT"),
            ("why_a", "TEXT"),
            ("why_b", "TEXT"),
            ("why_c", "TEXT"),
            ("why_d", "TEXT"),
            ("blanks_json", "TEXT"),
            ("passage_text", "TEXT"),
            ("rubric_json", "TEXT"),
            ("scrambled_words", "TEXT"),
            ("expected_answer", "TEXT"),
            ("word_count_min", "INTEGER"),
            ("word_count_max", "INTEGER"),
            ("audio_url", "TEXT"),
            ("image_url", "TEXT"),
            ("timer_seconds", "INTEGER"),
            ("passage_ref", "TEXT"),
            ("evidence", "TEXT"),
            ("common_trap", "TEXT"),
            ("tip", "TEXT"),
        ],
        "lessons": [
            ("lesson_code", "TEXT"),
            ("stage_id", "INTEGER"),
            ("order_num", "INTEGER"),
            ("xp_reward", "INTEGER DEFAULT 10"),
        ],
    }
    
    total_added = 0
    for table, cols_to_add in required_columns.items():
        # تحقق من وجود الجدول
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cur.fetchone():
            print(f"[ensure_schema] ⚠️ جدول {table} غير موجود - تخطّي", flush=True)
            continue
        
        # احصل على الأعمدة الموجودة
        cur.execute(f"PRAGMA table_info({table})")
        existing = [c[1] for c in cur.fetchall()]
        
        added = 0
        for col_name, col_def in cols_to_add:
            if col_name not in existing:
                try:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                    added += 1
                    total_added += 1
                except Exception as e:
                    print(f"[ensure_schema] ⚠️ {table}.{col_name}: {e}", flush=True)
        
        if added > 0:
            print(f"[ensure_schema] ✅ {table}: أُضيف {added} عمود", flush=True)
        else:
            print(f"[ensure_schema] ℹ️ {table}: كل الأعمدة موجودة", flush=True)
    
    # تحديث next_review للقيم NULL
    try:
        cur.execute("UPDATE error_bank SET next_review = datetime('now', '+2 days') WHERE next_review IS NULL")
        if cur.rowcount > 0:
            print(f"[ensure_schema] ✅ تحديث next_review لـ {cur.rowcount} سجل", flush=True)
    except: pass
    
    con.commit()
    con.close()
    print(f"[ensure_schema] ✅ اكتمل - إجمالي الأعمدة المُضافة: {total_added}", flush=True)
    return True


if __name__ == "__main__":
    ensure_schema()