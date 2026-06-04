"""
Yamen Academy - Admin API Blueprint
====================================
Flask Blueprint: /api/admin
يوفر endpoints إدارية مع طبقة إشعارات تيليجرام.
"""

import sys
import traceback
import json
from flask import Blueprint, request, jsonify, session

from config import ADMIN_IDS, BOT_TOKEN
from utils.notifications import send_telegram_notification, init_notifications

# ---- تأكد من تهيئة التوكن مرة واحدة ----
init_notifications(BOT_TOKEN)

admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


# ================================================================
# HELPERS
# ================================================================
def _success(data=None, msg="ok"):
    return jsonify({"status": "success", "message": msg, "data": data})


def _error(msg, code=400):
    return jsonify({"status": "error", "message": msg}), code


def _verify_admin():
    """يتأكد أن المستخدم مسجل دخول كأدمن."""
    user_id = session.get("user_id")
    if user_id is None:
        return None, _error("Unauthorized: no session", 401)
    if int(user_id) not in ADMIN_IDS:
        return None, _error("Forbidden: admin only", 403)
    return int(user_id), None


def _get_db():
    """وصول متزامن لقاعدة البيانات."""
    import sqlite3
    from config import DATABASE_PATH
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ================================================================
#  ⭐ ENDPOINT: GET /api/admin/stats
# ================================================================
@admin_api_bp.route("/stats", methods=["GET"])
def admin_stats():
    """إحصائيات سريعة للوحة التحكم."""
    _, auth_err = _verify_admin()
    if auth_err:
        return auth_err

    try:
        db = _get_db()

        total_students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        total_active = db.execute("SELECT COUNT(*) FROM students WHERE is_active = 1").fetchone()[0]
        pending = db.execute(
            "SELECT COUNT(*) FROM payments WHERE status = 'pending'"
        ).fetchone()[0]
        total_lessons = db.execute("SELECT COUNT(*) FROM content_index").fetchone()[0]
        active_subs = db.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE days_available > 0"
        ).fetchone()[0]

        # Phase 5.7: reading exam stats
        reading_attempts = db.execute(
            "SELECT COUNT(*) FROM reading_attempts WHERE status='completed'"
        ).fetchone()[0]
        reading_avg = db.execute(
            "SELECT ROUND(AVG(CAST(score AS FLOAT)/NULLIF(total,0)*100),1) FROM reading_attempts WHERE status='completed'"
        ).fetchone()[0] or 0
        writing_attempts_n = db.execute(
            "SELECT COUNT(*) FROM writing_attempts"
        ).fetchone()[0]

        db.close()

        return _success(data={
            "total_students": total_students,
            "active_students": total_active,
            "pending_payments": pending,
            "total_lessons": total_lessons,
            "active_subscriptions": active_subs,
            "reading_attempts": reading_attempts,
            "reading_avg_pct": reading_avg,
            "writing_attempts": writing_attempts_n,
        })
    except Exception:
        traceback.print_exc()
        return _error("Internal error loading stats", 500)


# ================================================================
#  ⭐ ENDPOINT: GET /api/admin/students
# ================================================================
@admin_api_bp.route("/students", methods=["GET"])
def admin_students():
    """قائمة الطلاب مع حالة التفعيل والـ placement."""
    _, auth_err = _verify_admin()
    if auth_err:
        return auth_err

    try:
        db = _get_db()
        rows = db.execute("""
            SELECT s.student_id, s.full_name, s.is_active,
                   p.band, p.level, p.path
            FROM students s
            LEFT JOIN placement_results p ON p.student_id = s.student_id
               AND p.id = (
                   SELECT MAX(id) FROM placement_results WHERE student_id = s.student_id
               )
            ORDER BY s.student_id
        """).fetchall()
        db.close()

        students = []
        for r in rows:
            students.append({
                "student_id": r["student_id"],
                "full_name": r["full_name"],
                "is_active": bool(r["is_active"]),
                "band": r["band"],
                "level": r["level"],
                "path": r["path"],
            })
        return _success(data=students)
    except Exception:
        traceback.print_exc()
        return _error("Internal error loading students", 500)


