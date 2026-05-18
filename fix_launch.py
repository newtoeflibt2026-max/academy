import os
BASE = r"C:\Users\nelt2\yamen_academy"

files = {
"config.py": """# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
    GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")
    DB_PATH      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")
    WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "http://localhost:8080")
    GROUP_LINK   = os.getenv("GROUP_LINK", "https://t.me/yamen_academy")
    ADMIN_IDS    = [5572314718]
    PORT         = int(os.getenv("PORT", 8080))

settings = Settings()
""",

"bot_database.py": """import sqlite3, os
from config import settings

def get_db():
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_bot_db():
    conn = get_db()
    conn.executescript(\"\"\"
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT UNIQUE NOT NULL,
        name TEXT DEFAULT 'طالب',
        target_band REAL DEFAULT 6.5,
        current_band REAL DEFAULT 0,
        path_type TEXT DEFAULT 'academic',
        days_left INTEGER DEFAULT 90,
        xp INTEGER DEFAULT 0,
        streak_days INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 0,
        subscription_type TEXT DEFAULT 'free',
        package_end DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT NOT NULL,
        plan_key TEXT,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ends_at TIMESTAMP,
        is_active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT NOT NULL,
        plan_key TEXT,
        plan_name TEXT,
        amount REAL DEFAULT 0,
        status TEXT DEFAULT 'pending',
        receipt_photo_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    \"\"\")
    conn.commit()
    conn.close()
    print("DB ready")

async def get_student(telegram_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM students WHERE telegram_id=?", (str(telegram_id),)).fetchone()
    conn.close()
    return dict(row) if row else None

async def create_student(telegram_id, name, target_band=6.5, path_type="academic", days_left=90):
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO students (telegram_id,name,target_band,path_type,days_left) VALUES (?,?,?,?,?)",
        (str(telegram_id), name, target_band, path_type, days_left))
    conn.commit()
    row = conn.execute("SELECT * FROM students WHERE telegram_id=?", (str(telegram_id),)).fetchone()
    conn.close()
    return dict(row) if row else None

async def get_subscription(telegram_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM subscriptions WHERE telegram_id=? AND is_active=1 AND ends_at > datetime('now') ORDER BY ends_at DESC LIMIT 1",
        (str(telegram_id),)).fetchone()
    conn.close()
    return dict(row) if row else None

async def create_payment(telegram_id, plan_key, plan_name, amount):
    conn = get_db()
    cur = conn.execute("INSERT INTO payments (telegram_id,plan_key,plan_name,amount) VALUES (?,?,?,?)",
        (str(telegram_id), plan_key, plan_name, amount))
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid

async def update_payment_receipt(payment_id, photo_id):
    conn = get_db()
    conn.execute("UPDATE payments SET receipt_photo_id=? WHERE id=?", (photo_id, payment_id))
    conn.commit()
    conn.close()

async def get_student_payment_status(telegram_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM payments WHERE telegram_id=? AND status='pending' LIMIT 1",
        (str(telegram_id),)).fetchone()
    conn.close()
    return dict(row) if row else None

async def approve_payment(payment_id, plan_key, telegram_id, days=30):
    conn = get_db()
    conn.execute("UPDATE payments SET status='approved' WHERE id=?", (payment_id,))
    conn.execute("INSERT INTO subscriptions (telegram_id,plan_key,ends_at) VALUES (?,?,datetime('now',?))",
        (str(telegram_id), plan_key, f"+{days} days"))
    conn.execute("UPDATE students SET is_active=1, subscription_type='premium' WHERE telegram_id=?",
        (str(telegram_id),))
    conn.commit()
    conn.close()
""",

"utils/__init__.py": "",

"utils/states.py": """from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_name        = State()
    waiting_for_path        = State()
    waiting_for_target_band = State()
    waiting_for_days        = State()
    waiting_for_name_edit   = State()

class PlacementStates(StatesGroup):
    answering = State()

class LessonStates(StatesGroup):
    viewing_content = State()
    doing_exercise  = State()

class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

class CorrectionStates(StatesGroup):
    waiting_for_essay    = State()
    waiting_for_speaking = State()
""",

"utils/ai_corrector.py": """import aiohttp
from config import settings

async def _gemini(prompt):
    key = settings.GEMINI_KEY
    if not key:
        return "مفتاح Gemini غير مضبوط"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload) as r:
            if r.status == 200:
                d = await r.json()
                try:
                    return d["candidates"][0]["content"]["parts"][0]["text"]
                except:
                    return "لم يتم الحصول على رد"
            return f"خطأ {r.status}"

async def correct_writing(text, task_type="Writing Task 2"):
    prompt = f"You are an IELTS examiner. Evaluate this essay in Arabic. Give band scores and tips.\\nTask: {task_type}\\nEssay: {text}"
    return await _gemini(prompt)

async def correct_speaking(transcript, part="Part 1", question=""):
    prompt = f"You are an IELTS examiner. Evaluate this speaking transcript in Arabic. Give band scores and tips.\\nQuestion: {question}\\nPart: {part}\\nTranscript: {transcript}"
    return await _gemini(prompt)
""",

"utils/voice_to_text.py": """import base64, aiohttp
from config import settings

async def voice_to_text(audio_bytes, mime_type="audio/ogg"):
    key = settings.GEMINI_KEY
    if not key:
        return ""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    audio_b64 = base64.b64encode(audio_bytes).decode()
    payload = {"contents": [{"parts": [
        {"inline_data": {"mime_type": mime_type, "data": audio_b64}},
        {"text": "Transcribe this audio to text exactly as spoken. Return only the transcript."}
    ]}]}
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload) as r:
            if r.status == 200:
                d = await r.json()
                try:
                    return d["candidates"][0]["content"]["parts"][0]["text"].strip()
                except:
                    return ""
    return ""
""",

"handlers/__init__.py": "",

"handlers/admin.py": """from aiogram import Router, F
from aiogram.types import CallbackQuery
from config import settings
from bot_database import approve_payment, get_db

router = Router(name="admin")

@router.callback_query(F.data.startswith("adm_approve:"))
async def admin_approve(cb: CallbackQuery):
    if cb.from_user.id not in settings.ADMIN_IDS:
        await cb.answer("غير مصرح", show_alert=True)
        return
    parts = cb.data.split(":")
    payment_id = int(parts[1])
    plan_key   = parts[2]
    user_id    = int(parts[3])
    days       = int(parts[4]) if len(parts) > 4 else 30
    try:
        await approve_payment(payment_id, plan_key, user_id, days)
        await cb.message.edit_caption(cb.message.caption + "\\n\\n✅ تم التفعيل", reply_markup=None)
        await cb.bot.send_message(user_id,
            f"🎉 <b>تم تفعيل اشتراكك!</b>\\nالباقة: <b>{plan_key}</b>\\nالمدة: <b>{days} يوم</b>\\n\\nابدأ دراستك الآن! 📚")
        await cb.answer("✅ تم التفعيل")
    except Exception as e:
        await cb.answer(f"خطأ: {e}", show_alert=True)

@router.callback_query(F.data.startswith("adm_reject:"))
async def admin_reject(cb: CallbackQuery):
    if cb.from_user.id not in settings.ADMIN_IDS:
        await cb.answer("غير مصرح", show_alert=True)
        return
    parts = cb.data.split(":")
    payment_id = int(parts[1])
    user_id    = int(parts[2])
    conn = get_db()
    conn.execute("UPDATE payments SET status='rejected' WHERE id=?", (payment_id,))
    conn.commit()
    conn.close()
    await cb.message.edit_caption(cb.message.caption + "\\n\\n❌ تم الرفض", reply_markup=None)
    await cb.bot.send_message(user_id, "❌ <b>تم رفض طلب الدفع.</b>\\n\\nللاستفسار تواصل معنا.")
    await cb.answer("تم الرفض")
""",

"main.py": """# -*- coding: utf-8 -*-
import asyncio, logging, importlib
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from bot_database import init_bot_db
from handlers.start import router as start_router
from handlers.subscriptions import router as sub_router
from handlers.admin import router as admin_router

def try_router(mod_name):
    try:
        mod = importlib.import_module(mod_name)
        r = getattr(mod, "router", None)
        if r:
            print(f"  + {mod_name}")
        return r
    except Exception as e:
        print(f"  - {mod_name}: {e}")
        return None

async def main():
    init_bot_db()
    bot = Bot(token=settings.BOT_TOKEN,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start_router)
    dp.include_router(sub_router)
    dp.include_router(admin_router)

    print("تحميل الـ handlers الاختيارية:")
    for mod in ["handlers.listening","handlers.lessons",
                "handlers.placement_test","handlers.writing",
                "handlers.speaking","handlers.correction"]:
        r = try_router(mod)
        if r:
            dp.include_router(r)

    await bot.delete_webhook(drop_pending_updates=True)
    print("=" * 40)
    print("البوت يعمل الآن!")
    print(f"DB: {settings.DB_PATH}")
    print("=" * 40)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
"""
}

for filename, content in files.items():
    path = os.path.join(BASE, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK: {filename}")

print("\nالان شغل: python main.py")
