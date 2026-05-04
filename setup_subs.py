import os

BASE = r"C:\yamen_academy"
FILES = {}

# ═══ utils/__init__.py ═══
FILES[r"utils\__init__.py"] = ""

# ═══ utils/states.py ═══
FILES[r"utils\states.py"] = """from aiogram.fsm.state import State, StatesGroup

class PaymentStates(StatesGroup):
    waiting_for_receipt = State()
"""

# ═══ تحديث database.py ═══
FILES["database.py"] = '''import sqlite3
from config import settings

def get_conn():
    conn = sqlite3.connect(settings.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            user_id       INTEGER PRIMARY KEY,
            full_name     TEXT    NOT NULL,
            level         TEXT    DEFAULT 'N/A',
            placement_done INTEGER DEFAULT 0,
            is_active     INTEGER DEFAULT 1,
            device_id     TEXT,
            joined_at     TEXT    DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS courses (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT    NOT NULL UNIQUE,
            description   TEXT,
            is_active     INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id     INTEGER NOT NULL,
            title         TEXT    NOT NULL,
            content       TEXT,
            properties    TEXT,
            order_num     INTEGER DEFAULT 0,
            is_active     INTEGER DEFAULT 1,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            plan_key      TEXT    NOT NULL,
            plan_name     TEXT    NOT NULL,
            starts_at     TEXT    DEFAULT (datetime('now','localtime')),
            ends_at       TEXT    NOT NULL,
            is_active     INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES students(user_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS payments (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            plan_key      TEXT    NOT NULL,
            plan_name     TEXT    NOT NULL,
            amount        REAL    NOT NULL,
            receipt_id    TEXT,
            status        TEXT    DEFAULT 'pending',
            created_at    TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES students(user_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS certificates (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            course_id     INTEGER NOT NULL,
            issued_at     TEXT    DEFAULT (datetime('now','localtime')),
            file_path     TEXT,
            FOREIGN KEY (user_id)  REFERENCES students(user_id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS points (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            lesson_id     INTEGER,
            score         REAL    DEFAULT 0,
            earned_at     TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id)   REFERENCES students(user_id) ON DELETE CASCADE,
            FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS affiliates (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL UNIQUE,
            ref_code      TEXT    NOT NULL UNIQUE,
            balance       REAL    DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES students(user_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS errors_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            question      TEXT,
            student_answer TEXT,
            correct_answer TEXT,
            recorded_at   TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES students(user_id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()

def seed_courses():
    conn = get_conn()
    for title, desc in [
        ("IELTS Preparation", "دورة تحضيرية لاختبار IELTS"),
        ("TOEFL Preparation", "دورة تحضيرية لاختبار TOEFL"),
        ("Foundation English", "دورة تأسيسية في اللغة الإنجليزية"),
    ]:
        conn.execute("INSERT OR IGNORE INTO courses (title, description) VALUES (?, ?)", (title, desc))
    conn.commit()
    conn.close()

def upsert_student(user_id: int, full_name: str) -> bool:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO students (user_id, full_name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET full_name = excluded.full_name",
        (user_id, full_name))
    conn.commit()
    is_new = cur.rowcount == 1
    conn.close()
    return is_new

def get_student(user_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM students WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def set_student_level(user_id: int, level: str):
    conn = get_conn()
    conn.execute("UPDATE students SET level = ?, placement_done = 1 WHERE user_id = ?", (level, user_id))
    conn.commit()
    conn.close()

def add_lesson(title: str, content: str, properties: str, course_id: int = 1, order: int = 0):
    conn = get_conn()
    conn.execute("INSERT INTO lessons (course_id, title, content, properties, order_num) VALUES (?,?,?,?,?)",
                 (course_id, title, content, properties, order))
    conn.commit()
    conn.close()

def toggle_status(table: str, item_id: int, status: int):
    conn = get_conn()
    col = "user_id" if table == "students" else "id"
    conn.execute(f'UPDATE "{table}" SET is_active = ? WHERE "{col}" = ?', (status, item_id))
    conn.commit()
    conn.close()

def get_all_students() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM students ORDER BY joined_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_lessons() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM lessons ORDER BY order_num").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ═══ الاشتراكات والدفع ═══

def get_subscription(user_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM subscriptions WHERE user_id = ? AND is_active = 1 AND ends_at > datetime('now','localtime') ORDER BY ends_at DESC LIMIT 1",
        (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_payment(user_id: int, plan_key: str, plan_name: str, amount: float) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO payments (user_id, plan_key, plan_name, amount) VALUES (?,?,?,?)",
        (user_id, plan_key, plan_name, amount))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid

def update_payment_receipt(payment_id: int, receipt_id: str):
    conn = get_conn()
    conn.execute("UPDATE payments SET receipt_id = ? WHERE id = ?", (receipt_id, payment_id))
    conn.commit()
    conn.close()

def approve_payment(payment_id: int, user_id: int, plan_key: str, plan_name: str, days: int):
    conn = get_conn()
    conn.execute("UPDATE payments SET status = 'approved' WHERE id = ?", (payment_id,))
    conn.execute(
        "INSERT INTO subscriptions (user_id, plan_key, plan_name, ends_at) VALUES (?,?,?,datetime('now','localtime','+" + str(days) + " days'))",
        (user_id, plan_key, plan_name))
    conn.commit()
    conn.close()

def reject_payment(payment_id: int):
    conn = get_conn()
    conn.execute("UPDATE payments SET status = 'rejected' WHERE id = ?", (payment_id,))
    conn.commit()
    conn.close()

def get_pending_payment(user_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM payments WHERE user_id = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 1",
        (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_payment_stats() -> dict:
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
    approved = conn.execute("SELECT COUNT(*) FROM payments WHERE status='approved'").fetchone()[0]
    total_amount = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='approved'").fetchone()[0]
    conn.close()
    return {"total": total, "pending": pending, "approved": approved, "total_amount": total_amount}

init_db()
seed_courses()
'''

