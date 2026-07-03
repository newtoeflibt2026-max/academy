import io
p = "routes/foundation.py"
s = io.open(p, encoding="utf-8").read()
anchor = '@foundation_bp.route("/mistakes")'
new_code = '''@foundation_bp.route("/api/mistakes/add", methods=["POST"])
def api_mistakes_add():
    from flask import request, jsonify
    data = request.get_json(silent=True) or {}
    user_id = str(data.get("user_id") or "")
    word = (data.get("word") or "").strip()
    meaning = (data.get("meaning") or "").strip()
    kind = (data.get("kind") or "meaning").strip()
    if not user_id or not word or not meaning:
        return jsonify({"success": False, "error": "missing fields"}), 400
    conn = db(); cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS manual_mistakes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT, word TEXT, meaning TEXT, kind TEXT,
        is_mastered INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("INSERT INTO manual_mistakes (user_id, word, meaning, kind) VALUES (?,?,?,?)",
                (user_id, word, meaning, kind))
    conn.commit(); conn.close()
    return jsonify({"success": True})


@foundation_bp.route("/api/mistakes/manual/<int:mid>/delete", methods=["POST"])
def api_mistakes_manual_delete(mid):
    from flask import request, jsonify
    data = request.get_json(silent=True) or {}
    user_id = str(data.get("user_id") or "")
    conn = db(); cur = conn.cursor()
    cur.execute("DELETE FROM manual_mistakes WHERE id=? AND user_id=?", (mid, user_id))
    conn.commit(); conn.close()
    return jsonify({"success": True})


'''
if "api_mistakes_add" in s:
    print("ROUTE ALREADY EXISTS")
elif anchor in s:
    s = s.replace(anchor, new_code + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("ADD/DELETE ROUTES ADDED")
else:
    print("ANCHOR NOT FOUND")