# ================================================================
#  ⭐ ENDPOINT: POST /api/admin/student/toggle_active/<id>
#                + إشعار تيليجرام عند التفعيل
# ================================================================
@admin_api_bp.route("/student/toggle_active/<int:student_id>", methods=["POST"])
def toggle_student_active(student_id):
    """
    تبديل حالة is_active للطالب.
    عند التفعيل (0→1): يرسل إشعار تيليجرام للطالب.
    """
    _, auth_err = _verify_admin()
    if auth_err:
        return auth_err

    try:
        db = _get_db()

        row = db.execute("SELECT is_active FROM students WHERE student_id = ?", (student_id,)).fetchone()
        if row is None:
            db.close()
            return _error(f"Student {student_id} not found", 404)

        current = row["is_active"]
        new_status = 0 if current else 1

        db.execute("UPDATE students SET is_active = ? WHERE student_id = ?", (new_status, student_id))
        db.commit()
        db.close()

        # ═══════════════════════════════════════
        #  📢 إشعار تيليجرام عند التفعيل فقط
        # ═══════════════════════════════════════
        if new_status == 1:
            try:
                send_telegram_notification(
                    student_id=student_id,
                    message_text=(
                        "<b>✅ تم تفعيل حسابك بنجاح في أكاديمية يامن!</b>\n"
                        "يمكنك الآن الدخول وتصفح الدورات والدروس المتاحة لك."
                    ),
                )
            except Exception as notify_err:
                # لا نمنع الـ response أبداً
                print(f"[ADMIN-API] ⚠️ فشل إرسال إشعار التفعيل: {notify_err}", file=sys.stderr)

        return _success(data={
            "student_id": student_id,
            "is_active": bool(new_status),
            "message": "تم التفعيل ✅" if new_status else "تم التعطيل ⛔",
        })
    except Exception:
        traceback.print_exc()
        return _error("Internal error", 500)


# ================================================================
#  ⭐ ENDPOINT: POST /api/admin/student/extend
#                + إشعار تيليجرام
# ================================================================
@admin_api_bp.route("/student/extend", methods=["POST"])
def extend_student_subscription():
    """
    تمديد اشتراك طالب بعدد أيام (JSON body: {student_id, days}).
    يرسل إشعار تيليجرام للطالب بعد التمديد.
    """
    _, auth_err = _verify_admin()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True)
    if not data:
        return _error("Missing JSON body")

    student_id = data.get("student_id")
    days = data.get("days")

    if not student_id or not days:
        return _error("Missing student_id or days")
    try:
        days = int(days)
    except (ValueError, TypeError):
        return _error("days must be an integer")
    if days <= 0:
        return _error("days must be positive")

    try:
        db = _get_db()

        # تفعيل الطالب إذا كان معطلاً
        db.execute("UPDATE students SET is_active = 1 WHERE student_id = ?", (student_id,))

        # تحديث أو إنشاء صف في subscriptions
        existing = db.execute(
            "SELECT id, days_available FROM subscriptions WHERE student_id = ?",
            (student_id,),
        ).fetchone()

        if existing:
            new_days = (existing["days_available"] or 0) + days
            db.execute(
                "UPDATE subscriptions SET days_available = ? WHERE student_id = ?",
                (new_days, student_id),
            )
        else:
            db.execute(
                "INSERT INTO subscriptions (student_id, days_available) VALUES (?, ?)",
                (student_id, days),
            )

        db.commit()
        db.close()

        # ═══════════════════════════════════════
        #  📢 إشعار تيليجرام
        # ═══════════════════════════════════════
        try:
            send_telegram_notification(
                student_id=student_id,
                message_text=(
                    f"<b>🔄 تحديث اشتراك:</b>\n"
                    f"تم تمديد فترة صلاحية اشتراكك بمقدار <b>{days}</b> يوماً إضافياً بنجاح.\n"
                    f"نتمنى لك توفيقاً مستمراً. 📚"
                ),
            )
        except Exception as notify_err:
            print(f"[ADMIN-API] ⚠️ فشل إرسال إشعار التمديد: {notify_err}", file=sys.stderr)

        return _success(data={
            "student_id": student_id,
            "days_added": days,
            "message": f"تمت إضافة {days} يوم بنجاح ✅",
        })
    except Exception:
        traceback.print_exc()
        return _error("Internal error", 500)


