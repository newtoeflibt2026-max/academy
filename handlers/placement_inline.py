# -*- coding: utf-8 -*-
"""
اختبار تحديد المستوى داخل Telegram (24 سؤالاً - CEFR)
+ توجيه تلقائي بعد النتيجة (Foundation أو TOEFL مباشر)
"""
from aiogram import types, Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import settings
import sqlite3
import logging

logger = logging.getLogger(__name__)
router = Router(name="placement_inline")

DB_PATH = settings.DB_PATH

# ═══════════════════════════════════════════════════
#  بنك الأسئلة (24 سؤالاً متدرجة - 6 مستويات CEFR)
# ═══════════════════════════════════════════════════
QUESTIONS = [
    # ===== A1 =====
    {"id":1,"level":"A1","skill":"grammar","q":"Choose the correct word:\n\nThis ____ a book.","options":{"A":"is","B":"are","C":"am","D":"be"},"answer":"A"},
    {"id":2,"level":"A1","skill":"vocab","q":"What is the opposite of big?","options":{"A":"tall","B":"small","C":"long","D":"wide"},"answer":"B"},
    {"id":3,"level":"A1","skill":"grammar","q":"Choose:\n\nI ____ a student.","options":{"A":"is","B":"are","C":"am","D":"be"},"answer":"C"},
    {"id":4,"level":"A1","skill":"vocab","q":"Apple is a kind of:","options":{"A":"animal","B":"fruit","C":"color","D":"car"},"answer":"B"},
    # ===== A2 =====
    {"id":5,"level":"A2","skill":"grammar","q":"Choose:\n\nShe ____ to school every day.","options":{"A":"go","B":"goes","C":"going","D":"gone"},"answer":"B"},
    {"id":6,"level":"A2","skill":"vocab","q":"What does happy mean?","options":{"A":"sad","B":"angry","C":"glad","D":"tired"},"answer":"C"},
    {"id":7,"level":"A2","skill":"grammar","q":"Choose the past tense:\n\nYesterday I ____ to the park.","options":{"A":"go","B":"went","C":"gone","D":"going"},"answer":"B"},
    {"id":8,"level":"A2","skill":"vocab","q":"Choose:\n\nHe is reading a ____.","options":{"A":"book","B":"eat","C":"run","D":"fast"},"answer":"A"},
    # ===== B1 =====
    {"id":9,"level":"B1","skill":"grammar","q":"Choose:\n\nIf it rains, I ____ stay home.","options":{"A":"will","B":"would","C":"was","D":"am"},"answer":"A"},
    {"id":10,"level":"B1","skill":"vocab","q":"What does benefit mean?","options":{"A":"harm","B":"advantage","C":"danger","D":"problem"},"answer":"B"},
    {"id":11,"level":"B1","skill":"grammar","q":"Choose:\n\nThe report ____ by the manager yesterday.","options":{"A":"wrote","B":"was written","C":"is writing","D":"writes"},"answer":"B"},
    {"id":12,"level":"B1","skill":"reading","q":"Despite the heavy rain, the match continued.\n\nThis means:","options":{"A":"The rain stopped the match","B":"The match was cancelled","C":"The match went on even though it rained","D":"There was no rain"},"answer":"C"},
    # ===== B2 =====
    {"id":13,"level":"B2","skill":"grammar","q":"Choose:\n\nIf I ____ rich, I would travel the world.","options":{"A":"am","B":"was","C":"were","D":"be"},"answer":"C"},
    {"id":14,"level":"B2","skill":"vocab","q":"Choose the synonym of significant:","options":{"A":"small","B":"important","C":"easy","D":"quick"},"answer":"B"},
    {"id":15,"level":"B2","skill":"vocab","q":"Choose the opposite of abundant:","options":{"A":"plentiful","B":"scarce","C":"rich","D":"full"},"answer":"B"},
    {"id":16,"level":"B2","skill":"reading","q":"The researchers findings were inconclusive.\n\nThis means:","options":{"A":"The results were very clear","B":"No clear conclusion was reached","C":"The research was successful","D":"The findings were published"},"answer":"B"},
    # ===== C1 =====
    {"id":17,"level":"C1","skill":"vocab","q":"Choose the meaning of elaborate (verb):","options":{"A":"to summarize briefly","B":"to explain in detail","C":"to ignore","D":"to repeat"},"answer":"B"},
    {"id":18,"level":"C1","skill":"grammar","q":"Choose:\n\nHardly ____ he arrived when the meeting started.","options":{"A":"has","B":"had","C":"did","D":"was"},"answer":"B"},
    {"id":19,"level":"C1","skill":"vocab","q":"Meticulous most nearly means:","options":{"A":"careless","B":"extremely careful","C":"lazy","D":"fast"},"answer":"B"},
    {"id":20,"level":"C1","skill":"reading","q":"Her argument, while compelling, rested on flawed premises.\n\nThe writer suggests the argument was:","options":{"A":"completely wrong","B":"persuasive but based on errors","C":"perfectly logical","D":"too short"},"answer":"B"},
    # ===== C2 =====
    {"id":21,"level":"C2","skill":"vocab","q":"Ubiquitous means:","options":{"A":"rare","B":"present everywhere","C":"ancient","D":"hidden"},"answer":"B"},
    {"id":22,"level":"C2","skill":"grammar","q":"Choose:\n\nWere it not for your help, I ____ failed.","options":{"A":"will have","B":"would have","C":"have","D":"had"},"answer":"B"},
    {"id":23,"level":"C2","skill":"vocab","q":"To exacerbate a problem means to:","options":{"A":"solve it","B":"make it worse","C":"ignore it","D":"explain it"},"answer":"B"},
    {"id":24,"level":"C2","skill":"reading","q":"The policy was ostensibly about safety, but its real aim was control.\n\nOstensibly implies the safety reason was:","options":{"A":"the true reason","B":"the apparent but not real reason","C":"unimportant","D":"illegal"},"answer":"B"},
]

