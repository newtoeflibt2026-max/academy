# -*- coding: utf-8 -*-
from flask import Flask, jsonify, render_template, request
import os, json
from datetime import datetime
from db import (get_db, get_all_students_db, get_student,
                activate_paid, deactivate_paid, update_student,
                get_setting, set_setting)

app = Flask(__name__)

# Phase 7: Placement test blueprint
try:
    from modules.placement_web import placement_bp
    app.register_blueprint(placement_bp)
    print('[OK] placement_bp registered')
except Exception as _e:
    print('[WARN] placement_bp not loaded:', _e)

app.secret_key = os.getenv("SECRET_KEY", "yamen-secret-2025")

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Pages Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/")
def index():
    from flask import render_template
    return render_template("admin_dashboard.html")

@app.route("/student")
def student():
    from flask import render_template
    return render_template("student_dashboard.html")

@app.route("/api/admin/stats")
def api_stats():
    conn = get_db()
    try:
        total    = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        paid     = conn.execute("SELECT COUNT(*) FROM students WHERE is_paid=1").fetchone()[0]
        active   = conn.execute("SELECT COUNT(*) FROM students WHERE is_active=1").fetchone()[0]
        pending  = conn.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
        plans_c  = conn.execute("SELECT COUNT(*) FROM subscription_plans WHERE is_active=1").fetchone()[0]
        revenue  = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='verified'").fetchone()[0]
        return jsonify({"total_students":total,"paid_students":paid,"active_students":active,
                        "pending_payments":pending,"active_plans":plans_c,"total_revenue":revenue})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Students Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/students")
