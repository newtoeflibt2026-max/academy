# -*- coding: utf-8 -*-
"""Sync sentence building lessons + exercises from JSON to DB"""
import os, sys, json, glob, sqlite3
sys.stdout.reconfigure(encoding="utf-8")

DB = os.environ.get("DB_PATH", "academy.db")
CONTENT_DIR = "content/sentence_building"

def sync_lessons():
    """Sync foundation lessons from foundation_lessons.json"""
    path = os.path.join(CONTENT_DIR, "foundation_lessons.json")
    if not os.path.exists(path):
        print(f"  [SKIP] No foundation_lessons.json")
        return 0
    with open(path, "r", encoding="utf-8") as f:
        lessons = json.load(f)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM sentence_foundation_lessons")
    for i, L in enumerate(lessons):
        cur.execute("""INSERT INTO sentence_foundation_lessons
            (rule_number, title_ar, title_en, rule_ar, rule_en, formula,
             examples_json, memory_trick_ar, order_index)
            VALUES (?,?,?,?,?,?,?,?,?)""", (
            L.get("rule_number", i+1),
            L.get("title_ar",""), L.get("title_en",""),
            L.get("rule_ar",""), L.get("rule_en",""),
            L.get("formula",""),
            json.dumps(L.get("examples",[]), ensure_ascii=False),
            L.get("memory_trick_ar",""),
            i
        ))
    conn.commit()
    conn.close()
    print(f"  [OK] Synced {len(lessons)} foundation lessons")
    return len(lessons)

def sync_exercises():
    """Sync exercises from all *.json files (except foundation_lessons.json and _schema.json)"""
    files = sorted([f for f in glob.glob(f"{CONTENT_DIR}/*.json")
                    if not os.path.basename(f).startswith("_")
                    and os.path.basename(f) != "foundation_lessons.json"])
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    total_inserted = 0
    total_updated = 0
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        exercises = data if isinstance(data, list) else data.get("exercises", [])
        for ex in exercises:
            code = ex.get("code")
            if not code:
                continue
            cur.execute("SELECT id FROM sentence_building_exercises WHERE code=?", (code,))
            row = cur.fetchone()
            row_data = (
                code,
                ex.get("target_tier","tier59"),
                ex.get("difficulty",1),
                ex.get("word_count", len(ex.get("correct_sentence","").split())),
                ex.get("correct_sentence",""),
                ex.get("arabic_translation",""),
                json.dumps(ex.get("scrambled_words",[]), ensure_ascii=False),
                ex.get("rule_applied",""),
                ex.get("strategy_ar",""),
                ex.get("explanation_ar",""),
                ex.get("common_error_ar",""),
                ex.get("hint_ar",""),
                ex.get("order_index",0)
            )
            if row:
                cur.execute("""UPDATE sentence_building_exercises SET
                    target_tier=?, difficulty=?, word_count=?, correct_sentence=?,
                    arabic_translation=?, scrambled_words_json=?, rule_applied=?,
                    strategy_ar=?, explanation_ar=?, common_error_ar=?, hint_ar=?,
                    order_index=? WHERE code=?""", row_data[1:] + (code,))
                total_updated += 1
            else:
                cur.execute("""INSERT INTO sentence_building_exercises
                    (code, target_tier, difficulty, word_count, correct_sentence,
                     arabic_translation, scrambled_words_json, rule_applied,
                     strategy_ar, explanation_ar, common_error_ar, hint_ar, order_index)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", row_data)
                total_inserted += 1
        print(f"  [OK] {os.path.basename(fp)}: processed {len(exercises)} exercises")
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM sentence_building_exercises")
    total = cur.fetchone()[0]
    conn.close()
    print(f"\n  Inserted: {total_inserted}, Updated: {total_updated}")
    print(f"  Total exercises in DB: {total}")
    return total

if __name__ == "__main__":
    print("="*50)
    print("Syncing Sentence Building Content")
    print("="*50)
    print("\n[LESSONS]")
    sync_lessons()
    print("\n[EXERCISES]")
    sync_exercises()
