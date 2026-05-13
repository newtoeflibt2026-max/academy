# main.py - بوت تيليجرام Yamen Academy (Aiogram 3)
import asyncio
import logging
import sys
import os

# إضافة المسار الجذر للمشروع
sys.path.insert(0, os.path.dirname(__file__))

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from config import BOT_TOKEN, ADMIN_IDS
from database import init_db, get_user, update_user_role

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# إنشاء كائنات البوت
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================== HANDLERS ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """أمر /start - بداية البوت"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "مستخدم"
    await message.answer(
        f"👋 أهلاً بك {first_name} في أكاديمية يامن!\n\n"
        f"📚 معرّفك: `{user_id}`\n\n"
        f"🎓 الأوامر المتاحة:\n"
        f"/start - البداية\n"
        f"/help - المساعدة\n"
        f"/admin - لوحة التحكم (للمسؤولين فقط)\n"
        f"/courses - عرض الدورات",
        parse_mode="Markdown"
    )
    logger.info(f"User {user_id} started the bot.")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """أمر /help"""
    await message.answer(
        "🎓 **أكاديمية يامن - المساعدة**\n\n"
        "📚 منصة تعليمية متكاملة لتعلم اللغات والمهارات.\n\n"
        "👑 للإمبراطورة دانية: استخدمي /admin",
        parse_mode="Markdown"
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """⚡ أمر /admin - مضمون الوصول لـ ADMIN_IDS"""
    user_id = message.from_user.id
    logger.info(f"⚡ /admin command from user {user_id}")

    # ✅ تأكد من أن الإمبراطورة دانية لها صلاحية
    if user_id in ADMIN_IDS:
        # ضمان الصلاحية في قاعدة البيانات أيضاً
        try:
            update_user_role(user_id, "admin")
            logger.info(f"✅ Admin role confirmed for user {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ DB update skipped: {e}")

        await message.answer(
            f"👑 **لوحة تحكم المسؤول**\n\n"
            f"🆔 معرّفك: `{user_id}`\n"
            f"✅ الصلاحية: مدير النظام\n\n"
            f"📊 **الإحصائيات:**\n"
            f"• افتح الرابط التالي في المتصفح للإحصائيات:\n"
            f"`{os.environ.get('API_BASE', 'https://yamen-academy.up.railway.app')}/api/admin/stats`\n\n"
            f"🛠 **الأوامر الإدارية:**\n"
            f"/admin - هذه اللوحة\n"
            f"/add_course - إضافة دورة\n"
            f"/stats - إحصائيات سريعة",
            parse_mode="Markdown"
        )
    else:
        logger.warning(f"⛔ Unauthorized admin attempt from user {user_id}")
        await message.answer("⛔ عذراً، هذا الأمر مخصص للمسؤولين فقط.")

@dp.message(Command("courses"))
async def cmd_courses(message: Message):
    """أمر /courses - عرض الدورات المتاحة"""
    await message.answer(
        "📚 **الدورات المتاحة**\n\n"
        "لرؤية جميع الدورات، تفضل بزيارة:\n"
        f"`{os.environ.get('API_BASE', 'https://yamen-academy.up.railway.app')}/api/courses`",
        parse_mode="Markdown"
    )

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """إحصائيات سريعة للمسؤول"""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ غير مصرح.")
        return
    try:
        from database import get_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM students")
        students = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM courses")
        courses = c.fetchone()[0]
        conn.close()
        await message.answer(
            f"📊 إحصائيات سريعة:\n👥 الطلاب: {students}\n📚 الدورات: {courses}"
        )
    except Exception as e:
        await message.answer(f"⚠️ خطأ: {e}")

# ==================== MAIN ====================

async def main():
    logger.info(f"🚀 Bot starting with ADMIN_IDS: {ADMIN_IDS}")

    # حذف أي webhook قديم وتصفية التحديثات المعلقة
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Webhook deleted, pending updates dropped.")

    # بدء قاعدة البيانات
    try:
        init_db()
        logger.info("✅ Database initialized.")
    except Exception as e:
        logger.error(f"❌ DB init failed: {e}")

    # بدء polling
    logger.info("🔄 Starting polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped.")
    except Exception as e:
        logger.critical(f"💥 Fatal error: {e}")