def api_students():
    q = request.args.get("q","").strip()
    conn = get_db()
    try:
        if q:
            rows = conn.execute(
                "SELECT * FROM students WHERE full_name LIKE ? OR username LIKE ? OR CAST(telegram_id AS TEXT) LIKE ? ORDER BY xp DESC",
                (f"%{q}%",f"%{q}%",f"%{q}%")).fetchall()
        else:
            rows = conn.execute("SELECT * FROM students ORDER BY xp DESC LIMIT 200").fetchall()
        return jsonify({"students":[dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/admin/students/<int:uid>")
def api_student_detail(uid):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM students WHERE telegram_id=?", (uid,)).fetchone()
        if not row: return jsonify({"error":"not found"}), 404
        return jsonify(dict(row))
    finally:
        conn.close()

@app.route("/api/admin/students/<int:uid>/activate-paid", methods=["POST"])
def api_activate_paid(uid):
    activate_paid(uid)
    return jsonify({"ok": True})

@app.route("/api/admin/students/<int:uid>/deactivate-paid", methods=["POST"])
def api_deactivate_paid(uid):
    deactivate_paid(uid)
    return jsonify({"ok": True})

@app.route("/api/admin/students/<int:uid>/toggle-active", methods=["POST"])
def api_toggle_active(uid):
    conn = get_db()
    try:
        row = conn.execute("SELECT is_active FROM students WHERE telegram_id=?", (uid,)).fetchone()
        if not row: return jsonify({"error":"not found"}), 404
        new_val = 0 if row[0] else 1
        conn.execute("UPDATE students SET is_active=? WHERE telegram_id=?", (new_val, uid))
        conn.commit()
        return jsonify({"ok": True, "is_active": new_val})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Questions Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/questions", methods=["GET"])
def api_get_questions():
    skill = request.args.get("skill","")
    conn = get_db()
    try:
        if skill:
            rows = conn.execute("SELECT * FROM questions WHERE skill=? ORDER BY id DESC", (skill,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM questions ORDER BY id DESC LIMIT 200").fetchall()
        return jsonify({"questions":[dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/admin/questions", methods=["POST"])
def api_add_question():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO questions
            (question_text,option_a,option_b,option_c,option_d,correct_option,skill,difficulty,explanation,timer_seconds)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (d.get("question_text",""), d.get("option_a",""), d.get("option_b",""),
             d.get("option_c",""), d.get("option_d",""), d.get("correct_option","a"),
             d.get("skill","grammar"), d.get("difficulty","medium"),
             d.get("explanation",""), int(d.get("timer_seconds",30))))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/questions/<int:qid>", methods=["DELETE"])
def api_delete_question(qid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM questions WHERE id=?", (qid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Lessons Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/lessons", methods=["GET"])
def api_get_lessons():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM lessons ORDER BY phase, order_num").fetchall()
        return jsonify({"lessons":[dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/admin/lessons", methods=["POST"])
def api_add_lesson():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO lessons
            (title,title_ar,description,skill,phase,order_num,content,xp_reward,timer_minutes,is_active)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (d.get("title",""), d.get("title_ar",""), d.get("description",""),
             d.get("skill","reading"), int(d.get("phase",1)), int(d.get("order_num",0)),
             d.get("content",""), int(d.get("xp_reward",10)),
             int(d.get("timer_minutes",0)), int(d.get("is_active",1))))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/lessons/<int:lid>", methods=["PUT"])
def api_update_lesson(lid):
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""UPDATE lessons SET title=?,title_ar=?,description=?,skill=?,
            phase=?,order_num=?,content=?,xp_reward=?,timer_minutes=?,is_active=?
            WHERE id=?""",
            (d.get("title",""), d.get("title_ar",""), d.get("description",""),
             d.get("skill","reading"), int(d.get("phase",1)), int(d.get("order_num",0)),
             d.get("content",""), int(d.get("xp_reward",10)),
             int(d.get("timer_minutes",0)), int(d.get("is_active",1)), lid))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/lessons/<int:lid>", methods=["DELETE"])
def api_delete_lesson(lid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM lessons WHERE id=?", (lid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Missions Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/missions", methods=["GET"])
def api_get_missions():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM daily_missions ORDER BY id DESC").fetchall()
        return jsonify({"missions":[dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/admin/missions", methods=["POST"])
def api_add_mission():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO daily_missions (title,description,mission_type,target_count,xp_reward)
            VALUES (?,?,?,?,?)""",
            (d.get("title",""), d.get("description",""), d.get("mission_type","quiz"),
             int(d.get("target_count",1)), int(d.get("xp_reward",20))))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/missions/<int:mid>", methods=["DELETE"])
def api_delete_mission(mid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM daily_missions WHERE id=?", (mid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Plans Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/plans", methods=["GET"])
def api_get_plans():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM subscription_plans ORDER BY price").fetchall()
        return jsonify({"plans":[dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/admin/plans", methods=["POST"])
def api_add_plan():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO subscription_plans
            (name,name_ar,price,currency,duration_days,description,features,is_active,is_featured)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (d.get("name",""), d.get("name_ar",""), float(d.get("price",25000)),
             d.get("currency","IQD"), int(d.get("duration_days",30)),
             d.get("description",""), json.dumps(d.get("features",[])),
             int(d.get("is_active",1)), int(d.get("is_featured",0))))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/plans/<int:pid>", methods=["PUT"])
def api_update_plan(pid):
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""UPDATE subscription_plans SET
            name=?,name_ar=?,price=?,currency=?,duration_days=?,
            description=?,features=?,is_active=?,is_featured=? WHERE id=?""",
            (d.get("name",""), d.get("name_ar",""), float(d.get("price",25000)),
             d.get("currency","IQD"), int(d.get("duration_days",30)),
             d.get("description",""), json.dumps(d.get("features",[])),
             int(d.get("is_active",1)), int(d.get("is_featured",0)), pid))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/plans/<int:pid>", methods=["DELETE"])
def api_delete_plan(pid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM subscription_plans WHERE id=?", (pid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/plans/<int:pid>/toggle", methods=["POST"])
def api_toggle_plan(pid):
    conn = get_db()
    try:
        row = conn.execute("SELECT is_active FROM subscription_plans WHERE id=?", (pid,)).fetchone()
        if not row: return jsonify({"error":"not found"}), 404
        new_val = 0 if row[0] else 1
        conn.execute("UPDATE subscription_plans SET is_active=? WHERE id=?", (new_val, pid))
        conn.commit()
        return jsonify({"ok": True, "is_active": new_val})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Payments Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/payments", methods=["GET"])
def api_get_payments():
    conn = get_db()
    try:
        rows = conn.execute("""SELECT p.*, s.full_name, s.username
            FROM payments p LEFT JOIN students s ON p.user_id=s.telegram_id
            ORDER BY p.created_at DESC LIMIT 100""").fetchall()
        return jsonify({"payments":[dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/admin/payments/<int:pid>/verify", methods=["POST"])
def api_verify_payment(pid):
    conn = get_db()
    try:
        row = conn.execute("SELECT user_id FROM payments WHERE id=?", (pid,)).fetchone()
        if not row: return jsonify({"error":"not found"}), 404
        conn.execute("UPDATE payments SET status='verified', verified_at=CURRENT_TIMESTAMP WHERE id=?", (pid,))
        conn.execute("UPDATE students SET is_paid=1 WHERE telegram_id=?", (row[0],))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Settings Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/settings", methods=["GET"])
def api_get_settings():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM system_settings").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/admin/settings", methods=["POST"])
def api_update_settings():
    d = request.json or {}
    for key, value in d.items():
        set_setting(key, str(value))
    return jsonify({"ok": True})

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Phase settings Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/phases", methods=["GET"])
def api_get_phases():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM phase_settings ORDER BY phase_number").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/admin/phases/<int:phase_num>", methods=["PUT"])
def api_update_phase(phase_num):
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""UPDATE phase_settings SET
            phase_name=?,min_xp=?,min_streak=?,min_quiz_score=?,min_attendance_days=?,description=?
            WHERE phase_number=?""",
            (d.get("phase_name",""), int(d.get("min_xp",0)), int(d.get("min_streak",0)),
             float(d.get("min_quiz_score",0)), int(d.get("min_attendance_days",0)),
             d.get("description",""), phase_num))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Broadcast Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/broadcast", methods=["POST"])
def api_broadcast():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO broadcasts (title,message,target,target_user_id)
            VALUES (?,?,?,?)""",
            (d.get("title",""), d.get("message",""),
             d.get("target","all"), int(d.get("target_user_id",0))))
        conn.commit()
        return jsonify({"ok": True, "note": "saved - bot will send on next cycle"})
    finally:
        conn.close()

@app.route("/api/admin/broadcast/history", methods=["GET"])
def api_broadcast_history():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM broadcasts ORDER BY created_at DESC LIMIT 50").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Student messages Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/messages", methods=["GET"])
def api_get_messages():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM student_messages ORDER BY created_at DESC LIMIT 100").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/admin/messages/<int:mid>/read", methods=["POST"])
def api_mark_read(mid):
    conn = get_db()
    try:
        conn.execute("UPDATE student_messages SET is_read=1 WHERE id=?", (mid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/student/message", methods=["POST"])
def api_student_message():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO student_messages (user_id,username,full_name,message)
            VALUES (?,?,?,?)""",
            (int(d.get("user_id",0)), d.get("username",""),
             d.get("full_name",""), d.get("message","")))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Public endpoints Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/public/plans", methods=["GET"])
def api_public_plans():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM subscription_plans WHERE is_active=1 ORDER BY price").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/user/graduation-status", methods=["GET"])
def api_grad_status():
    uid = request.args.get("user_id", 0, type=int)
    if not uid:
        return jsonify({"error": "user_id required"}), 400
    conn = get_db()
    try:
        student = conn.execute("SELECT * FROM students WHERE telegram_id=?", (uid,)).fetchone()
        if not student:
            return jsonify({"error": "not found"}), 404
        s = dict(student)
        min_xp    = int(get_setting("graduation_min_xp", "500"))
        min_tasks = int(get_setting("graduation_min_tasks", "50"))
        min_streak= int(get_setting("graduation_min_streak", "7"))
        min_mock  = float(get_setting("graduation_min_mock_score", "70"))
        checks = {
            "xp":     {"current": s.get("xp",0),             "required": min_xp,    "ok": s.get("xp",0) >= min_xp},
            "tasks":  {"current": s.get("tasks_completed",0), "required": min_tasks, "ok": s.get("tasks_completed",0) >= min_tasks},
            "streak": {"current": s.get("streak",0),          "required": min_streak,"ok": s.get("streak",0) >= min_streak},
            "mock":   {"current": s.get("mock_score",0),       "required": min_mock,  "ok": s.get("mock_score",0) >= min_mock},
        }
        ready = all(v["ok"] for v in checks.values())
        return jsonify({"ready": ready, "checks": checks, "student": s})
    finally:
        conn.close()


# Ã¢â€â‚¬Ã¢â€â‚¬ Phase Settings Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/phase-settings", methods=["GET"])
def api_phase_settings_get():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM phase_settings ORDER BY phase_number").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/admin/phase-settings/<int:pid>", methods=["PUT"])
def api_phase_settings_put(pid):
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""UPDATE phase_settings SET phase_name=?,min_xp=?,min_streak=?,
            min_quiz_score=?,min_attendance_days=?,description=? WHERE phase_number=?""",
            (d.get("phase_name",""), int(d.get("min_xp",0)), int(d.get("min_streak",0)),
             float(d.get("min_quiz_score",0)), int(d.get("min_attendance_days",0)),
             d.get("description",""), pid))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬ Grading Rules Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/grading-rules", methods=["GET"])
def api_grading_rules_get():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM essay_grading_rules ORDER BY id").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/admin/grading-rules", methods=["POST"])
def api_grading_rules_post():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("INSERT INTO essay_grading_rules (criteria,max_score,description) VALUES (?,?,?)",
            (d.get("criteria",""), int(d.get("max_score",10)), d.get("description","")))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/grading-rules/<int:rid>", methods=["DELETE"])
def api_grading_rules_delete(rid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM essay_grading_rules WHERE id=?", (rid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


# Ã¢â€â‚¬Ã¢â€â‚¬ Quiz Result from Student Portal Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/student/quiz-result", methods=["POST"])
def api_quiz_result():
    d = request.json or {}
    uid      = int(d.get("user_id", 0))
    skill    = d.get("skill", "")
    xp_earned= int(d.get("xp_earned", 0))
    score    = float(d.get("score", 0))
    if uid and xp_earned > 0:
        conn = get_db()
        try:
            conn.execute("UPDATE students SET xp=xp+?, tasks_completed=tasks_completed+1 WHERE telegram_id=?",
                         (xp_earned, uid))
            conn.execute("INSERT INTO xp_log (user_id,amount,reason) VALUES (?,?,?)",
                         (uid, xp_earned, f"quiz_{skill}_{score:.0f}%"))
            conn.commit()
        finally:
            conn.close()
    return jsonify({"ok": True})


# Ã¢â€â‚¬Ã¢â€â‚¬ Add Student Manually Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/students/add", methods=["POST"])
def api_add_student():
    d = request.json or {}
    tid  = int(d.get("telegram_id", 0))
    name = d.get("full_name", "").strip()
    user = d.get("username", "").strip()
    paid = int(d.get("is_paid", 0))
    if not tid:
        return jsonify({"error": "telegram_id Ã™â€¦Ã˜Â·Ã™â€žÃ™Ë†Ã˜Â¨"}), 400
    conn = get_db()
    try:
        conn.execute("""INSERT OR IGNORE INTO students
            (telegram_id, full_name, username, is_paid, is_active)
            VALUES (?,?,?,?,1)""", (tid, name, user, paid))
        if paid:
            conn.execute("UPDATE students SET is_paid=1 WHERE telegram_id=?", (tid,))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬ Phase Settings Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Entry point Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@app.route("/api/student/profile", methods=["GET"])
def api_student_profile():
    uid = request.args.get("user_id", "")
    if not uid:
        return jsonify({"error": "user_id required"}), 400
    conn = get_db()
    try:
        # Ã˜Â§Ã˜Â¨Ã˜Â­Ã˜Â« Ã˜Â¨Ã™Æ’Ã™â€žÃ˜Â§ Ã˜Â§Ã™â€žÃ˜Â¹Ã™â€¦Ã™Ë†Ã˜Â¯Ã™Å Ã™â€ 
        s = conn.execute(
            "SELECT * FROM students WHERE user_id=? OR telegram_id=?",
            (uid, uid)
        ).fetchone()
        if not s:
            return jsonify({"found": False})
        d = dict(s)
        return jsonify({
            "found": True,
            "is_paid": bool(d.get("is_paid", 0)),
            "is_active": bool(d.get("is_active", 0)),
            "full_name": d.get("full_name") or d.get("name", ""),
            "level": d.get("level", "beginner"),
            "xp": d.get("xp", 0) or d.get("total_xp", 0),
            "streak": d.get("streak", 0) or d.get("streak_days", 0),
            "placement_done": bool(d.get("placement_done", 0)),
            "current_phase": d.get("current_phase", 1) or d.get("stage", 1),
            "tasks_completed": d.get("tasks_completed", 0),
            "completed_lessons": d.get("completed_lessons", 0),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# Payment Approval / Rejection endpoints
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

@app.route("/api/admin/payments/<int:pid>/approve", methods=["POST"])
def api_approve_payment(pid):
    from datetime import datetime
    conn = get_db()
    try:
        pay = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
        if not pay:
            return jsonify({"error": "Payment not found"}), 404
        pay = dict(pay)
        uid = pay.get("user_id") or pay.get("telegram_id")
        plan_id = pay.get("plan_id", 1)

        # Ã˜ÂªÃ™ÂÃ˜Â¹Ã™Å Ã™â€ž Ã˜Â§Ã™â€žÃ˜Â·Ã˜Â§Ã™â€žÃ˜Â¨
        conn.execute("""
            UPDATE students SET is_paid=1, is_active=1,
            subscription_type='paid',
            last_activity=?
            WHERE user_id=? OR telegram_id=?
        """, (datetime.now().isoformat(), uid, str(uid)))

        # Ã˜ÂªÃ˜Â­Ã˜Â¯Ã™Å Ã˜Â« Ã˜Â­Ã˜Â§Ã™â€žÃ˜Â© Ã˜Â§Ã™â€žÃ˜Â¯Ã™ÂÃ˜Â¹
        conn.execute("""
            UPDATE payments SET status='approved', verified_at=?
            WHERE id=?
        """, (datetime.now().isoformat(), pid))

        conn.commit()

        # Ã˜Â¥Ã˜Â´Ã˜Â¹Ã˜Â§Ã˜Â± Ã˜Â§Ã™â€žÃ˜Â·Ã˜Â§Ã™â€žÃ˜Â¨ Ã˜Â¹Ã˜Â¨Ã˜Â± Ã˜Â§Ã™â€žÃ˜Â¨Ã™Ë†Ã˜Âª
        try:
            import asyncio, os
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            token = os.environ.get("BOT_TOKEN", "")
            if token and uid:
                async def notify():
                    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                    await bot.send_message(
                        chat_id=int(uid),
                        text="Ã¢Å“â€¦ <b>Ã˜ÂªÃ™â€¦ Ã˜ÂªÃ™ÂÃ˜Â¹Ã™Å Ã™â€ž Ã˜Â§Ã˜Â´Ã˜ÂªÃ˜Â±Ã˜Â§Ã™Æ’Ã™Æ’!</b>\n\nÃ™â€¦Ã˜Â±Ã˜Â­Ã˜Â¨Ã˜Â§Ã™â€¹ Ã˜Â¨Ã™Æ’ Ã™ÂÃ™Å  Ã˜Â£Ã™Æ’Ã˜Â§Ã˜Â¯Ã™Å Ã™â€¦Ã™Å Ã˜Â© Ã™Å Ã˜Â§Ã™â€¦Ã™â€  Ã™â€žÃ™â€žÃ˜ÂªÃ™Ë†Ã™ÂÃ™â€ž Ã°Å¸Å½â€œ\nÃ˜Â§Ã˜Â¨Ã˜Â¯Ã˜Â£ Ã˜Â±Ã˜Â­Ã™â€žÃ˜ÂªÃ™Æ’ Ã˜Â§Ã™â€žÃ˜ÂªÃ˜Â¹Ã™â€žÃ™Å Ã™â€¦Ã™Å Ã˜Â© Ã˜Â§Ã™â€žÃ˜Â¢Ã™â€ !"
                    )
                    await bot.session.close()
                asyncio.run(notify())
        except Exception as e:
            print(f"Bot notify error: {e}")

        return jsonify({"ok": True, "message": "Ã˜ÂªÃ™â€¦ Ã˜ÂªÃ™ÂÃ˜Â¹Ã™Å Ã™â€ž Ã˜Â§Ã™â€žÃ˜Â·Ã˜Â§Ã™â€žÃ˜Â¨"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/admin/payments/<int:pid>/reject", methods=["POST"])
def api_reject_payment(pid):
    conn = get_db()
    try:
        pay = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
        if not pay:
            return jsonify({"error": "Payment not found"}), 404
        pay = dict(pay)
        uid = pay.get("user_id") or pay.get("telegram_id")

        conn.execute("UPDATE payments SET status='rejected' WHERE id=?", (pid,))
        conn.commit()

        # Ã˜Â¥Ã˜Â´Ã˜Â¹Ã˜Â§Ã˜Â± Ã˜Â§Ã™â€žÃ˜Â·Ã˜Â§Ã™â€žÃ˜Â¨
        try:
            import asyncio, os
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            token = os.environ.get("BOT_TOKEN", "")
            if token and uid:
                async def notify():
                    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                    await bot.send_message(
                        chat_id=int(uid),
                        text="Ã¢ÂÅ’ <b>Ã˜ÂªÃ™â€¦ Ã˜Â±Ã™ÂÃ˜Â¶ Ã˜Â·Ã™â€žÃ˜Â¨ Ã˜Â§Ã™â€žÃ˜Â§Ã˜Â´Ã˜ÂªÃ˜Â±Ã˜Â§Ã™Æ’</b>\n\nÃ™Å Ã˜Â±Ã˜Â¬Ã™â€° Ã˜Â§Ã™â€žÃ˜ÂªÃ™Ë†Ã˜Â§Ã˜ÂµÃ™â€ž Ã™â€¦Ã˜Â¹ Ã˜Â§Ã™â€žÃ˜Â£Ã˜Â¯Ã™â€¦Ã™â€  Ã™â€žÃ™â€žÃ™â€¦Ã˜Â²Ã™Å Ã˜Â¯ Ã™â€¦Ã™â€  Ã˜Â§Ã™â€žÃ™â€¦Ã˜Â¹Ã™â€žÃ™Ë†Ã™â€¦Ã˜Â§Ã˜Âª."
                    )
                    await bot.session.close()
                asyncio.run(notify())
        except Exception as e:
            print(f"Bot notify error: {e}")

        return jsonify({"ok": True, "message": "Ã˜ÂªÃ™â€¦ Ã˜Â±Ã™ÂÃ˜Â¶ Ã˜Â§Ã™â€žÃ˜Â·Ã™â€žÃ˜Â¨"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/admin/students/<int:uid>/delete", methods=["DELETE"])
def api_delete_student(uid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM students WHERE user_id=? OR telegram_id=?", (uid, str(uid)))
        conn.execute("DELETE FROM payments WHERE user_id=? OR telegram_id=?", (uid, str(uid)))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/admin/students/<int:uid>/send-message", methods=["POST"])
def api_send_message_to_student(uid):
    d = request.json or {}
    text = d.get("text", "").strip()
    if not text:
        return jsonify({"error": "Ã˜Â§Ã™â€žÃ™â€ Ã˜Âµ Ã™â€¦Ã˜Â·Ã™â€žÃ™Ë†Ã˜Â¨"}), 400
    try:
        import asyncio, os
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        token = os.environ.get("BOT_TOKEN", "")
        if not token:
            return jsonify({"error": "BOT_TOKEN Ã˜ÂºÃ™Å Ã˜Â± Ã™â€¦Ã˜Â¶Ã˜Â¨Ã™Ë†Ã˜Â·"}), 500
        async def send():
            bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            await bot.send_message(chat_id=uid, text=text)
            await bot.session.close()
        asyncio.run(send())
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# Ã°Å¸â€œÅ¡ LESSON CONTENT MANAGEMENT Ã¢â‚¬â€ Phase 2A
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

ALLOWED_ITEM_TABLES = {
    "words":     "lesson_letter_fill",
    "texts":     "lesson_practice_texts",
    "questions": "lesson_questions",
    "dragdrop":  "lesson_drag_drop",
}

def _get_lesson_or_404(lid):
    conn = get_db()
    row = conn.execute("SELECT * FROM lessons WHERE id=?", (lid,)).fetchone()
    conn.close()
    return dict(row) if row else None


@app.route("/api/admin/lessons/<int:lid>/full", methods=["GET"])
def api_lesson_full(lid):
    """Return everything for one lesson."""
    try:
        lesson = _get_lesson_or_404(lid)
        if not lesson:
            return jsonify({"error": "Lesson not found"}), 404

        # parse explanation_json if exists
        try:
            lesson["explanation"] = json.loads(lesson.get("explanation_json") or "{}")
        except Exception:
            lesson["explanation"] = {}

        conn = get_db()
        words = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_letter_fill WHERE lesson_id=? ORDER BY order_num, id", (lid,)).fetchall()]
        for w in words:
            try:
                w["letter_array"] = json.loads(w.get("letter_array_json") or "[]")
            except Exception:
                w["letter_array"] = []

        texts = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_practice_texts WHERE lesson_id=? ORDER BY order_num, id", (lid,)).fetchall()]
        for t in texts:
            try:
                t["answers"] = json.loads(t.get("answers_json") or "{}")
            except Exception:
                t["answers"] = {}

        questions = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_questions WHERE lesson_id=? ORDER BY order_num, id", (lid,)).fetchall()]
        for q in questions:
            try:
                q["options"] = json.loads(q.get("options_json") or "{}")
            except Exception:
                q["options"] = {}

        dragdrops = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_drag_drop WHERE lesson_id=? ORDER BY order_num, id", (lid,)).fetchall()]
        for d in dragdrops:
            try:
                d["items"] = json.loads(d.get("items_json") or "[]")
                d["correct_order"] = json.loads(d.get("correct_order_json") or "[]")
            except Exception:
                d["items"] = []
                d["correct_order"] = []

        conn.close()
        return jsonify({
            "lesson": lesson,
            "words": words,
            "texts": texts,
            "questions": questions,
            "dragdrops": dragdrops,
            "counts": {
                "words": len(words),
                "texts": len(texts),
                "questions": len(questions),
                "dragdrops": len(dragdrops),
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/<int:lid>/words", methods=["POST"])
def api_add_word(lid):
    """Add a letter-fill word to a lesson."""
    try:
        if not _get_lesson_or_404(lid):
            return jsonify({"error": "Lesson not found"}), 404
        d = request.get_json(force=True) or {}
        word = (d.get("word") or "").strip().upper()
        if not word:
            return jsonify({"error": "word required"}), 400
        letter_array = d.get("letter_array") or list(word)

        conn = get_db()
        cur = conn.cursor()
        order_num = (cur.execute(
            "SELECT COALESCE(MAX(order_num),0)+1 FROM lesson_letter_fill WHERE lesson_id=?",
            (lid,)).fetchone()[0])
        cur.execute("""
            INSERT INTO lesson_letter_fill
            (lesson_id, word, translation, sentence, hint, letter_array_json, order_num)
            VALUES (?,?,?,?,?,?,?)
        """, (lid, word, d.get("translation",""), d.get("sentence",""),
              d.get("hint",""), json.dumps(letter_array, ensure_ascii=False), order_num))
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "id": new_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/<int:lid>/texts", methods=["POST"])
def api_add_text(lid):
    """Add a practice text."""
    try:
        if not _get_lesson_or_404(lid):
            return jsonify({"error": "Lesson not found"}), 404
        d = request.get_json(force=True) or {}
        content = (d.get("content") or "").strip()
        if not content:
            return jsonify({"error": "content required"}), 400

        conn = get_db()
        cur = conn.cursor()
        order_num = (cur.execute(
            "SELECT COALESCE(MAX(order_num),0)+1 FROM lesson_practice_texts WHERE lesson_id=?",
            (lid,)).fetchone()[0])
        cur.execute("""
            INSERT INTO lesson_practice_texts
            (lesson_id, text_id, level, text_type, content, answers_json, order_num)
            VALUES (?,?,?,?,?,?,?)
        """, (lid, d.get("text_id",""), d.get("level","easy"),
              d.get("text_type","complete_words"), content,
              json.dumps(d.get("answers", {}), ensure_ascii=False), order_num))
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "id": new_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/<int:lid>/questions", methods=["POST"])
def api_add_lesson_question(lid):
    """Add a question to a lesson (timer default 30s)."""
    try:
        if not _get_lesson_or_404(lid):
            return jsonify({"error": "Lesson not found"}), 404
        d = request.get_json(force=True) or {}
        question = (d.get("question") or "").strip()
        if not question:
            return jsonify({"error": "question required"}), 400

        conn = get_db()
        cur = conn.cursor()
        order_num = (cur.execute(
            "SELECT COALESCE(MAX(order_num),0)+1 FROM lesson_questions WHERE lesson_id=? AND order_num<999",
            (lid,)).fetchone()[0])
        cur.execute("""
            INSERT INTO lesson_questions
            (lesson_id, q_id, q_type, question, passage_ref,
             options_json, correct_answer, explanation, evidence,
             common_trap, tip, timer_seconds, order_num)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (lid, d.get("q_id",""), d.get("q_type","factual"),
              question, d.get("passage_ref",""),
              json.dumps(d.get("options", {}), ensure_ascii=False),
              d.get("correct_answer","A"),
              d.get("explanation",""), d.get("evidence",""),
              d.get("common_trap",""), d.get("tip",""),
              int(d.get("timer_seconds", 30)), order_num))
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "id": new_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/<int:lid>/dragdrop", methods=["POST"])
def api_add_dragdrop(lid):
    """Add a drag-and-drop exercise."""
    try:
        if not _get_lesson_or_404(lid):
            return jsonify({"error": "Lesson not found"}), 404
        d = request.get_json(force=True) or {}
        title = (d.get("title") or "").strip()
        items = d.get("items") or []
        correct_order = d.get("correct_order") or []
        if not items:
            return jsonify({"error": "items required"}), 400

        conn = get_db()
        cur = conn.cursor()
        order_num = (cur.execute(
            "SELECT COALESCE(MAX(order_num),0)+1 FROM lesson_drag_drop WHERE lesson_id=?",
            (lid,)).fetchone()[0])
        cur.execute("""
            INSERT INTO lesson_drag_drop
            (lesson_id, title, exercise_type, instructions,
             items_json, correct_order_json, order_num)
            VALUES (?,?,?,?,?,?,?)
        """, (lid, title, d.get("exercise_type","sentence_order"),
              d.get("instructions",""),
              json.dumps(items, ensure_ascii=False),
              json.dumps(correct_order, ensure_ascii=False), order_num))
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "id": new_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/import-json", methods=["POST"])
def api_import_lesson_json():
    """Import a full lesson from JSON (single lesson object or {'lessons': [...]})"""
    try:
        d = request.get_json(force=True) or {}
        # supports both: single lesson, or { "lessons": [...] }
        lessons_in = d.get("lessons") if "lessons" in d else [d]
        if not isinstance(lessons_in, list) or not lessons_in:
            return jsonify({"error": "no lessons in JSON"}), 400

        conn = get_db()
        cur = conn.cursor()
        added = []

        XP_DEFAULT = 40

        for L in lessons_in:
            code = (L.get("lesson_id") or L.get("code") or "").strip()
            title = (L.get("title") or "").strip() or "Untitled"
            focus = L.get("focus_point","")
            exp_json = json.dumps(L.get("explanation", {}), ensure_ascii=False)
            xp = int(L.get("xp_reward", XP_DEFAULT))
            skill = L.get("skill","reading")
            phase = int(L.get("phase", 1))
            timer_min = int(L.get("timer_minutes", 15))

            # next order_num
            order_num = (cur.execute(
                "SELECT COALESCE(MAX(order_num),0)+1 FROM lessons").fetchone()[0])

            cur.execute("""
                INSERT INTO lessons
                (title, title_ar, lesson_code, focus_point, explanation_json,
                 skill, phase, order_num, xp_reward, timer_minutes, is_active, content)
                VALUES (?,?,?,?,?,?,?,?,?,?,1,?)
            """, (title, title, code, focus, exp_json, skill, phase,
                  order_num, xp, timer_min, focus))
            lesson_pk = cur.lastrowid

            # words
            for i, w in enumerate(L.get("letter_fill_exercise",{}).get("target_words",[]), start=1):
                cur.execute("""
                    INSERT INTO lesson_letter_fill
                    (lesson_id, word, translation, sentence, hint, letter_array_json, order_num)
                    VALUES (?,?,?,?,?,?,?)
                """, (lesson_pk, w.get("word",""), w.get("translation",""),
                      w.get("sentence",""), w.get("hint",""),
                      json.dumps(w.get("letter_array",[]), ensure_ascii=False), i))

            # practice texts (all levels merged)
            order = 0
            for level_key in ("easy","medium","intermediate","difficult"):
                for t in L.get("practice_texts",{}).get(level_key, []):
                    order += 1
                    cur.execute("""
                        INSERT INTO lesson_practice_texts
                        (lesson_id, text_id, level, text_type, content, answers_json, order_num)
                        VALUES (?,?,?,?,?,?,?)
                    """, (lesson_pk, t.get("id",""), level_key, "complete_words",
                          t.get("text",""),
                          json.dumps(t.get("answers",{}), ensure_ascii=False), order))

            # generic questions list (multiple shapes)
            def _insert_question(q, qtype, passage=""):
                cur.execute("""
                    INSERT INTO lesson_questions
                    (lesson_id, q_id, q_type, question, passage_ref,
                     options_json, correct_answer, explanation, evidence,
                     common_trap, tip, timer_seconds, order_num)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,30,0)
                """, (lesson_pk, q.get("q_id",""), qtype,
                      q.get("question",""), q.get("passage", passage),
                      json.dumps(q.get("options",{}), ensure_ascii=False),
                      q.get("correct_answer",""),
                      q.get("explanation",""), q.get("evidence",""),
                      q.get("common_trap",""), q.get("tip","")))

            pq = L.get("practice_questions", {})
            type_map = {
                "factual_questions":"factual",
                "negative_factual_questions":"negative_factual",
                "vocabulary_questions":"vocabulary",
                "inference_questions":"inference",
                "rhetorical_purpose_questions":"rhetorical",
                "insert_sentence_questions":"insert_sentence",
                "paragraph_relationship_questions":"paragraph_relation",
            }
            if isinstance(pq, dict):
                for cat, qlist in pq.items():
                    if isinstance(qlist, list):
                        for q in qlist:
                            _insert_question(q, type_map.get(cat, cat))

            for sk in ("practice_set","practice_set_1","practice_set_2"):
                ps = L.get(sk, {})
                for q in ps.get("questions", []):
                    _insert_question(q, q.get("type","factual").lower().replace(" ","_"),
                                     ps.get("passage_title",""))

            fq = L.get("final_comprehensive_quiz", {})
            for q in fq.get("questions", []):
                _insert_question(q, q.get("type","factual").lower().replace(" ","_"))

            iq = L.get("inference_question", {})
            if iq:
                cur.execute("""
                    INSERT INTO lesson_questions
                    (lesson_id, q_id, q_type, question, options_json,
                     correct_answer, explanation, timer_seconds, order_num)
                    VALUES (?,?,'inference',?,?,?,?,30,999)
                """, (lesson_pk, f"{code}_final" if code else "final",
                      iq.get("question",""),
                      json.dumps(iq.get("options",{}), ensure_ascii=False),
                      iq.get("correct_answer",""),
                      iq.get("explanation","")))

            added.append({"id": lesson_pk, "code": code, "title": title})

        conn.commit()
        conn.close()
        return jsonify({"ok": True, "added": added, "count": len(added)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lesson-item/<table>/<int:item_id>", methods=["DELETE"])
def api_delete_lesson_item(table, item_id):
    """Delete a word/text/question/dragdrop item."""
    try:
        tbl = ALLOWED_ITEM_TABLES.get(table)
        if not tbl:
            return jsonify({"error": "invalid table"}), 400
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {tbl} WHERE id=?", (item_id,))
        conn.commit()
        affected = cur.rowcount
        conn.close()
        return jsonify({"ok": True, "deleted": affected})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lesson-item/<table>/<int:item_id>", methods=["PUT"])
def api_update_lesson_item(table, item_id):
    """Update a lesson item (partial update with whitelisted columns)."""
    try:
        tbl = ALLOWED_ITEM_TABLES.get(table)
        if not tbl:
            return jsonify({"error": "invalid table"}), 400
        d = request.get_json(force=True) or {}

        # whitelist columns per table
        allowed_cols = {
            "lesson_letter_fill":     ["word","translation","sentence","hint","letter_array_json","order_num"],
            "lesson_practice_texts":  ["text_id","level","text_type","content","answers_json","order_num"],
            "lesson_questions":       ["q_id","q_type","question","passage_ref","options_json",
                                       "correct_answer","explanation","evidence","common_trap",
                                       "tip","timer_seconds","order_num"],
            "lesson_drag_drop":       ["title","exercise_type","instructions","items_json",
                                       "correct_order_json","order_num"],
        }[tbl]

        # auto-convert dict/list fields to JSON string
        json_fields = {"options","letter_array","answers","items","correct_order"}
        body = {}
        for k, v in d.items():
            if k in json_fields:
                body[k + "_json"] = json.dumps(v, ensure_ascii=False)
            else:
                body[k] = v

        sets, vals = [], []
        for col in allowed_cols:
            if col in body:
                sets.append(f"{col}=?")
                vals.append(body[col])
        if not sets:
            return jsonify({"error": "no valid fields"}), 400
        vals.append(item_id)

        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"UPDATE {tbl} SET {', '.join(sets)} WHERE id=?", vals)
        conn.commit()
        affected = cur.rowcount
        conn.close()
        return jsonify({"ok": True, "updated": affected})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Student Lessons API Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/lessons", methods=["GET"])
def api_student_lessons():
    """Returns active lessons for students."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, lesson_code, title, title_ar, description,
                   COALESCE(skill_type, skill) AS skill_type,
                   COALESCE(skill, skill_type) AS skill,
                   COALESCE(stage, phase, 1) AS stage,
                   COALESCE(phase, stage, 1) AS phase,
                   COALESCE(xp_reward, 20) AS xp_reward,
                   COALESCE(order_num, id) AS order_num,
                   focus_point, is_active
            FROM lessons
            WHERE COALESCE(is_active, 1) = 1
            ORDER BY stage, phase, order_num, id
        """).fetchall()
        return jsonify({"lessons": [dict(r) for r in rows]})
    finally:
        conn.close()


@app.route("/api/lessons/<int:lid>", methods=["GET"])
def api_student_lesson_detail(lid):
    """Returns one full lesson with words/texts/questions for students."""
    conn = get_db()
    try:
        lesson_row = conn.execute(
            "SELECT * FROM lessons WHERE id=? AND COALESCE(is_active,1)=1",
            (lid,)
        ).fetchone()
        if not lesson_row:
            return jsonify({"error": "Lesson not found"}), 404
        lesson = dict(lesson_row)
        try:
            lesson["explanation"] = json.loads(lesson.get("explanation_json") or "{}")
        except Exception:
            lesson["explanation"] = {}

        words = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_letter_fill WHERE lesson_id=? ORDER BY order_num, id",
            (lid,)
        ).fetchall()]
        texts = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_practice_texts WHERE lesson_id=? ORDER BY order_num, id",
            (lid,)
        ).fetchall()]
        questions = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_questions WHERE lesson_id=? ORDER BY order_num, id",
            (lid,)
        ).fetchall()]
        dragdrops = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_drag_drop WHERE lesson_id=? ORDER BY order_num, id",
            (lid,)
        ).fetchall()]
        return jsonify({
            "lesson": lesson,
            "words": words,
            "texts": texts,
            "questions": questions,
            "dragdrops": dragdrops,
            "counts": {
                "words": len(words), "texts": len(texts),
                "questions": len(questions), "dragdrops": len(dragdrops)
            }
        })
    finally:
        conn.close()


