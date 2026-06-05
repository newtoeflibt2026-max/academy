
# ─── Phase Settings ──────────────────────────────────────
@app.route("/api/admin/phase-settings", methods=["GET"])
def api_phase_settings():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM phase_settings ORDER BY phase_number").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/admin/phase-settings/<int:pid>", methods=["PUT"])
def api_update_phase_setting(pid):
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""UPDATE phase_settings SET
            phase_name=?, min_xp=?, min_streak=?,
            min_quiz_score=?, min_attendance_days=?, description=?
            WHERE phase_number=?""",
            (d.get("phase_name",""), int(d.get("min_xp",0)),
             int(d.get("min_streak",0)), float(d.get("min_quiz_score",0)),
             int(d.get("min_attendance_days",0)), d.get("description",""), pid))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# ─── Grading Rules ───────────────────────────────────────
@app.route("/api/admin/grading-rules", methods=["GET"])
def api_get_grading_rules():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM essay_grading_rules ORDER BY id").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/admin/grading-rules", methods=["POST"])
def api_add_grading_rule():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO essay_grading_rules
            (criteria, max_score, description)
            VALUES (?,?,?)""",
            (d.get("criteria",""), int(d.get("max_score",10)),
             d.get("description","")))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/grading-rules/<int:rid>", methods=["DELETE"])
def api_delete_grading_rule(rid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM essay_grading_rules WHERE id=?", (rid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()
