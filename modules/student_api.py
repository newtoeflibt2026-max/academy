import sys
import sqlite3
import traceback
from flask import Blueprint, jsonify, render_template, session

from config import DATABASE_PATH

# ═══ Blueprint – MUST be named "student_api_bp" (app.py expects this) ═══
student_api_bp = Blueprint("student_api", __name__)


def _get_db():
    """Open a synchronous SQLite connection with Row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _student_from_session():
    """Pull student_id from Flask session safely."""
    sid = session.get("student_id") or session.get("user_id")
    if sid is None:
        return None
    return int(sid)


# ═══════════════════════════════════════════════════════════════
#  GET /dashboard  – render student dashboard layout
# ═══════════════════════════════════════════════════════════════
@student_api_bp.route("/dashboard")
def student_dashboard():
    """Serve the student dashboard page (or config)."""
    try:
        sid = _student_from_session()
        if sid is None:
            return jsonify({"error": "Not logged in"}), 401

        db = _get_db()
        row = db.execute(
            "SELECT student_id, full_name, is_active FROM students WHERE student_id = ?",
            (sid,),
        ).fetchone()
        db.close()

        if row is None:
            return jsonify({"error": "Student not found"}), 404

        return render_template(
            "dashboard.html",
            student=dict(row),
            dashboard_config={
                "show_progress": True,
                "show_lessons": True,
                "show_billing": bool(row["is_active"]),
            },
        )
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500


# ═══════════════════════════════════════════════════════════════
#  GET /api/student/profile  – JSON profile for logged-in student
# ═══════════════════════════════════════════════════════════════
@student_api_bp.route("/api/student/profile")
def student_profile():
    """Return full student profile JSON from session user_id."""
    try:
        sid = _student_from_session()
        if sid is None:
            return jsonify({"error": "Not logged in"}), 401

        db = _get_db()

        # student record
        student = db.execute(
            "SELECT student_id, full_name, is_active, created_at "
            "FROM students WHERE student_id = ?",
            (sid,),
        ).fetchone()

        if student is None:
            db.close()
            return jsonify({"error": "Student not found"}), 404

        # placement result
        placement = db.execute(
            "SELECT band, level, path, score "
            "FROM placement_results "
            "WHERE student_id = ? ORDER BY id DESC LIMIT 1",
            (sid,),
        ).fetchone()

        # subscription info
        sub = db.execute(
            "SELECT days_available, plan_type, expires_at "
            "FROM subscriptions WHERE student_id = ?",
            (sid,),
        ).fetchone()

        db.close()

        profile = {
            "student_id": student["student_id"],
            "full_name": student["full_name"],
            "is_active": bool(student["is_active"]),
            "created_at": str(student["created_at"]) if student["created_at"] else None,
            "placement": dict(placement) if placement else None,
            "subscription": dict(sub) if sub else None,
        }

        return jsonify({"status": "success", "data": profile}), 200

    except Exception:
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Internal server error"}), 500
