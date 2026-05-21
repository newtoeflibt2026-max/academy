# -*- coding: utf-8 -*-
"""
subscription_helpers.py
─────────────────────────────
دوال مساعدة لإدارة الاشتراكات وقفل الدروس اليومي.

الباقات:
  - free          : درس/24 ساعة، 30 يوم سقف، يتطلب مهام أسبوعية
  - monthly_30    : درس/24 ساعة، 30 يوم
  - quarterly_90  : درس/24 ساعة، 90 يوم
  - emergency     : كل الدروس مفتوحة، 30 يوم
"""
import sqlite3
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

DB_PATH = r"C:\Users\nelt2\yamen_academy\academy.db"
DAILY_LOCK_HOURS = 24
ISO_FMT = "%Y-%m-%d %H:%M:%S"


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_dt(value):
    """يحاول تحويل قيمة نصية إلى datetime، يُعيد None إن فشل."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    for fmt in (ISO_FMT, "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.split(".")[0][:19], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", ""))
    except Exception:
        logger.warning(f"_parse_dt: cannot parse {value!r}")
        return None


def get_subscription_limits(sub_type):
    """يجلب صف limits للباقة. يعيد dict أو None."""
    try:
        conn = _db()
        row = conn.execute(
            "SELECT * FROM subscription_limits WHERE subscription_type=?",
            (sub_type,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"get_subscription_limits: {e}")
        return None


def get_subscription_info(telegram_id):
    """
    يجلب معلومات اشتراك الطالب الشاملة.
    يعيد dict فيه:
      sub_type, started_at, duration_days, expires_at, days_left,
      is_expired, last_lesson_at, free_week_number, weekly_task_status
    """
    tid = str(telegram_id)
    try:
        conn = _db()
        row = conn.execute("""
            SELECT subscription_type, subscription_started_at,
                   last_lesson_completed_at, free_week_number,
                   weekly_task_status, weekly_task_submitted_at
            FROM students WHERE telegram_id=?
        """, (tid,)).fetchone()
        conn.close()
    except Exception as e:
        logger.error(f"get_subscription_info: {e}")
        return None

    if not row:
        return None

    info = dict(row)
    sub_type = info.get("subscription_type") or "free"
    info["sub_type"] = sub_type

    limits = get_subscription_limits(sub_type) or {}
    duration = limits.get("duration_days", 30)
    info["duration_days"] = duration
    info["limits"] = limits

    started = _parse_dt(info.get("subscription_started_at"))
    now = datetime.now()

    if started:
        expires = started + timedelta(days=duration)
        info["expires_at"] = expires.strftime(ISO_FMT)
        delta = expires - now
        info["days_left"] = max(0, delta.days)
        info["is_expired"] = delta.total_seconds() <= 0
    else:
        info["expires_at"] = None
        info["days_left"] = duration
        info["is_expired"] = False

    return info


def is_subscription_active(telegram_id):
    """True إن الاشتراك نشط ولم ينتهِ."""
    info = get_subscription_info(telegram_id)
    if not info:
        return False
    return not info.get("is_expired", False)


def activate_subscription(telegram_id, sub_type=None):
    """
    يبدأ الاشتراك الآن (يضبط subscription_started_at = now).
    لو sub_type مُمرَّر، يُغيّر نوع الاشتراك أيضاً.
    """
    tid = str(telegram_id)
    now_str = datetime.now().strftime(ISO_FMT)
    try:
        conn = _db()
        if sub_type:
            conn.execute(
                "UPDATE students SET subscription_type=?, subscription_started_at=? WHERE telegram_id=?",
                (sub_type, now_str, tid)
            )
        else:
            conn.execute(
                "UPDATE students SET subscription_started_at=? WHERE telegram_id=?",
                (now_str, tid)
            )
        conn.commit()
        conn.close()
        logger.info(f"Subscription activated: tid={tid}, type={sub_type}, at={now_str}")
        return True
    except Exception as e:
        logger.error(f"activate_subscription: {e}")
        return False


def seconds_until_next_lesson(telegram_id):
    """
    يعيد عدد الثواني المتبقية حتى يستطيع الطالب فتح الدرس التالي.
    0 إن كان مفتوحاً الآن. -1 إن انتهى الاشتراك.
    """
    info = get_subscription_info(telegram_id)
    if not info:
        return 0

    if info.get("sub_type") == "emergency":
        return 0

    if info.get("is_expired"):
        return -1

    last = _parse_dt(info.get("last_lesson_completed_at"))
    if not last:
        return 0  # لم يُكمل أي درس بعد

    elapsed = datetime.now() - last
    remaining = timedelta(hours=DAILY_LOCK_HOURS) - elapsed
    secs = int(remaining.total_seconds())
    return max(0, secs)


def can_start_new_lesson(telegram_id):
    """
    هل يستطيع الطالب فتح درس جديد الآن؟
    يعيد (allowed: bool, reason: str, wait_seconds: int).

    Reasons:
      - emergency_unlock   : باقة طوارئ، كل شيء مفتوح
      - first_lesson       : أول درس له
      - daily_unlock       : مضى 24+ ساعة على آخر درس
      - daily_lock         : لم تمر 24 ساعة بعد
      - subscription_expired : الاشتراك منتهي
      - no_data            : لم يُعثر على الطالب
    """
    info = get_subscription_info(telegram_id)
    if not info:
        return (False, "no_data", 0)

    if info.get("sub_type") == "emergency":
        return (True, "emergency_unlock", 0)

    if info.get("is_expired"):
        return (False, "subscription_expired", -1)

    last = _parse_dt(info.get("last_lesson_completed_at"))
    if not last:
        return (True, "first_lesson", 0)

    elapsed = datetime.now() - last
    if elapsed >= timedelta(hours=DAILY_LOCK_HOURS):
        return (True, "daily_unlock", 0)

    remaining = timedelta(hours=DAILY_LOCK_HOURS) - elapsed
    return (False, "daily_lock", int(remaining.total_seconds()))


def mark_lesson_completed_now(telegram_id):
    """يسجل الآن كوقت إكمال آخر درس (يبدأ عدّاد الـ 24 ساعة)."""
    tid = str(telegram_id)
    now_str = datetime.now().strftime(ISO_FMT)
    try:
        conn = _db()
        conn.execute(
            "UPDATE students SET last_lesson_completed_at=? WHERE telegram_id=?",
            (now_str, tid)
        )
        conn.commit()
        conn.close()
        logger.debug(f"mark_lesson_completed_now: tid={tid}, at={now_str}")
        return True
    except Exception as e:
        logger.error(f"mark_lesson_completed_now: {e}")
        return False


def format_wait_time_ar(seconds):
    """يُنسق ثوانٍ إلى نص عربي مقروء."""
    if seconds <= 0:
        return "متاح الآن"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours >= 1:
        if minutes >= 1:
            return f"{hours} ساعة و {minutes} دقيقة"
        return f"{hours} ساعة"
    if minutes >= 1:
        return f"{minutes} دقيقة"
    return f"{seconds} ثانية"


def get_lock_message_ar(telegram_id):
    """
    يعيد رسالة عربية مناسبة لشرح لماذا الدرس مقفل (للعرض في البوت).
    إن كان مفتوحاً يعيد None.
    """
    allowed, reason, wait = can_start_new_lesson(telegram_id)
    if allowed:
        return None

    info = get_subscription_info(telegram_id) or {}
    sub_type = info.get("sub_type", "free")

    if reason == "daily_lock":
        wait_str = format_wait_time_ar(wait)
        if sub_type == "free":
            return (
                f"⏰ <b>الدرس التالي مقفل</b>\n\n"
                f"الباقة المجانية تتيح درساً واحداً كل 24 ساعة.\n\n"
                f"🕒 يفتح بعد: <b>{wait_str}</b>\n\n"
                f"💎 للحصول على وصول أسرع، اطّلع على الباقات المدفوعة."
            )
        return (
            f"⏰ <b>الدرس التالي مقفل</b>\n\n"
            f"درس واحد كل 24 ساعة لضمان الاستيعاب الجيد.\n\n"
            f"🕒 يفتح بعد: <b>{wait_str}</b>"
        )

    if reason == "subscription_expired":
        return (
            "🔒 <b>انتهى اشتراكك</b>\n\n"
            "لمتابعة التعلم، يرجى تجديد الاشتراك.\n"
            "تواصل مع الإدارة للاطّلاع على الباقات."
        )

    if reason == "no_data":
        return "❌ لم يتم العثور على حسابك. اضغط /start"

    return None


# ─────────────────────────────────────────────
# اختبارات سريعة عند التشغيل المباشر
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    tid = sys.argv[1] if len(sys.argv) > 1 else "5572314718"
    print(f"=== Testing for telegram_id={tid} ===\n")

    info = get_subscription_info(tid)
    print("get_subscription_info:")
    if info:
        for k, v in info.items():
            if k != "limits":
                print(f"  {k}: {v}")
    print()

    allowed, reason, wait = can_start_new_lesson(tid)
    print(f"can_start_new_lesson: allowed={allowed}, reason={reason}, wait={wait}s")
    print(f"  → {format_wait_time_ar(wait) if wait > 0 else 'now'}")
    print()

    msg = get_lock_message_ar(tid)
    if msg:
        print("Lock message:")
        print(msg)
    else:
        print("✅ Lesson is unlocked (no lock message).")