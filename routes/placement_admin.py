import os, sqlite3
from flask import Blueprint, render_template, request, abort

placement_admin_bp = Blueprint("placement_admin", __name__)
DB_PATH = os.environ.get("DB_PATH", "academy.db")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "yamen2026")

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@placement_admin_bp.route("/admin/placement-results")
def placement_results_page():
    if request.args.get("key") != ADMIN_KEY:
        abort(403)
    conn = _db()
    rows = conn.execute("""
        SELECT telegram_id, full_name, name, username, phone,
               placement_score, placement_path, level
        FROM students
        WHERE placement_done=1 OR (placement_score IS NOT NULL AND placement_score>0)
        ORDER BY placement_score DESC
    """).fetchall()
    conn.close()
    students = []
    for r in rows:
        d = dict(r)
        d["display_name"] = d.get("full_name") or d.get("name") or "—"
        students.append(d)
    total = len(students)
    avg = round(sum((s["placement_score"] or 0) for s in students) / total, 1) if total else 0
    return render_template("admin_placement.html", students=students, total=total, avg=avg)
