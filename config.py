# config.py - إعدادات الأكاديمية
import os

# ⚡ ADMIN_IDS: أضف كل الآيديهات اللي لها صلاحية الأدمن (الإمبراطورة دانية + أي مشرفين)
ADMIN_IDS = [5602495831, 469136626, 5572314718]

# Telegram Bot Token - يُقرأ من Railway Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# API Base URL
API_BASE = os.environ.get("API_BASE", "")

# إعدادات قاعدة البيانات
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "data", "academy.db")
