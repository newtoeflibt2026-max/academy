"""
subscription_helpers.py — Wave 6 (Sections-based Packages)
─────────────────────────────────────────────────────────────
دوال مركزية لفحص صلاحية وصول الطالب لكل قسم.

الأقسام (section codes):
  reading | listening | writing | speaking | foundation | mock | full | free

الباقة "full" تفتح كل شيء.
الباقة "free" تفتح القراءة (أو التأسيس إذا placement_score < 60) — درس/يوم لمدة 15 يوم.
"""
import sqlite3
import os
import datetime
from functools import wraps
from flask import request, jsonify, render_template, redirect, url_for

DB_PATH = os.environ.get("DB_PATH", "academy.db")

# ════════════════════════════════════════════════
# Section access matrix
# ════════════════════════════════════════════════
SECTION_MAP = {
    "reading":    ["reading", "full"],
    "listening":  ["listening", "full"],
    "writing":    ["writing", "full"],
    "speaking":   ["speaking", "full"],
    "foundation": ["foundation", "full"],
    "mock":       ["mock", "full"],
}

# Free plan special: reading OR foundation depending on placement
def _free_allows(section, placement_score):
    """الباقة المجانية تفتح القراءة فقط، أو التأسيس إذا placement < 60"""
    if placement_score is None or placement_score < 60:
        return section == "foundation"
    return section == "reading"


# ════════════════════════════════════════════════
# Core: get student subscription info
# ════════════════════════════════════════════════
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def get_student(user_id):
    """جلب بيانات الطالب الأساسية"""
    if not user_id:
        return None
    try:
        con = _conn()
        row = con.execute(
            "SELECT * FROM students WHERE user_id=? OR telegram_id=?",
            (str(user_id), str(user_id))
        ).fetchone()
        con.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"[subs] get_student error: {e}")
        return None


def get_active_subscription(user_id):
    """
    إرجاع dict بالاشتراك الفعّال للطالب أو None.
    يفحص: is_paid, package_end, subscription_type/subscription_section.
    """
    st = get_student(user_id)
    if not st:
        return None

    section = (st.get("subscription_section") or "").strip()
    is_paid = st.get("is_paid") or 0
    pkg_end = st.get("package_end")
    sub_type = (st.get("subscription_type") or "").strip()

    # تحقق من انتهاء المدة
    if pkg_end:
        try:
            end_dt = datetime.datetime.fromisoformat(str(pkg_end).replace("Z", ""))
            if end_dt < datetime.datetime.now():
                return None  # منتهية
        except Exception:
            pass  # تنسيق غريب → نسمح

    # الباقة المجانية مفعّلة فقط إذا approved + ضمن 15 يوم
    if section == "free" or sub_type == "free":
        promo_status = (st.get("promo_task_status") or "").strip()
        if promo_status != "approved":
            return None
        # 15 يوم من signup_date أو subscription_started_at
        start = st.get("subscription_started_at") or st.get("signup_date")
        if start:
            try:
                start_dt = datetime.datetime.fromisoformat(str(start).replace("Z", ""))
                if (datetime.datetime.now() - start_dt).days >= 15:
                    return None
            except Exception:
                pass
        return {"section": "free", "writing_q": 0, "speaking_q": 0, "is_free": True}

    if not is_paid:
        return None

    return {
        "section": section or sub_type,
        "writing_q": st.get("writing_review_remaining") or 0,
        "speaking_q": st.get("speaking_review_remaining") or 0,
        "is_free": False,
        "package_end": pkg_end,
    }


def has_access(user_id, section):
    """
    فحص رئيسي: هل يستطيع الطالب الوصول لقسم معيّن؟
    section ∈ {reading, listening, writing, speaking, foundation, mock}
    """
    # الأدمن دائماً مسموح
    admin_ids = (os.environ.get("ADMIN_IDS") or "").split(",")
    if str(user_id) in [a.strip() for a in admin_ids if a.strip()]:
        return True

    sub = get_active_subscription(user_id)
    if not sub:
        return False

    # الباقة الشاملة (full) تفتح كل شيء
    if sub["section"] == "full":
        return True

    # الباقة المجانية: قراءة أو تأسيس حسب placement
    if sub.get("is_free"):
        st = get_student(user_id)
        return _free_allows(section, st.get("placement_score") if st else None)

    # الباقات النوعية — تدعم عدة أقسام مفصولة بفاصلة (مثل: writing,reading)
    allowed_sections = SECTION_MAP.get(section, [])
    student_sections = [x.strip() for x in str(sub["section"]).split(",") if x.strip()]
    if "full" in student_sections:
        return True
    return any(ss in allowed_sections for ss in student_sections)


