# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.states import PaymentStates
from bot_database import create_payment, get_student
from config import settings
from loguru import logger

router = Router(name="subscriptions")

PLANS = {
    "flex_30": {
        "name": "المسار المرن 30 يوم",
        "price": 25,
        "days": 30,
        "speed": 1,
        "desc": "درس واحد يومياً - مناسب للمبتدئين",
        "emoji": "🌱"
    },
    "excellence_90": {
        "name": "مسار التفوق 90 يوم",
        "price": 60,
        "days": 90,
        "speed": 1,
        "desc": "درس يومي + تتبع كامل للتقدم",
        "emoji": "🎯"
    },
    "emergency_30": {
        "name": "مسار الطوارئ المكثف",
        "price": 80,
        "days": 30,
        "speed": 4,
        "desc": "حتى 4 دروس يومياً - للمتقدمين قبل الامتحان",
        "emoji": "🚀"
    },
    "vip_20h": {
        "name": "باقة VIP 20 ساعة برايفت",
        "price": 400,
        "days": 90,
        "speed": 4,
        "desc": "20 ساعة تدريب خاص + مسار الطوارئ مجاناً",
        "emoji": "👑"
    },
}

def plans_keyboard():
    kb = InlineKeyboardBuilder()
    for key, plan in PLANS.items():
        kb.button(
            text=f"{plan['emoji']} {plan['name']} - {plan['price']} دينار",
            callback_data=f"buy:{key}"
        )
    kb.button(text="📖 أدخل كود الكتاب", callback_data="book:code")
    kb.button(text="🏠 رجوع", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()

async def show_plans(cb: CallbackQuery):
    await cb.message.edit_text(
        "💎 <b>باقات أكاديمية يامن</b>\n\n"
        "🌱 <b>المسار المرن 30 يوم</b> — 25 دينار\n"
        "    درس واحد يومياً، مثالي للانطلاق\n\n"
        "🎯 <b>مسار التفوق 90 يوم</b> — 60 دينار\n"
        "    المسار الأكاديمي الكامل من الصفر للاحتراف\n\n"
        "🚀 <b>مسار الطوارئ المكثف</b> — 80 دينار\n"
        "    4 دروس يومياً للمتقدمين قبل الامتحان\n\n"
        "👑 <b>VIP 20 ساعة برايفت</b> — 400 دينار\n"
        "    20 ساعة تدريب خاص + مسار الطوارئ مجاناً\n\n"
        "📖 <b>كتاب يامن؟</b> أدخل الكود للتفعيل الفوري!",
        reply_markup=plans_keyboard()
    )
    await cb.answer()

@router.callback_query(F.data.startswith("buy:"))
async def buy_plan(cb: CallbackQuery, state: FSMContext):
    plan_key = cb.data.split(":")[1]
    plan = PLANS.get(plan_key)
    if not plan:
        await cb.answer("باقة غير موجودة!", show_alert=True)
        return

    await state.update_data(plan_key=plan_key, plan=plan)

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ تأكيد الدفع وإرسال الإيصال", callback_data=f"confirm_pay:{plan_key}")
    kb.button(text="🔙 رجوع للباقات", callback_data="menu:subscribe")
    kb.adjust(1)

    await cb.message.edit_text(
        f"{plan['emoji']} <b>{plan['name']}</b>\n\n"
        f"💰 السعر: <b>{plan['price']} دينار أردني</b>\n"
        f"📅 المدة: <b>{plan['days']} يوم</b>\n"
        f"📖 {plan['desc']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💳 <b>طريقة الدفع:</b>\n"
        "ارسل المبلغ عبر:\n"
        "• <b>CliQ</b>: yamen_academy\n"
        "• <b>زين كاش</b>: 0791234567\n\n"
        "بعد الدفع اضغط <b>تأكيد</b> وأرسل صورة الإيصال 👇",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data.startswith("confirm_pay:"))
async def confirm_pay(cb: CallbackQuery, state: FSMContext):
    plan_key = cb.data.split(":")[1]
    plan = PLANS.get(plan_key)
    await state.update_data(plan_key=plan_key, plan=plan)

    kb = InlineKeyboardBuilder()
    kb.button(text="❌ إلغاء", callback_data="menu:subscribe")

    await cb.message.edit_text(
        "📸 <b>أرسل صورة إيصال الدفع الآن</b>\n\n"
        "سيتم مراجعتها وتفعيل حسابك خلال دقائق ✅",
        reply_markup=kb.as_markup()
    )
    await state.set_state(PaymentStates.waiting_for_receipt)
    await cb.answer()

@router.message(PaymentStates.waiting_for_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    plan_key = data.get("plan_key", "unknown")
    plan = data.get("plan", PLANS.get(plan_key, {}))
    plan_name = plan.get("name", plan_key)
    amount = plan.get("price", 0)
    days = plan.get("days", 30)

    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id

    pid = create_payment(
        telegram_id=user_id,
        plan_key=plan_key,
        plan_name=plan_name,
        amount=amount,
        receipt_photo_id=photo_id
    )

    kb = InlineKeyboardBuilder()
    kb.button(text=f"✅ تفعيل {days}يوم", callback_data=f"adm_approve:{pid}:{plan_key}:{plan_name}:{user_id}:{days}")
    kb.button(text="❌ رفض", callback_data=f"adm_reject:{pid}:{user_id}")
    kb.adjust(2)

    for admin_id in settings.ADMIN_IDS:
        try:
            student = get_student(user_id)
            name = student.get("name", "غير معروف") if student else "غير معروف"
            await message.bot.send_photo(
                chat_id=admin_id,
                photo=photo_id,
                caption=(
                    f"💰 <b>طلب اشتراك جديد</b>\n\n"
                    f"👤 الاسم: <b>{name}</b>\n"
                    f"🆔 ID: <code>{user_id}</code>\n"
                    f"📦 الباقة: <b>{plan_name}</b>\n"
                    f"💵 المبلغ: <b>{amount} دينار</b>\n"
                    f"📅 المدة: <b>{days} يوم</b>\n"
                    f"🔢 رقم الطلب: <b>#{pid}</b>"
                ),
                reply_markup=kb.as_markup()
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

    await state.clear()

    kb2 = InlineKeyboardBuilder()
    kb2.button(text="🏠 الرئيسية", callback_data="menu:main")
    await message.answer(
        "✅ <b>تم استلام إيصالك!</b>\n\n"
        "سيتم مراجعة الدفع وتفعيل حسابك خلال دقائق 🎉\n"
        "ستصلك رسالة تأكيد فور التفعيل.",
        reply_markup=kb2.as_markup()
    )

@router.callback_query(F.data == "book:code")
async def book_code_prompt(cb: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ إلغاء", callback_data="menu:subscribe")
    await cb.message.edit_text(
        "📖 <b>تفعيل كتاب يامن</b>\n\n"
        "أرسل كود التفعيل الموجود في الكتاب المطبوع:",
        reply_markup=kb.as_markup()
    )
    await state.set_state(PaymentStates.waiting_for_receipt)
    await cb.answer()
