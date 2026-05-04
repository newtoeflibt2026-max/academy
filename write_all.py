import os

base = r"C:\yamen_academy"

# ########## database.py ##########
database_py = """import sqlite3, os, threading
from config import settings

_local = threading.local()
DB_PATH = getattr(settings, 'DB_PATH', 'data/academy.db')

def get_conn():
    if not hasattr(_local, 'conn') or _local.conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
        _local.conn.row_factory = sqlite3.Row
    return _local.conn

def init_db():
    conn = get_conn()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS students (
            user_id INTEGER PRIMARY KEY, full_name TEXT, username TEXT DEFAULT "",
            level TEXT DEFAULT "", placement_done INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1, xp INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, level TEXT,
            price REAL, duration_days INTEGER, is_vip INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, title TEXT,
            content TEXT, properties TEXT DEFAULT "", order_num INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            media_type TEXT DEFAULT "", media_file_id TEXT DEFAULT "",
            action_type TEXT DEFAULT "", action_label TEXT DEFAULT ""
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan_name TEXT,
            course_id INTEGER,
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, end_date TIMESTAMP,
            is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan_name TEXT,
            amount REAL, status TEXT DEFAULT "pending", receipt_file_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS admin_settings (
            key TEXT PRIMARY KEY, value TEXT
        );
        CREATE TABLE IF NOT EXISTS xp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
            reason TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS daily_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, options TEXT,
            correct_idx INTEGER, sent_at TIMESTAMP, is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS challenge_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, challenge_id INTEGER, user_id INTEGER,
            answer_idx INTEGER, is_correct INTEGER, response_time_sec REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS vault_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT,
            unlock_level TEXT, is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, feature TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

def _safe_fetchone(query, params=()):
    try: return get_conn().execute(query, params).fetchone()
    except Exception as e:
        try: get_conn().execute("INSERT OR IGNORE INTO errors_log (error,ctx) VALUES (?,?)", (str(e), query))
        except: pass
        return None

def _safe_fetchall(query, params=()):
    try: return get_conn().execute(query, params).fetchall()
    except Exception as e:
        try: get_conn().execute("INSERT OR IGNORE INTO errors_log (error,ctx) VALUES (?,?)", (str(e), query))
        except: pass
        return []

def _safe_exec(query, params=()):
    try:
        get_conn().execute(query, params)
        get_conn().commit()
    except Exception as e:
        try: get_conn().execute("INSERT OR IGNORE INTO errors_log (error,ctx) VALUES (?,?)", (str(e), query))
        except: pass
        raise e

def add_student(user_id, full_name, username=""):
    _safe_exec("INSERT OR IGNORE INTO students (user_id, full_name, username) VALUES (?,?,?)", (user_id, full_name, username))

def upsert_student(user_id, full_name, username=""):
    add_student(user_id, full_name, username)

def get_student(user_id):
    return _safe_fetchone("SELECT * FROM students WHERE user_id=?", (user_id,))

def get_all_students():
    return _safe_fetchall("SELECT * FROM students ORDER BY created_at DESC")

def set_placement_done(user_id, level):
    _safe_exec("UPDATE students SET placement_done=1, level=? WHERE user_id=?", (level, user_id))

def toggle_student_active(user_id):
    row = _safe_fetchone("SELECT is_active FROM students WHERE user_id=?", (user_id,))
    if row: _safe_exec("UPDATE students SET is_active=? WHERE user_id=?", (0 if row["is_active"] else 1, user_id))

def add_xp(user_id, amount, reason=""):
    _safe_exec("UPDATE students SET xp = xp + ? WHERE user_id=?", (amount, user_id))
    _safe_exec("INSERT INTO xp_log (user_id, amount, reason) VALUES (?,?,?)", (user_id, amount, reason))

def get_leaderboard(limit=10):
    return _safe_fetchall("SELECT full_name, xp FROM students WHERE is_active=1 ORDER BY xp DESC LIMIT ?", (limit,))

def add_lesson(title, content, course_id=1, order_num=0, properties="", media_type="", media_file_id="", action_type="", action_label=""):
    _safe_exec("INSERT INTO lessons (title, content, properties, course_id, order_num, media_type, media_file_id, action_type, action_label) VALUES (?,?,?,?,?,?,?,?,?)",
               (title, content, properties, course_id, order_num, media_type, media_file_id, action_type, action_label))

def get_all_lessons():
    return _safe_fetchall("SELECT * FROM lessons ORDER BY order_num")

def get_pending_payments():
    return _safe_fetchall("SELECT * FROM payments WHERE status='pending'")

def update_payment_status(pid, status):
    _safe_exec("UPDATE payments SET status=? WHERE id=?", (status, pid))

def add_payment(user_id, plan_name, amount, receipt_file_id):
    _safe_exec("INSERT INTO payments (user_id, plan_name, amount, receipt_file_id) VALUES (?,?,?,?)", (user_id, plan_name, amount, receipt_file_id))

def add_subscription(user_id, plan_name, duration_days=30, course_id=None):
    import datetime
    end = (datetime.datetime.now() + datetime.timedelta(days=duration_days)).strftime("%Y-%m-%d %H:%M:%S")
    _safe_exec("INSERT INTO subscriptions (user_id, plan_name, course_id, end_date) VALUES (?,?,?,?)", (user_id, plan_name, course_id, end))

def get_stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM students WHERE is_active=1").fetchone()[0]
    try:
        paying = conn.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
    except:
        paying = 0
    return {"total_students": total, "active_students": active, "pending_payments": paying}
"""

