# modules/subscription_engine.py — نظام الاشتراكات والدفع (ويب)
from __future__ import annotations

import json, sqlite3, os, uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template, current_app, send_from_directory
from werkzeug.utils import secure_filename
from loguru import logger

sub_bp = Blueprint("subscriptions_web", __name__)

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_storage", "yamen.db")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_storage", "receipts")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}

# ── الباقات (متطابقة مع subscriptions.py) ────────────────────────────────────
PLANS = {
    "flexible": {
        "key": "flexible",
        "name": "المسار المرن",
        "emoji": "📘",
        "price": 30,
        "days": 30,
        "months": 1,
        "unlock_ratio": 0.333,       # ثلث الدروس فقط
        "description": "مناسب للمتعلم المنتظم — شهر كامل من التدريب المنظم",
        "features": ["✅ ثلث الدروس من كل قسم", "✅ اختبارات تجريبية", "✅ تتبع التقدم"],
        "note": "يفتح ثلث الدروس من كل قسم لمدة شهر واحد"
    },
    "excellence": {
        "key": "excellence",
        "name": "مسار التفوق",
        "emoji": "🏆",
        "price": 65,
        "days": 90,
        "months": 3,
        "unlock_ratio": 0.333,       # كل شهر يفتح ثلث
        "description": "الأفضل قيمةً — 3 أشهر لرفع درجتك بشكل مضمون",
        "features": ["✅ جميع مميزات المرن", "✅ خطة مخصصة", "✅ أولوية الدعم", "✅ دروس موزعة على 3 أشهر"],
        "note": "توزع الدروس على 3 أشهر بالتساوي"
    },
    "emergency": {
        "key": "emergency",
        "name": "مسار الطوارئ",
        "emoji": "⚡",
        "price": 45,
        "days": 30,
        "months": 1,
        "unlock_ratio": 1.0,         # كل الدروس
        "description": "امتحانك قريب؟ تدريب مكثف لأقصى استفادة في وقت قصير",
        "features": ["✅ كل الدروس مفتوحة فوراً", "✅ خطة يومية مكثفة", "✅ تركيز على نقاط الضعف", "✅ محاكاة حقيقية"],
        "note": "جميع الدروس مفتوحة من اليوم الأول"
    },
}

PAYMENT_METHODS = {
    "zain": {
        "key": "zain",
        "name": "زين كاش",
        "emoji": "💚",
        "number": "0798919150",
        "instructions": "افتح تطبيق زين كاش → إرسال → أدخل الرقم → أدخل المبلغ → أرسل"
    },
    "click": {
        "key": "click",
        "name": "كليك — البنك الإسلامي",
        "emoji": "🔵",
        "number": "0798919150",
        "instructions": "افتح تطبيق كليك → تحويل → أدخل الرقم → أدخل المبلغ → حوّل"
    },
    "western_union": {
        "key": "western_union",
        "name": "Western Union — دولي",
        "emoji": "🌍",
        "number": "00962798919150",
        "instructions": "يرجى التواصل عبر واتساب على الرقم 00962798919150 لإتمام الدفع",
        "needs_whatsapp": True
    },
}