# ═══ تحديث config.py ═══
FILES["config.py"] = """import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: list[int] = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
    DB_PATH: str = os.getenv("DB_PATH", "ielts_bot.db")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_WRITING_KEYS: list[str] = [k.strip() for k in os.getenv("GEMINI_WRITING_KEYS", "").split(",") if k.strip()]
    GEMINI_SPEAKING_KEYS: list[str] = [k.strip() for k in os.getenv("GEMINI_SPEAKING_KEYS", "").split(",") if k.strip()]
    STORAGE_CHANNEL_ID: int = int(os.getenv("STORAGE_CHANNEL_ID", "0"))
    GROUP_LINK: str = os.getenv("GROUP_LINK", "")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    WALLET_NUMBER: str = os.getenv("WALLET_NUMBER", "0798919150")
    WHATSAPP_SUPPORT: str = os.getenv("WHATSAPP_SUPPORT", "00962798919150")

settings = Settings()
"""

# ═══ handlers/subscriptions.py ═══
FILES[r"handlers\subscriptions.py"] = """from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from config import settings
from database import (
    get_student, create_payment, update_payment_receipt,
    get_subscription, get_pending_payment,
)
from utils.states import PaymentStates
import logging

logger = logging.getLogger(__name__)
router = Router(name="subscriptions")

# ═══ الباقات ═══

PLANS = {
    "flexible": {
        "name": "📘 المسار المرن", "price": 30, "days": 30,
        "desc": "مناسب للمتعلم المنتظم — شهر كامل من التدريب المنظم",
        "features": ["✅ جميع الدروس", "✅ اختبارات تجريبية", "✅ تتبع التقدم"],
    },
    "excellence": {
        "name": "🏆 مسار التفوق", "price": 65, "days": 90,
        "desc": "الأفضل قيمةً — 3 أشهر لرفع درجتك بشكل مضمون",
        "features": ["✅ جميع مميزات المرن", "✅ خطة مخصصة", "✅ أولوية الدعم"],
    },
    "emergency": {
        "name": "⚡ مسار الطوارئ", "price": 45, "days": 30,
        "desc": "امتحانك قريب؟ تدريب مكثف لأقصى استفادة في وقت قصير",
        "features": ["✅ خطة يومية مكثفة", "✅ تركيز على نقاط الضعف", "✅ محاكاة حقيقية"],
    },
    "vip": {
        "name": "👑 VIP دراسة خاصة", "price": 400, "days": 60,
        "desc": "20 ساعة برايفت مع دكتور يامن — دروس خاصة خارج البوت",
        "features": ["✅ 20 ساعة برايفت", "✅ جدول مرن", "✅ متابعة شخصية", "✅ تقارير أسبوعية"],
        "is_vip": True,
    },
    "self_study": {
        "name": "📖 دراسة ذاتية", "price": 15, "days": 120,
        "desc": "كتاب يامن للآيلتس من المكتبات المعتمدة — دراسة على راحتك",
        "features": ["✅ كتاب يامن للآيلتس", "✅ خطة دراسة 4 شهور", "✅ تمارين ذاتية"],
        "is_self_study": True,
    },
}

# ═══ طرق الدفع ═══

PAYMENT_METHODS = {
    "zain": {
        "name": "💚 زين كاش", "number": settings.WALLET_NUMBER,
        "inst": "افتح تطبيق زين كاش → إرسال → أدخل الرقم → أدخل المبلغ → أرسل",
    },
    "click": {
        "name": "🔵 كليك — البنك الإسلامي", "number": settings.WALLET_NUMBER,
        "inst": "افتح تطبيق كليك → تحويل → أدخل الرقم → أدخل المبلغ → حوّل",
    },
    "western_union": {
        "name": "🌍 Western Union — دولي", "number": settings.WHATSAPP_SUPPORT,
        "inst": f"راسلنا واتساب: {settings.WHATSAPP_SUPPORT}",
    },
}

# ═══ لوحات المفاتيح ═══

def build_plans_kb():
    kb = InlineKeyboardBuilder()
    for key, plan in PLANS.items():
        kb.row(InlineKeyboardButton(
            text=f"{plan['name']} — {plan['price']} دينار",
            callback_data=f"sub:plan:{key}"))
    kb.row(InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="menu:main"))
    return kb

def build_methods_kb(plan_key: str):
    kb = InlineKeyboardBuilder()
    for mkey, method in PAYMENT_METHODS.items():
        kb.row(InlineKeyboardButton(
            text=f"{method['name']}",
            callback_data=f"sub:method:{plan_key}:{mkey}"))
    kb.row(InlineKeyboardButton(text="🔙 رجوع للباقات", callback_data="menu:subscribe"))
    return kb

def build_cancel_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="❌ إلغاء", callback_data="sub:cancel"))
    return kb

def build_back_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="menu:main"))
    kb.row(InlineKeyboardButton(text="💎 عرض الباقات", callback_data="menu:subscribe"))
    return kb

# ═══ عرض الباقات ═══

@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    await show_plans_msg(message)

@router.callback_query(F.data == "menu:subscribe")
async def cb_subscribe(callback: CallbackQuery):
    await show_plans_cb(callback)

async def show_plans_msg(message: Message):
    sub = get_subscription(message.from_user.id)
    if sub:
        await message.answer(
            f"✅ <b>لديك اشتراك نشط!</b>\\n\\nالباقة: <b>{sub['plan_name']}</b>\\nينتهي: <b>{sub['ends_at'][:10]}</b>")
        return
    text = "💎 <b>باقات أكاديمية يامن</b>\\n━━━━━━━━━━━━━━━\\n"
    for key, plan in PLANS.items():
        text += f"\\n{plan['name']} — <b>{plan['price']} دينار</b>\\n  {plan['desc']}\\n"
        for f in plan["features"]: text += f"  {f}\\n"
    text += "\\n👇 <b>اختر باقتك:</b>"
    await message.answer(text, reply_markup=build_plans_kb().as_markup())

async def show_plans_cb(callback: CallbackQuery):
    sub = get_subscription(callback.from_user.id)
    if sub:
        await callback.message.edit_text(
            f"✅ <b>لديك اشتراك نشط!</b>\\n\\nالباقة: <b>{sub['plan_name']}</b>\\nينتهي: <b>{sub['ends_at'][:10]}</b>\\n\\nاستمر في دراستك 💪")
        await callback.answer()
        return
    text = "💎 <b>باقات أكاديمية يامن</b>\\n━━━━━━━━━━━━━━━\\n"
    for key, plan in PLANS.items():
        text += f"\\n{plan['name']} — <b>{plan['price']} دينار</b>\\n  {plan['desc']}\\n"
        for f in plan["features"]: text += f"  {f}\\n"
    text += "\\n👇 <b>اختر باقتك:</b>"
    await callback.message.edit_text(text, reply_markup=build_plans_kb().as_markup())
    await callback.answer()

# ═══ اختيار الباقة ═══

@router.callback_query(F.data.startswith("sub:plan:"))
async def select_plan(callback: CallbackQuery):
    plan_key = callback.data.split(":")[2]
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("❌ باقة غير صالحة", show_alert=True)
        return
    text = f"{plan['name']}\\n━━━━━━━━━━━━━━━\\n💰 السعر: <b>{plan['price']} دينار</b>\\n⏳ المدة: <b>{plan['days']} يوم</b>\\n📝 {plan['desc']}\\n\\n<b>المميزات:</b>\\n"
    for f in plan["features"]: text += f"  {f}\\n"
    text += "\\n💳 <b>اختر طريقة الدفع:</b>"
    await callback.message.edit_text(text, reply_markup=build_methods_kb(plan_key).as_markup())
    await callback.answer()

# ═══ اختيار طريقة الدفع ═══

@router.callback_query(F.data.startswith("sub:method:"))
async def select_method(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    plan_key = parts[2]
    method_key = parts[3]
    plan = PLANS.get(plan_key)
    method = PAYMENT_METHODS.get(method_key)
    if not plan or not method:
        await callback.answer("❌ خيار غير صالح", show_alert=True)
        return

    # تحقق من دفع معلق
    existing = get_pending_payment(callback.from_user.id)
    if existing:
        await callback.message.edit_text("⚠️ <b>لديك طلب دفع معلق.</b>\\n\\nانتظر مراجعة الأدمن.", reply_markup=build_back_kb().as_markup())
        await callback.answer()
        return

    payment_id = create_payment(callback.from_user.id, plan_key, plan["name"], float(plan["price"]))
    await state.update_data(payment_id=payment_id, plan_key=plan_key)
    await state.set_state(PaymentStates.waiting_for_receipt)

    text = (
        f"💳 <b>تعليمات الدفع</b>\\n━━━━━━━━━━━━━━━\\n"
        f"الباقة: <b>{plan['name']}</b>\\n"
        f"المبلغ: <b>{plan['price']} دينار</b>\\n"
        f"الدفع عبر: <b>{method['name']}</b>\\n\\n"
        f"📱 <b>الرقم:</b> <code>{method['number']}</code>\\n\\n"
        f"📋 <b>الخطوات:</b>\\n  {method['inst']}\\n\\n"
        f"📸 <b>بعد الدفع — أرسل صورة الوصل هنا</b>\\n\\n"
        f"🔢 رقم الطلب: <code>#{payment_id}</code>"
    )
    await callback.message.edit_text(text, reply_markup=build_cancel_kb().as_markup())
    await callback.answer()
    logger.info(f"Payment #{payment_id} created — user={callback.from_user.id} plan={plan_key}")

# ═══ استقبال صورة الوصل ═══

@router.message(PaymentStates.waiting_for_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    payment_id = data.get("payment_id")
    plan_key = data.get("plan_key")
    if not payment_id:
        await message.answer("❌ انتهت الجلسة. أرسل /subscribe من جديد.")
        await state.clear()
        return

    photo_id = message.photo[-1].file_id
    update_payment_receipt(payment_id, photo_id)
    await state.clear()

    plan = PLANS.get(plan_key, {})
    student = get_student(message.from_user.id)
    student_name = student["full_name"] if student else "غير معروف"

    await message.answer(
        f"✅ <b>تم استلام الوصل!</b>\\n\\nرقم الطلب: <code>#{payment_id}</code>\\n\\n⏳ سيتم التفعيل خلال دقائق.",
        reply_markup=build_back_kb().as_markup())

    # ═══ إشعار الأدمن ═══
    admin_text = (
        f"🔔 <b>طلب دفع جديد</b>\\n━━━━━━━━━━━━━━━\\n"
        f"👤 الطالب: <b>{student_name}</b>\\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\\n"
        f"💎 الباقة: <b>{plan.get('name', plan_key)}</b>\\n"
        f"💰 المبلغ: <b>{plan.get('price', '؟')} دينار</b>\\n"
        f"🔢 رقم الطلب: <code>#{payment_id}</code>"
    )
    admin_kb = InlineKeyboardBuilder()
    admin_kb.row(InlineKeyboardButton(
        text="✅ موافقة",
        callback_data=f"adm:approve:{payment_id}:{message.from_user.id}:{plan_key}:{plan.get('name','')}:{plan.get('days',30)}"))
    admin_kb.row(InlineKeyboardButton(
        text="❌ رفض",
        callback_data=f"adm:reject:{payment_id}:{message.from_user.id}"))
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_photo(admin_id, photo_id, caption=admin_text, reply_markup=admin_kb.as_markup())
        except Exception as e:
            logger.error(f"Admin notify fail: {e}")

@router.message(PaymentStates.waiting_for_receipt)
async def not_photo(message: Message):
    await message.answer("📸 <b>أرسل صورة الوصل من جهازك.</b>", reply_markup=build_cancel_kb().as_markup())

# ═══ إلغاء ═══
@router.callback_query(F.data == "sub:cancel")
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ <b>تم إلغاء الدفع.</b>", reply_markup=build_back_kb().as_markup())
    await callback.answer()

# ═══ القائمة الرئيسية ═══
@router.callback_query(F.data == "menu:main")
async def back_main(callback: CallbackQuery):
    await callback.message.edit_text("🏠 القائمة الرئيسية — اختر ما تريد:")
    await callback.answer()
"""

