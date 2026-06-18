# -*- coding: utf-8 -*-
"""صفحة إنجازات الطالب - شريط تقدّم لكل قسم. Data-driven وقابل للتوسّع."""
import os, sqlite3
from flask import Blueprint, render_template, request

achievements_bp = Blueprint("achievements", __name__)
DB_PATH = os.environ.get("DB_PATH", "academy.db")

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _scalar(conn, sql, params=()):
    try:
        r = conn.execute(sql, params).fetchone()
        return (r[0] if r and r[0] is not None else 0)
    except Exception:
        return 0

# ====== تعريف الأقسام (لإضافة قسم جديد: أضف سطرًا واحدًا هنا) ======
# done_fn(conn, uid) -> عدد المُنجَز ، total ثابت أو دالة ، enabled: متاح الآن؟

def _allowed_sections(conn, uid):
    """يُرجع set بأكواد الأقسام المسموحة حسب اشتراكات الطالب النشطة."""
    allowed=set()
    try:
        rows=conn.execute(
            "SELECT plan_name FROM subscriptions WHERE (user_id=? OR telegram_id=?) AND is_active=1",
            (uid, str(uid))
        ).fetchall()
        for r in rows:
            pn=(r[0] or '').lower()
            if 'full' in pn or 'premium' in pn or 'foundation_full' in pn:
                return {'foundation','writing','reading','listening','speaking','mock','full'}
            for code in ('foundation','writing','reading','listening','speaking','mock','free'):
                if code in pn:
                    allowed.add(code)
    except Exception as e:
        print('[achievements] allowed err', e)
    return allowed

def _sections(conn, uid):
    return [
        {
            "key": "foundation", "name": "التأسيس", "icon": "🏗️", "color": "#06b6d4",
            "url": f"/foundation?user_id={uid}",
            "done": _scalar(conn, "SELECT COUNT(DISTINCT exercise_id) FROM sentence_building_progress WHERE user_id=? AND is_correct=1", (str(uid),)),
            "total": _scalar(conn, "SELECT COUNT(*) FROM sentence_building_exercises WHERE is_active=1"),
            "enabled": True,
        },
        {
            "key": "writing", "name": "الكتابة", "icon": "✍️", "color": "#3b82f6",
            "url": f"/writing?user_id={uid}",
            "done": _scalar(conn, "SELECT COUNT(*) FROM writing_progress WHERE telegram_id=? AND status='completed'", (uid,)),
            "total": _scalar(conn, "SELECT COUNT(*) FROM writing_lessons WHERE is_exam=0"),
            "enabled": True,
        },
        {
            "key": "reading", "name": "القراءة", "icon": "📖", "color": "#10b981",
            "url": f"/reading/?user_id={uid}",
            "done": _scalar(conn, "SELECT COUNT(DISTINCT content_id) FROM reading_attempts WHERE student_id=? AND status='completed'", (uid,)),
            "total": _scalar(conn, "SELECT COUNT(*) FROM mini_lessons WHERE is_active=1 AND section='reading'"),
            "enabled": True,
        },
        {
            "key": "listening", "name": "الاستماع", "icon": "🎧", "color": "#8b5cf6",
            "url": f"/listening?user_id={uid}",
            "done": _scalar(conn, "SELECT COUNT(*) FROM listening_progress WHERE telegram_id=? AND status='completed'", (uid,)),
            "total": _scalar(conn, "SELECT COUNT(*) FROM listening_lessons WHERE is_active=1"),
            "enabled": True,
        },
        {
            "key": "speaking", "name": "المحادثة", "icon": "🎤", "color": "#f59e0b",
            "url": f"/speaking?user_id={uid}",
            "done": _scalar(conn, "SELECT COUNT(*) FROM speaking_v2_progress WHERE user_id=? AND status='completed'", (str(uid),)),
            "total": _scalar(conn, "SELECT COUNT(*) FROM speaking_v2_lessons WHERE is_active=1"),
            "enabled": True,
        },
        {
            "key": "mock", "name": "الامتحان التجريبي", "icon": "📝", "color": "#dc2626",
            "url": f"/mock-exam?user_id={uid}",
            "done": _scalar(conn, "SELECT COUNT(*) FROM stage_exam_attempts WHERE telegram_id=? AND passed=1", (uid,)),
            "total": _scalar(conn, "SELECT COUNT(DISTINCT stage_id) FROM writing_lessons WHERE is_exam=1"),
            "enabled": False,  # غيّرها إلى True عند جاهزية المحتوى
        },
    ]

@achievements_bp.route("/achievements")
@achievements_bp.route("/my-achievements")
def achievements():
    uid = request.args.get("user_id") or request.args.get("student_id") or ""
    conn = _db()
    secs = _sections(conn, uid)
    secs = sorted(secs, key=lambda x: ['foundation', 'reading', 'listening', 'speaking', 'writing', 'mock'].index(x["key"]) if x["key"] in ['foundation', 'reading', 'listening', 'speaking', 'writing', 'mock'] else 99)
    allowed = _allowed_sections(conn, uid)
    conn.close()
    # اعرض فقط الأقسام التي يملك الطالب اشتراكًا فيها
    if allowed:
        secs = [x for x in secs if x['key'] in allowed]
    for s in secs:
        t = s["total"] or 0
        d = min(s["done"], t) if t else s["done"]
        s["done"] = d
        s["remaining"] = max(t - d, 0)
        s["percent"] = round((d / t) * 100) if t else 0
    enabled = [s for s in secs if s["enabled"] and s["total"]]
    tot_done = sum(s["done"] for s in enabled)
    tot_all = sum(s["total"] for s in enabled)
    overall = round((tot_done / tot_all) * 100) if tot_all else 0
    return render_template("achievements.html", sections=secs, overall=overall,
                           tot_done=tot_done, tot_all=tot_all, user_id=uid)
