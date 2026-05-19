# -*- coding: utf-8 -*-
"""
init_missing_tables.py
شغّلي هذا الملف مرة واحدة لإضافة الجداول الجديدة للـ DB الموجودة
python init_missing_tables.py
"""
from bot_database import init_bot_db

if __name__ == "__main__":
    print("🔄 جارٍ تحديث قاعدة البيانات...")
    init_bot_db()
    print("✅ تم تحديث قاعدة البيانات بنجاح!")
    print("\n📋 الجداول الجديدة المضافة:")
    print("  • user_skills_progress — تقدم المهارات الأربع")
    print("  • daily_missions       — المهام اليومية")
    print("  • user_missions        — إنجازات الطلاب")
    print("  • essay_grading_rules  — معايير التصحيح")
    print("  • phase_settings       — شروط الانتقال")
    print("  • system_settings      — إعدادات النظام")
    print("\n📋 الأعمدة الجديدة في students:")
    print("  • is_paid           — حالة الدفع (0/1)")
    print("  • tasks_completed   — عدد المهام المنجزة")
    print("  • completed_lessons — عدد الدروس المكتملة")
    print("  • phone             — رقم الهاتف")