# ── Database helpers ─────────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                web_user_id TEXT UNIQUE,
                name        TEXT NOT NULL,
                path_type   TEXT DEFAULT 'academic',
                target_band REAL DEFAULT 6.0,
                current_band REAL DEFAULT 0,
                days_left   INTEGER DEFAULT 60,
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS payments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                plan_key    TEXT NOT NULL,
                plan_name   TEXT NOT NULL,
                amount      REAL NOT NULL,
                method      TEXT,
                status      TEXT DEFAULT 'pending',
                receipt_path TEXT,
                admin_notes TEXT,
                approved_by TEXT,
                approved_at TEXT,
                rejected_at TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS subscriptions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL UNIQUE,
                plan_key    TEXT NOT NULL,
                plan_name   TEXT NOT NULL,
                starts_at   TEXT NOT NULL DEFAULT (datetime('now')),
                ends_at     TEXT NOT NULL,
                is_active   INTEGER DEFAULT 1,
                payment_id  INTEGER REFERENCES payments(id),
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS lesson_progress (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                lesson_id   TEXT NOT NULL,
                completed   INTEGER DEFAULT 0,
                score       REAL DEFAULT 0,
                completed_at TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, lesson_id)
            );
            CREATE TABLE IF NOT EXISTS admin_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id    TEXT NOT NULL,
                action      TEXT NOT NULL,
                target_id   TEXT,
                details     TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );
        """)
        db.commit()
    logger.info("✅ Payment/Subscription tables initialized")

# Initialize on import
init_db()

# ── Helper: allowed file ─────────────────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ── Helper: get available lesson ids ─────────────────────────────────────────
def get_all_lesson_ids():
    """قراءة lessons_map.json لمعرفة جميع الدروس المتاحة."""
    map_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_storage", "reading", "lessons_map.json")
    if not os.path.exists(map_path):
        return []
    with open(map_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [l["lesson_id"] for l in data.get("lessons", [])]

# ── Helper: calculate unlocked lessons for a subscription ────────────────────
def get_unlocked_lessons(user_id: str) -> dict:
    """Returns: {unlocked_lesson_ids: [...], total: N, unlocked: M, month: X}"""
    all_ids = get_all_lesson_ids()
    if not all_ids:
        return {"unlocked_lesson_ids": [], "total": 0, "unlocked": 0, "month": 0}

    with get_db() as db:
        sub = db.execute(
            "SELECT * FROM subscriptions WHERE user_id=? AND is_active=1 AND ends_at > datetime('now')",
            (user_id,)
        ).fetchone()
        if not sub:
            return {"unlocked_lesson_ids": [], "total": len(all_ids), "unlocked": 0, "month": 0}

        plan = PLANS.get(sub["plan_key"])
        if not plan:
            return {"unlocked_lesson_ids": [], "total": len(all_ids), "unlocked": 0, "month": 0}

        # طوارئ: كل الدروس
        if plan["unlock_ratio"] >= 1.0:
            return {
                "unlocked_lesson_ids": all_ids,
                "total": len(all_ids),
                "unlocked": len(all_ids),
                "month": 1
            }

        # مرن / تفوق: حسب الشهر
        start_date = datetime.fromisoformat(sub["starts_at"])
        now = datetime.now()
        # month number (1-based)
        days_elapsed = (now - start_date).days
        month_num = min(plan["months"], max(1, days_elapsed // 30 + 1))

        per_month = max(1, len(all_ids) // plan["months"])
        unlocked_count = month_num * per_month
        if plan["key"] == "flexible":
            unlocked_count = per_month  # شهر واحد فقط
            month_num = 1

        unlocked_ids = all_ids[:min(unlocked_count, len(all_ids))]
        return {
            "unlocked_lesson_ids": unlocked_ids,
            "total": len(all_ids),
            "unlocked": len(unlocked_ids),
            "month": month_num
        }

# ──────────────────────────────────────────────────────────────────────────────
# API ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@sub_bp.route("/api/plans")
def api_plans():
    """إرجاع الباقات وطرق الدفع."""
    return jsonify({
        "plans": {k: {kk: vv for kk, vv in v.items()} for k, v in PLANS.items()},
        "payment_methods": {k: {kk: vv for kk, vv in v.items()} for k, v in PAYMENT_METHODS.items()},
    })

@sub_bp.route("/api/payment/create", methods=["POST"])
def api_create_payment():
    """إنشاء طلب دفع جديد."""
    data = request.json
    user_id = data.get("user_id") or request.cookies.get("yamen_user_id") or str(uuid.uuid4())
    plan_key = data.get("plan_key")
    method = data.get("method")

    if plan_key not in PLANS:
        return jsonify({"error": "باقة غير صالحة"}), 400
    if method not in PAYMENT_METHODS:
        return jsonify({"error": "طريقة دفع غير صالحة"}), 400

    plan = PLANS[plan_key]
    with get_db() as db:
        # Check if student exists
        student = db.execute("SELECT * FROM students WHERE web_user_id=?", (user_id,)).fetchone()
        if not student:
            db.execute(
                "INSERT INTO students (web_user_id, name, path_type, target_band, days_left) VALUES (?,?,?,?,?)",
                (user_id, data.get("name", "مستخدم جديد"), data.get("path_type", "academic"), float(data.get("target_band", 6.0)), int(data.get("days_left", 60)))
            )
        db.commit()

        # Check pending payment
        pending = db.execute(
            "SELECT id FROM payments WHERE user_id=? AND status='pending'", (user_id,)
        ).fetchone()
        if pending:
            return jsonify({"error": "لديك طلب دفع معلق بالفعل", "payment_id": pending["id"]}), 409

        # Create payment
        cur = db.execute(
            """INSERT INTO payments (user_id, plan_key, plan_name, amount, method, status)
               VALUES (?,?,?,?,?,'pending')""",
            (user_id, plan_key, plan["name"], plan["price"], method)
        )
        db.commit()
        payment_id = cur.lastrowid

    logger.info(f"Payment #{payment_id} created: user={user_id} plan={plan_key} method={method}")
    return jsonify({"payment_id": payment_id, "user_id": user_id, "message": "تم إنشاء طلب الدفع"})


@sub_bp.route("/api/payment/upload-receipt", methods=["POST"])
def api_upload_receipt():
    """رفع صورة الوصل."""
    if "receipt" not in request.files:
        return jsonify({"error": "لم يتم إرفاق صورة"}), 400

    file = request.files["receipt"]
    payment_id = request.form.get("payment_id")
    user_id = request.form.get("user_id") or request.cookies.get("yamen_user_id")

    if not payment_id or not user_id:
        return jsonify({"error": "معرّف الدفع مطلوب"}), 400

    if not file or not allowed_file(file.filename):
        return jsonify({"error": "صيغة الملف غير مدعومة. استخدم: png, jpg, jpeg, gif, webp, pdf"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"receipt_{payment_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    with get_db() as db:
        db.execute(
            "UPDATE payments SET receipt_path=?, updated_at=datetime('now') WHERE id=? AND user_id=?",
            (filename, int(payment_id), user_id)
        )
        db.commit()

    logger.info(f"Receipt uploaded for payment #{payment_id}: {filename}")
    return jsonify({"message": "✅ تم رفع الوصل بنجاح. سيتم مراجعة طلبك قريباً.", "payment_id": payment_id})


@sub_bp.route("/api/payment/status")
def api_payment_status():
    """معرفة حالة الدفع."""
    user_id = request.args.get("user_id") or request.cookies.get("yamen_user_id")
    payment_id = request.args.get("payment_id")

    with get_db() as db:
        if payment_id:
            p = db.execute("SELECT * FROM payments WHERE id=? AND user_id=?", (int(payment_id), user_id)).fetchone()
        else:
            p = db.execute("SELECT * FROM payments WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user_id,)).fetchone()

        if not p:
            return jsonify({"status": "none"})

        sub = db.execute("SELECT * FROM subscriptions WHERE user_id=? AND is_active=1", (user_id,)).fetchone()

        return jsonify({
            "payment_id": p["id"],
            "status": p["status"],
            "plan_name": p["plan_name"],
            "amount": p["amount"],
            "created_at": p["created_at"],
            "subscription_active": bool(sub),
            "subscription_ends": sub["ends_at"] if sub else None,
        })


@sub_bp.route("/api/my-lessons")
def api_my_lessons():
    """الدروس المتاحة للمستخدم حسب اشتراكه."""
    user_id = request.args.get("user_id") or request.cookies.get("yamen_user_id")
    if not user_id:
        return jsonify({"error": "لم يتم التعرف على المستخدم"}), 400

    unlocked = get_unlocked_lessons(user_id)
    return jsonify(unlocked)


@sub_bp.route("/api/progress/save", methods=["POST"])
def api_save_progress():
    """حفظ تقدم الدرس."""
    data = request.json
    user_id = data.get("user_id") or request.cookies.get("yamen_user_id")
    lesson_id = data.get("lesson_id")
    completed = data.get("completed", 0)
    score = data.get("score", 0)

    with get_db() as db:
        db.execute(
            """INSERT INTO lesson_progress (user_id, lesson_id, completed, score, completed_at)
               VALUES (?,?,?,?,datetime('now'))
               ON CONFLICT(user_id, lesson_id) DO UPDATE SET
               completed=excluded.completed, score=excluded.score,
               completed_at=CASE WHEN excluded.completed=1 THEN datetime('now') ELSE lesson_progress.completed_at END""",
            (user_id, lesson_id, completed, score)
        )
        db.commit()
    return jsonify({"message": "✅ تم حفظ التقدم"})


# ── WEB PAGES ────────────────────────────────────────────────────────────────
@sub_bp.route("/subscribe")
def page_subscribe():
    """صفحة الاشتراك والباقات."""
    return render_template("pricing.html", plans=PLANS, methods=PAYMENT_METHODS)

@sub_bp.route("/payment/<plan_key>")
def page_payment(plan_key):
    """صفحة الدفع لباقة محددة."""
    if plan_key not in PLANS:
        return "باقة غير موجودة", 404
    return render_template("payment.html", plan=PLANS[plan_key], methods=PAYMENT_METHODS)

@sub_bp.route("/register")
def page_register():
    return render_template("register.html")


# ── ADMIN ENDPOINTS ──────────────────────────────────────────────────────────
@sub_bp.route("/admin/subscriptions")
def admin_dashboard():
    """لوحة تحكم الأدمن."""
    return render_template("admin_subscriptions.html", plans=PLANS, methods=PAYMENT_METHODS)

@sub_bp.route("/api/admin/payments")
def api_admin_payments():
    """قائمة جميع طلبات الدفع (للأدمن)."""
    status_filter = request.args.get("status", "all")
    with get_db() as db:
        if status_filter == "all":
            rows = db.execute(
                "SELECT p.*, s.is_active as sub_active, s.ends_at FROM payments p LEFT JOIN subscriptions s ON s.payment_id = p.id ORDER BY p.created_at DESC"
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT p.*, s.is_active as sub_active, s.ends_at FROM payments p LEFT JOIN subscriptions s ON s.payment_id = p.id WHERE p.status=? ORDER BY p.created_at DESC",
                (status_filter,)
            ).fetchall()
    return jsonify([dict(r) for r in rows])

@sub_bp.route("/api/admin/approve", methods=["POST"])
def api_admin_approve():
    """موافقة على طلب دفع وتفعيل الاشتراك."""
    data = request.json
    payment_id = data.get("payment_id")
    admin_id = data.get("admin_id", "web_admin")
    notes = data.get("notes", "")

    with get_db() as db:
        payment = db.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
        if not payment:
            return jsonify({"error": "طلب الدفع غير موجود"}), 404
        if payment["status"] not in ("pending", "rejected"):
            return jsonify({"error": f"لا يمكن الموافقة على طلب حالته {payment['status']}"}), 400

        plan = PLANS.get(payment["plan_key"])
        if not plan:
            return jsonify({"error": "الباقة غير معروفة"}), 400

        start_date = datetime.now().isoformat()
        end_date = (datetime.now() + timedelta(days=plan["days"])).isoformat()

        # Update payment
        db.execute(
            "UPDATE payments SET status='approved', approved_by=?, approved_at=datetime('now'), admin_notes=?, updated_at=datetime('now') WHERE id=?",
            (admin_id, notes, payment_id)
        )

        # Create/update subscription
        db.execute(
            """INSERT INTO subscriptions (user_id, plan_key, plan_name, starts_at, ends_at, is_active, payment_id)
               VALUES (?,?,?,?,?,1,?)
               ON CONFLICT(user_id) DO UPDATE SET
               plan_key=excluded.plan_key, plan_name=excluded.plan_name,
               starts_at=excluded.starts_at, ends_at=excluded.ends_at,
               is_active=1, payment_id=excluded.payment_id,
               updated_at=datetime('now')""",
            (payment["user_id"], plan["key"], plan["name"], start_date, end_date, payment_id)
        )

        # Update student active flag
        db.execute(
            "UPDATE students SET is_active=1, updated_at=datetime('now') WHERE web_user_id=?",
            (payment["user_id"],)
        )

        # Log
        db.execute(
            "INSERT INTO admin_log (admin_id, action, target_id, details) VALUES (?,?,?,?)",
            (admin_id, "approve_payment", str(payment_id),
             f"Approved payment #{payment_id} | Plan: {plan['name']} | User: {payment['user_id']} | Until: {end_date}")
        )
        db.commit()

    logger.info(f"✅ Payment #{payment_id} APPROVED by {admin_id}")
    return jsonify({"message": "✅ تمت الموافقة وتفعيل الاشتراك", "ends_at": end_date})


@sub_bp.route("/api/admin/reject", methods=["POST"])
def api_admin_reject():
    """رفض طلب دفع."""
    data = request.json
    payment_id = data.get("payment_id")
    admin_id = data.get("admin_id", "web_admin")
    notes = data.get("notes", "")

    with get_db() as db:
        payment = db.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
        if not payment:
            return jsonify({"error": "طلب الدفع غير موجود"}), 404
        if payment["status"] not in ("pending", "approved"):
            return jsonify({"error": f"لا يمكن رفض طلب حالته {payment['status']}"}), 400

        db.execute(
            "UPDATE payments SET status='rejected', approved_by=?, rejected_at=datetime('now'), admin_notes=?, updated_at=datetime('now') WHERE id=?",
            (admin_id, notes, payment_id)
        )

        # Cancel active subscription if exists
        db.execute(
            "UPDATE subscriptions SET is_active=0, updated_at=datetime('now') WHERE payment_id=? AND is_active=1",
            (payment_id,)
        )

        # Log
        db.execute(
            "INSERT INTO admin_log (admin_id, action, target_id, details) VALUES (?,?,?,?)",
            (admin_id, "reject_payment", str(payment_id),
             f"Rejected payment #{payment_id} | Notes: {notes} | User: {payment['user_id']}")
        )
        db.commit()

    logger.info(f"❌ Payment #{payment_id} REJECTED by {admin_id}")
    return jsonify({"message": "❌ تم رفض الطلب وإلغاء الاشتراك إن وجد"})


@sub_bp.route("/api/admin/stats")
def api_admin_stats():
    """إحصائيات الأدمن."""
    with get_db() as db:
        total_students = db.execute("SELECT COUNT(*) as c FROM students").fetchone()["c"]
        pending = db.execute("SELECT COUNT(*) as c FROM payments WHERE status='pending'").fetchone()["c"]
        approved = db.execute("SELECT COUNT(*) as c FROM payments WHERE status='approved'").fetchone()["c"]
        rejected = db.execute("SELECT COUNT(*) as c FROM payments WHERE status='rejected'").fetchone()["c"]
        active_subs = db.execute(
            "SELECT COUNT(*) as c FROM subscriptions WHERE is_active=1 AND ends_at > datetime('now')"
        ).fetchone()["c"]
        total_revenue = db.execute(
            "SELECT COALESCE(SUM(amount),0) as c FROM payments WHERE status='approved'"
        ).fetchone()["c"]
        recent_logs = db.execute(
            "SELECT * FROM admin_log ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    return jsonify({
        "total_students": total_students,
        "pending_payments": pending,
        "approved_payments": approved,
        "rejected_payments": rejected,
        "active_subscriptions": active_subs,
        "total_revenue_jod": total_revenue,
        "recent_logs": [dict(r) for r in recent_logs]
    })

@sub_bp.route("/api/admin/cancel-subscription", methods=["POST"])
def api_admin_cancel_subscription():
    """إلغاء اشتراك نشط (صلاحية الأدمن للإلغاء بعد الموافقة)."""
    data = request.json
    user_id = data.get("user_id")
    admin_id = data.get("admin_id", "web_admin")
    notes = data.get("notes", "")

    if not user_id:
        return jsonify({"error": "معرّف المستخدم مطلوب"}), 400

    with get_db() as db:
        sub = db.execute(
            "SELECT * FROM subscriptions WHERE user_id=? AND is_active=1",
            (user_id,)
        ).fetchone()
        if not sub:
            return jsonify({"error": "لا يوجد اشتراك نشط لهذا المستخدم"}), 404

        db.execute("UPDATE subscriptions SET is_active=0, updated_at=datetime('now') WHERE id=?", (sub["id"],))
        db.execute(
            "UPDATE payments SET status='rejected', admin_notes=?, rejected_at=datetime('now'), updated_at=datetime('now') WHERE id=?",
            (notes, sub["payment_id"])
        )
        db.execute(
            "INSERT INTO admin_log (admin_id, action, target_id, details) VALUES (?,?,?,?)",
            (admin_id, "cancel_subscription", user_id,
             f"Cancelled active subscription | Plan: {sub['plan_name']} | Notes: {notes}")
        )
        db.commit()

    logger.info(f"🚫 Subscription cancelled for user {user_id} by {admin_id}")
    return jsonify({"message": "✅ تم إلغاء الاشتراك"})

@sub_bp.route("/receipts/<filename>")
def serve_receipt(filename):
    """عرض صورة الوصل للأدمن."""
    return send_from_directory(UPLOAD_DIR, filename)

print("✅ subscription_engine.py CREATED")