@app.route("/api/lessons/<int:lid>/complete", methods=["POST"])
def api_student_complete_lesson(lid):
    """Marks a lesson as completed and awards XP."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or data.get("telegram_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    conn = get_db()
    try:
        lesson = conn.execute(
            "SELECT id, xp_reward, COALESCE(skill, skill_type, 'reading') AS skill FROM lessons WHERE id=?",
            (lid,)
        ).fetchone()
        if not lesson:
            return jsonify({"error": "Lesson not found"}), 404
        xp = int(lesson["xp_reward"] or 20)
        skill = lesson["skill"] or "reading"
        conn.execute(
            "UPDATE students SET xp = COALESCE(xp,0) + ?, total_xp = COALESCE(total_xp,0) + ? WHERE telegram_id=?",
            (xp, xp, user_id)
        )
        try:
            conn.execute(
                "INSERT INTO xp_log (user_id, amount, reason) VALUES (?,?,?)",
                (user_id, xp, "lesson_" + str(lid) + "_" + skill)
            )
        except Exception:
            pass
        conn.commit()
        return jsonify({"ok": True, "xp_awarded": xp, "skill": skill})
    finally:
        conn.close()



# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Student Profile by ID (for student_dashboard) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/student/<int:uid>", methods=["GET"])
def api_student_by_id(uid):
    """Returns full student profile by telegram_id for student dashboard."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM students WHERE telegram_id=?", (uid,)
        ).fetchone()
        if not row:
            return jsonify({"error": "student not found"}), 404
        d = dict(row)
        # Normalize fields the dashboard expects
        d.setdefault("level", "beginner")
        d.setdefault("xp", d.get("total_xp", 0) or 0)
        d.setdefault("streak", d.get("streak_days", 0) or 0)
        d.setdefault("missions_completed", d.get("missions_completed", 0) or 0)
        d.setdefault("placement_score", d.get("placement_score", 0) or 0)
        d.setdefault("full_name", d.get("name") or d.get("username") or "Ã˜Â·Ã˜Â§Ã™â€žÃ˜Â¨")
        return jsonify(d)
    finally:
        conn.close()