# ═══ تحديث admin.py — إضافة أزرار الاشتراكات ═══
FILES[r"handlers\admin.py"] = """from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from config import settings
from database import (
    add_lesson, toggle_status, get_all_students, get_all_lessons,
    approve_payment, reject_payment, get_payment_stats,
)
from keyboards.main_kb import admin_panel_kb

router = Router()

class AddLesson(StatesGroup):
    waiting = State()

def is_admin(uid: int) -> bool:
    return uid in settings.ADMIN_IDS

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ عذراً، هذا الأمر للمسؤولين فقط.")
        return
    await message.answer("🎛 لوحة تحكم يامن أكاديمي:", reply_markup=admin_panel_kb().as_markup())

@router.callback_query(F.data == "add_lesson")
async def ask_lesson(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddLesson.waiting)
    await callback.message.answer("📝 أرسل تفاصيل الدرس:\\n`العنوان | المحتوى | الخواص`", parse_mode="Markdown")
    await callback.answer()

@router.message(AddLesson.waiting)
async def save_lesson(message: types.Message, state: FSMContext):
    if "|" not in message.text:
        await message.answer("❌ استخدم الفاصل | بين العنوان والمحتوى والخواص")
        return
    parts = [p.strip() for p in message.text.split("|", 2)]
    if len(parts) == 3:
        add_lesson(*parts)
        await message.answer(f"✅ تم حفظ الدرس: {parts[0]}")
    else:
        await message.answer("❌ الصيغة: العنوان | المحتوى | الخواص")
    await state.clear()

@router.callback_query(F.data == "list_students")
async def list_students(callback: types.CallbackQuery):
    students = get_all_students()
    if not students:
        await callback.answer("لا يوجد طلاب.")
        return
    b = InlineKeyboardBuilder()
    for s in students:
        st = "🟢" if s["is_active"] else "🔴"
        b.row(InlineKeyboardButton(text=f"{st} {s['full_name']} - {s['level']}",
                                   callback_data=f"tog_students_{s['user_id']}_{0 if s['is_active'] else 1}"))
    b.adjust(1)
    await callback.message.edit_text("👥 اضغط لتبديل الحالة:", reply_markup=b.as_markup())
    await callback.answer()

@router.callback_query(F.data == "list_lessons")
async def list_lessons(callback: types.CallbackQuery):
    lessons = get_all_lessons()
    if not lessons:
        await callback.answer("لا توجد دروس.")
        return
    b = InlineKeyboardBuilder()
    for l in lessons:
        st = "🟢" if l["is_active"] else "🔴"
        b.row(InlineKeyboardButton(text=f"{st} {l['title']}",
                                   callback_data=f"tog_lessons_{l['id']}_{0 if l['is_active'] else 1}"))
    b.adjust(1)
    await callback.message.edit_text("📚 اضغط لتبديل الحالة:", reply_markup=b.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("tog_"))
async def toggle(callback: types.CallbackQuery):
    _, table, item_id, new_status = callback.data.split("_")
    toggle_status(table, int(item_id), int(new_status))
    await callback.answer("✅ تم التحديث")
    await callback.message.delete()

@router.callback_query(F.data == "stats")
async def stats(callback: types.CallbackQuery):
    students = get_all_students()
    lessons = get_all_lessons()
    ps = get_payment_stats()
    active = sum(1 for s in students if s["is_active"])
    await callback.message.edit_text(
        f"📊 <b>الإحصائيات</b>\\n━━━━━━━━━━\\n"
        f"👥 الطلاب: {len(students)} (نشط: {active})\\n"
        f"📚 الدروس: {len(lessons)}\\n"
        f"💳 المدفوعات: {ps['total']} (معلق: {ps['pending']}, مقبول: {ps['approved']})\\n"
        f"💰 الإيرادات: {ps['total_amount']:.0f} دينار")
    await callback.answer()

# ═══ موافقة/رفض الدفع ═══

@router.callback_query(F.data.startswith("adm:approve:"))
async def approve_pay(callback: types.CallbackQuery, bot):
    parts = callback.data.split(":")
    payment_id = int(parts[2])
    user_id = int(parts[3])
    plan_key = parts[4]
    plan_name = parts[5]
    days = int(parts[6])
    approve_payment(payment_id, user_id, plan_key, plan_name, days)
    await callback.message.edit_caption(
        callback.message.caption + "\\n\\n✅ <b>تمت الموافقة</b>")
    try:
        await bot.send_message(user_id, f"🎉 <b>تم تفعيل اشتراكك!</b>\\n\\nالباقة: <b>{plan_name}</b>\\nالمدة: <b>{days} يوم</b>\\n\\nابدأ دراستك الآن 🚀")
    except:
        pass
    await callback.answer("✅ تمت الموافقة")

@router.callback_query(F.data.startswith("adm:reject:"))
async def reject_pay(callback: types.CallbackQuery, bot):
    parts = callback.data.split(":")
    payment_id = int(parts[2])
    user_id = int(parts[3])
    reject_payment(payment_id)
    await callback.message.edit_caption(
        callback.message.caption + "\\n\\n❌ <b>تم الرفض</b>")
    try:
        await bot.send_message(user_id, "❌ <b>عذراً، لم يتم قبول وصلك.</b>\\n\\nراجع المبلغ والرقم وحاول مجدداً.")
    except:
        pass
    await callback.answer("❌ تم الرفض")
"""

