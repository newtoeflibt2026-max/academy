with open("templates/student_portal.html", "r", encoding="utf-8") as f:
    content = f.read()

# إصلاح API endpoint للطالب ليبحث بكلا العمودين
old = "'/api/user/graduation-status?user_id='"
new = "'/api/student/profile?user_id='"

# إضافة endpoint جديد في app.py
api_code = '''
@app.route("/api/student/profile", methods=["GET"])
def api_student_profile():
    uid = request.args.get("user_id", "")
    if not uid:
        return jsonify({"error": "user_id required"}), 400
    conn = get_db()
    try:
        # ابحث بكلا العمودين
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
'''

with open("app.py", "r", encoding="utf-8") as f:
    app_content = f.read()

if "api_student_profile" not in app_content:
    # أضف قبل if __name__
    if 'if __name__ == "__main__":' in app_content:
        app_content = app_content.replace(
            'if __name__ == "__main__":',
            api_code + '\nif __name__ == "__main__":'
        )
    else:
        app_content += api_code
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(app_content)
    print("Added /api/student/profile endpoint")
else:
    print("Endpoint already exists")

# إصلاح student_portal.html - استخدام الـ endpoint الجديد
content = content.replace(
    "/api/user/graduation-status",
    "/api/student/profile"
)

# إصلاح شرط الموافقة
content = content.replace(
    "data.is_paid === false",
    "data.found === false || data.is_paid === false"
)
content = content.replace(
    "data.is_active === false", 
    "data.is_active === false"
)

with open("templates/student_portal.html", "w", encoding="utf-8") as f:
    f.write(content)
print("student_portal.html updated")
print("ALL DONE")