# Backward compatibility
def has_active_subscription(user_id):
    """قديم — يبقى للتوافق"""
    return get_active_subscription(user_id) is not None


# ════════════════════════════════════════════════
# Pass-score calculator (target-based, dynamic)
# ════════════════════════════════════════════════
def get_pass_score(user_id, section):
    """
    علامة النجاح المطلوبة للطالب في كل قسم (TOEFL iBT - من 30).

    الأهداف المعتمدة (الأردن):
      target=59 → 18/30 لكل قسم
      target=69 → 22/30 لكل قسم
      target=90 → 28/30 لكل قسم

    التأسيس: ثابت 80/100 (نسبة إتقان).

    أي target آخر → يُقرّب لأقرب هدف معتمد.

    يرجع dict: {pass_score, max_score, target_total, note}
    """
    # جدول العلامات المعتمد
    PASS_TABLE = {
        59: 18,
        69: 22,
        90: 28,
    }

    st = get_student(user_id)
    target = 59  # default آمن
    if st:
        try:
            target = int(st.get("target_score") or st.get("target_band") or 59)
        except (ValueError, TypeError):
            target = 59

    # التأسيس: ثابت
    if section == "foundation":
        return {"pass_score": 80, "max_score": 100, "target_total": target,
                "note": "إتقان التأسيس ثابت 80%"}

    # ابحث عن الـ target في الجدول، وإلا قرّب لأقرب target
    if target in PASS_TABLE:
        pass_score = PASS_TABLE[target]
        note = f"target={target} معتمد → {pass_score}/30"
    else:
        # قرّب لأقرب target معتمد
        closest = min(PASS_TABLE.keys(), key=lambda t: abs(t - target))
        pass_score = PASS_TABLE[closest]
        note = f"target={target} غير معتمد → قُرّب لـ {closest} → {pass_score}/30"

    return {
        "pass_score": pass_score,
        "max_score": 30,
        "target_total": target,
        "note": note
    }


# ════════════════════════════════════════════════
# Quota helpers (writing/speaking human review)
# ════════════════════════════════════════════════
def get_review_quota(user_id, kind):
    """kind = 'writing' | 'speaking' → عدد التصحيحات المتبقية"""
    st = get_student(user_id)
    if not st:
        return 0
    field = "writing_review_remaining" if kind == "writing" else "speaking_review_remaining"
    return int(st.get(field) or 0)


def consume_review_quota(user_id, kind):
    """ينقص واحد من رصيد التصحيح. يرجع True إذا نجح، False إذا فارغ."""
    remaining = get_review_quota(user_id, kind)
    if remaining <= 0:
        return False
    field = "writing_review_remaining" if kind == "writing" else "speaking_review_remaining"
    try:
        con = _conn()
        con.execute(f"UPDATE students SET {field}=? WHERE user_id=? OR telegram_id=?",
                    (remaining - 1, str(user_id), str(user_id)))
        con.commit()
        con.close()
        return True
    except Exception as e:
        print(f"[subs] consume_review_quota error: {e}")
        return False


