import os
ADMIN_IDS = [5602495831, 469136626, 5572314718]
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
API_BASE = os.environ.get("API_BASE", "")
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "data", "academy.db")
