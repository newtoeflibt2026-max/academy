# -*- coding: utf-8 -*-
import os

def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

_load_env()

class Settings:
    BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
    GEMINI_KEY   = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_WRITING_KEYS = os.environ.get("GEMINI_WRITING_KEYS", "")
    GEMINI_SPEAKING_KEYS = os.environ.get("GEMINI_SPEAKING_KEYS", "")
    # مسار قاعدة البيانات: يمكن تجاوزه بـ DB_PATH في .env
    try:
        from db import DB_PATH
    except ImportError:
        DB_PATH = os.environ.get("DB_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")
    DATABASE_PATH = DB_PATH  # alias for legacy modules
    WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "http://localhost:8080")
    GROUP_LINK   = os.environ.get("GROUP_LINK", "https://t.me/yamen_academy")
    ADMIN_IDS    = [
        int(x.strip()) for x in os.environ.get("ADMIN_IDS", "5572314718").split(",")
        if x.strip().isdigit()
    ]
    PORT              = int(os.environ.get("PORT", 8080))
    NGROK_AUTHTOKEN   = os.environ.get("NGROK_AUTHTOKEN", "")
    FORCE_SUB_CHANNELS = os.environ.get("FORCE_SUB_CHANNELS", "")

settings = Settings()

# Module-level exports for legacy compatibility
DB_PATH = Settings.DB_PATH
DATABASE_PATH = Settings.DB_PATH
