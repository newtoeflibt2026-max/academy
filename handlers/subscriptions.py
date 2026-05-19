# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import sqlite3, os, logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = Router(name="subscriptions")

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "academy.db")
)
ADMIN_IDS = [
    int(x) for x in os.environ.get("ADMIN_IDS", "5572314718").split(",")
    if x.strip().isdigit()
]


class SubStates(StatesGroup):
    waiting_receipt = State()


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_plans():
    try:
        conn = db()
        rows = conn.execute(
            "SELECT * FROM subscription_plans WHERE is_active=1 ORDER BY price"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"get_plans: {e}")
        return []


@router.callback_query(F.data == "menu_subscriptions")
async def show_plans(cb: CallbackQuery):
    await cb.answer()
    plans = get_plans()

    if not plans:
        kb = InlineKeyboardBuilder()
        kb.button(text="🏠 الرئيسية", callback_data="menu_main")
        await cb.message.answer(
            "💳 لا توجد باقات متاحة حالياً.\nتواصل مع الأدمن: @YamenAdmin",
            reply_markup=kb.as_markup()
        )
        return

    EMOJI = {"M": "📗", "T": "🏆", "E": "⚡", "V": "👑"}

    text = "💳 <b>باقات أكاديمية يامن للتوفل</b>\n\n"
    kb   = InlineKeyboardBuilder()

    for p in plans:
        name  = p.get("plan_name", "باقة")
        price = p.get("price", 0)
        days  = p.get("days", 30)
        speed = p.get("speed", 1)
        desc  = p.get("description", "")
        key   = p.get("plan_key", str(p.get("id")))
        emoji = EMOJI.get(p.get("emoji", ""), "📚")

        text += (
            f"{emoji} <b>{name}</b>\n"
            f"   💰 {price:,} دينار عراقي\n"
            f"   📅 {days} يوم | 📖 {speed} درس/يوم\n"
            f"   📝 {desc}\n\n"
        )
        kb.button(
            text=f"{emoji} اشترك في {name}",
            callback_data=f"sub_select:{key}"
        )

    kb.button(text="🏠 الرئيسية", callback_data="menu_main")
    kb.adjust(1)

    await cb.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("sub_select:"))