# ########## handlers/admin.py ##########
admin_py = """from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from config import settings
from database import get_all_students, get_pending_payments, get_all_lessons, add_lesson, toggle_student_active, get_stats, add_subscription, update_payment_status

router = Router()

class AddLesson(StatesGroup):
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_level = State()
    waiting_for_media = State()
    waiting_for_action = State()

def admin_only(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not admin_only(message.from_user.id):
        await message.answer("⛔ غير مصرح لك")
        return
    stats = get_stats()
    text = f"🎓 لوحة تحكم أكاديمية يامن\\n\\n📊 إحصائيات:\\n• الطلاب: {stats['total_students']}\\n• النشطين: {stats['active_students']}\\n• مدفوعات معلقة: {stats['pending_payments']}\\n\\nاختر القسم:"
    kb = InlineKeyboardBuilder()
    kb.button(text="📚 المحتوى والدروس", callback_data="adm_sector_content")
    kb.button(text="👥 المستخدمين", callback_data="adm_sector_users")
    kb.button(text="💳 المدفوعات", callback_data="adm_sector_payments")
    kb.adjust(1)
    await message.answer(text, reply_markup=kb.as_markup())

@router.callback_query(F.data == "adm_sector_content")
async def sector_content(callback: types.CallbackQuery):
    if not admin_only(callback.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ إضافة درس جديد", callback_data="adm_add_lesson")
    kb.button(text="📋 عرض جميع الدروس", callback_data="adm_list_lessons")
    kb.button(text="🔙 رجوع", callback_data="adm_back")
    kb.adjust(1)
    try: await callback.message.edit_text("📚 المحتوى والدروس\\n\\nماذا تريد أن تفعل؟", reply_markup=kb.as_markup())
    except TelegramBadRequest: pass
    await callback.answer()

@router.callback_query(F.data == "adm_add_lesson")
async def add_lesson_step1(callback: types.CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id): return
    await state.set_state(AddLesson.waiting_for_title)
    await callback.message.answer("📝 أرسل عنوان الدرس:\\n\\nأرسل /cancel للإلغاء.")
    await callback.answer()

@router.message(AddLesson.waiting_for_title, F.text)
async def add_lesson_step2(message: types.Message, state: FSMContext):
    if message.text == "/cancel": await state.clear(); await message.answer("❌ تم الإلغاء."); return
    await state.update_data(title=message.text.strip())
    await state.set_state(AddLesson.waiting_for_content)
    await message.answer("📄 الآن أرسل محتوى الدرس:\\n\\nأرسل /cancel للإلغاء.")

@router.message(AddLesson.waiting_for_content, F.text)
async def add_lesson_step3(message: types.Message, state: FSMContext):
    if message.text == "/cancel": await state.clear(); await message.answer("❌ تم الإلغاء."); return
    await state.update_data(content=message.text.strip())
    await state.set_state(AddLesson.waiting_for_level)
    kb = InlineKeyboardBuilder()
    kb.button(text="🔰 Foundation", callback_data="lvl_Foundation")
    kb.button(text="🟡 Intermediate", callback_data="lvl_Intermediate")
    kb.button(text="🔴 Advanced", callback_data="lvl_Advanced")
    kb.adjust(1)
    await message.answer("📊 اختر مستوى الدرس:", reply_markup=kb.as_markup())

@router.callback_query(AddLesson.waiting_for_level, F.data.startswith("lvl_"))
async def add_lesson_step4(callback: types.CallbackQuery, state: FSMContext):
    level = callback.data.split("_")[1]
    await state.update_data(level=level)
    await state.set_state(AddLesson.waiting_for_media)
    kb = InlineKeyboardBuilder()
    kb.button(text="⏭️ تخطي", callback_data="media_skip")
    await callback.message.edit_text("🖼️ هل تريد إضافة وسائط للدرس؟\\n\\n• صورة توضيحية\\n• مقطع صوتي\\n• فيديو\\n\\nأرسل الملف الآن، أو اضغط تخطي.", reply_markup=kb.as_markup())
    await callback.answer()

@router.message(AddLesson.waiting_for_media, F.photo)
async def add_lesson_media_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(media_type="photo", media_file_id=file_id)
    await _ask_action(message, state)

@router.message(AddLesson.waiting_for_media, F.audio)
async def add_lesson_media_audio(message: types.Message, state: FSMContext):
    await state.update_data(media_type="audio", media_file_id=message.audio.file_id)
    await _ask_action(message, state)

@router.message(AddLesson.waiting_for_media, F.voice)
async def add_lesson_media_voice(message: types.Message, state: FSMContext):
    await state.update_data(media_type="voice", media_file_id=message.voice.file_id)
    await _ask_action(message, state)

@router.message(AddLesson.waiting_for_media, F.video)
async def add_lesson_media_video(message: types.Message, state: FSMContext):
    await state.update_data(media_type="video", media_file_id=message.video.file_id)
    await _ask_action(message, state)

@router.callback_query(AddLesson.waiting_for_media, F.data == "media_skip")
async def add_lesson_media_skip(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(media_type="", media_file_id="")
    await _show_action(callback, state)

async def _ask_action(dest, state: FSMContext):
    await state.set_state(AddLesson.waiting_for_action)
    kb = InlineKeyboardBuilder()
    kb.button(text="🎤 زر تحدث", callback_data="act_speaking")
    kb.button(text="✍️ زر تصحيح كتابة", callback_data="act_writing")
    kb.button(text="⏭️ بدون زر", callback_data="act_none")
    kb.adjust(1)
    if isinstance(dest, types.CallbackQuery):
        try: await dest.message.edit_text("🔘 هل تريد إضافة زر تفاعلي للطالب؟", reply_markup=kb.as_markup())
        except TelegramBadRequest: pass
    else:
        await dest.answer("🔘 هل تريد إضافة زر تفاعلي للطالب؟", reply_markup=kb.as_markup())

async def _show_action(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddLesson.waiting_for_action)
    kb = InlineKeyboardBuilder()
    kb.button(text="🎤 زر تحدث", callback_data="act_speaking")
    kb.button(text="✍️ زر تصحيح كتابة", callback_data="act_writing")
    kb.button(text="⏭️ بدون زر", callback_data="act_none")
    kb.adjust(1)
    try: await callback.message.edit_text("🔘 هل تريد إضافة زر تفاعلي للطالب؟", reply_markup=kb.as_markup())
    except TelegramBadRequest: pass

@router.callback_query(AddLesson.waiting_for_action, F.data.startswith("act_"))
async def add_lesson_finish(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    data = await state.get_data()
    
    action_type = ""
    action_label = ""
    if action == "speaking":
        action_type = "speaking"
        action_label = "🎤 تحدث"
    elif action == "writing":
        action_type = "writing"
        action_label = "✍️ صحح كتابتي"
    
    data = await state.get_data()
    course_map = {"Foundation": 1, "Intermediate": 2, "Advanced": 3}
    course_id = course_map.get(data.get("level", "Foundation"), 1)
    
    import sqlite3
    conn = sqlite3.connect(settings.DB_PATH)
    cur = conn.execute("SELECT MAX(order_num) as mx FROM lessons WHERE course_id=?", (course_id,))
    row = cur.fetchone()
    max_order = row[0] if row and row[0] else 0
    conn.close()
    
    add_lesson(
        title=data["title"], content=data["content"], course_id=course_id,
        order_num=max_order + 1,
        media_type=data.get("media_type", ""), media_file_id=data.get("media_file_id", ""),
        action_type=action_type, action_label=action_label
    )
    
    await state.clear()
    
    extras = []
    if data.get("media_type"): extras.append(f"🖼️ وسائط: {data['media_type']}")
    if action_type: extras.append(f"🔘 زر: {action_label}")
    extra_text = " | ".join(extras) if extras else "بدون وسائط إضافية"
    
    try:
        await callback.message.edit_text(
            f"✅ تمت إضافة الدرس بنجاح!\\n\\n📖 {data['title']}\\n📊 المستوى: {data.get('level', '—')}\\n{extra_text}"
        )
    except TelegramBadRequest: pass
    await callback.answer()

@router.callback_query(F.data == "adm_list_lessons")
async def list_lessons(callback: types.CallbackQuery):
    lessons = get_all_lessons()
    if not lessons: await callback.answer("لا توجد دروس بعد", show_alert=True); return
    text = "📋 جميع الدروس:\\n\\n"
    for l in lessons[:30]:
        status = "✅" if l.get("is_active") else "🚫"
        lvl = {1: "Foundation", 2: "Intermediate", 3: "Advanced"}.get(l.get("course_id"), "—")
        media_icon = {"photo":"🖼️","audio":"🎵","voice":"🎙️","video":"🎬"}.get(l.get("media_type",""), "")
        btn_icon = "🔘" if l.get("action_type") else ""
        text += f"{status} #{l['id']} | {lvl} {media_icon}{btn_icon} | {l['title'][:30]}\\n"
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 رجوع", callback_data="adm_sector_content")
    try: await callback.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest: pass
    await callback.answer()

@router.callback_query(F.data == "adm_back")
async def admin_back(callback: types.CallbackQuery):
    stats = get_stats()
    text = f"🎓 لوحة تحكم أكاديمية يامن\\n\\n📊 إحصائيات:\\n• الطلاب: {stats['total_students']}\\n• النشطين: {stats['active_students']}\\n• مدفوعات معلقة: {stats['pending_payments']}\\n\\nاختر القسم:"
    kb = InlineKeyboardBuilder()
    kb.button(text="📚 المحتوى والدروس", callback_data="adm_sector_content")
    kb.button(text="👥 المستخدمين", callback_data="adm_sector_users")
    kb.button(text="💳 المدفوعات", callback_data="adm_sector_payments")
    kb.adjust(1)
    try: await callback.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest: pass
    await callback.answer()

@router.callback_query(F.data == "adm_sector_users")
async def sector_users(callback: types.CallbackQuery):
    students = get_all_students()
    text = "👥 قائمة الطلاب:\\n\\n"
    for s in students[:20]:
        icon = "✅" if s.get("is_active") else "🚫"
        text += f"{icon} {s['full_name']} | {s.get('level','—')}\\n"
    kb = InlineKeyboardBuilder()
    for s in students[:20]:
        kb.button(text=f"{'🚫 إلغاء' if s.get('is_active') else '✅ تفعيل'} {s['full_name'][:15]}", callback_data=f"tog_{s['user_id']}")
    kb.button(text="🔙 رجوع", callback_data="adm_back")
    kb.adjust(1)
    try: await callback.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest: pass
    await callback.answer()

@router.callback_query(F.data.startswith("tog_"))
async def toggle_user(callback: types.CallbackQuery):
    uid = int(callback.data.split("_")[1])
    toggle_student_active(uid)
    await callback.answer("✅ تم تبديل الحالة")
    students = get_all_students()
    text = "👥 قائمة الطلاب:\\n\\n"
    for s in students[:20]:
        icon = "✅" if s.get("is_active") else "🚫"
        text += f"{icon} {s['full_name']} | {s.get('level','—')}\\n"
    kb = InlineKeyboardBuilder()
    for s in students[:20]:
        kb.button(text=f"{'🚫 إلغاء' if s.get('is_active') else '✅ تفعيل'} {s['full_name'][:15]}", callback_data=f"tog_{s['user_id']}")
    kb.button(text="🔙 رجوع", callback_data="adm_back")
    kb.adjust(1)
    try: await callback.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest: pass

@router.callback_query(F.data == "adm_sector_payments")
async def sector_payments(callback: types.CallbackQuery):
    pending = get_pending_payments()
    if not pending:
        kb = InlineKeyboardBuilder()
        kb.button(text="🔙 رجوع", callback_data="adm_back")
        try: await callback.message.edit_text("💳 لا توجد مدفوعات معلقة", reply_markup=kb.as_markup())
        except TelegramBadRequest: pass
    else:
        text = "💳 مدفوعات معلقة:\\n\\n"
        for p in pending: text += f"#{p['id']} | user={p['user_id']} | {p['plan_name']} | {p['amount']}د.أ\\n"
        kb = InlineKeyboardBuilder()
        for p in pending:
            kb.button(text=f"✅ موافقة + تفعيل #{p['id']}", callback_data=f"appr_{p['id']}")
        kb.button(text="🔙 رجوع", callback_data="adm_back")
        kb.adjust(1)
        try: await callback.message.edit_text(text, reply_markup=kb.as_markup())
        except TelegramBadRequest: pass
    await callback.answer()

@router.callback_query(F.data.startswith("appr_"))
async def approve_payment(callback: types.CallbackQuery):
    pid = int(callback.data.split("_")[1])
    pending = get_pending_payments()
    payment = next((p for p in pending if p["id"] == pid), None)
    if not payment: await callback.answer("❌ غير موجود", show_alert=True); return
    update_payment_status(pid, "approved")
    add_subscription(payment["user_id"], payment["plan_name"], 30)
    await callback.bot.send_message(payment["user_id"], "🎉 تم تفعيل اشتراكك! استخدم /start ثم '📚 دوراتي' للبدء.")
    await callback.answer("✅ تمت الموافقة والتفعيل")
    pending2 = get_pending_payments()
    if not pending2:
        kb = InlineKeyboardBuilder()
        kb.button(text="🔙 رجوع", callback_data="adm_back")
        try: await callback.message.edit_text("💳 لا توجد مدفوعات معلقة", reply_markup=kb.as_markup())
        except TelegramBadRequest: pass
    else:
        text = "💳 مدفوعات معلقة:\\n\\n"
        for p in pending2: text += f"#{p['id']} | user={p['user_id']} | {p['plan_name']} | {p['amount']}د.أ\\n"
        kb = InlineKeyboardBuilder()
        for p in pending2:
            kb.button(text=f"✅ موافقة + تفعيل #{p['id']}", callback_data=f"appr_{p['id']}")
        kb.button(text="🔙 رجوع", callback_data="adm_back")
        kb.adjust(1)
        try: await callback.message.edit_text(text, reply_markup=kb.as_markup())
        except TelegramBadRequest: pass
"""

