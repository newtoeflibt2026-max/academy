flask==3.1.0
flask-cors==5.0.1
aiogram==3.17.0
aiohttp==3.11.0
gunicorn==23.0.0
{
  "build": {
    "builder": "RAILPACK",
    "buildCommand": "pip install --upgrade pip && pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "gunicorn api_server:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --worker-class sync & python main.py",
    "healthcheckPath": "/api/health",
    "restartPolicyType": "ALWAYS",
    "restartPolicyMaxRetries": 10
  }
}
"""
Yamen Academy - Unified Entry Point
Runs Flask API + Telegram Bot together on Railway
"""
import os
import sys
import threading
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("yamen_academy")

# ── Ensure data directory exists ──
os.makedirs("data", exist_ok=True)

# ── Flask API thread ──
def run_flask():
    from api_server import app
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Flask API starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ── Telegram Bot async ──
async def run_bot():
    from config import BOT_TOKEN
    from aiogram import Bot, Dispatcher
    from aiogram.enums import ParseMode
    from handlers import register_all

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    register_all(dp)

    logger.info("🤖 Telegram Bot starting...")
    await dp.start_polling(bot)

# ── Main ──
def main():
    # Start Flask in a daemon thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Run bot in the main thread
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
{
  "build": {
    "builder": "RAILPACK",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "python run.py",
    "healthcheckPath": "/api/health",
    "restartPolicyType": "ALWAYS"
  }
}
@app.route('/api/health')
def health():
    return {"status": "ok", "service": "Yamen Academy API"}
// سيتم استبداله تلقائياً بعد النشر برابط Railway
const CONFIG = {
    BOT_TOKEN: "8518957777:AAFgLsnfJTeqPxI57F8RO2-o4SKeyi2Q7qM",
    API_BASE: "https://YOUR-RAILWAY-APP.railway.app",  // سيُستبدل بعد النشر
    ADMIN_IDS: [469136626, 5572314718],
    GROUP_LINK: "https://t.me/+2NkF901AApcyODk0",
    COLORS: {
        primary: "#3B82F6",
        gold: "#F59E0B",
        bg: "#F8FAFC",
        card: "#FFFFFF",
        text: "#1E293B"
    }
};
