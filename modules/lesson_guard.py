# modules/lesson_guard.py
# GUARD: blocks direct access to lesson URLs unless subscription is active
import sqlite3, os
from functools import wraps
from flask import Blueprint, request, redirect, url_for, abort, jsonify

lesson_guard_bp = Blueprint("lesson_guard", __name__)

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_storage", "yamen.db")

def _get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def subscription_required(f):
    """Decorator: rejects request if user has no active subscription."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = request.cookies.get("yamen_user_id")
        if not user_id:
            # try query string fallback
            user_id = request.args.get("user_id")
        if not user_id:
            # no identity → redirect to subscribe
            if request.path.startswith("/api/"):
                return jsonify({"error": "الاشتراك مطلوب للوصول", "redirect": "/subscribe"}), 403
            return redirect("/subscribe")

        db = _get_db()
        sub = db.execute(
            "SELECT 1 FROM subscriptions WHERE user_id=? AND is_active=1 AND ends_at > datetime('now')",
            (user_id,)
        ).fetchone()
        db.close()

        if not sub:
            if request.path.startswith("/api/"):
                return jsonify({"error": "الاشتراك غير فعال — يرجى الاشتراك", "redirect": "/subscribe"}), 403
            # HTML response: show a friendly block page with "Complete Subscription" button
            return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>الوصول مقيد</title>
<script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
<div class="bg-white rounded-2xl shadow-xl p-10 max-w-md text-center">
  <div class="text-5xl mb-4">🔒</div>
  <h1 class="text-2xl font-bold text-gray-800 mb-2">الوصول مقيد</h1>
  <p class="text-gray-600 mb-6">يجب أن يكون اشتراكك مفعّلاً للوصول إلى هذا الدرس</p>
  <a href="/subscribe" class="inline-block bg-indigo-600 text-white px-8 py-3 rounded-xl font-bold hover:bg-indigo-700 transition">💎 إتمام الاشتراك</a>
  <br><a href="/" class="text-sm text-gray-400 mt-4 inline-block hover:underline">العودة للرئيسية</a>
</div></body></html>"""

        return f(*args, **kwargs)
    return wrapper

# Attach the decorator as a blueprint-wide before_request
@lesson_guard_bp.before_app_request
def protect_lesson_routes():
    """Intercept ALL /lesson/* and /api/reading/view/* requests and check subscription."""
    path = request.path
    protected_patterns = ("/lesson/", "/api/reading/view/", "/api/reading/lesson/", "/api/my-lessons")
    if any(path.startswith(p) for p in protected_patterns):
        return subscription_required(lambda: None)()
    return None

print("✅ lesson_guard.py CREATED — all lesson routes protected")
