import os

BASE = r'C:\yamen_academy'

# ============================================================
# 1) config.py
# ============================================================
files = {}
files['config.py'] = r'''
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
DB_PATH = r"C:\yamen_academy\data\academy.db"
ADMIN_IDS = {469136626}
'''

# ============================================================
# 2) main.py
# ============================================================
files['main.py'] = r'''
import asyncio, logging, sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import BOT_TOKEN
from handlers import register_all

async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    register_all(dp)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
'''

# ============================================================
# 3) handlers/start.py — main menu + registration
# ============================================================
files['handlers/start.py'] = r'''
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database import upsert_student, get_student, get_error_bank_count, get_student_level

router = Router()

class RegState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

# ─── /start ───
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    student = get_student(uid)
    if student and student.get("full_name"):
        await show_main_menu(message)
        return
    await state.set_state(RegState.waiting_for_name)
    await message.answer("👋 أهلاً بك في *أكاديمية يامن*!\n\nمن فضلك، أرسل اسمك الكامل:", parse_mode="Markdown")

@router.message(RegState.waiting_for_name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(RegState.waiting_for_phone)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 مشاركة الرقم", request_contact=True)]],
                             resize_keyboard=True, one_time_keyboard=True)
    await message.answer("📱 أرسل رقم هاتفك أو اضغط الزر:", reply_markup=kb)

@router.message(RegState.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    phone = message.contact.phone_number if message.contact else message.text.strip()
    upsert_student(message.from_user.id, data["name"], phone)
    await state.clear()
    await message.answer(f"✅ تم التسجيل! مرحباً {data['name']} 🎉", reply_markup=types.ReplyKeyboardRemove())
    await show_main_menu(message)

# ─── MAIN MENU ───
async def show_main_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 دوراتي", callback_data="my_courses"),
         InlineKeyboardButton(text="📝 امتحان المستوى", callback_data="placement_test")],
        [InlineKeyboardButton(text="✍️ تدريب التهجئة", callback_data="spelling_practice"),
         InlineKeyboardButton(text="🔁 بنك الأخطاء", callback_data="error_bank_review")],
        [InlineKeyboardButton(text="⚡ تحدي 60 ثانية", callback_data="daily_challenge"),
         InlineKeyboardButton(text="💎 اشترك الآن", callback_data="menu_subscribe")],
        [InlineKeyboardButton(text="📊 تقدمي", callback_data="my_progress")],
    ])
    await message.answer("🏠 *القائمة الرئيسية*", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "student_menu")
async def back_to_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 دوراتي", callback_data="my_courses"),
         InlineKeyboardButton(text="📝 امتحان المستوى", callback_data="placement_test")],
        [InlineKeyboardButton(text="✍️ تدريب التهجئة", callback_data="spelling_practice"),
         InlineKeyboardButton(text="🔁 بنك الأخطاء", callback_data="error_bank_review")],
        [InlineKeyboardButton(text="⚡ تحدي 60 ثانية", callback_data="daily_challenge"),
         InlineKeyboardButton(text="💎 اشترك الآن", callback_data="menu_subscribe")],
        [InlineKeyboardButton(text="📊 تقدمي", callback_data="my_progress")],
    ])
    await callback.message.edit_text("🏠 *القائمة الرئيسية*", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()
'''

# ============================================================
# 4) handlers/student.py — progress + leaderboard
# ============================================================
files['handlers/student.py'] = r'''
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_student, get_leaderboard, get_error_bank_count, get_quiz_attempts

router = Router()

@router.callback_query(F.data == "my_progress")
async def my_progress(callback: types.CallbackQuery):
    uid = callback.from_user.id
    student = get_student(uid)
    if not student:
        await callback.answer("سجل أولاً", show_alert=True); return
    err_count = get_error_bank_count(uid)
    attempts = get_quiz_attempts(uid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="student_menu")],
    ])
    await callback.message.edit_text(
        f"📊 *تقدم {student.get('full_name','الطالب')}*\n\n"
        f"🎯 المستوى: *{student.get('level','?')}*\n"
        f"⭐ XP: *{student.get('xp',0)}*\n"
        f"📝 أخطاء في البنك: *{err_count}*\n"
        f"🧪 اختبارات مكتملة: *{len(attempts)}*\n\n"
        f"🏆 *أفضل 5 طلاب:*\n" +
        "\n".join([f"{i+1}. {r['full_name']} — {r['xp']}XP"
                   for i,r in enumerate(get_leaderboard(5))]),
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()
'''