async def select_plan(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    plan_key = cb.data.split(":")[1]

    try:
        conn = db()
        plan = conn.execute(
            "SELECT * FROM subscription_plans WHERE plan_key=?", (plan_key,)
        ).fetchone()
        conn.close()
        plan = dict(plan) if plan else None
    except Exception:
        plan = None

    if not plan:
        await cb.message.answer("❌ الباقة غير موجودة")
        return

    await state.update_data(selected_plan=plan_key, plan_name=plan.get("plan_name"))
    await state.set_state(SubStates.waiting_receipt)

    kb = InlineKeyboardBuilder()
    kb.button(text="❌ إلغاء", callback_data="menu_subscriptions")
    kb.adjust(1)

    await cb.message.answer(
        f"💳 <b>تفعيل باقة: {plan.get('plan_name')}</b>\n\n"
        f"💰 السعر: <b>{plan.get('price', 0):,} دينار</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📲 <b>طريقة الدفع:</b>\n"
        f"1. حوّل المبلغ عبر:\n"
        f"   • زين كاش: <code>07XXXXXXXXX</code>\n"
        f"   • آسيا حوالة: <code>07XXXXXXXXX</code>\n\n"
        f"2. أرسل صورة إيصال التحويل هنا\n\n"
        f"⏳ سيتم تفعيل حسابك خلال دقائق بعد المراجعة.",
        reply_markup=kb.as_markup(), parse_mode="HTML"
    )


@router.message(SubStates.waiting_receipt, F.photo | F.document)
async def receive_receipt(message: Message, state: FSMContext):
    data      = await state.get_data()
    plan_key  = data.get("selected_plan", "unknown")
    plan_name = data.get("plan_name", "غير محدد")
    user_id   = str(message.from_user.id)
    username  = message.from_user.username or "بدون يوزرنيم"
    full_name = message.from_user.full_name or ""

    # احفظ الدفعة في DB
    file_id = ""
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id

    try:
        conn = db()
        conn.execute(
            "INSERT INTO payments (telegram_id, plan_key, amount, status, receipt_file_id) "
            "SELECT ?, plan_key, price, 'pending', ? FROM subscription_plans WHERE plan_key=?",
            (user_id, file_id, plan_key)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"save payment: {e}")

    await state.clear()

    # أرسل للأدمن
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    if BOT_TOKEN and ADMIN_IDS:
        try:
            bot = Bot(
                token=BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
            admin_text = (
                f"💳 <b>طلب اشتراك جديد!</b>\n\n"
                f"👤 {full_name} (@{username})\n"
                f"🆔 <code>{user_id}</code>\n"
                f"📦 الباقة: <b>{plan_name}</b>\n\n"
                f"للتفعيل: /activate_{user_id}"
            )
            kb = InlineKeyboardBuilder()
            kb.button(
                text="✅ تفعيل الاشتراك",
                callback_data=f"admin_activate:{user_id}:{plan_key}"
            )
            kb.button(
                text="❌ رفض",
                callback_data=f"admin_reject:{user_id}"
            )
            kb.adjust(1)
            for admin_id in ADMIN_IDS:
                try:
                    if message.photo:
                        await bot.send_photo(
                            admin_id, file_id,
                            caption=admin_text,
                            reply_markup=kb.as_markup()
                        )
                    else:
                        await bot.send_message(
                            admin_id, admin_text,
                            reply_markup=kb.as_markup()
                        )
                except Exception as e:
                    logger.warning(f"notify admin {admin_id}: {e}")
            await bot.session.close()
        except Exception as e:
            logger.error(f"admin notify: {e}")

    await message.answer(
        "✅ <b>تم استلام إيصالك!</b>\n\n"
        "سيتم مراجعة طلبك وتفعيل حسابك خلال دقائق.\n"
        "شكراً لانضمامك لأكاديمية يامن! 🎓",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_activate:"))
async def admin_activate(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ غير مصرح", show_alert=True)
        return

    parts    = cb.data.split(":")
    user_id  = parts[1]
    plan_key = parts[2]

    try:
        conn = db()
        plan = conn.execute(
            "SELECT * FROM subscription_plans WHERE plan_key=?", (plan_key,)
        ).fetchone()

        days     = plan["days"] if plan else 30
        end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        # فعّل الاشتراك
        conn.execute(
            "UPDATE students SET is_paid=1 WHERE telegram_id=?", (user_id,)
        )
        # أضف سجل اشتراك
        conn.execute(
            "INSERT INTO subscriptions "
            "(telegram_id, plan_key, plan_name, start_date, end_date, is_active) "
            "VALUES (?, ?, ?, date('now'), ?, 1)",
            (user_id, plan_key,
             plan["plan_name"] if plan else plan_key,
             end_date)
        )
        # حدّث حالة الدفع
        conn.execute(
            "UPDATE payments SET status='approved' "
            "WHERE telegram_id=? AND status='pending'",
            (user_id,)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"activate: {e}")
        await cb.answer(f"❌ خطأ: {e}", show_alert=True)
        return

    # أبلغ الطالب
    try:
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        bot = Bot(
            token=os.environ.get("BOT_TOKEN", ""),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        await bot.send_message(
            int(user_id),
            f"🎉 <b>تم تفعيل اشتراكك!</b>\n\n"
            f"📦 الباقة: <b>{plan['plan_name'] if plan else plan_key}</b>\n"
            f"📅 تنتهي في: <b>{end_date}</b>\n\n"
            f"ابدأ دروسك الآن بكتابة /start 🚀"
        )
        await bot.session.close()
    except Exception as e:
        logger.warning(f"notify student: {e}")

    await cb.message.edit_caption(
        cb.message.caption + "\n\n✅ <b>تم التفعيل</b>"
        if cb.message.caption else "✅ تم التفعيل"
    )
    await cb.answer("✅ تم تفعيل الاشتراك!")


@router.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ غير مصرح", show_alert=True)
        return

    user_id = cb.data.split(":")[1]
    try:
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        bot = Bot(
            token=os.environ.get("BOT_TOKEN", ""),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        await bot.send_message(
            int(user_id),
            "❌ <b>تم رفض طلب الاشتراك.</b>\n\n"
            "يرجى التواصل مع الأدمن للمزيد من المعلومات: @YamenAdmin"
        )
        await bot.session.close()
    except Exception as e:
        logger.warning(f"reject notify: {e}")

    await cb.answer("تم الرفض")
    await cb.message.reply("❌ تم رفض الطلب")