# ═══ تحديث main.py ═══
FILES["main.py"] = """import asyncio, logging, sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
from handlers import student, admin, placement_test, writing, speaking, subscriptions

async def main():
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL), stream=sys.stdout)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(
        student.router, admin.router, placement_test.router,
        writing.router, speaking.router, subscriptions.router)
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
"""

# ═══ تحديث student.py ═══
FILES[r"handlers\student.py"] = """from aiogram import Router, F, types
from aiogram.filters import CommandStart
from keyboards.main_kb import start_test_kb
from database import upsert_student, get_student, get_subscription
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton

router = Router()

def main_menu_kb():
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="✍️ تصحيح كتابة"), KeyboardButton(text="🎤 تقييم تحدث"))
    b.row(KeyboardButton(text="📚 دروسي"), KeyboardButton(text="📊 تقاريري"))
    b.row(KeyboardButton(text="💎 الاشتراك"))
    b.adjust(2)
    return b

@router.message(CommandStart())
async def welcome(message: types.Message):
    user = message.from_user
    is_new = upsert_student(user.id, user.full_name)
    student = get_student(user.id)

    if is_new or not student["placement_done"]:
        await message.answer(
            f"👋 أهلاً {user.full_name} في أكاديمية يامن الرقمية!\\n\\nقبل البدء، يجب إجراء اختبار مستوى سريع (10 أسئلة).",
            reply_markup=start_test_kb().as_markup())
    else:
        sub = get_subscription(user.id)
        sub_text = f"\\n\\n✅ اشتراكك: <b>{sub['plan_name']}</b> (ينتهي {sub['ends_at'][:10]})" if sub else "\\n\\n⚠️ ليس لديك اشتراك نشط — اضغط 💎 الاشتراك"
        await message.answer(
            f"👋 مرحباً بعودتك {user.full_name}!\\nمستواك: {student['level']}{sub_text}",
            reply_markup=main_menu_kb().as_markup(resize_keyboard=True))

@router.message(F.text == "💎 الاشتراك")
async def menu_subscribe(message: types.Message):
    from handlers.subscriptions import show_plans_msg
    await show_plans_msg(message)
"""

# ═══ تحديث keyboards/main_kb.py ═══
FILES[r"keyboards\main_kb.py"] = """from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def admin_panel_kb():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="➕ إضافة درس", callback_data="add_lesson"))
    b.row(InlineKeyboardButton(text="👥 إدارة الطلاب", callback_data="list_students"))
    b.row(InlineKeyboardButton(text="📚 إدارة الدروس", callback_data="list_lessons"))
    b.row(InlineKeyboardButton(text="💳 طلبات الدفع", callback_data="payment_requests"))
    b.row(InlineKeyboardButton(text="📊 إحصائيات", callback_data="stats"))
    return b

def start_test_kb():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🚀 ابدأ اختبار المستوى", callback_data="start_placement"))
    return b
"""

# ═══ BUILD ═══
print("🏗 بناء نظام الاشتراكات والدفع...")
for path, content in FILES.items():
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ {path}")
print("\n🎉 تم البناء! شغّل: python main.py")
