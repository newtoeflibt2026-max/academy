import sys
from flask import Blueprint, jsonify, session
from config import ADMIN_IDS

dashboard_fix_bp = Blueprint("dashboard_fix", __name__)

@dashboard_fix_bp.route("/api/admin/test_mock", methods=["GET"])
def test_mock_data():
    """Provides validated mock data structure for diagnostic runs."""
    try:
        mock_data = {
            "status": "success",
            "course_name": "\U0001f4d6 Reading - TOEFL 2026",
            "version": "v40"
        }
        return jsonify(mock_data), 200
    except Exception as e:
        print(f"Error within mock diagnostic setup: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error", "message": "Internal setup error"}), 500
