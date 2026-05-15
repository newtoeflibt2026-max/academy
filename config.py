import os

# ═══ صلاحيات الأدمن ═══
ADMIN_IDS = [
    5602495831,   # 👑 الإمبراطورة دانية — الصلاحية المطلقة
    469136626,    # مشرف احتياطي
    5572314718,   # مشرف احتياطي
]

# ═══ إعدادات البوت ═══
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
API_BASE     = os.environ.get("API_BASE", "https://api.telegram.org")
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yamen_academy.db")

# ═══ إعدادات السيرفر ═══
WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "https://your-app.up.railway.app")
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook")
WEBAPP_HOST  = os.environ.get("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT  = int(os.environ.get("PORT", 8080))

print(f"⚙️  Config loaded | ADMIN_IDS={ADMIN_IDS} | PORT={WEBAPP_PORT}")
