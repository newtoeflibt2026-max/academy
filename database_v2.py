"""
database_v2.py — bridge import for backward compatibility
All functions delegate to bot_database.py
"""
from bot_database import (
    init_db, get_db,
    create_student, get_student, update_student,
    get_all_students, search_students,
    activate_paid, deactivate_paid,
    get_students_count,
    add_xp, get_skills_progress, update_streak,
    get_setting, set_setting, get_all_settings,
    check_graduation,
    get_daily_missions, add_daily_mission, complete_mission,
    get_grading_rules, grade_essay,
    get_phase_settings, update_phase_settings,
    get_questions, add_question, delete_question,
    get_payments, add_payment, verify_payment,
    get_leaderboard, get_leaderboard_data,
)

__all__ = [
    'init_db','get_db',
    'create_student','get_student','update_student',
    'get_all_students','search_students',
    'activate_paid','deactivate_paid','get_students_count',
    'add_xp','get_skills_progress','update_streak',
    'get_setting','set_setting','get_all_settings',
    'check_graduation',
    'get_daily_missions','add_daily_mission','complete_mission',
    'get_grading_rules','grade_essay',
    'get_phase_settings','update_phase_settings',
    'get_questions','add_question','delete_question',
    'get_payments','add_payment','verify_payment',
    'get_leaderboard','get_leaderboard_data',
]