@app.route("/api/leaderboard", methods=["GET"])
def api_leaderboard():
    """Top students by XP for leaderboard tab."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT telegram_id, full_name, username,
                   COALESCE(xp, total_xp, 0) AS xp,
                   COALESCE(streak_days, streak, 0) AS streak,
                   level
            FROM students
            WHERE COALESCE(is_active, 1) = 1
            ORDER BY xp DESC
            LIMIT 50
        """).fetchall()
        return jsonify({"leaderboard": [dict(r) for r in rows]})
    finally:
        conn.close()


@app.route("/api/user/graduation-status", methods=["GET"])
def api_graduation_status():
    """Returns graduation eligibility for a student."""
    sid = request.args.get("student_id", type=int)
    if not sid:
        return jsonify({"error": "student_id required"}), 400
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM students WHERE telegram_id=?", (sid,)
        ).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        d = dict(row)
        return jsonify({
            "is_graduated": bool(d.get("is_graduated", 0)),
            "mock_score": d.get("mock_exam_score") or d.get("mock_score") or 0,
            "required_score": d.get("required_score") or 80,
            "tasks_completed": d.get("tasks_completed", 0) or 0,
            "completed_lessons": d.get("completed_lessons", 0) or 0,
            "xp": d.get("xp", 0) or 0,
        })
    finally:
        conn.close()



# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Lesson detail page Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/lesson/<int:lid>")
def lesson_page(lid):
    """Serves the full lesson page for students."""
    return render_template("lesson_view.html", lesson_id=lid)



# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# â”€â”€â”€ Mini App lesson page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route("/miniapp/plans")
def miniapp_plans_page():
    """Render pricing page (reads plans dynamically from /api/miniapp/plans)."""
    sid = _request.args.get("student_id", "")
    return render_template("pricing.html", student_id=sid)

@app.route("/miniapp/lesson/<int:lid>")
def miniapp_lesson_page(lid):
    from flask import render_template
    return render_template("miniapp_lesson.html", lesson_id=lid)

#  Mini App APIs â€” Phase 2 (added by automated script)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
import json as _json
import sqlite3 as _sqlite3
from datetime import datetime as _datetime, timedelta as _timedelta
from flask import jsonify as _jsonify, request as _request

def _miniapp_db():
    """Get DB connection using same path resolver as the bot."""
    import os as _os
    _path = "/app/data/academy.db" if _os.path.exists("/app/data") else _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "academy.db")
    _conn = _sqlite3.connect(_path)
    _conn.row_factory = _sqlite3.Row
    return _conn


@app.route("/api/miniapp/lessons")
def miniapp_lessons_list():
    """List lessons for student with status (locked/available/completed)."""
    try:
        sid = _request.args.get("student_id", type=int)
        if not sid:
            return _jsonify({"error": "student_id required"}), 400
        
        conn = _miniapp_db()
        cur = conn.cursor()
        
        # Get student
        cur.execute("SELECT user_id, current_phase, xp, track FROM students WHERE user_id=?", (sid,))
        student = cur.fetchone()
        if not student:
            conn.close()
            return _jsonify({"error": "student not found"}), 404
        
        current_phase = student["current_phase"] or 1
        
        # Get last attempt for cooldown
        cur.execute("""
            SELECT lesson_id, finished_at, passed 
            FROM lesson_attempts 
            WHERE telegram_id=? AND passed=1 
            ORDER BY finished_at DESC LIMIT 1
        """, (str(sid),))
        last_attempt = cur.fetchone()
        
        cooldown_lesson_id = None
        cooldown_until = None
        if last_attempt and last_attempt["finished_at"]:
            try:
                finished = _datetime.fromisoformat(last_attempt["finished_at"].replace(" ", "T"))
                unlock_at = finished + _timedelta(hours=24)
                if unlock_at > _datetime.utcnow():
                    cooldown_lesson_id = last_attempt["lesson_id"]
                    cooldown_until = unlock_at.isoformat()
            except Exception:
                pass
        
        # Get all completed lesson IDs for this student
        cur.execute("""
            SELECT DISTINCT lesson_id FROM lesson_attempts 
            WHERE telegram_id=? AND passed=1
        """, (str(sid),))
        completed_ids = {row["lesson_id"] for row in cur.fetchall()}
        
        # Get lessons grouped by stage
        cur.execute("""
            SELECT l.id, l.title, l.title_ar, l.skill, l.stage_id, l.order_index, 
                   l.xp_reward, l.section_name, l.content,
                   s.code as stage_code, s.name_ar as stage_name,
                   (SELECT COUNT(*) FROM lesson_questions WHERE lesson_id=l.id) as q_count
            FROM lessons l
            LEFT JOIN stages s ON s.id = l.stage_id
            WHERE l.is_active=1 AND l.stage_id <= ?
            ORDER BY l.stage_id, l.order_index
        """, (current_phase + 1,))  # show current + next stage
        
        lessons_by_stage = {}
        for row in cur.fetchall():
            lid = row["id"]
            stage_id = row["stage_id"]
            
            # Determine status
            if lid in completed_ids:
                status = "completed"
            elif cooldown_lesson_id and lid > cooldown_lesson_id and stage_id == current_phase:
                status = "locked_cooldown"
            elif stage_id > current_phase:
                status = "locked_stage"
            else:
                status = "available"
            
            if stage_id not in lessons_by_stage:
                lessons_by_stage[stage_id] = {
                    "stage_id": stage_id,
                    "stage_code": row["stage_code"],
                    "stage_name": row["stage_name"],
                    "lessons": []
                }
            
            title = row["title"] or row["title_ar"] or f"Lesson {lid}"
            lessons_by_stage[stage_id]["lessons"].append({
                "id": lid,
                "title": title,
                "skill": row["skill"] or "general",
                "section": row["section_name"] or "general",
                "xp_reward": row["xp_reward"] or 10,
                "questions_count": row["q_count"],
                "status": status,
                "order": row["order_index"]
            })
        
        conn.close()
        return _jsonify({
            "student_id": sid,
            "current_phase": current_phase,
            "cooldown_until": cooldown_until,
            "stages": list(lessons_by_stage.values())
        })
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/miniapp/lesson/<int:lid>")
def miniapp_lesson_detail(lid):
    """Get lesson content + questions (without correct answers)."""
    try:
        sid = _request.args.get("student_id", type=int)
        
        conn = _miniapp_db()
        cur = conn.cursor()
        
        # Get lesson
        cur.execute("""
            SELECT id, title, title_ar, content, skill, stage_id, xp_reward, 
                   vocabulary, grammar_rule, focus_point, section_name
            FROM lessons WHERE id=? AND is_active=1
        """, (lid,))
        lesson = cur.fetchone()
        if not lesson:
            conn.close()
            return _jsonify({"error": "lesson not found"}), 404
        
        # Get questions (without correct_answer, without explanation, without tip)
        cur.execute("""
            SELECT id, q_id, q_type, question, options_json, timer_seconds, order_num
            FROM lesson_questions 
            WHERE lesson_id=? 
            ORDER BY order_num, id
        """, (lid,))
        questions = []
        for row in cur.fetchall():
            opts = {}
            try:
                opts = _json.loads(row["options_json"] or "{}")
            except Exception:
                pass
            questions.append({
                "id": row["id"],
                "q_id": row["q_id"],
                "type": row["q_type"],
                "question": row["question"],
                "options": opts,
                "timer": row["timer_seconds"] or 30,
                "order": row["order_num"]
            })
        
        # Has the student completed this lesson?
        completed = False
        last_score = None
        if sid:
            cur.execute("""
                SELECT score_percent FROM lesson_attempts 
                WHERE telegram_id=? AND lesson_id=? AND passed=1 
                ORDER BY finished_at DESC LIMIT 1
            """, (str(sid), lid))
            r = cur.fetchone()
            if r:
                completed = True
                last_score = r["score_percent"]
        
        conn.close()
        title = lesson["title"] or lesson["title_ar"] or f"Lesson {lid}"
        return _jsonify({
            "id": lesson["id"],
            "title": title,
            "content": lesson["content"] or "",
            "skill": lesson["skill"] or "general",
            "stage_id": lesson["stage_id"],
            "xp_reward": lesson["xp_reward"] or 10,
            "vocabulary": lesson["vocabulary"],
            "grammar_rule": lesson["grammar_rule"],
            "focus_point": lesson["focus_point"],
            "section": lesson["section_name"],
            "questions": questions,
            "completed": completed,
            "last_score": last_score
        })
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/miniapp/quiz/check", methods=["POST"])
def miniapp_quiz_check():
    """Check single answer; return correctness + concept + explanation if wrong."""
    try:
        data = _request.get_json(force=True) or {}
        question_id = data.get("question_id")
        user_answer = (data.get("answer") or "").strip().upper()
        if not question_id:
            return _jsonify({"error": "question_id required"}), 400
        
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT correct_answer, concept, explanation, tip 
            FROM lesson_questions WHERE id=?
        """, (question_id,))
        q = cur.fetchone()
        conn.close()
        if not q:
            return _jsonify({"error": "question not found"}), 404
        
        correct = (q["correct_answer"] or "").strip().upper()
        is_correct = (user_answer == correct)
        
        resp = {
            "is_correct": is_correct,
            "correct_answer": correct,
        }
        # Show concept + explanation only on wrong answers
        if not is_correct:
            resp["concept"] = q["concept"] or ""
            resp["explanation"] = q["explanation"] or ""
            resp["tip"] = q["tip"] or ""
        return _jsonify(resp)
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/miniapp/quiz/submit", methods=["POST"])
def miniapp_quiz_submit():
    """Submit full quiz; save attempt; award XP; return result."""
    try:
        data = _request.get_json(force=True) or {}
        sid = data.get("student_id")
        lid = data.get("lesson_id")
        answers = data.get("answers") or []  # [{"q_id":..., "user":..., "correct":..., "is_correct":bool}, ...]
        
        if not sid or not lid:
            return _jsonify({"error": "student_id and lesson_id required"}), 400
        
        conn = _miniapp_db()
        cur = conn.cursor()
        
        # Compute score
        total = len(answers)
        correct = sum(1 for a in answers if a.get("is_correct"))
        score = (correct / total * 100) if total else 0
        passed = 1 if score >= 70 else 0
        
        now = _datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get lesson xp reward
        cur.execute("SELECT xp_reward FROM lessons WHERE id=?", (lid,))
        lrow = cur.fetchone()
        xp_reward = (lrow["xp_reward"] if lrow else 10) or 10
        xp_earned = xp_reward if passed else int(xp_reward * (score / 100))
        
        # Save attempt
        cur.execute("""
            INSERT INTO lesson_attempts 
              (telegram_id, lesson_id, started_at, finished_at, correct_count, total_questions, passed, score_percent, answers_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(sid), lid, now, now, correct, total, passed, score, _json.dumps(answers, ensure_ascii=False)))
        
        # Update student XP only if passed
        if passed:
            cur.execute("UPDATE students SET xp = COALESCE(xp,0) + ? WHERE user_id=?", (xp_earned, sid))
            # Log XP
            try:
                cur.execute("""
                    INSERT INTO xp_log (user_id, amount, reason, created_at)
                    VALUES (?, ?, ?, ?)
                """, (sid, xp_earned, f"lesson_{lid}_quiz", now))
            except Exception:
                pass  # xp_log may have different schema
        
        # Get updated XP
        cur.execute("SELECT xp FROM students WHERE user_id=?", (sid,))
        new_xp = cur.fetchone()
        new_xp_val = new_xp["xp"] if new_xp else 0
        
        conn.commit()
        conn.close()
        
        return _jsonify({
            "passed": bool(passed),
            "score": round(score, 1),
            "correct": correct,
            "total": total,
            "xp_earned": xp_earned if passed else 0,
            "total_xp": new_xp_val,
            "cooldown_hours": 24 if passed else 0
        })
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/miniapp/plans")
def miniapp_plans():
    """Get active subscription plans."""
    try:
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, name_ar, price, currency, duration_days, 
                   description, features, is_featured
            FROM subscription_plans 
            WHERE is_active=1 
            ORDER BY is_featured DESC, price ASC
        """)
        plans = []
        for row in cur.fetchall():
            features = []
            try:
                features = _json.loads(row["features"] or "[]")
            except Exception:
                features = [row["features"]] if row["features"] else []
            plans.append({
                "id": row["id"],
                "name": row["name_ar"] or row["name"],
                "price": row["price"],
                "currency": row["currency"],
                "duration_days": row["duration_days"],
                "description": row["description"],
                "features": features,
                "is_featured": bool(row["is_featured"])
            })
        conn.close()
        return _jsonify({"plans": plans})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  End of Mini App APIs
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•



# ============ PHASE 4B: QUIZ ROUTES + APIs ============
@app.route("/miniapp/quiz/<int:lid>")
def miniapp_quiz_page(lid):
    from flask import render_template
    return render_template("miniapp_quiz.html", lesson_id=lid)


@app.route("/api/miniapp/quiz/start", methods=["POST"])
def miniapp_quiz_start():
    """Start quiz: check cooldown, start attempt, return questions (no answers)."""
    try:
        import quiz_engine as qe
        data = _request.get_json(force=True) or {}
        sid = str(data.get("student_id") or "")
        lid = data.get("lesson_id")
        if not sid or not lid:
            return _jsonify({"error": "student_id and lesson_id required"}), 400

        # Cooldown check
        try:
            cd = qe.get_cooldown_status(sid, int(lid))
            if cd and cd.get("locked"):
                return _jsonify({"cooldown": cd})
        except Exception as _e:
            pass

        # Get questions (without correct answers)
        # Fetch questions directly from DB (bypass quiz_engine for accurate options_json reading)
        conn_q = _miniapp_db()
        cur_q = conn_q.cursor()
        cur_q.execute("""
            SELECT id, q_id, q_type, question, options_json, passage_ref,
                   timer_seconds, order_num
            FROM lesson_questions
            WHERE lesson_id=?
            ORDER BY order_num, id
        """, (int(lid),))
        rows = cur_q.fetchall()
        conn_q.close()

        # Shuffle order
        import random as _rnd
        rows_list = list(rows)
        _rnd.shuffle(rows_list)

        safe_questions = []
        for row in rows_list:
            try:
                opts = _json.loads(row["options_json"] or "{}")
            except Exception:
                opts = {}
            safe_questions.append({
                "id": row["id"],
                "q_id": row["q_id"],
                "q_type": row["q_type"] or "mcq",
                "question": row["question"] or "",
                "options": opts,
                "passage_ref": row["passage_ref"] or "",
                "timer_seconds": row["timer_seconds"] or 30,
                "order_num": row["order_num"] or 0,
            })

        # Start attempt
        attempt_id = None
        try:
            attempt_id = qe.start_quiz_attempt(sid, int(lid))
        except Exception as _e:
            pass

        # Get student target & required streak
        try:
            _target = qe.get_student_target(sid)
        except Exception:
            _target = 69
        try:
            _required = qe.get_required_streak(_target)
        except Exception:
            _required = 3

        return _jsonify({
            "attempt_id": attempt_id,
            "questions": safe_questions,
            "total": len(safe_questions),
            "target_score": _target,
            "required_streak": _required,
        })
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/miniapp/quiz/answer", methods=["POST"])
def miniapp_quiz_answer():
    """Check single answer; record mistake in error_bank if wrong."""
    try:
        import quiz_engine as qe
        data = _request.get_json(force=True) or {}
        sid = str(data.get("student_id") or "")
        qid = data.get("question_id")
        user_answer = (data.get("answer") or "").strip().upper()
        if not qid:
            return _jsonify({"error": "question_id required"}), 400

        # Use quiz_engine.check_answer
        is_correct, correct_ans, explanation = qe.check_answer(int(qid), user_answer)

        # Get concept, tip, evidence, common_trap from DB
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("SELECT concept, tip, evidence, common_trap, q_type, passage_ref FROM lesson_questions WHERE id=?", (int(qid),))
        row = cur.fetchone()
        conn.close()
        concept = row["concept"] if row else ""
        tip = row["tip"] if row else ""
        evidence = row["evidence"] if row else ""
        common_trap = row["common_trap"] if row else ""
        q_type_meta = row["q_type"] if row else ""
        passage_ref_meta = row["passage_ref"] if row else ""

        # Record mistake if wrong
        if not is_correct and sid:
            try:
                qe.record_mistake(sid, int(qid), user_answer, correct_ans or "")
            except Exception as _e:
                pass

        return _jsonify({
            "is_correct": is_correct,
            "correct_answer": correct_ans or "",
            "explanation": explanation or "",
            "concept": concept or "",
            "tip": tip or "",
            "evidence": evidence or "",
            "common_trap": common_trap or "",
            "q_type": q_type_meta or "",
            "passage_ref": passage_ref_meta or ""
        })
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/miniapp/quiz/finish", methods=["POST"])
def miniapp_quiz_finish():
    """Finish quiz using streak-based passing (get_required_streak)."""
    try:
        import quiz_engine as qe
        data = _request.get_json(force=True) or {}
        sid = str(data.get("student_id") or "")
        lid = data.get("lesson_id")
        attempt_id = data.get("attempt_id")
        answers = data.get("answers") or []

        if not sid or not lid:
            return _jsonify({"error": "student_id and lesson_id required"}), 400

        total = len(answers)
        correct = sum(1 for a in answers if a.get("is_correct"))

        # Compute best consecutive correct streak (in answer order)
        best_streak = 0
        cur_streak = 0
        for a in answers:
            if a.get("is_correct"):
                cur_streak += 1
                if cur_streak > best_streak:
                    best_streak = cur_streak
            else:
                cur_streak = 0

        # Get student target -> required streak
        try:
            target = qe.get_student_target(sid)
        except Exception:
            target = 69
        try:
            required = qe.get_required_streak(target)
        except Exception:
            required = 3

        passed = best_streak >= required
        score = (correct / total * 100) if total else 0

        # xp_reward from lessons
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("SELECT xp_reward FROM lessons WHERE id=?", (int(lid),))
        lrow = cur.fetchone()
        xp_reward = (lrow["xp_reward"] if lrow else 10) or 10
        conn.close()

        xp_earned = 0
        cooldown_seconds = 0
        cooldown_message = ""

        if passed:
            try:
                qe.finish_quiz_attempt(attempt_id, correct, total, answers)
            except Exception:
                pass
            xp_earned = xp_reward
            try:
                qe.clear_cooldown(sid, int(lid))
            except Exception:
                pass
        else:
            try:
                qe.finish_quiz_attempt(attempt_id, correct, total, answers)
            except Exception:
                pass
            try:
                fail_info = qe.register_failed_attempt(sid, int(lid))
                if isinstance(fail_info, dict):
                    cooldown_seconds = int(fail_info.get("wait_seconds", 0) or 0)
                    cooldown_message = fail_info.get("motivation", "") or ""
            except Exception:
                cooldown_seconds = 300

        return _jsonify({
            "passed": passed,
            "score": round(score, 1),
            "correct": correct,
            "wrong": total - correct,
            "total": total,
            "best_streak": best_streak,
            "required_streak": required,
            "target_score": target,
            "xp_earned": xp_earned,
            "cooldown_seconds": cooldown_seconds,
            "cooldown_message": cooldown_message,
        })
    except Exception as e:
        return _jsonify({"error": str(e)}), 500
# ============ END PHASE 4B ============


if __name__ == "__main__":
    import os as _os
    _port = int(_os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=_port, debug=False)


# ===================== Phase 9: Admin + Placement Questions CRUD =====================
@app.route("/admin")
def admin_page():
    from flask import render_template
    return render_template("admin.html")

@app.route("/api/admin/placement-questions", methods=["GET"])
def api_admin_placement_list():
    import sqlite3
    try:
        conn = sqlite3.connect("academy.db"); conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM placement_questions ORDER BY id DESC").fetchall()
        conn.close()
        return _jsonify({"questions": [dict(r) for r in rows]})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/placement-questions", methods=["POST"])
def api_admin_placement_create():
    import sqlite3
    try:
        d = _request.get_json(force=True) or {}
        conn = sqlite3.connect("academy.db")
        conn.execute("""
            INSERT INTO placement_questions
            (question_text, option_a, option_b, option_c, option_d, correct_option, skill, skill_type, difficulty, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d.get("question_text",""), d.get("option_a",""), d.get("option_b",""),
            d.get("option_c",""), d.get("option_d",""), (d.get("correct_option","A") or "A").upper(),
            d.get("skill","grammar"), d.get("skill","grammar"),
            d.get("difficulty","medium"), 1 if d.get("is_active", True) else 0
        ))
        conn.commit(); conn.close()
        return _jsonify({"ok": True})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/placement-questions/<int:qid>", methods=["PUT"])
