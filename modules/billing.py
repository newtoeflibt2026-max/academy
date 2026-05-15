from flask import Blueprint, jsonify, request
from modules.models import query_db, execute_db

billing_bp = Blueprint("billing", __name__)

@billing_bp.route("/api/plans")
def get_plans():
    rows = query_db("SELECT * FROM billing_plans WHERE is_active=1")
    plans = []
    for r in rows:
        plans.append({"id": r["id"], "name": r["name"], "price_monthly": r["price_monthly"], "features": r["features"]})
    return jsonify(plans)

@billing_bp.route("/api/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()
    sid = data.get("student_id")
    pid = data.get("plan_id")
    execute_db("INSERT OR REPLACE INTO subscriptions (student_id, plan_id, status, expires_at) VALUES (?,?,?,datetime('now','+30 days'))", (sid, pid))
    return jsonify({"ok": True})

@billing_bp.route("/api/status/<int:student_id>")
def subscription_status(student_id):
    row = query_db("SELECT s.*, p.name FROM subscriptions s JOIN billing_plans p ON s.plan_id=p.id WHERE s.student_id=? AND s.status='active' ORDER BY s.id DESC LIMIT 1", (student_id,), one=True)
    return jsonify({"active": row is not None, "plan": dict(row) if row else None})
