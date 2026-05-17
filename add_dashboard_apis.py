"""Add missing dashboard API endpoints to app.py."""
import re

path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

new_routes = '''
# ============================================================
# DASHBOARD API ENDPOINTS (v40 - Missing Routes Fix)
# ============================================================

@app.route("/api/dashboard/courses")
def api_dashboard_courses():
    """Return courses for the dashboard."""
    try:
        import sqlite3
        user_id = request.args.get("user_id", "")
        conn = sqlite3.connect("data/yamen_academy.db")
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM courses WHERE is_active = 1").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows] if rows else [])
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/dashboard/activation-status")
def api_dashboard_activation_status():
    """Return student activation/subscription status."""
    try:
        import sqlite3
        user_id = request.args.get("user_id", "")
        conn = sqlite3.connect("data/yamen_academy.db")
        conn.row_factory = sqlite3.Row

        # Check if student exists
        student_row = None
        if user_id:
            # Try as telegram_id
            try:
                sid = int(user_id)
                student_row = conn.execute(
                    "SELECT * FROM students WHERE telegram_id = ?", (sid,)
                ).fetchone()
            except ValueError:
                pass

        # Check subscription
        sub_row = None
        if student_row:
            sub_row = conn.execute(
                "SELECT * FROM subscriptions WHERE student_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
                (student_row["telegram_id"],)
            ).fetchone()

        conn.close()

        result = {
            "is_active": bool(student_row),
            "placement_done": bool(student_row["placement_done"]) if student_row else False,
            "placement_level": student_row["placement_level"] if student_row else None,
            "has_subscription": bool(sub_row),
            "subscription_status": "active" if sub_row else "inactive"
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/placement/my-result")
def api_placement_my_result():
    """Return placement test result for a student."""
    try:
        import sqlite3
        student_id = request.args.get("student_id", "")
        if not student_id:
            return jsonify({"status": "error", "message": "Missing student_id"}), 400

        conn = sqlite3.connect("data/yamen_academy.db")
        conn.row_factory = sqlite3.Row

        # Get placement result
        try:
            sid = int(student_id)
        except ValueError:
            sid = student_id

        placement = conn.execute(
            "SELECT * FROM placement_results WHERE student_id = ? ORDER BY id DESC LIMIT 1",
            (sid,)
        ).fetchone()

        conn.close()

        if placement:
            return jsonify(dict(placement))
        else:
            return jsonify({"status": "not_found", "message": "No placement result yet"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

'''

# Inject before if __name__
pos = code.find("if __name__")
if pos != -1:
    code = code[:pos] + new_routes + "\n" + code[pos:]
else:
    code += new_routes

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

# Verify
route_count = code.count("@app.route")
print("Total routes in app.py: " + str(route_count))
print("[OK] 3 missing dashboard APIs added:")
print("  GET /api/dashboard/courses")
print("  GET /api/dashboard/activation-status")
print("  GET /api/placement/my-result")
