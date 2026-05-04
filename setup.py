# setup.py — باني مشروع أكاديمية يامن V3
import os

BASE = r"C:\yamen_academy"

FILES = {}

# ─── .env ───
FILES[".env"] = """BOT_TOKEN=####################################
ADMIN_IDS=5572314718
DB_PATH=ielts_bot.db
GEMINI_API_KEY=AIzaSyBfu0gQwsBOqh6dzTVBaOcFByEzjJ9unxM
GEMINI_WRITING_KEYS=AIzaSyDkAuMCa9rBQGiFkqxIauUCL7eXQyP2aHw,AIzaSyDGRbeskDR64jlDFkC5UzSdfleMp_sUwKc,AIzaSyDFU5MAO20Hssq6SWS-F0TGGint3IZUwKc
GEMINI_SPEAKING_KEYS=AIzaSyCBFNExYp5-9yFjHFrnaqUS-yZn_YqigSY,AIzaSyAXGja3hvzIo2SyTTQcuKBNa-yHZghHu8M,AIzaSyBWj39r49ORhKEpoDLhk6bpPiJLGrmohW0
STORAGE_CHANNEL_ID=-3792834322
GROUP_LINK=https://t.me/+2NkF901AApcyODk0
ENVIRONMENT=development
LOG_LEVEL=DEBUG
"""

# ─── requirements.txt ───
FILES["requirements.txt"] = """aiogram>=3.27.0
python-dotenv>=1.0.0
aiofiles>=24.0.0
"""

# ─── config.py ───
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

settings = Settings()
"""

# ─── database.py ───
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
            course_id     INTEGER NOT NULL,
            start_date    TEXT    DEFAULT (datetime('now','localtime')),
            end_date      TEXT    NOT NULL,
            is_active     INTEGER DEFAULT 1,
            FOREIGN KEY (user_id)  REFERENCES students(user_id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
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

init_db()
seed_courses()
'''

# ─── keyboards/__init__.py ───
FILES[r"keyboards\__init__.py"] = ""

# ─── keyboards/main_kb.py ───
FILES[r"keyboards\main_kb.py"] = """from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def admin_panel_kb():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="➕ إضافة درس", callback_data="add_lesson"))
    b.row(InlineKeyboardButton(text="👥 إدارة الطلاب", callback_data="list_students"))
    b.row(InlineKeyboardButton(text="📚 إدارة الدروس", callback_data="list_lessons"))
    b.row(InlineKeyboardButton(text="📊 إحصائيات", callback_data="stats"))
    return b

def start_test_kb():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🚀 ابدأ اختبار المستوى", callback_data="start_placement"))
    return b
"""

# ─── handlers/__init__.py ───
FILES[r"handlers\__init__.py"] = ""

# ─── handlers/placement_test.py ───
FILES[r"handlers\placement_test.py"] = """from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import set_student_level

router = Router()

QUESTIONS = [
    {"q": "What ___ your name?", "opts": ["is", "are", "am", "be"], "ans": 0, "diff": 1},
    {"q": "She ___ to school every day.", "opts": ["go", "goes", "going", "gone"], "ans": 1, "diff": 1},
    {"q": "Choose the correct sentence:", "opts": ["He don't like coffee", "He doesn't like coffee", "He not like coffee", "He no like coffee"], "ans": 1, "diff": 2},
    {"q": "I have been waiting for you ___ two hours.", "opts": ["since", "for", "during", "while"], "ans": 1, "diff": 2},
    {"q": "If I ___ rich, I would travel the world.", "opts": ["am", "was", "were", "be"], "ans": 2, "diff": 3},
    {"q": "The book, ___ I borrowed from the library, is fascinating.", "opts": ["that", "which", "what", "who"], "ans": 1, "diff": 3},
    {"q": "The scientist made a significant ___ in cancer research.", "opts": ["breakdown", "breakthrough", "breakup", "breakout"], "ans": 1, "diff": 4},
    {"q": "Despite ___ hard, he failed the exam.", "opts": ["he studied", "studying", "he studying", "studied"], "ans": 1, "diff": 4},
    {"q": "The phenomenon can be ___ to several factors.", "opts": ["attributed", "contributed", "distributed", "retributed"], "ans": 0, "diff": 5},
    {"q": "Had the government acted sooner, the crisis ___ averted.", "opts": ["would be", "would have been", "will be", "had been"], "ans": 1, "diff": 5},
]

class PlacementState(StatesGroup):
    answering = State()

@router.callback_query(F.data == "start_placement")
async def start_placement(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(PlacementState.answering)
    await state.update_data(idx=0, correct=0)
    await send_q(callback.message, state, 0)
    await callback.answer()

async def send_q(msg: types.Message, state: FSMContext, idx: int):
    if idx >= len(QUESTIONS):
        await finish(msg, state)
        return
    q = QUESTIONS[idx]
    b = InlineKeyboardBuilder()
    for i, opt in enumerate(q["opts"]):
        b.row(InlineKeyboardButton(text=opt, callback_data=f"pt_{idx}_{i}"))
    await msg.answer(f"📝 سؤال {idx+1}/{len(QUESTIONS)}:\\n\\n{q['q']}", reply_markup=b.as_markup())

@router.callback_query(F.data.startswith("pt_"))
async def handle_answer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx = data["idx"]
    chosen = int(callback.data.split("_")[2])
    if chosen == QUESTIONS[idx]["ans"]:
        data["correct"] += 1
    data["idx"] += 1
    await state.update_data(data)
    await callback.message.delete()
    await send_q(callback.message, state, data["idx"])
    await callback.answer()

async def finish(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    score = data["correct"]
    if score <= 3:
        level = "Foundation"
    elif score <= 6:
        level = "IELTS/TOEFL Intermediate"
    else:
        level = "IELTS/TOEFL Advanced"
    set_student_level(msg.chat.id, level)
    await msg.answer(f"✅ انتهى الاختبار!\\n\\nنتيجتك: {score}/{len(QUESTIONS)}\\nمستواك: {level}")
    await state.clear()
"""

# ─── handlers/admin.py ───
FILES[r"handlers\admin.py"] = """from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import settings
from database import add_lesson, toggle_status, get_all_students, get_all_lessons
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
    active = sum(1 for s in students if s["is_active"])
    await callback.message.edit_text(
        f"📊 إحصائيات:\\n\\n👥 الطلاب: {len(students)} (نشط: {active})\\n📚 الدروس: {len(lessons)}")
    await callback.answer()
"""

# ─── handlers/student.py ───
FILES[r"handlers\student.py"] = """from aiogram import Router, F, types
from aiogram.filters import CommandStart
from keyboards.main_kb import start_test_kb
from database import upsert_student, get_student

router = Router()

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
        await message.answer(f"👋 مرحباً بعودتك {user.full_name}!\\nمستواك: {student['level']}")
"""

# ─── main.py ───
FILES["main.py"] = """import asyncio, logging, sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
from handlers import student, admin, placement_test

async def main():
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL), stream=sys.stdout)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(student.router, admin.router, placement_test.router)
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
"""

# ═══════ BUILD ═══════
print("🚀 بناء أكاديمية يامن V3...")
for path, content in FILES.items():
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ {path}")

print(f"\n🎉 تم البناء في: {BASE}")
print("الخطوة التالية: شغّل install_and_run.py")
