# -*- coding: utf-8 -*-
import sqlite3, json, sys

DB = "academy.db"
JSON_PATH = "content/reading_section.json"

# XP map حسب نوع الدرس
XP_MAP = {
    "R-01": 20, "R-02": 20,
    "R-03": 40, "R-04": 40,
    "R-05": 50, "R-06": 50, "R-07": 50, "R-08": 50,
    "R-09": 30,
    "R-10": 60, "R-11": 60,
    "R-12": 80,
}

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = ON")
cur = conn.cursor()

print("🗑️  حذف الدروس القديمة من جدول lessons...")
cur.execute("DELETE FROM lessons")
print(f"   تم حذف الدروس. باقي: {cur.execute('SELECT COUNT(*) FROM lessons').fetchone()[0]}")

# إضافة عمود lesson_code إذا لم يكن موجوداً
existing_cols = [c[1] for c in cur.execute("PRAGMA table_info(lessons)").fetchall()]
if "lesson_code" not in existing_cols:
    cur.execute("ALTER TABLE lessons ADD COLUMN lesson_code TEXT")
    print("   + عمود lesson_code أُضيف")
if "focus_point" not in existing_cols:
    cur.execute("ALTER TABLE lessons ADD COLUMN focus_point TEXT")
    print("   + عمود focus_point أُضيف")
if "explanation_json" not in existing_cols:
    cur.execute("ALTER TABLE lessons ADD COLUMN explanation_json TEXT")
    print("   + عمود explanation_json أُضيف")

print("\n🏗️  إنشاء الجداول الجديدة...")

cur.execute("""
CREATE TABLE IF NOT EXISTS lesson_letter_fill (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL,
    word TEXT NOT NULL,
    translation TEXT,
    sentence TEXT,
    hint TEXT,
    letter_array_json TEXT,
    order_num INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
)""")
print("   + lesson_letter_fill")

cur.execute("""
CREATE TABLE IF NOT EXISTS lesson_practice_texts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL,
    text_id TEXT,
    level TEXT,
    text_type TEXT,
    content TEXT,
    answers_json TEXT,
    order_num INTEGER DEFAULT 0,
    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
)""")
print("   + lesson_practice_texts")

cur.execute("""
CREATE TABLE IF NOT EXISTS lesson_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL,
    q_id TEXT,
    q_type TEXT,
    question TEXT NOT NULL,
    passage_ref TEXT,
    options_json TEXT,
    correct_answer TEXT,
    explanation TEXT,
    evidence TEXT,
    common_trap TEXT,
    tip TEXT,
    timer_seconds INTEGER DEFAULT 30,
    order_num INTEGER DEFAULT 0,
    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
)""")
print("   + lesson_questions")

cur.execute("""
CREATE TABLE IF NOT EXISTS lesson_drag_drop (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL,
    title TEXT,
    exercise_type TEXT DEFAULT 'sentence_order',
    instructions TEXT,
    items_json TEXT,
    correct_order_json TEXT,
    order_num INTEGER DEFAULT 0,
    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
)""")
print("   + lesson_drag_drop")

conn.commit()

# تحميل JSON
print("\n📥 قراءة JSON...")
with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

lessons = data["lessons"]
print(f"   عدد الدروس: {len(lessons)}")

# استيراد كل درس
stats = {"lessons": 0, "words": 0, "texts": 0, "questions": 0}