# تخزين مؤقت في الذاكرة: user_id -> {idx, answers, correct}
SESSIONS = {}


# ═══════════════════════════════════════════════════
#  أدوات DB
# ═══════════════════════════════════════════════════
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _save_placement_result(user_id, score_pct, path, stage_id):
    conn = _db()
    cur = conn.cursor()
    cur.execute("""UPDATE students
                   SET placement_done=1, placement_score=?, placement_path=?,
                       current_stage_id=?
                   WHERE telegram_id=?""",
                (float(score_pct), path, stage_id, user_id))
    conn.commit()
    # إنشاء سجل في stage_progress للمرحلة الأولى
    cur.execute("""INSERT OR IGNORE INTO stage_progress
                   (student_id, stage_id, status, started_at)
                   VALUES (?, ?, 'unlocked', datetime('now'))""",
                (user_id, stage_id))
    conn.commit()
    conn.close()


def _get_first_stage_id(path):
    """يرجع ID المرحلة الأولى حسب المسار (للتوافق مع الكود القديم)."""
    code = "F1" if path == "foundation" else "TR1"
    return _get_first_stage_id_by_code(code)


def _get_first_stage_id_by_code(code):
    """يرجع ID المرحلة حسب الكود (F1, TR1, TR2 ...)."""
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM stages WHERE code=?", (code,))
    row = cur.fetchone()
    conn.close()
    return row["id"] if row else None


