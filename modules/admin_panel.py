"""
admin_panel.py — Blueprint لوحة الإمبراطورة السيادية
تحكم مطلق: إضافة/حذف/تعديل/إخفاء أي مهارة بحقول حرة
"""
from flask import Blueprint, render_template, jsonify, request
from modules.models import query_db, execute_db
from datetime import datetime

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# ═══ الصفحة الرئيسية ═══
@admin_bp.route("/")
def admin_dashboard():
    return render_template("admin.html")

# ═══ الإحصائيات ═══
@admin_bp.route("/api/stats")
def api_stats():
    sc = query_db("SELECT COUNT(*) as c FROM students", one=True)
    lc = query_db("SELECT COUNT(*) as c FROM library_items WHERE is_active=1", one=True)
    kc = query_db("SELECT COUNT(*) as c FROM daily_skills WHERE is_active=1", one=True)
    qc = query_db("SELECT COUNT(*) as c FROM questions WHERE is_active=1", one=True)
    return jsonify({
        "students": sc["c"] if sc else 0,
        "library": lc["c"] if lc else 0,
        "skills": kc["c"] if kc else 0,
        "questions": qc["c"] if qc else 0
    })

# ═══ ① Dynamic Skills API ═══
@admin_bp.route("/api/skills")
def api_get_skills():
    rows = query_db("SELECT * FROM daily_skills ORDER BY sort_order, id")
    return jsonify([dict(r) for r in rows] if rows else [])

@admin_bp.route("/api/skills/add", methods=["POST"])
def api_add_skill():
    """إضافة مهارة جديدة — حقول حرة بالكامل"""
    d = request.get_json()
    title      = d.get("title", "").strip()
    skill_type = d.get("skill_type", "custom").strip()
    task_type  = d.get("task_type", "text").strip()
    icon       = d.get("icon", "📝").strip()
    time_limit = int(d.get("time_limit", 45))
    telegram_link = d.get("telegram_link", "").strip()

    if not title:
        return jsonify({"error": "اسم المهارة مطلوب"}), 400

    execute_db(
        """INSERT INTO daily_skills (title, skill_type, task_type, icon, time_limit, telegram_link, is_active)
           VALUES (?, ?, ?, ?, ?, ?, 1)""",
        (title, skill_type, task_type, icon, time_limit, telegram_link))

    # تسجيل في النشاط
    sid = query_db("SELECT last_insert_rowid() as id", one=True)
    return jsonify({
        "success": True,
        "skill": {
            "id": sid["id"] if sid else 0,
            "title": title,
            "skill_type": skill_type,
            "task_type": task_type,
            "icon": icon,
            "time_limit": time_limit
        },
        "message": f"✅ تمت إضافة: {title}"
    })

@admin_bp.route("/api/skills/toggle", methods=["POST"])
def api_toggle_skill():
    """تفعيل/إخفاء مهارة"""
    d = request.get_json()
    sid = d.get("id")
    active = d.get("is_active", 0)
    execute_db("UPDATE daily_skills SET is_active=? WHERE id=?", (active, sid))
    return jsonify({"success": True})

@admin_bp.route("/api/skills/update", methods=["POST"])
def api_update_skill():
    """تحديث بيانات مهارة موجودة"""
    d = request.get_json()
    sid = d.get("id")
    if not sid:
        return jsonify({"error": "ID مطلوب"}), 400

    title = d.get("title", "").strip()
    skill_type = d.get("skill_type", "").strip()
    task_type = d.get("task_type", "").strip()
    icon = d.get("icon", "").strip()
    time_limit = int(d.get("time_limit", 45))
    telegram_link = d.get("telegram_link", "").strip()

    execute_db(
        """UPDATE daily_skills SET title=?, skill_type=?, task_type=?, icon=?, time_limit=?, telegram_link=?
           WHERE id=?""",
        (title, skill_type, task_type, icon, time_limit, telegram_link, sid))

    return jsonify({"success": True, "message": f"✅ تم تحديث: {title}"})

@admin_bp.route("/api/skills/delete/<int:skill_id>", methods=["DELETE"])
def api_delete_skill(skill_id):
    execute_db("DELETE FROM daily_skills WHERE id=?", (skill_id,))
    return jsonify({"success": True})

@admin_bp.route("/api/skills/reorder", methods=["POST"])
def api_reorder_skills():
    """إعادة ترتيب المهارات"""
    d = request.get_json()
    order = d.get("order", [])  # [{id: 1, sort_order: 0}, ...]
    for item in order:
        execute_db("UPDATE daily_skills SET sort_order=? WHERE id=?", (item["sort_order"], item["id"]))
    return jsonify({"success": True})

# ═══ ② Library API ═══
@admin_bp.route("/api/library")
def api_get_library():
    rows = query_db("SELECT * FROM library_items WHERE is_active=1 ORDER BY sort_order, id")
    return jsonify([dict(r) for r in rows] if rows else [])

@admin_bp.route("/api/library/add", methods=["POST"])
def api_add_library():
    d = request.get_json()
    title = d.get("title", "").strip()
    item_type = d.get("item_type", "pdf").strip()
    url = d.get("url", "").strip()
    telegram_link = d.get("telegram_link", "").strip()
    icon = d.get("icon", "📄").strip()
    category = d.get("category", "general").strip()

    if not title:
        return jsonify({"error": "العنوان مطلوب"}), 400

    execute_db(
        "INSERT INTO library_items (title, item_type, url, telegram_link, icon, category) VALUES (?,?,?,?,?,?)",
        (title, item_type, url, telegram_link, icon, category))
    return jsonify({"success": True, "message": f"✅ أُضيف: {title}"})

@admin_bp.route("/api/library/delete/<int:item_id>", methods=["DELETE"])
def api_delete_library(item_id):
    execute_db("DELETE FROM library_items WHERE id=?", (item_id,))
    return jsonify({"success": True})

# ═══ ③ AI Config API ═══
@admin_bp.route("/api/ai_config")
def api_get_ai_config():
    rows = query_db("SELECT * FROM ai_config ORDER BY id")
    return jsonify([dict(r) for r in rows] if rows else [])

@admin_bp.route("/api/ai_config/update", methods=["POST"])
def api_update_ai_config():
    d = request.get_json()
    key = d.get("config_key")
    val = d.get("config_value")
    execute_db("UPDATE ai_config SET config_value=?, updated_at=CURRENT_TIMESTAMP WHERE config_key=?", (val, key))
    return jsonify({"success": True})

# ═══ ④ Students API ═══
@admin_bp.route("/api/students")
def api_get_students():
    rows = query_db("SELECT * FROM students ORDER BY xp DESC")
    return jsonify([dict(r) for r in rows] if rows else [])

# ═══ سجل النشاط ═══
@admin_bp.route("/api/activity")
def api_get_activity():
    rows = query_db(
        "SELECT a.*, s.first_name, s.username FROM activity_log a "
        "LEFT JOIN students s ON a.user_id = s.telegram_id "
        "ORDER BY a.created_at DESC LIMIT 50")
    return jsonify([dict(r) for r in rows] if rows else [])
