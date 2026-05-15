# ================================================================
#  CONTENT ENGINE ROUTES (add to app.py imports + route section)
#  These are READ-ONLY routes that call content_engine functions.
#  Paste this block into app.py after the existing route definitions.
# ================================================================

# === Add this import at the top of app.py ===
# from modules.content_engine import (
#     get_index, list_lessons, get_lesson, get_next_lesson,
#     search_lessons, get_categories, scan_content,
#     create_lesson_from_admin, update_lesson_from_admin, delete_lesson_from_admin
# )

# === Add these routes inside app.py ===

# @app.route("/api/content/index")
# def content_index():
#     return jsonify(get_index())

# @app.route("/api/content/lessons")
# def content_lessons():
#     cat = request.args.get("category")
#     diff = request.args.get("difficulty")
#     return jsonify(list_lessons(category=cat, difficulty=diff))

# @app.route("/api/content/lesson/<lesson_id>")
# def content_lesson(lesson_id):
#     lesson = get_lesson(lesson_id)
#     if not lesson:
#         return jsonify({"error": "Lesson not found"}), 404
#     return jsonify(lesson)

# @app.route("/api/content/next_lesson/<lesson_id>")
# def content_next_lesson(lesson_id):
#     lesson = get_next_lesson(lesson_id)
#     if not lesson:
#         return jsonify({"message": "No next lesson"}), 404
#     return jsonify(lesson)

# @app.route("/api/content/search")
# def content_search():
#     q = request.args.get("q", "")
#     if not q:
#         return jsonify([])
#     return jsonify(search_lessons(q))

# @app.route("/api/content/categories")
# def content_categories():
#     return jsonify(get_categories())

# # === ADMIN content management routes ===
# @app.route("/api/admin/content/create", methods=["POST"])
# def admin_content_create():
#     data = request.get_json()
#     result = create_lesson_from_admin(data)
#     return jsonify(result)

# @app.route("/api/admin/content/update/<lesson_id>", methods=["PUT"])
# def admin_content_update(lesson_id):
#     data = request.get_json()
#     result = update_lesson_from_admin(lesson_id, data)
#     return jsonify(result)

# @app.route("/api/admin/content/delete/<lesson_id>", methods=["DELETE"])
# def admin_content_delete(lesson_id):
#     result = delete_lesson_from_admin(lesson_id)
#     return jsonify(result)

# @app.route("/api/admin/content/rescan", methods=["POST"])
# def admin_content_rescan():
#     scan_content()
#     return jsonify({"ok": True, "index": get_index()})