# ════════════════════════════════════════════════
# Decorator for routes
# ════════════════════════════════════════════════
def require_section_access(section):
    """
    Decorator يحمي Flask route. الاستخدام:
        @app.route("/reading")
        @require_section_access("reading")
        def reading_index(): ...

    يستخرج user_id من query/form/json تلقائياً.
    """
    def deco(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # استخراج user_id
            user_id = (request.args.get("user_id")
                       or request.args.get("student_id")
                       or request.form.get("user_id")
                       or request.form.get("student_id")
                       or (request.get_json(silent=True) or {}).get("user_id")
                       or (request.get_json(silent=True) or {}).get("student_id"))

            if not user_id:
                # حاول من kwargs (المسارات التي تحتوي على <user_id>)
                user_id = kwargs.get("user_id") or kwargs.get("student_id")

            if not user_id:
                user_id = (request.cookies.get("user_id")
                           or request.headers.get("X-User-Id"))
                if user_id == "guest":
                    user_id = None

            if not user_id:
                return render_locked_page(section, reason="no_user")

            if not has_access(user_id, section):
                return render_locked_page(section, reason="no_access", user_id=user_id)

            return f(*args, **kwargs)
        return wrapped
    return deco


def render_locked_page(section, reason="no_access", user_id=None):
    """صفحة مغلقة جميلة مع زر للاشتراك"""
    section_names = {
        "reading":    "القراءة 📖",
        "listening":  "الاستماع 🎧",
        "writing":    "الكتابة ✍️",
        "speaking":   "المحادثة 🗣️",
        "foundation": "التأسيس 🏗️",
        "mock":       "الامتحانات التجريبية 📝",
    }
    section_ar = section_names.get(section, section)

    try:
        return render_template(
            "subscription_required.html",
            section=section,
            section_ar=section_ar,
            reason=reason,
            user_id=user_id or ""
        ), 403
    except Exception:
        # fallback HTML
        return f"""
        <!doctype html><html dir="rtl"><head><meta charset="utf-8">
        <title>اشتراك مطلوب</title>
        <style>
            body{{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);
                  color:#fff;text-align:center;padding:60px 20px;min-height:100vh;margin:0}}
            .card{{background:rgba(255,255,255,0.12);backdrop-filter:blur(10px);
                   max-width:480px;margin:0 auto;padding:40px;border-radius:24px}}
            h1{{font-size:28px;margin:0 0 16px}}
            p{{font-size:17px;line-height:1.7;opacity:0.95}}
            a.btn{{display:inline-block;background:#f59e0b;color:#fff;padding:14px 32px;
                   border-radius:14px;text-decoration:none;font-weight:bold;margin-top:20px;
                   font-size:16px}}
        </style></head><body>
        <div class="card">
        <div style="font-size:72px;margin-bottom:12px">🔒</div>
        <h1>قسم {section_ar} مغلق</h1>
        <p>هذا القسم متاح للمشتركين فقط.<br>اختر الباقة المناسبة لك من البوت لتفعيله.</p>
        <a class="btn" href="https://t.me/YamenAcademyBot">العودة للبوت لاختيار باقة</a>
        </div>
        </body></html>
        """, 403


# ════════════════════════════════════════════════
# Activation helpers (يستخدمها payments.py)
# ════════════════════════════════════════════════
def activate_subscription(user_id, plan_name):
    """
    تفعيل باقة لطالب. يحدّث:
      is_paid, subscription_type, subscription_section, package_end,
      writing_review_remaining, speaking_review_remaining, subscription_started_at
    """
    try:
        con = _conn()
        plan = con.execute(
            "SELECT * FROM subscription_plans WHERE name=? AND is_active=1",
            (plan_name,)
        ).fetchone()
        if not plan:
            con.close()
            return False, "الباقة غير موجودة"

        plan = dict(plan)
        now = datetime.datetime.now()
        end = now + datetime.timedelta(days=int(plan["duration_days"]))

        con.execute("""
            UPDATE students
            SET is_paid=?, subscription_type=?, subscription_section=?,
                package_end=?, subscription_started_at=?,
                writing_review_remaining=?, speaking_review_remaining=?
            WHERE user_id=? OR telegram_id=?
        """, (
            0 if plan["section_code"] == "free" else 1,
            plan["name"],
            plan["section_code"],
            end.isoformat(timespec="seconds"),
            now.isoformat(timespec="seconds"),
            int(plan.get("writing_review_quota") or 0),
            int(plan.get("speaking_review_quota") or 0),
            str(user_id), str(user_id)
        ))
        con.commit()
        con.close()
        return True, plan
    except Exception as e:
        print(f"[subs] activate_subscription error: {e}")
        return False, str(e)


# ════════════════════════════════════════════════
# Diagnostics
# ════════════════════════════════════════════════
def debug_access(user_id):
    """طباعة تشخيصية"""
    st = get_student(user_id)
    sub = get_active_subscription(user_id)
    print(f"=== Access debug for {user_id} ===")
    print(f"  student exists: {bool(st)}")
    if st:
        print(f"  is_paid={st.get('is_paid')} section={st.get('subscription_section')}")
        print(f"  package_end={st.get('package_end')} placement={st.get('placement_score')}")
    print(f"  active subscription: {sub}")
    for sec in ["reading","listening","writing","speaking","foundation","mock"]:
        print(f"  has_access({sec}): {has_access(user_id, sec)}")