# ============================================================
# 5) handlers/subscriptions.py — plans + receipt photo
# ============================================================
files['handlers/subscriptions.py'] = r'''
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import add_payment

router = Router()

PLANS = [
    ("🥉 شهر واحد", "1month", 10, 30),
    ("🥈 3 شهور", "3months", 25, 90),
    ("🥇 سنة كاملة", "yearly", 80, 365),
]

@router.callback_query(F.data == "menu_subscribe")
async def menu_subscribe(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{name} — {price}\$", callback_data=f"plan_{key}")]
        for name, key, price, days in PLANS
    ] + [[InlineKeyboardButton(text="🔙 رجوع", callback_data="student_menu")]])
    await callback.message.edit_text("💎 *خطط الاشتراك*\nاختر خطتك:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("plan_"))
async def show_plan(callback: types.CallbackQuery):
    key = callback.data.split("_")[1]
    plan = next((p for p in PLANS if p[1] == key), None)
    if not plan:
        await callback.answer("❌ خطة غير موجودة", show_alert=True); return
    name, _, price, days = plan
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 إرسال إيصال الدفع", callback_data=f"pay_{key}")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="menu_subscribe")],
    ])
    await callback.message.edit_text(
        f"*{name}* — {price}\$ لمدة {days} يوم\n\n"
        "للاشتراك:\n1️⃣ حوّل المبلغ\n2️⃣ أرسل صورة الإيصال هنا",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pay_"))
async def request_receipt(callback: types.CallbackQuery):
    key = callback.data.split("_")[1]
    plan = next((p for p in PLANS if p[1] == key), None)
    await callback.message.edit_text(
        f"📸 أرسل صورة إيصال الدفع الآن\nالخطة: *{plan[0]}* — {plan[2]}\$",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(F.photo)
async def handle_receipt_photo(message: types.Message):
    file_id = message.photo[-1].file_id
    add_payment(message.from_user.id, 'subscription', 0, file_id)
    await message.answer("✅ تم استلام الإيصال! سيراجعه الأدمن قريباً.")
'''

# ============================================================
# 6) handlers/daily_challenge.py — 60-sec challenge
# ============================================================
files['handlers/daily_challenge.py'] = r'''
from aiogram import Router, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_today_challenge, add_xp
import asyncio

router = Router()

class ChallengeState(StatesGroup):
    waiting = State()

@router.callback_query(F.data == "daily_challenge")
async def daily_challenge(callback: types.CallbackQuery, state: FSMContext):
    challenge = get_today_challenge()
    if not challenge:
        await callback.message.edit_text("📭 لا يوجد تحدي اليوم. عد غداً!")
        await callback.answer(); return
    uid = callback.from_user.id
    xp = challenge['xp_reward']
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏱️ ابدأ التحدي!", callback_data="start_challenge")],
    ])
    await callback.message.edit_text(
        f"⚡ *تحدي اليوم*\n\n{challenge['question']}\n\n"
        f"🏆 المكافأة: *+{xp} XP*\nالوقت: 60 ثانية",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "start_challenge")
async def start_challenge(callback: types.CallbackQuery, state: FSMContext):
    challenge = get_today_challenge()
    if not challenge:
        await callback.answer("لا يوجد تحدي"); return
    await state.update_data(answer=challenge['answer'], xp=challenge['xp_reward'], cid=challenge['id'], start=True)
    await state.set_state(ChallengeState.waiting)
    await callback.message.edit_text(
        "⏱️ *60 ثانية!*\nاكتب إجابتك الآن:\n\n"
        "/cancel للإلغاء",
        parse_mode="Markdown"
    )
    await callback.answer()
    # Timer: auto-cancel after 60s
    await asyncio.sleep(60)
    current = await state.get_state()
    if current == "ChallengeState:waiting":
        await state.clear()
        try:
            await callback.message.edit_text("⏰ انتهى الوقت! حاول غداً.")
        except Exception:
            pass

@router.message(ChallengeState.waiting)
async def handle_challenge(message: types.Message, state: FSMContext):
    if message.text and message.text.strip() == '/cancel':
        await state.clear()
        await message.answer("🚫 ألغي التحدي.")
        return
    data = await state.get_data()
    await state.clear()
    correct = data['answer'].lower().strip()
    user_ans = message.text.strip().lower() if message.text else ''
    if user_ans == correct:
        add_xp(message.from_user.id, data['xp'], 'daily_challenge')
        await message.answer(f"✅ إجابة صحيحة! +{data['xp']} XP 🏆")
    else:
        await message.answer(f"❌ خطأ! الإجابة الصحيحة: *{data['answer']}*", parse_mode="Markdown")
'''

