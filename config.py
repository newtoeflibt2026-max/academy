# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

# تحميل المتغيرات من ملف .env فوراً عند تشغيل السيرفر
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'yamen_academy_secure_key_2026')
    TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '123456789:ABCdefGhIJK...')
    DATABASE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'academy.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # تحويل نص المعرفات إلى قائمة أرقام صالحة برمجياً
    raw_admins = os.environ.get('ADMIN_IDS', '123456789')
    ADMIN_IDS = [int(uid.strip()) for uid in raw_admins.split(',') if uid.strip().isdigit()]

# المتغيرات الأساسية المطلوبة في ملف main.py لمنع الـ ImportError
WEBHOOK_HOST = os.environ.get('WEBHOOK_HOST', 'https://yamen-academy-webapp.com')
settings = Config()