# ########## handlers/courses.py ##########
courses_py = """from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from database import get_student, get_all_lessons, get_conn

router = Router()

COURSE_INFO = {
    "Foundation": {"title": "IELTS Foundation", "desc": "للمبتدئين — أساسيات اللغة", "duration": "30 يوم"},
    "Intermediate": {"title": "IELTS Intermediate", "desc": "للمتوسطين — تطوير المهارات", "duration": "60 يوم"},
    "Advanced": {"title": "IELTS Advanced", "desc": "للمتقدمين — إتقان IELTS", "duration": "90 يوم"},
}

def _has_active_sub(user_id: int) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM subscriptions WHERE user_id=? AND is_active=1 AND end_date >= datetime('now')",
        (user_id,)
    ).fetchone()
    return bool(row)

def _get_lessons_for_level(level: str):
    conn = get_conn()
    course_id = {"Foundation": 1, "Intermediate": 2, "Advanced": 3}.get(level, 1)
    rows = conn.execute(
        "SELECT * FROM lessons WHERE course_id=? AND is_active=1 ORDER BY order_num",
        (course_id,)
    ).fetchall()
    return [dict(r) for r in rows]

@router.callback_query(F.data == "my_courses")
async def my_courses(callback: types.CallbackQuery):
    student = get_student(callback.from_user.id)
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 رجوع", callback_data="main_menu")
    if not student or not student.get("placement_done"):
        try: await callback.message.edit_text("⚠️ يجب إجراء اختبار تحديد المستوى أولاً.", reply_markup=kb.as_markup())
        except TelegramBadRequest: pass
        await callback.answer()
        return
    level = student["level"]
    has_sub = _has_active_sub(callback.from_user.id)
    info = COURSE_INFO.get(level, COURSE_INFO["Foundation"])
    if not has_sub:
        text = f"📚 {info['title']}\\n\\n{info['desc']}\\n⏱️ المدة: {info['duration']}\\n\\n⚠️ لا يوجد اشتراك نشط.\\nاشترك أولاً للوصول إلى الدروس."
        kb2 = InlineKeyboardBuilder()
        kb2.button(text="💎 الاشتراك الآن", callback_data="menu_subscribe")
        kb2.button(text="🔙 رجوع", callback_data="main_menu")
        kb2.adjust(1)
        try: await callback.message.edit_text(text, reply_markup=kb2.as_markup())
        except TelegramBadRequest: pass
        await callback.answer()
        return
    lessons = _get_lessons_for_level(level)
    if not lessons:
        text = f"📚 {info['title']}\\n\\n✅ اشتراكك نشط!\\nلا توجد دروس مضافة بعد — سيتم إضافتها قريباً."
        try: await callback.message.edit_text(text, reply_markup=kb.as_markup())
        except TelegramBadRequest: pass
        await callback.answer()
        return
    text = f"📚 {info['title']}\\n✅ اشتراكك نشط — اختر الدرس:\\n"
    kb3 = InlineKeyboardBuilder()
    for l in lessons:
        icon = "📖"
        if l.get("media_type") == "photo": icon = "🖼️"
        elif l.get("media_type") in ("audio", "voice"): icon = "🎵"
        elif l.get("media_type") == "video": icon = "🎬"
        extra = " 🔘" if l.get("action_type") else ""
        kb3.button(text=f"{icon} {l['title'][:35]}{extra}", callback_data=f"view_lesson_{l['id']}")
    kb3.button(text="🔙 رجوع", callback_data="main_menu")
    kb3.adjust(1)
    try: await callback.message.edit_text(text, reply_markup=kb3.as_markup(), parse_mode="HTML")
    except TelegramBadRequest: pass
    await callback.answer()

@router.callback_query(F.data.startswith("view_lesson_"))
async def view_lesson(callback: types.CallbackQuery):
    lesson_id = int(callback.data.split("_")[-1])
    conn = get_conn()
    row = conn.execute("SELECT * FROM lessons WHERE id=?", (lesson_id,)).fetchone()
    if not row:
        kb = InlineKeyboardBuilder()
        kb.button(text="🔙 دوراتي", callback_data="my_courses")
        try: await callback.message.edit_text("الدرس غير موجود.", reply_markup=kb.as_markup())
        except TelegramBadRequest: pass
        await callback.answer()
        return
    l = dict(row)
    try:
        if l.get("media_type") == "photo" and l.get("media_file_id"):
            await callback.message.answer_photo(l["media_file_id"], caption=f"📖 {l['title']}")
        elif l.get("media_type") == "audio" and l.get("media_file_id"):
            await callback.message.answer_audio(l["media_file_id"], caption=f"🎵 {l['title']}")
        elif l.get("media_type") == "voice" and l.get("media_file_id"):
            await callback.message.answer_voice(l["media_file_id"])
        elif l.get("media_type") == "video" and l.get("media_file_id"):
            await callback.message.answer_video(l["media_file_id"], caption=f"🎬 {l['title']}")
    except TelegramBadRequest: pass
    text = f"📖 *{l['title']}*\\n\\n{l['content']}"
    kb = InlineKeyboardBuilder()
    if l.get("action_type") == "speaking":
        kb.button(text=l.get("action_label", "🎤 تحدث"), callback_data=f"speak_lesson_{l['id']}")
    elif l.get("action_type") == "writing":
        kb.button(text=l.get("action_label", "✍️ صحح كتابتي"), callback_data=f"write_lesson_{l['id']}")
    kb.button(text="🔙 دوراتي", callback_data="my_courses")
    kb.adjust(1)
    try: await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    except TelegramBadRequest:
        await callback.message.edit_text(text.replace("*",""), reply_markup=kb.as_markup())
    await callback.answer()
"""

# ===== WRITE ALL FILES =====
files = {
    "database.py": database_py,
    r"handlers\\admin.py": admin_py,
    r"handlers\\courses.py": courses_py,
}

for relpath, content in files.items():
    fullpath = os.path.join(base, relpath)
    os.makedirs(os.path.dirname(fullpath), exist_ok=True)
    with open(fullpath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ {relpath}")

print("\\n====== ALL 3 FILES WRITTEN ======")
