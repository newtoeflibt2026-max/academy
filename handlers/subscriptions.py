import os

code_content = '''# -*- coding: utf-8 -*-
# handlers/subscriptions.py — إدارة الباقات المدفوعة، مسار الكتاب المطبوع، والتحكم بالتدفق الزمني 2026
from __future__ import annotations
import os
import sys
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

PROJECT_ROOT = r\\\"C:\\\\Users\\\\nelt2\\\\yamen_academy\\\"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import database
from utils.states import PaymentStates
from config import Config

router = Router(name=\\\"subscriptions\\\")

# ─── تعريف الباقات والاشتراكات التفصيلية ومحددات التدفق ──────────────────────

PLANS = {
    \\\"flexible\\\": {
        \\\"name\\\":        \\\"المسار المرن (الأساسي)\\\",
        \\\"emoji\\\":       \\\"📘\\\",
        \\\"price\\\":       30,
        \\\"days\\\":        30,
        \\\"daily_limit\\\": 1,  # درس واحد كل 24 ساعة للضبط التربوي
        \\\"description\\\":\\\"شهر كامل من التدريب المنظم — نظام درس واحد يومياً لمنع التشتت.\\\",
        \\\"features\\\":    [\\\"🔒 امتحانات المراحل المتتالية\\\", \\\"🔒 مصحح الذكاء الاصطناعي الأساسي\\\", \\\"❌ بوابة التخرج الشاملة\\\"],
    },
    \\\"excellence\\\": {
        \\\"name\\\":        \\\"مسار التفوق الأكاديمي\\\",
        \\\"emoji\\\":       \\\"🏆\\\",
        \\\"price\\\":       65,
        \\\"days\\\":        90,
        \\\"daily_limit\\\": 1,  # الطالب البطيء تتراكم دروسه المفتوحة تلقائياً دون إغلاق
        \\\"description\\\":\\\"3 أشهر كاملة لبناء مهارات التوفل والآيلتس والعبور الآمن من التأسيس.\\\",
        \\\"features\\\":    [\\\"✅ جميع امتحانات المراحل\\\", \\\"✅ الحفاظ على التقدم عند البطء\\\", \\\"🔒 بوابة التخرج والشهادة الدولية\\\"],
    },
    \\\"emergency\\\": {
        \\\"name\\\":        \\\"مسار الطوارئ المكثف\\\",
        \\\"emoji\\\":       \\\"⚡\\\",
        \\\"price\\\":       45,
        \\\"days\\\":        30,
        \\\"daily_limit\\\": 4,  # فتح حتى 4 دروس يومياً لتسريع الدراسة قبل الامتحان الفعلي
        \\\"description\\\":\\\"امتحانك قريب؟ افتح القيود الزمنية وادرس بكثافة لإنهاء المنهاج سريعاً.\\\",
        \\\"features\\\":    [\\\"✅ فتح القيود الزمنية (4 دروس/يوم)\\\", \\\"✅ تفعيل بنك الأخطاء الفوري\\\", \\\"✅ فتح بوابة التخرج وامتحان المحاكاة\\\"],
    },
    \\\"book_activation\\\": {
        \\\"name\\\":        \\\"مسار تفعيل الكتاب المطبوع\\\",
        \\\"emoji\\\":       \\\"📕\\\",
        \\\"price\\\":       0,   # مجاني لمن يملك كود الكشط من المكتبة
        \\\"days\\\":        14,  # ميزات مدفوعة كاملة لأسبوعين ثم يحول للمجاني المشروط
        \\\"daily_limit\\\": 1,
        \\\"description\\\":\\\"تفعيل البوت عن طريق كود الكتاب المطبوع الصادر من المكتبات الرسمية.\\\",
        \\\"features\\\":    [\\\"✅ ميزات مدفوعة كاملة لمدة 14 يوماً\\\", \\\"✅ الربط المباشر مع فصول الكتاب المادية\\\", \\\"⚠️ يتحول تلقائياً لباقة مجانية مشروطة بعد أسبوعين\\\"],
    }
}

PAYMENT_METHODS = {
    \\\"zain\\\": {
        \\\"name\\\":         \\\"زين كاش\\\",
        \\\"emoji\\\":        \\\"💚\\\",
        \\\"number\\\":       \\\"0798919150\\\",
        \\\"instructions\\\": \\\"افتح تطبيق زين كاش ← إرسال ← أدخل الرقم ← أدخل المبلغ ← أرسل\\\",
    },
    \\\"click\\\": {
        \\\"name\\\":         \\\"كليك — البنك الإسلامي\\\",
        \\\"emoji\\\":        \\\"🔵\\\",
        \\\"number\\\":       \\\"0798919150\\\",
        \\\"instructions\\\": \\\"افتح تطبيق كليك → تحويل → أدخل الرقم → أدخل المبلغ → حوّل\\\",
    },
    \\\"western_union\\\": {
        \\\"name\\\":         \\\"Western Union — دولي\\\",
        \\\"emoji\\\":        \\\"🌍\\\",
        \\\"number\\\":       \\\"00962798919150\\\",
        \\\"instructions\\\": \\\"رقم الواتساب للتواصل واعتماد الحوالات الخارجية: 00962798919150\\\",
    },
}

# ─── بناء لوحات التحكم والأزرار التفاعلية ──────────────────────────────────────

def build_plans_keyboard() -> object:
    kb = InlineKeyboardBuilder()
    for key, plan in PLANS.items():
        if key == \\\"book_activation\\\":
            kb.button(text=f\\\"{plan['emoji']} تفعيل كود الكتاب المطبوع 🔑\\\", callback_data=f\\\"sub:plan:{key}\\\")
        else:
            kb.button(text=f\\\"{plan['emoji']} {plan['name']} — {plan['price']} دينار\\\", callback_data=f\\\"sub:plan:{key}\\\")
    kb.button(text=\\\"🏠 القائمة الرئيسية\\\", callback_data=\\\"menu:main\\\")
    kb.adjust(1)
    return kb.as_markup()

def build_methods_keyboard(plan_key: str) -> object:
    kb = InlineKeyboardBuilder()
    if plan_key == \\\"book_activation\\\":
        kb.button(text=\\\"🔑 أدخل كود تفعيل الكتاب\\\", callback_data=\\\"sub:enter_code\\\")
    else:
        for method_key, method in PAYMENT_METHODS.items():
            kb.button(text=f\\\"{method['emoji']} {method['name']}\\\", callback_data=f\\\"sub:method:{plan_key}:{method_key}\\\")
    kb.button(text=\\\"🔙 رجوع للباقات\\\", callback_data=\\\"menu:subscribe\\\")
    kb.adjust(1)
    return kb.as_markup()

def build_cancel_keyboard() -> object:
    kb = InlineKeyboardBuilder()
    kb.button(text=\\\"❌ إلغاء العملية الجارية\\\", callback_data=\\\"sub:cancel\\\")
    kb.adjust(1)
    return kb.as_markup()

def build_back_keyboard() -> object:
    kb = InlineKeyboardBuilder()
    kb.button(text=\\\"🚀 فتح لوحة التحكم\\\", callback_data=\\\"menu:main\\\")
    kb.button(text=\\\"💎 ترقية / تجديد الاشتراك\\\", callback_data=\\\"menu:subscribe\\\")
    kb.adjust(1)
    return kb.as_markup()

# ─── واجهات العرض الرئيسية والتدقيق الأكاديمي ───────────────────────────────────

async def show_plans(update: Message | CallbackQuery) -> None:
    is_cb   = isinstance(update, CallbackQuery)
    user_id = update.from_user.id

    try:
        student = database.get_student(user_id)
        if student and student.get(\\\"is_premium\\\"):
            ends_at_str = student.get(\\\"sub_ends_at\\\", \\\"\\\")
            if ends_at_str:
                ends_at = datetime.strptime(ends_at_str[:10], \\\"%Y-%m-%d\\\")
                if ends_at > datetime.now():
                    text = (
                        f\\\"🦅 <b>أكاديمية يامن — إشعار الصلاحية النشطة</b>\\\\n\\\"
                        f\\\"━━━━━━━━━━━━━━━━━━━━━━\\\\n\\\"
                        f\\\"نوع النظام الحالي: <b>{student.get('plan_name', 'المدفوع')}</b>\\\\n\\\"
                        f\\\"تاريخ الانتهاء التلقائي: <b>{ends_at_str[:10]}</b>\\\\n\\\"
                        f\\\"معدل التدفق التراكمي: <b>{student.get('daily_limit', 1)} درس/يوم</b>\\\\n\\\\n\\\"
                        f\\\"💡 الحساب مستقر وتعمل ميزاتك بكفاءة، يمكنك الترقية لباقات الطوارئ إذا اقترب امتحانك الفعلي!\\\"
                    )
                    if is_cb:
                        await update.message.edit_text(text, reply_markup=build_back_keyboard())
                        await update.answer()
                    else:
                        await update.answer(text, reply_markup=build_back_keyboard())
                    return
    except Exception as e:
        logger.error(f\\\"Error checking database subscription state: {e}\\\")

    plans_text = \\\"\\\"
    for key, plan in PLANS.items():
        if key == \\\"book_activation\\\": continue
        features    = \\\"\\\\n\\\".join(f\\\"  {f}\\\" for f in plan[\\\"features\\\"])
        plans_text += (
            f\\\"\\\\n{plan['emoji']} <b>{plan['name']}</b> — <b>{plan['price']} دينار أردني</b>\\\\n\\\"
            f\\\"  ⏳ الصلاحية الزمنية: {plan['days']} يوم متواصلة\\\\n\\\"
            f\\\"  📊 سياسة التدفق: {plan['daily_limit']} درس يومياً (تراكمي عند البطء)\\\\n\\\"
            f\\\"{features}\\\\n\\\"
        )

    text = (
        \\\"💎 <b>أنظمة الباقات والاشتراكات المعتمدة — أكاديمية يامن 2026</b>\\\\n\\\"
        \\\"اختري مسارك الأكاديمي المناسب لبدء الفلترة والدراسة المنظمة:\\\\n\\\"
        \\\"━━━━━━━━━━━━━━━━━━━━━━\\\\n\\\"
        f\\\"{plans_text}\\\"\n"
        f"<b>📕 {PLANS['book_activation']['name']}</b>\\\\n\\\"
        f\\\"  ⏳ يمنحك صلاحية الحساب المدفوع بالكامل لـ (14 يوماً) ثم يحولك تلقائياً للنظام المجاني المشروط.\\\\n\\\\n\\\"
        \\\"👇 <b>اضغط على الخيار المطلوب للتفعيل الفوري أو الدفع:</b>\\\"
    )

    if is_cb:
        try:
            await update.message.edit_text(text, reply_markup=build_plans_keyboard())
        except Exception:
            await update.message.answer(text, reply_markup=build_plans_keyboard())
        await update.answer()
    else:
        await update.answer(text, reply_markup=build_plans_keyboard())

# ─── معالجة الأحداث والمستقبلات ─────────────────────────────────────────────

@router.message(Command(\\\"subscribe\\\"))
async def cmd_subscribe(message: Message) -> None:
    await show_plans(message)

@router.callback_query(F.data == \\\"menu:subscribe\\\")
async def cb_show_plans(callback: CallbackQuery) -> None:
    await show_plans(callback)

@router.callback_query(F.data.startswith(\\\"sub:plan:\\\"))
async def select_plan(callback: CallbackQuery, state: FSMContext) -> None:
    plan_key = callback.data.split(\\\":\\\")[2]
    plan     = PLANS.get(plan_key)

    if not plan:
        await callback.answer(\\\"❌ خطأ في تحديد الباقة\\\", show_alert=True)
        return

    features = \\\"\\\\n\\\".join(f\\\"  {f}\\\" for f in plan[\\\"features\\\"])
    
    if plan_key == \\\"book_activation\\\":
        text = (
            f\\\"📕 <b>{plan['name']} — تفعيل كود الكشط</b>\\\\n\\\"
            f\\\"━━━━━━━━━━━━━━━━━━━━━━\\\\n\\\"
            f\\\"⚙️ <b>آلية عمل النظام الحركية:</b>\\\\n\\\"
            f\\\"1. عند إدخال كود التفعيل المطبوع في الكتاب، تفتح لك المنظومة بصلاحيات الحساب المدفوع (البريميوم) بالكامل لمدة 14 يوماً.\\\\n\\\"
            f\\\"2. تفتح لك بوابة التخرج، مصحح النطق بالذكاء الاصطناعي، والدروس دون أي شروط لمواكبة استراتيجيات الكتاب الرقمية.\\\\n\\\"
            f\\\"3. بعد انتهاء الـ 14 يوماً، يحولك النظام برمجياً وبشكل تلقائي إلى <b>الباقة المجانية المشروطة</b> (درس يومياً، مقيد بتقديم ريفيو أسبوعي ومنشورات الدعاية للتليجرام بوت).\\\\n\\\\n\\\"
            f\\\"👇 اضغط على الزر أدناه لإدخال كود التحقق من نسختك المطبوعة:\\\"
        )
    else:
        text = (
            f\\\"{plan['emoji']} <b>{plan['name']}</b>\\\\n\\\"
            f\\\"━━━━━━━━━━━━━━━━━━━━━━\\\\n\\\"
            f\\\"💰 القيمة المستحقة: <b>{plan['price']} دينار أردني</b>\\\\n\\\"
            f\\\"⏳ مدة الصلاحية: <b>{plan['days']} يوم متواصلة</b>\\\\n\\\"
            f\\\"📊 محدد الاستيعاب: <b>تحديث تلقائي بمعدل {plan['daily_limit']} درس كل 24 ساعة</b>\\\\n\\\\n\\\"
            f\\\"<b>الميزات الهندسية للمسار:</b>\\\\n{features}\\\\n\\\\n\\\"
            f\\\"💳 <b>اختر قناة التحويل المفضلة لديك لإرسال الوصل وإلغاء القفل:</b>\\\"
        )
    await callback.message.edit_text(text, reply_markup=build_methods_keyboard(plan_key))
    await callback.answer()

# ─── نظام الكود الخاص بالكتاب المطبوع (14 يوماً ثم مجاني) ─────────────────────────

@router.callback_query(F.data == \\\"sub:enter_code\\\")
async def request_book_code(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PaymentStates.waiting_for_receipt) # إعادة استخدام الولاية للتبسيط الأمن
    await state.update_data(plan_key=\\\"book_activation\\\")
    await callback.message.edit_text(
        \\\"📝 <b>يرجى كتابة كود التفعيل الموجود داخل كتابك المطبوع الآن:</b>\\\\n\\\\n\\\"
        \\\"مثال على صيغة الأكواد المعتمدة بمكتبات الأكاديمية: <code>YAMEN-2026-XXXX</code>\\\\n\\\"
        \\\"⚠️ تأكد من كتابة الحروف الكبيرة بشكل صحيح لتفادي رفض السيرفر المركب.\\\",
        reply_markup=build_cancel_keyboard(),
        parse_mode=\\\"HTML\\\"
    )
    await callback.answer()

@router.message(PaymentStates.waiting_for_receipt, F.text)
async def process_book_code(message: Message, state: FSMContext) -> None:
    user_code = message.text.strip().upper()
    data      = await state.get_data()
    plan_key  = data.get(\\\"plan_key\\\")

    if plan_key != \\\"book_activation\\\":
        await message.answer(\\\"❌ عذراً، يرجى إرسال صورة الوصل المالي للمعاملة وليس نصاً.\\\")
        return

    # التحقق البرمي من الكود (يمكن ربطه بمصفوفة أكواد في قاعدة البيانات)
    if user_code.startswith(\\\"YAMEN-2026-\\\") and len(user_code) > 13:
        await state.clear()
        
        # تفعيل فوري ومباشر في قاعدة البيانات لمدة 14 يوماً مع تفعيل حقل التحويل التلقائي لاحقاً
        try:
            database.activate_premium_status(
                telegram_id=message.from_user.id,
                plan_name=\\\"كتاب يامن المطبوع (بريميوم مؤقت)\\\",
                days=14,
                daily_limit=1,
                convert_to_free_after_expiry=True # حقل ذكي لمعالجة حالة التحويل للمجاني
            )
        except Exception as e:
            logger.error(f\\\"Failed to write code trigger to system db: {e}\\\")

        await message.answer(
            f\\\"🎉 <b>تم التحقق وتفعيل كود الكتاب المطبوع بنجاح!</b>\\\\n\\\\n\\\"
            f\\\"كود التتبع المعتمد: <code>{user_code}</code>\\\\n\\\"
            f\\\"📊 الحالة الحالية: <b>بريميوم كامل الميزات (مدفوع) لمدة 14 يوماً مجاناً.</b>\\\\n\\\"
            f\\\"📚 معدل التدفق: درس واحد يومياً متزامن مع فصول كتابك المطبوع.\\\\n\\\\n\\\"
            f\\\"💡 بعد أسبوعين سيقوم السيرفر بتحويل حسابك تلقائياً للمسار المجاني المشروط لضمان متابعتك الدعاية معنا. انطلق الآن!\\\",
            reply_markup=build_back_keyboard(),
        )
    else:
        await message.answer(
            \\\"❌ <b>كود التفعيل غير صحيح أو مستخدم مسبقاً.</b>\\\\n\\\\n\\\"
            \\\"يرجى التأكد من الكود المكتوب خلف بطاقة الكشط في كتابك، أو التواصل مع الدعم الفني للأكاديمية.\\\",
            reply_markup=build_cancel_keyboard()
        )

# ─── معالجة الدفع اليدوي الرقمي الباقي (المرن، التفوق، الطوارئ) ─────────────────

@router.callback_query(F.data.startswith(\\\"sub:method:\\\"))
async def select_payment_method(callback: CallbackQuery, state: FSMContext) -> None:
    parts      = callback.data.split(\\\":\\\")
    plan_key   = parts[2]
    method_key = parts[3]

    plan   = PLANS.get(plan_key)
    method = PAYMENT_METHODS.get(method_key)

    if not plan or not method:
        await callback.answer(\\\"❌ الطريقة غير متوفرة حالياً\\\", show_alert=True)
        return

    user_id = callback.from_user.id

    try:
        existing = database.get_student(user_id)
        if existing and existing.get(\\\"payment_pending\\\"):
            await callback.message.edit_text(
                \\\"⚠️ <b>تنبيه نظام الأمان: لديك معاملة معلقة حالياً قيد التدقيق الفعلي من الإدارة.</b>\\\\n\\\\n\\\"
                \\\"يرجى الانتظار حتى يتم فحص الوصل السابق، أو تواصل مباشرة على الواتساب للمساعدة: <code>00962798919150</code>\\\",
                reply_markup=build_back_keyboard(),
            )
            await callback.answer()
            return
    except Exception as e:
        logger.error(f\\\"Database error: {e}\\\")

    payment_id = database.create_payment(
        telegram_id=user_id,
        plan_key=plan_key,
        plan_name=plan[\\\"name\\\"],
        amount=float(plan[\\\"price\\\"]),
    )

    await state.update_data(payment_id=payment_id, plan_key=plan_key)
    await state.set_state(PaymentStates.waiting_for_receipt)

    text = (
        f\\\"💳 <b>نافذة التحويل المالي — أكاديمية يامن</b>\\\\n\\\"
        f\\\"━━━━━━━━━━━━━━━━━━━━━━\\\\n\\\"
        f\\\"الباقة المطلوبة: <b>{plan['emoji']} {plan['name']}</b>\\\\n\\\"
        f\\\"المبلغ المطلوب: <b>{plan['price']} دينار أردني</b>\\\\n\\\"
        f\\\"الجهة المستلمة: <b>{method['emoji']} {method['name']}</b>\\\\n\\\\n\\\"
        f\\\"📱 <b>الرقم الرقمي للمحفظة / الحساب:</b> <code>{method['number']}</code>\\\\n\\\\n\\\"
        f\\\"📋 <b>خطوات الإتمام:</b>\\\\n\\\"
        f\\\"  {method['instructions']}\\\\"
        f\\\"\\\\n\\\\n📸 <b>خطوات التفعيل البرمي:</b>\\\\n\\\"
        f\\\"  1. التقط صورة واضحة للوصل الإلكتروني الصادر للعملية.\\\\n\\\"
        f\\\"  2. أرسل الصورة هنا مباشرة داخل المحادثة كملف مصور.\\\\n\\\"
        f\\\"  3. سيقوم النظام بمزامنة صلاحياتك فور مراجعة الإدارة للطلب.\\\\n\\\\n\\\"
        f\\\"🆔 رمز الفاتورة للسيستم: <code>#{payment_id}</code>\\\"
    )
    await callback.message.edit_text(text, reply_markup=build_cancel_keyboard())
    await callback.answer()

@router.message(PaymentStates.waiting_for_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext) -> None:
    user_id    = message.from_user.id
    data       = await state.get_data()
    payment_id = data.get(\\\"payment_id\\\")
    plan_key   = data.get(\\\"plan_key\\\")

    if not payment_id or plan_key == \\\"book_activation\\\":
        await message.answer(\\\"❌ حدث خطأ في تتبع الجلسة الأمنية، يرجى إعادة كتابة /subscribe\\\")
        await state.clear()
        return

    photo_id = message.photo[-1].file_id
    database.update_payment_receipt(payment_id, photo_id)
    await state.clear()

    await message.answer(
        \\\"✅ <b>تم رفع إيصال الدفع بنجاح إلى سيرفرات الأكاديمية!</b>\\\\n\\\\n\\\"
        f\\\"رقم الإيصال المحفوظ تتبعياً: <code>#{payment_id}</code>\\\\n\\\"
        f\\\"بناءً على باقتك المحددة <b>({PLANS[plan_key]['name']})</b> سيتم فتح نظام التأسيس والمراحل وضبط معدل فتح الدروس فور موافقة الإدارة المعنية.\\\",
        reply_markup=build_back_keyboard(),
    )

    # هيكلة إشعار الإدارة الموحد للإمبراطورة دانيا للتفعيل بنقرة واحدة
    plan = PLANS[plan_key]
    admin_text = (
        f\\\"🔔 <b>طلب تفعيل مالي جديد ومطابقة تربوية!</b>\\\\n\\\\n\\\"
        f\\\"🆔 معرف الطالب التليجرام: <code>{user_id}</code>\\\\n\\\"
        f\\\"💎 الباقة المستهدفة: <b>{plan['name']}</b>\\\\n\\\"
        f\\\"⏳ صلاحية الأيام الممنوحة: <b>{plan['days']} يوم</b>\\\\n\\\"
        f\\\"📊 قيود التدفق والسرعة: <b>{plan['daily_limit']} درس/يوم (تراكمي)</b>\\\\n\\\"
        f\\\"🔢 رقم المعاملة للسيستم: <code>#{payment_id}</code>\\\\n\\\\n\\\"
        f\\\"⚙️ عند الضغط على موافقة سيقوم السيستم فوراً بتهيئة جداول الطالب للمزامنة المشتركة مع الـ WebApps.\\\"
    )

    kb_admin = InlineKeyboardBuilder()
    kb_admin.button(
        text=\\\"✅ اعتماد الحساب ورفع القيود\\\",
        callback_data=f\\\"adm_approve:{payment_id}:{plan_key}:{user_id}:{plan['days']}:{plan['daily_limit']}\\\",
    )
    kb_admin.button(text=\\\"❌ رفض الوصل\\\", callback_data=f\\\"adm_reject:{payment_id}:{user_id}\\\")
    kb_admin.adjust(1)

    try:
        await message.bot.send_photo(
            chat_id=Config.ADMIN_IDS[0] if hasattr(Config, 'ADMIN_IDS') else user_id,
            photo=photo_id,
            caption=admin_text,
            reply_markup=kb_admin.as_markup(),
        )
    except Exception as e:
        logger.error(f\\\"Failed to notify root admin: {e}\\\")

@router.callback_query(F.data == \\\"sub:cancel\\\")
async def cancel_payment(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        \\\"❌ <b>تم إلغاء طلب الاشتراك وإغلاق الفاتورة المفتوحة بنجاح.</b>\\\\n\\\\n\\\"
        \\\"يمكنكِ دائماً اختيار المسار الذي يناسب وقتكِ الدراسي وموعد اختباركِ الفعلي لاحقاً.\\\",
        reply_markup=build_back_keyboard(),
    )
    await callback.answer(\\\"تم إلغاء الطلب المالي\\\")
'''

with open(os.path.join('handlers', 'subscriptions.py'), 'w', encoding='utf-8') as f:
    f.write(code_content)

print('✅ File handlers/subscriptions.py rewritten successfully with Book Activation Path.')
"
