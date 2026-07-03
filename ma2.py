import io
p = "routes/foundation.py"
s = io.open(p, encoding="utf-8").read()
anchor = '''    cur.execute("""SELECT COUNT(*) FROM error_bank eb
                     WHERE eb.user_id=?""", (user_id,))
    total = cur.fetchone()[0]'''
inject = '''    # MERGE_MANUAL_MISTAKES: كلمات أضافها الطالب يدوياً
    try:
        cur.execute("""CREATE TABLE IF NOT EXISTS manual_mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, word TEXT, meaning TEXT, kind TEXT,
            is_mastered INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""SELECT id, word, meaning, kind, created_at
                       FROM manual_mistakes WHERE user_id=?
                       ORDER BY created_at DESC LIMIT 200""", (str(user_id),))
        for _mr in cur.fetchall():
            _md = dict(_mr)
            _kind_lbl = "إملاء" if _md.get("kind") == "spelling" else "معنى"
            mistakes.insert(0, {
                "id": "M" + str(_md["id"]),
                "manual_id": _md["id"],
                "question_id": None,
                "error_type": "manual",
                "wrong_answer": _md.get("word",""),
                "correct_answer": _md.get("meaning",""),
                "created_at": _md.get("created_at"),
                "times_correct_after": 0, "is_mastered": 0,
                "explanation_ar": "أضفتها بنفسك (" + _kind_lbl + ")",
                "question_text": "📌 " + _md.get("word",""),
            })
    except Exception as _e:
        print("[MERGE_MANUAL_MISTAKES] skip:", _e)

    cur.execute("""SELECT COUNT(*) FROM error_bank eb
                     WHERE eb.user_id=?""", (user_id,))
    total = cur.fetchone()[0]'''
if "MERGE_MANUAL_MISTAKES" in s:
    print("ALREADY MERGED")
elif anchor in s:
    s = s.replace(anchor, inject, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("MANUAL MISTAKES MERGED")
else:
    print("ANCHOR NOT FOUND")
