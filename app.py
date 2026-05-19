# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template, send_file
import json, os, re
from datetime import datetime
from database import (
    init_db, seed_demo_data, get_db,
    get_student_by_id, get_student_by_telegram,
    get_all_students, get_daily_tasks, toggle_task,
    get_errors, get_leaderboard, get_admin_stats,
    get_all_questions, get_all_payments,
    get_writing_corrections_today, increment_writing_corrections,
    save_writing_submission, save_speaking_submission
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "yamen-secret-2025")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# تهيئة قاعدة البيانات عند بدء التشغيل
with app.app_context():
    init_db()
    seed_demo_data()
# ─── Admin Routes Registration ───────────────────────────────
try:
    from admin_routes import register_admin_routes
    register_admin_routes(app)
    print('✅ Admin routes registered')
except Exception as _e:
    print(f'[WARN] admin_routes: {_e}')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
