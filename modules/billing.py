"""
billing.py v17.0 — نظام الباقات والاشتراكات
- استيراد خطط الأسعار
- تفعيل/تعطيل المحتوى حسب حالة الاشتراك
"""
from flask import Blueprint, jsonify, request
from modules.models import query_db, execute_db
from datetime import datetime, timedelta

billing_bp = Blueprint("billing", __name__, url_prefix="/billing")

@billing_bp.route("/api/plans")
def api_get_plans():
    """جميع الباقات المتاحة"""
    rows = query_db("SELECT * FROM billing_plans WHERE is_active=1 ORDER BY sort_order")
    return jsonify([dict(r) for r in rows] if rows else [])

@billing_bp.route("/api/subscribe", methods=["POST"])
def api_subscribe():
    """تفعيل اشتراك طالب"""
    d = request.get_json()
    user_id = d.get("user_id")
    plan_id = d.get("plan_id")

    if not user_id or not plan_id:
        return jsonify({"error": "البيانات مطلوبة"}), 400

    plan = query_db("SELECT * FROM billing_plans WHERE id=?", (plan_id,), one=True)
    if not plan:
        return jsonify({"error": "باقة غير موجودة"}), 404

    # إلغاء الاشتراكات السابقة
    execute_db("UPDATE subscriptions SET status='expired' WHERE user_id=? AND status='active'", (user_id,))

    # إنشاء اشتراك جديد
    end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    execute_db(
        """INSERT INTO subscriptions (user_id, plan_id, plan_name, status, start_date, end_date, payment_method, amount_paid)
           VALUES (?,?,?,?,CURRENT_TIMESTAMP,?,?,?)""",
        (user_id, plan_id, plan["name"], "active", end_date,
         d.get("payment_method", "manual"), plan["price_monthly"]))

    execute_db("INSERT INTO activity_log (user_id, action, details) VALUES (?,?,?)",
               (user_id, "subscription_activated", f"Plan: {plan['name']}"))

    return jsonify({"success": True, "plan": plan["name"], "end_date": end_date})

@billing_bp.route("/api/status/<int:user_id>")
def api_subscription_status(user_id):
    """حالة اشتراك الطالب"""
    row = query_db(
        "SELECT * FROM subscriptions WHERE user_id=? AND status='active' ORDER BY id DESC LIMIT 1",
        (user_id,), one=True)

    if row:
        sub = dict(row)
        # التحقق من انتهاء الصلاحية
        if sub["end_date"] and datetime.strptime(sub["end_date"], "%Y-%m-%d %H:%M:%S") < datetime.now():
            execute_db("UPDATE subscriptions SET status='expired' WHERE id=?", (sub["id"],))
            return jsonify({"active": False, "plan": None, "message": "انتهى الاشتراك"})

        return jsonify({
            "active": True,
            "plan": sub["plan_name"],
            "plan_id": sub["plan_id"],
            "start_date": sub["start_date"],
            "end_date": sub["end_date"]
        })

    return jsonify({"active": False, "plan": None})

@billing_bp.route("/api/admin/subscriptions")
def api_admin_subscriptions():
    """قائمة اشتراكات جميع الطلاب (للإدارة)"""
    rows = query_db(
        """SELECT s.*, st.first_name, st.username FROM subscriptions s
           LEFT JOIN students st ON s.user_id = st.telegram_id
           ORDER BY s.created_at DESC LIMIT 100""")
    return jsonify([dict(r) for r in rows] if rows else [])
