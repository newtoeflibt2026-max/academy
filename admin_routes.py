"""
admin_routes.py — All admin & user API routes
"""
from flask import jsonify, request as req, render_template, send_from_directory
import json as _json
import os


def register_admin_routes(app):
    @app.route("/student")
    @app.route("/portal")
    def student_portal():
        return render_template("student_portal.html")

    # ─── Admin Dashboard Page ────────────────────────────────────
    @app.route("/")
    @app.route("/admin")
    @app.route("/dashboard")
    def admin_dashboard():
        template_path = os.path.join(app.root_path, "templates", "admin_dashboard.html")
        if os.path.exists(template_path):
            return render_template("admin_dashboard.html")
        return "<h1>لوحة التحكم</h1><p>ملف admin_dashboard.html غير موجود في templates/</p>", 200

    # ─── Stats ───────────────────────────────────────────────────
    @app.route("/api/admin/stats", methods=["GET"])
    def api_stats():
        try:
            from bot_database import get_students_count, get_leaderboard, get_questions
            counts = get_students_count()
            leaders = get_leaderboard(5)
            q_count = len(get_questions(limit=9999))
            return jsonify({"counts": counts, "leaderboard": leaders, "question_count": q_count})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ─── Students ────────────────────────────────────────────────
    @app.route("/api/admin/students", methods=["GET"])
    def api_students():
        try:
            from bot_database import get_all_students, search_students
            q = req.args.get("q", "").strip()
            data = search_students(q) if q else get_all_students(limit=300)
            return jsonify({"students": data, "total": len(data)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/students/<int:uid>", methods=["GET"])
    def api_student_detail(uid):
        try:
            from bot_database import get_student, get_skills_progress, check_graduation
            s = get_student(uid)
            if not s:
                return jsonify({"error": "not found"}), 404
            s["skills"] = get_skills_progress(uid)
            s["graduation"] = check_graduation(uid)
            return jsonify(s)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/students/<int:uid>/activate", methods=["POST"])
    def api_activate(uid):
        try:
            from bot_database import activate_paid
            activate_paid(uid)
            return jsonify({"ok": True, "message": "تم تفعيل الحساب المدفوع"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/students/<int:uid>/deactivate", methods=["POST"])
    def api_deactivate(uid):
        try:
            from bot_database import deactivate_paid
            deactivate_paid(uid)
            return jsonify({"ok": True, "message": "تم إلغاء التفعيل"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/students/<int:uid>/toggle-active", methods=["POST"])
    def api_toggle_active(uid):
        try:
            from bot_database import get_student, update_student
            s = get_student(uid)
            if not s:
                return jsonify({"error": "not found"}), 404
            new_val = 0 if s.get("is_active", 1) else 1
            update_student(uid, is_active=new_val)
            return jsonify({"ok": True, "is_active": new_val})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ─── Questions ───────────────────────────────────────────────
    @app.route("/api/admin/questions", methods=["GET"])
    def api_get_questions():
        try:
            from bot_database import get_questions
            skill = req.args.get("skill")
            questions = get_questions(skill=skill, limit=500)
            return jsonify({"questions": questions})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/questions", methods=["POST"])
    def api_add_question():
        try:
            from bot_database import add_question
            data = req.get_json() or {}
            add_question(
                data.get("question_text", ""),
                data.get("skill", "reading"),
                data.get("question_type", "mcq"),
                data.get("options"),
                data.get("correct_answer"),
                data.get("explanation"),
                data.get("lesson_id")
            )
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/questions/<int:qid>", methods=["DELETE"])
    def api_delete_question(qid):
        try:
            from bot_database import delete_question
            delete_question(qid)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ─── Missions ────────────────────────────────────────────────
    @app.route("/api/admin/missions", methods=["GET"])
    def api_get_missions():
        try:
            from bot_database import get_daily_missions
            return jsonify({"missions": get_daily_missions()})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/missions", methods=["POST"])
    def api_add_mission():
        try:
            from bot_database import add_daily_mission
            data = req.get_json() or {}
            add_daily_mission(
                data.get("title", ""),
                data.get("description", ""),
                data.get("mission_type", "reading"),
                data.get("xp_reward", 20),
                data.get("target_date")
            )
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/missions/<int:mid>", methods=["PUT"])
    def api_update_mission(mid):
        try:
            from bot_database import get_db
            data = req.get_json() or {}
            conn = get_db()
            conn.execute(
                "UPDATE daily_missions SET title=?,description=?,mission_type=?,xp_reward=?,target_date=?,is_active=? WHERE id=?",
                (data.get("title"), data.get("description"),
                 data.get("mission_type", "reading"),
                 data.get("xp_reward", 20),
                 data.get("target_date"),
                 data.get("is_active", 1), mid)
            )
            conn.commit()
            conn.close()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/missions/<int:mid>", methods=["DELETE"])
    def api_delete_mission(mid):
        try:
            from bot_database import get_db
            conn = get_db()
            conn.execute("DELETE FROM daily_missions WHERE id=?", (mid,))
            conn.commit()
            conn.close()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ─── Grading Rules ───────────────────────────────────────────
    @app.route("/api/admin/grading-rules", methods=["GET"])
    def api_get_grading():
        try:
            from bot_database import get_grading_rules
            return jsonify({"rules": get_grading_rules()})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/grading-rules", methods=["POST"])
    def api_add_grading():
        try:
            from bot_database import get_db
            data = req.get_json() or {}
            conn = get_db()
            conn.execute(
                "INSERT INTO essay_grading_rules (topic,skill,vocab_keywords,connector_keywords,forbidden_words,vocab_points,connector_points,forbidden_penalty,max_score) VALUES (?,?,?,?,?,?,?,?,?)",
                (data.get("topic", ""), data.get("skill", "writing"),
                 _json.dumps(data.get("vocab_keywords", [])),
                 _json.dumps(data.get("connector_keywords", [])),
                 _json.dumps(data.get("forbidden_words", [])),
                 data.get("vocab_points", 2.0),
                 data.get("connector_points", 3.0),
                 data.get("forbidden_penalty", 1.0),
                 data.get("max_score", 100.0))
            )
            conn.commit()
            conn.close()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/grading-rules/<int:rid>", methods=["DELETE"])
    def api_delete_grading(rid):
        try:
            from bot_database import get_db
            conn = get_db()
            conn.execute("DELETE FROM essay_grading_rules WHERE id=?", (rid,))
            conn.commit()
            conn.close()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ─── Phase Settings ──────────────────────────────────────────
    @app.route("/api/admin/phase-settings", methods=["GET"])
    def api_get_phases():
        try:
            from bot_database import get_phase_settings
            return jsonify({"phases": get_phase_settings()})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/phase-settings/<int:pnum>", methods=["PUT"])
    def api_update_phase(pnum):
        try:
            from bot_database import update_phase_settings
            data = req.get_json() or {}
            data.pop("phase_number", None)
            update_phase_settings(pnum, **data)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ─── System Settings ─────────────────────────────────────────
    @app.route("/api/admin/settings", methods=["GET"])
    def api_get_settings():
        try:
            from bot_database import get_all_settings
            return jsonify({"settings": get_all_settings()})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/settings", methods=["POST"])
    def api_update_settings():
        try:
            from bot_database import set_setting
            data = req.get_json() or {}
            for key, value in data.items():
                set_setting(key, str(value))
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ─── Payments ────────────────────────────────────────────────
    @app.route("/api/admin/payments", methods=["GET"])
    def api_get_payments():
        try:
            from bot_database import get_payments
            return jsonify({"payments": get_payments(100)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/payments/<int:pid>/verify", methods=["POST"])
    def api_verify_payment(pid):
        try:
            from bot_database import verify_payment
            ok = verify_payment(pid)
            return jsonify({"ok": ok})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ─── Graduation Status ────────────────────────────────────────
    @app.route("/api/user/graduation-status", methods=["GET"])
    def api_graduation_status():
        try:
            from bot_database import check_graduation
            user_id = req.args.get("user_id", type=int)
            if not user_id:
                return jsonify({"error": "user_id required"}), 400
            return jsonify(check_graduation(user_id))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ─── Subscription Plans ──────────────────────────────────────
    @app.route("/api/admin/plans", methods=["GET"])
    def api_get_plans():
        try:
            from bot_database import get_db
            conn = get_db()
            rows = conn.execute("SELECT * FROM subscription_plans ORDER BY price ASC").fetchall()
            conn.close()
            return jsonify({"plans": [dict(r) for r in rows]})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/plans", methods=["POST"])
    def api_add_plan():
        try:
            from bot_database import get_db
            import json
            data = req.get_json() or {}
            conn = get_db()
            conn.execute('''INSERT INTO subscription_plans
                (name,name_ar,price,currency,duration_days,description,features,is_active,is_featured)
                VALUES (?,?,?,?,?,?,?,?,?)''',
                (data.get("name",""), data.get("name_ar",""),
                 float(data.get("price",0)),
                 data.get("currency","IQD"),
                 int(data.get("duration_days",30)),
                 data.get("description",""),
                 json.dumps(data.get("features",[]), ensure_ascii=False),
                 int(data.get("is_active",1)),
                 int(data.get("is_featured",0))))
            conn.commit()
            conn.close()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/plans/<int:pid>", methods=["PUT"])
    def api_update_plan(pid):
        try:
            from bot_database import get_db
            import json
            data = req.get_json() or {}
            conn = get_db()
            conn.execute('''UPDATE subscription_plans SET
                name=?, name_ar=?, price=?, currency=?,
                duration_days=?, description=?, features=?,
                is_active=?, is_featured=?,
                updated_at=datetime("now")
                WHERE id=?''',
                (data.get("name",""), data.get("name_ar",""),
                 float(data.get("price",0)),
                 data.get("currency","IQD"),
                 int(data.get("duration_days",30)),
                 data.get("description",""),
                 json.dumps(data.get("features",[]), ensure_ascii=False),
                 int(data.get("is_active",1)),
                 int(data.get("is_featured",0)),
                 pid))
            conn.commit()
            conn.close()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/plans/<int:pid>", methods=["DELETE"])
    def api_delete_plan(pid):
        try:
            from bot_database import get_db
            conn = get_db()
            conn.execute("DELETE FROM subscription_plans WHERE id=?", (pid,))
            conn.commit()
            conn.close()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/admin/plans/<int:pid>/toggle", methods=["POST"])
    def api_toggle_plan(pid):
        try:
            from bot_database import get_db
            conn = get_db()
            row = conn.execute("SELECT is_active FROM subscription_plans WHERE id=?", (pid,)).fetchone()
            if not row:
                conn.close()
                return jsonify({"error": "not found"}), 404
            new_val = 0 if row["is_active"] else 1
            conn.execute("UPDATE subscription_plans SET is_active=? WHERE id=?", (new_val, pid))
            conn.commit()
            conn.close()
            return jsonify({"ok": True, "is_active": new_val})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/public/plans", methods=["GET"])
    def api_public_plans():
        try:
            from bot_database import get_db
            conn = get_db()
            rows = conn.execute("SELECT * FROM subscription_plans WHERE is_active=1 ORDER BY price ASC").fetchall()
            conn.close()
            return jsonify({"plans": [dict(r) for r in rows]})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