# ═══════════════════════════════════════════════════
#  لوحات المفاتيح
# ═══════════════════════════════════════════════════
def kb_question(qid):
    q = QUESTIONS[qid]
    rows = []
    for letter in ["A", "B", "C", "D"]:
        rows.append([InlineKeyboardButton(
            text=f"{letter}) {q['options'][letter]}",
            callback_data=f"pl:ans:{qid}:{letter}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_after_result(path):
    btn_text = "🛠️ ابدأ التأسيس (المرحلة F1)" if path == "foundation" else "🎯 ابدأ TOEFL (المرحلة TR1)"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, callback_data="open_first_stage")],
        [InlineKeyboardButton(text="📋 القائمة الرئيسية", callback_data="back_to_menu")],
    ])


def kb_start_test():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 ابدأ الآن", callback_data="pl:start")],
        [InlineKeyboardButton(text="↩️ لاحقاً", callback_data="back_to_menu")],
    ])


# ═══════════════════════════════════════════════════
#  نقطة الدخول: بدء الاختبار (يُستدعى من start.py)
# ═══════════════════════════════════════════════════
@router.callback_query(F.data == "pl:begin")
async def cb_begin_placement(callback: types.CallbackQuery):
    """يظهر شاشة تعليمات الاختبار."""
    await callback.answer()
    text = (
        "🔬 <b>اختبار تحديد المستوى</b>\n\n"
        "📝 <b>التعليمات:</b>\n"
        "• 24 سؤالاً متدرجة من السهل للصعب (قواعد + مفردات + قراءة)\n"
        "• لا يوجد وقت محدد، خذ راحتك\n"
        "• اختر إجابة واحدة لكل سؤال\n"
        "• لا توجد عودة للسؤال السابق\n\n"
        "🎯 <b>التوجيه التلقائي:</b>\n"
        "• سنحدد مستواك الأوروبي (CEFR) بدقة من A1 إلى C2\n"
        "• ونرسم لك خطة دراسة تناسب مستواك تماماً\n\n"
        "هل أنت مستعد؟ 👇"
    )
    await callback.message.edit_text(text, reply_markup=kb_start_test())


@router.callback_query(F.data == "pl:start")
async def cb_start_test(callback: types.CallbackQuery):
    """يبدأ السؤال الأول."""
    user_id = callback.from_user.id
    SESSIONS[user_id] = {"idx": 0, "answers": [], "correct": 0}
    await _show_question(callback, 0)


async def _show_question(callback, qid):
    q = QUESTIONS[qid]
    skill_ar = {"grammar": "📐 قواعد", "vocab": "📚 مفردات", "reading": "📖 قراءة"}.get(q["skill"], "")
    text = (
        f"<b>السؤال {qid+1} من {len(QUESTIONS)}</b> | {skill_ar}\n\n"
        f"{q['q']}"
    )
    await callback.message.edit_text(text, reply_markup=kb_question(qid))


@router.callback_query(F.data.startswith("pl:ans:"))
async def cb_answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in SESSIONS:
        await callback.answer("⚠️ ابدأ الاختبار من جديد بالأمر /start", show_alert=True)
        return

    try:
        parts = callback.data.split(":")
        qid = int(parts[2])
        chosen = parts[3]
    except (ValueError, IndexError):
        await callback.answer("❌ خطأ في البيانات", show_alert=True)
        return

    session = SESSIONS[user_id]
    q = QUESTIONS[qid]
    is_correct = (chosen == q["answer"])
    session["answers"].append({"qid": qid, "chosen": chosen, "correct": is_correct})
    if is_correct:
        session["correct"] += 1

    await callback.answer("✅ تم التسجيل", show_alert=False)

    # الانتقال للسؤال التالي
    next_idx = qid + 1
    if next_idx < len(QUESTIONS):
        session["idx"] = next_idx
        await _show_question(callback, next_idx)
    else:
        await _finish_test(callback, user_id)


