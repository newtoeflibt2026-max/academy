import io
p = "routes/writing_toefl.py"
s = io.open(p, encoding="utf-8").read()
marker = "def api_lesson_submit"
route_code = '''@writing_bp.route("/writing/my-mistakes")
@require_section_access("writing")
def writing_my_mistakes():
    import json as _json
    tg_id = request.args.get("user_id") or _get_tg_id()
    conn = _db()
    c = conn.cursor()
    rows = c.execute(
        "SELECT answer_json FROM writing_attempts WHERE telegram_id=? AND answer_json IS NOT NULL ORDER BY rowid DESC",
        (str(tg_id),)
    ).fetchall()
    conn.close()
    seen = set()
    mistakes = []
    for r in rows:
        try:
            d = _json.loads(r["answer_json"])
        except Exception:
            continue
        for m in (d.get("mistakes") or []):
            key = (m.get("user_answer",""), m.get("correct_answer",""))
            if key in seen:
                continue
            seen.add(key)
            mistakes.append(m)
    return render_template("toefl_writing/my_mistakes.html",
        mistakes=mistakes, user_id=tg_id, total=len(mistakes))


'''
if "def writing_my_mistakes" in s:
    print("ROUTE ALREADY EXISTS")
else:
    idx = s.find("@writing_bp.route(\"/api/writing/lesson/")
    if idx == -1:
        print("ANCHOR NOT FOUND")
    else:
        s = s[:idx] + route_code + s[idx:]
        io.open(p, "w", encoding="utf-8").write(s)
        print("MISTAKES ROUTE ADDED")