# ============================================================
# 7) handlers/speaking.py — voice note evaluation (Gemini placeholder)
# ============================================================
files['handlers/speaking.py'] = r'''
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import add_xp, get_lesson

router = Router()

@router.callback_query(F.data.startswith("speaking_"))
async def speaking_prompt(callback: types.CallbackQuery):
    lesson_id = int(callback.data.split("_")[1])
    les = get_lesson(lesson_id)
    prompt = les['content'][:200] if les else "تحدث عن نفسك"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 دوراتي", callback_data="my_courses")],
    ])
    await callback.message.edit_text(
        f"🎤 *تحدث*\n\nالموضوع:\n_{prompt}_\n\n"
        "أرسل رسالة صوتية (Voice Note) وسيتم تقييم نطقك.",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.message(F.voice)
async def handle_voice(message: types.Message):
    await message.answer(
        "🎤 تم استلام التسجيل الصوتي!\n"
        "⚙️ جارٍ تحليل النطق...\n\n"
        "*(ميزة تقييم النطق قيد التطوير)*"
    )
'''

# ============================================================
# 8) handlers/writing.py — text correction
# ============================================================
files['handlers/writing.py'] = r'''
from aiogram import Router, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import add_xp, get_lesson, add_to_error_bank

router = Router()

class WriteState(StatesGroup):
    waiting = State()

@router.callback_query(F.data.startswith("writing_"))
async def writing_prompt(callback: types.CallbackQuery, state: FSMContext):
    lesson_id = int(callback.data.split("_")[1])
    les = get_lesson(lesson_id)
    prompt = les['content'][:300] if les else "اكتب فقرة عن نفسك"
    await state.update_data(lesson_id=lesson_id)
    await state.set_state(WriteState.waiting)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 دوراتي", callback_data="my_courses")],
    ])
    await callback.message.edit_text(
        f"✍️ *تصحيح الكتابة*\n\nالموضوع:\n_{prompt}_\n\n"
        "أرسل النص الذي تريد تصحيحه:",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.message(WriteState.waiting)
async def handle_writing(message: types.Message, state: FSMContext):
    text = message.text
    if not text or len(text) < 5:
        await message.answer("⚠️ النص قصير جداً. أرسل جملة كاملة.")
        return
    await state.clear()
    # Simple feedback (Gemini integration placeholder)
    word_count = len(text.split())
    errors_found = max(0, word_count // 10)
    xp = max(5, word_count * 2)
    add_xp(message.from_user.id, xp, 'writing_correction')
    await message.answer(
        f"✍️ *نتيجة التصحيح*\n\n"
        f"📝 عدد الكلمات: *{word_count}*\n"
        f"🔍 أخطاء محتملة: *~{errors_found}*\n"
        f"⭐ XP: +{xp}\n\n"
        f"*نصيحتي:* راجع الكلمات المميزة.\n"
        f"_(التصحيح المتقدم بالذكاء الاصطناعي قيد التطوير)_",
        parse_mode="Markdown"
    )
'''

# ============================================================
# WRITE ALL
# ============================================================
for rel_path, content in files.items():
    full_path = os.path.join(BASE, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')
    print(f'✅ Written: {rel_path}')

print('\n========== ALL 8 FILES BUILT ==========')
print('Now:')
print('  1) Edit config.py  → add your BOT_TOKEN')
print('  2) cd C:\\yamen_academy && python database.py')
print('  3) python main.py')