async def _finish_test(callback, user_id):
    # ينهي الاختبار، يحسب مستوى CEFR الحقيقي، يحفظه، ويعرض خطة الدراسة
    session = SESSIONS.get(user_id, {})
    answers = session.get('answers', [])
    levels_order = ['A1','A2','B1','B2','C1','C2']
    per_level = {lv: {'correct':0,'total':0} for lv in levels_order}
    qmap = {q['id']: q for q in QUESTIONS}
    for a in answers:
        q = qmap.get(a['qid'])
        if not q:
            continue
        lv = q.get('level','B1')
        per_level[lv]['total'] += 1
        if a.get('correct'):
            per_level[lv]['correct'] += 1
    cefr = 'A1'
    for lv in levels_order:
        d = per_level[lv]
        if d['total'] > 0 and d['correct'] >= 3:
            cefr = lv
        elif d['total'] > 0 and d['correct'] < 2:
            break
    total_correct = sum(d['correct'] for d in per_level.values())
    total_all = sum(d['total'] for d in per_level.values()) or 1
    score_pct = round((total_correct/total_all)*100, 1)
    if cefr in ('A1','A2'):
        level_emoji = '🔴'; path = 'foundation'; first_stage_code = 'F1'
        path_msg = ('🛠️ <b>خطة دراستك: التأسيس من البداية</b>\\n\\n' + 'ستبدأ من المرحلة الأولى للتأسيس لبناء القواعد والمفردات خطوة بخطوة، ثم تنتقل تدريجياً للقراءة والاستماع.\\n\\n' + '💡 هذا المسار يبني قاعدة قوية تنطلق منها نحو TOEFL.')
    elif cefr == 'B1':
        level_emoji = '🟡'; path = 'foundation'; first_stage_code = 'F3'
        path_msg = ('📘 <b>خطة دراستك: تقوية ثم انطلاق</b>\\n\\n' + 'أساسياتك جيدة! ستبدأ من مراحل التأسيس المتقدمة لسد الثغرات، ثم تنتقل سريعاً إلى القراءة في TOEFL.\\n\\n' + '💪 أنت قريب من الجاهزية الكاملة.')
    elif cefr == 'B2':
        level_emoji = '🟢'; path = 'toefl'; first_stage_code = 'TR1'
        path_msg = ('🎯 <b>خطة دراستك: TOEFL مباشرة</b>\\n\\n' + 'مستواك جيد جداً! ستتخطى التأسيس وتبدأ من القراءة والاستماع في TOEFL مباشرة.\\n\\n' + '🚀 ركز على استراتيجيات الامتحان والكتابة والمحادثة.')
    else:
        level_emoji = '🏆'; path = 'toefl'; first_stage_code = 'TR2'
        path_msg = ('🎯 <b>خطة دراستك: TOEFL متقدم</b>\\n\\n' + 'مستواك ممتاز! ستبدأ مباشرة من القراءة المتوسطة في TOEFL وتركز على النقاط الدقيقة التي ترفع علامتك.\\n\\n' + '🌟 هدفك إتقان التفاصيل وتحقيق درجة عالية.')
    cefr_names = {'A1':'مبتدئ (A1)','A2':'أساسي (A2)','B1':'متوسط (B1)','B2':'فوق المتوسط (B2)','C1':'متقدم (C1)','C2':'إتقان (C2)'}
    level_label = cefr_names.get(cefr, cefr)
    stage_id = _get_first_stage_id_by_code(first_stage_code)
    _save_placement_result(user_id, score_pct, path, stage_id)
    text = ('🎉 <b>اكتمل اختبار تحديد المستوى!</b>\\n\\n' + '📊 <b>مستواك الأوروبي (CEFR):</b>\\n' + level_emoji + ' <b>' + level_label + '</b>\\n\\n' + path_msg + '\\n\\n' + '📍 نقطة البداية: <b>' + first_stage_code + '</b>\\n' + 'اضغط الزر للانطلاق 👇')
    await callback.message.edit_text(text, reply_markup=kb_after_result(path))
    # ===== رسالة دعوة للطالب + تقرير للأدمن =====
    try:
        invite = (
            '🎓 <b>مبروك! حددنا مستواك بدقة.</b>\n\n' +
            'الآن تخيّل أن معلماً ذكياً للتوفل الدولي الجديد يرافقك خطوة بخطوة، يصحّح أخطاءك، ويتابع تقدمك يومياً. 🤖✨\n\n' +
            '🔥 <b>عرض خاص: خصم يصل إلى 70% لفترة محدودة!</b>\n\n' +
            'سجّل الآن وابدأ رحلتك نحو الدرجة التي تحلم بها. 👇'
        )
        admin_username = getattr(settings, 'ADMIN_USERNAME', 'yamen_academy')
        invite_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🎯 سجّل الآن واحصل على خصم 70%', url='https://t.me/' + admin_username)],
        ])
        await callback.message.answer(invite, reply_markup=invite_kb)
    except Exception as e:
        logger.error('invite message failed: %s', e)
    # ===== تقرير للأدمن =====
    try:
        student_name = callback.from_user.full_name or 'طالب'
        student_uname = ('@' + callback.from_user.username) if callback.from_user.username else 'لا يوجد'
        report = (
            '🔔 <b>طالب جديد أنهى اختبار تحديد المستوى</b>\n\n' +
            '👤 الاسم: ' + student_name + '\n' +
            '🆔 المعرّف: <code>' + str(user_id) + '</code>\n' +
            '📎 اليوزر: ' + student_uname + '\n' +
            '📊 المستوى الأوروبي: <b>' + level_label + '</b>\n' +
            '🛤️ المسار المقترح: ' + first_stage_code
        )
        for admin_id in settings.ADMIN_IDS:
            try:
                await callback.bot.send_message(admin_id, report)
            except Exception as ee:
                logger.error('admin report to %s failed: %s', admin_id, ee)
    except Exception as e:
        logger.error('admin report failed: %s', e)
    SESSIONS.pop(user_id, None)