for idx, L in enumerate(lessons, start=1):
    code = L["lesson_id"]
    title = L["title"]
    focus = L.get("focus_point", "")
    explanation_json = json.dumps(L.get("explanation", {}), ensure_ascii=False)
    xp = XP_MAP.get(code, 30)

    cur.execute("""
        INSERT INTO lessons
        (title, title_ar, lesson_code, focus_point, explanation_json,
         skill, phase, order_num, xp_reward, timer_minutes, is_active, content)
        VALUES (?,?,?,?,?,'reading',1,?,?,15,1,?)
    """, (title, title, code, focus, explanation_json, idx, xp, focus))
    lesson_pk = cur.lastrowid
    stats["lessons"] += 1

    # 1) letter_fill_exercise
    lfx = L.get("letter_fill_exercise", {})
    for i, w in enumerate(lfx.get("target_words", []), start=1):
        cur.execute("""
            INSERT INTO lesson_letter_fill
            (lesson_id, word, translation, sentence, hint, letter_array_json, order_num)
            VALUES (?,?,?,?,?,?,?)
        """, (lesson_pk, w["word"], w.get("translation",""),
              w.get("sentence",""), w.get("hint",""),
              json.dumps(w.get("letter_array",[]), ensure_ascii=False), i))
        stats["words"] += 1

    # 2) practice_texts (للدرس R-03)
    pts = L.get("practice_texts", {})
    order = 0
    for level in ("easy","medium","difficult"):
        for t in pts.get(level, []):
            order += 1
            cur.execute("""
                INSERT INTO lesson_practice_texts
                (lesson_id, text_id, level, text_type, content, answers_json, order_num)
                VALUES (?,?,?,?,?,?,?)
            """, (lesson_pk, t.get("id",""), level, "complete_words",
                  t.get("text",""),
                  json.dumps(t.get("answers",{}), ensure_ascii=False), order))
            stats["texts"] += 1

    # 3) practice_exercises (للدرس R-04 - بنية مختلفة)
    pex = L.get("practice_exercises", {})
    for level in ("easy","intermediate","difficult"):
        for ex in pex.get(level, []):
            ex_id = ex.get("exercise_id","")
            ex_type = ex.get("type","")
            for q in ex.get("questions", []):
                cur.execute("""
                    INSERT INTO lesson_questions
                    (lesson_id, q_id, q_type, question, passage_ref,
                     options_json, correct_answer, explanation, tip,
                     timer_seconds, order_num)
                    VALUES (?,?,'factual',?,?,?,?,?,?,30,?)
                """, (lesson_pk, q.get("q_id",""), q["question"], f"{ex_id} - {ex_type}",
                      json.dumps(q.get("options",{}), ensure_ascii=False),
                      q.get("correct_answer",""),
                      q.get("explanation",""), q.get("tip",""), 0))
                stats["questions"] += 1

    # 4) practice_questions (R-05 إلى R-08, R-10, R-11)
    pq = L.get("practice_questions", {})
    if isinstance(pq, dict):
        for category, qlist in pq.items():
            if not isinstance(qlist, list):
                continue
            qtype_map = {
                "factual_questions": "factual",
                "negative_factual_questions": "negative_factual",
                "vocabulary_questions": "vocabulary",
                "inference_questions": "inference",
                "rhetorical_purpose_questions": "rhetorical",
                "insert_sentence_questions": "insert_sentence",
                "paragraph_relationship_questions": "paragraph_relation",
            }
            qtype = qtype_map.get(category, category)
            for q in qlist:
                cur.execute("""
                    INSERT INTO lesson_questions
                    (lesson_id, q_id, q_type, question, passage_ref,
                     options_json, correct_answer, explanation, evidence,
                     common_trap, timer_seconds, order_num)
                    VALUES (?,?,?,?,?,?,?,?,?,?,30,0)
                """, (lesson_pk, q.get("q_id",""), qtype,
                      q.get("question",""), q.get("passage", q.get("paragraph","")),
                      json.dumps(q.get("options",{}), ensure_ascii=False),
                      q.get("correct_answer",""),
                      q.get("explanation",""), q.get("evidence",""),
                      q.get("common_trap","")))
                stats["questions"] += 1

    # 5) practice_set (R-10) and practice_set_1/2 (R-10) and practice_set (R-11)
    for set_key in ("practice_set","practice_set_1","practice_set_2"):
        ps = L.get(set_key, {})
        passage = ps.get("passage_title","")
        for q in ps.get("questions", []):
            cur.execute("""
                INSERT INTO lesson_questions
                (lesson_id, q_id, q_type, question, passage_ref,
                 options_json, correct_answer, explanation, evidence,
                 timer_seconds, order_num)
                VALUES (?,?,?,?,?,?,?,?,?,30,0)
            """, (lesson_pk, q.get("q_id",""),
                  q.get("type","factual").lower().replace(" ","_"),
                  q.get("question",""), q.get("passage", passage),
                  json.dumps(q.get("options",{}), ensure_ascii=False),
                  q.get("correct_answer",""),
                  q.get("explanation",""), q.get("evidence","")))
            stats["questions"] += 1

    # 6) final_comprehensive_quiz (R-12)
    fq = L.get("final_comprehensive_quiz", {})
    for q in fq.get("questions", []):
        cur.execute("""
            INSERT INTO lesson_questions
            (lesson_id, q_id, q_type, question, passage_ref,
             options_json, correct_answer, explanation, evidence,
             timer_seconds, order_num)
            VALUES (?,?,?,?,?,?,?,?,?,30,0)
        """, (lesson_pk, q.get("q_id",""),
              q.get("type","factual").lower().replace(" ","_"),
              q.get("question",""), q.get("passage",""),
              json.dumps(q.get("options",{}), ensure_ascii=False),
              q.get("correct_answer",""),
              q.get("explanation",""), q.get("evidence","")))
        stats["questions"] += 1

    # 7) inference_question (سؤال نهائي لكل درس)
    iq = L.get("inference_question", {})
    if iq:
        cur.execute("""
            INSERT INTO lesson_questions
            (lesson_id, q_id, q_type, question,
             options_json, correct_answer, explanation,
             timer_seconds, order_num)
            VALUES (?,?,'inference',?,?,?,?,30,999)
        """, (lesson_pk, f"{code}_final",
              iq.get("question",""),
              json.dumps(iq.get("options",{}), ensure_ascii=False),
              iq.get("correct_answer",""),
              iq.get("explanation","")))
        stats["questions"] += 1

    print(f"   [{idx:2d}/12] {code} | {title[:50]}  → XP={xp}")

conn.commit()

print("\n" + "="*60)
print("📊 الإحصائيات النهائية:")
print("="*60)
for t in ("lessons","lesson_letter_fill","lesson_practice_texts","lesson_questions","lesson_drag_drop"):
    c = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"   {t:30s} → {c}")

print("\n📋 الدروس المضافة (lesson_code | title | XP | عدد الأسئلة):")
rows = cur.execute("""
    SELECT l.lesson_code, l.title, l.xp_reward,
           (SELECT COUNT(*) FROM lesson_questions WHERE lesson_id=l.id) AS q_count,
           (SELECT COUNT(*) FROM lesson_letter_fill WHERE lesson_id=l.id) AS w_count,
           (SELECT COUNT(*) FROM lesson_practice_texts WHERE lesson_id=l.id) AS t_count
    FROM lessons l ORDER BY l.order_num
""").fetchall()
for r in rows:
    print(f"   {r[0]:5s} | XP={r[2]:3d} | Q={r[3]:2d} | W={r[4]:2d} | T={r[5]:2d} | {r[1][:45]}")

conn.close()
print("\n✅ تم بنجاح!")