def api_admin_placement_update(qid):
    import sqlite3
    try:
        d = _request.get_json(force=True) or {}
        conn = sqlite3.connect("academy.db")
        conn.execute("""
            UPDATE placement_questions
            SET question_text=?, option_a=?, option_b=?, option_c=?, option_d=?,
                correct_option=?, skill=?, skill_type=?, difficulty=?, is_active=?
            WHERE id=?
        """, (
            d.get("question_text",""), d.get("option_a",""), d.get("option_b",""),
            d.get("option_c",""), d.get("option_d",""), (d.get("correct_option","A") or "A").upper(),
            d.get("skill","grammar"), d.get("skill","grammar"),
            d.get("difficulty","medium"), 1 if d.get("is_active", True) else 0, qid
        ))
        conn.commit(); conn.close()
        return _jsonify({"ok": True})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/placement-questions/<int:qid>", methods=["DELETE"])
def api_admin_placement_delete(qid):
    import sqlite3
    try:
        conn = sqlite3.connect("academy.db")
        conn.execute("DELETE FROM placement_questions WHERE id=?", (qid,))
        conn.commit(); conn.close()
        return _jsonify({"ok": True})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/placement-questions/<int:qid>/toggle", methods=["POST"])
def api_admin_placement_toggle(qid):
    import sqlite3
    try:
        conn = sqlite3.connect("academy.db")
        row = conn.execute("SELECT is_active FROM placement_questions WHERE id=?", (qid,)).fetchone()
        if not row: return _jsonify({"error": "not found"}), 404
        new_val = 0 if row[0] == 1 else 1
        conn.execute("UPDATE placement_questions SET is_active=? WHERE id=?", (new_val, qid))
        conn.commit(); conn.close()
        return _jsonify({"ok": True, "is_active": new_val})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