@router.callback_query(F.data == "pl:cancel")
async def cb_cancel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    SESSIONS.pop(user_id, None)
    await callback.answer("تم الإلغاء")
    await callback.message.edit_text(
        "❌ تم إلغاء اختبار تحديد المستوى.\n\nأرسل /start للعودة."
    )


# ═══════════════════════════════════════════════════
#  بعد النتيجة: فتح المرحلة الأولى
# ═══════════════════════════════════════════════════
@router.callback_query(F.data == "open_first_stage")
async def cb_open_first(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = _db()
    cur = conn.cursor()
    cur.execute("""SELECT s.code, s.name_ar, s.description
                   FROM students st JOIN stages s ON s.id = st.current_stage_id
                   WHERE st.telegram_id=?""", (user_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        await callback.answer("⚠️ لم يتم تحديد مرحلتك بعد", show_alert=True)
        return

    await callback.answer()
    text = (
        f"📍 <b>{row['name_ar']}</b> ({row['code']})\n\n"
        f"📝 {row['description']}\n\n"
        "🚀 مرحلتك الأولى مفتوحة!\n"
        "افتح القائمة الرئيسية واختر <b>📚 دروسي</b> للبدء."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 القائمة الرئيسية", callback_data="back_to_menu")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "back_to_menu")
async def cb_back_menu(callback: types.CallbackQuery):
    from handlers.start import get_main_keyboard, _get_student_setup
    user_id = callback.from_user.id
    setup = _get_student_setup(user_id)
    is_paid = bool(setup.get("is_paid", 0))
    target = setup.get("target_score", 0)
    path = setup.get("placement_path") or "toefl"
    path_ar = "🛠️ تأسيس + TOEFL" if path == "foundation" else "🎯 TOEFL مباشر"
    text = (
        f"📋 <b>القائمة الرئيسية</b>\n\n"
        f"🎯 الهدف: <b>{target}</b> | المسار: {path_ar}"
    )
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=get_main_keyboard(is_paid, user_id=user_id))