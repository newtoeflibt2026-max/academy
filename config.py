import os

ADMIN_IDS = [5602495831, 469136626, 5572314718]
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
DATABASE_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yamen_academy.db")
WEBAPP_PORT    = int(os.getenv("PORT", "8080"))
UPLOAD_FOLDER  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
JSON_PLACEMENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "placement_questions.json")
ALLOWED_EXTENSIONS = {"pdf", "mp3", "mp4", "jpg", "jpeg", "png", "gif", "webp", "ogg", "wav", "webm"}
MAX_CONTENT_LENGTH = 150 * 1024 * 1024  # 150 MB

print(f"[CONFIG] ADMIN_IDS={ADMIN_IDS}")
print(f"[CONFIG] DB={DATABASE_PATH}, PORT={WEBAPP_PORT}")
print(f"[CONFIG] PLACEMENT_JSON={JSON_PLACEMENT}")