# ================================================================
#  ENDPOINT: GET /api/admin/payments/pending
# ================================================================
@admin_api_bp.route("/payments/pending", methods=["GET"])
def pending_payments():
    """المدفوعات المعلقة."""
    _, auth_err = _verify_admin()
    if auth_err:
        return auth_err

    try:
        db = _get_db()
        rows = db.execute(
            "SELECT * FROM payments WHERE status = 'pending' ORDER BY created_at DESC"
        ).fetchall()
        db.close()

        return _success(data=[dict(r) for r in rows])
    except Exception:
        traceback.print_exc()
        return _error("Internal error", 500)


# ================================================================
#  ENDPOINT: POST /api/admin/payment/approve/<id>
# ================================================================
@admin_api_bp.route("/payment/approve/<int:payment_id>", methods=["POST"])
def approve_payment(payment_id):
    """الموافقة على دفعة — تفعيل الطالب وإنشاء/تحديث الاشتراك."""
    _, auth_err = _verify_admin()
    if auth_err:
        return auth_err

    try:
        db = _get_db()

        payment = db.execute(
            "SELECT * FROM payments WHERE id = ?", (payment_id,)
        ).fetchone()
        if not payment:
            db.close()
            return _error("Payment not found", 404)

        student_id = payment["student_id"]
        plan = payment.get("plan", "flexible")
        plan_days = {"flexible": 30, "emergency": 30, "excellence": 90}

        # موافقة
        db.execute("UPDATE payments SET status = 'approved' WHERE id = ?", (payment_id,))

        # تفعيل الطالب
        db.execute("UPDATE students SET is_active = 1 WHERE student_id = ?", (student_id,))

        # اشتراك
        days = plan_days.get(plan, 30)
        existing = db.execute(
            "SELECT id, days_available FROM subscriptions WHERE student_id = ?",
            (student_id,),
        ).fetchone()
        if existing:
            new_days = (existing["days_available"] or 0) + days
            db.execute(
                "UPDATE subscriptions SET days_available = ? WHERE student_id = ?",
                (new_days, student_id),
            )
        else:
            db.execute(
                "INSERT INTO subscriptions (student_id, days_available) VALUES (?, ?)",
                (student_id, days),
            )

        db.commit()

        # إشعار
        try:
            send_telegram_notification(
                student_id=student_id,
                message_text=(
                    f"<b>✅ تم تأكيد دفعتك!</b>\n"
                    f"تمت إضافة <b>{days}</b> يوم إلى اشتراكك.\n"
                    f"أهلاً بك في أكاديمية يامن! 🎉"
                ),
            )
        except Exception:
            pass

        db.close()
        return _success(data={"payment_id": payment_id, "status": "approved"})
    except Exception:
        traceback.print_exc()
        return _error("Internal error", 500)


# ================================================================
#  ENDPOINT: POST /api/admin/payment/reject/<id>
# ================================================================
@admin_api_bp.route("/payment/reject/<int:payment_id>", methods=["POST"])
def reject_payment(payment_id):
    """رفض دفعة."""
    _, auth_err = _verify_admin()
    if auth_err:
        return auth_err

    try:
        db = _get_db()
        db.execute("UPDATE payments SET status = 'rejected' WHERE id = ?", (payment_id,))
        db.commit()
        db.close()
        return _success(data={"payment_id": payment_id, "status": "rejected"})
    except Exception:
        traceback.print_exc()
        return _error("Internal error", 500)
