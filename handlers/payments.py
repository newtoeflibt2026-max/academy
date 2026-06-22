# -*- coding: utf-8 -*-
"""
handlers/payments.py - نظام الدفع الكامل
"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import logging, os
from datetime import datetime, timedelta
from db import get_db

logger = logging.getLogger(__name__)
router = Router(name="payments")

ADMIN_IDS = [
    int(x.strip()) for x in os.environ.get("ADMIN_IDS", "5572314718").split(",")
    if x.strip().isdigit()
]
BOT_TOKEN  = os.environ.get("BOT_TOKEN", "")
ADMIN_PHONE = "0798919150"
CURRENCY    = "د.أ"   # دينار أردني


class PayStates(StatesGroup):
    waiting_receipt = State()


# ══ عرض الباقات ══════════════════════════════
@router.callback_query(F.data == "menu_subscriptions")
async def show_plans(cb: CallbackQuery):
    await cb.answer()
    conn = get_db()
    try:
        plans = [dict(r) for r in
                 conn.execute("SELECT * FROM subscription_plans WHERE is_active=1 ORDER BY price").fetchall()]
    finally:
        conn.close()

    if not plans:
        kb = InlineKeyboardBuilder()
        kb.button(text="🏠 الرئيسية", callback_data="menu_main")
        await cb.message.answer("لا توجد باقات متاحة حالياً.", reply_markup=kb.as_markup())
        return

    text = "💳 <b>باقات أكاديمية يامن للتوفل</b>\n\n"
    kb   = InlineKeyboardBuilder()

    for p in plans:
        price   = float(p.get("price", 0))
        days    = p.get("duration_days", 30)
        name_ar = p.get("name_ar", p.get("name", "باقة"))
        desc    = p.get("description", "")
        pid     = p.get("id")
        star    = "⭐ " if p.get("is_featured") else ""
        price_text = "مجاني 🎁" if price == 0 else f"{price:,.0f} {CURRENCY}"

        text += f"{star}<b>{name_ar}</b>\n"
        text += f"   💰 {price_text} | 📅 {days} يوم\n"
        if desc:
            text += f"   📝 {desc}\n"
        text += "\n"

        kb.button(
            text=f"{star}اشترك — {name_ar} ({price_text})",
            callback_data=f"sub_select:{pid}"
        )

    kb.button(text="🏠 الرئيسية", callback_data="menu_main")
    kb.adjust(1)
    await cb.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


# ══ اختيار باقة ══════════════════════════════
@router.callback_query(F.data.startswith("sub_select:"))
async def select_plan(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    pid = int(cb.data.split(":")[1])

    conn = get_db()
    try:
        row  = conn.execute("SELECT * FROM subscription_plans WHERE id=?", (pid,)).fetchone()
        plan = dict(row) if row else None
    finally:
        conn.close()

    if not plan:
        await cb.message.answer("❌ الباقة غير موجودة.")
        return

    price   = float(plan.get("price", 0))
    name_ar = plan.get("name_ar", "باقة")
    uid     = cb.from_user.id

    # ── باقة مجانية: تفعيل فوري ──────────────
    if price == 0:
        conn = get_db()
        try:
            conn.execute(
            """UPDATE students SET is_paid=1, is_active=1, subscription_type='مجانية', package_end=date('now','+7 days') WHERE telegram_id=?""", (uid,))
            conn.execute(
                """INSERT OR IGNORE INTO payments
                   (user_id,plan_id,amount,currency,status,notes)
                   VALUES (?,?,0,'JOD','verified','باقة مجانية - تفعيل تلقائي')""",
                (uid, pid))
            conn.commit()
        finally:
            conn.close()

        kb = InlineKeyboardBuilder()
        kb.button(text="🚀 ابدأ التعلم الآن", callback_data="menu_main")
        await cb.message.answer(
            f"🎁 <b>تم تفعيل {name_ar} مجاناً!</b>\n\n"
            f"✅ حسابك نشط — ابدأ رحلتك الآن!",
            reply_markup=kb.as_markup(), parse_mode="HTML"
        )
        return

    # ── باقة مدفوعة: طلب الوصل ────────────────
    await state.update_data(plan_id=pid, plan_name=name_ar, plan_price=price)
    await state.set_state(PayStates.waiting_receipt)

    kb = InlineKeyboardBuilder()
    kb.button(text="❌ إلغاء", callback_data="menu_subscriptions")
    kb.adjust(1)

    await cb.message.answer(
        f"💳 <b>تفعيل باقة: {name_ar}</b>\n\n"
        f"💰 السعر: <b>{price:,.0f} {CURRENCY}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📲 <b>طريقة الدفع:</b>\n\n"
        f"حوّل المبلغ عبر CliQ أو تحويل بنكي إلى:\n"
        f"📱 <code>{ADMIN_PHONE}</code>\n\n"
        f"📸 <b>بعد التحويل أرسل صورة الإيصال هنا مباشرة</b>\n\n"
        f"⏳ سيتم تفعيل حسابك خلال دقائق بعد مراجعة الأدمن.",
        reply_markup=kb.as_markup(), parse_mode="HTML"
    )


# ══ استلام الوصل ═════════════════════════════
@router.message(PayStates.waiting_receipt, F.photo | F.document)
async def receive_receipt(message: Message, state: FSMContext):
    data       = await state.get_data()
    plan_id    = data.get("plan_id", 1)
    plan_name  = data.get("plan_name", "غير محدد")
    plan_price = data.get("plan_price", 0)
    uid        = message.from_user.id
    username   = message.from_user.username or "بدون يوزرنيم"
    full_name  = message.from_user.full_name or ""

    file_id = ""
    is_photo = bool(message.photo)
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id

    # حفظ الدفعة
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO payments
               (user_id,plan_id,amount,currency,status,proof_file,notes)
               VALUES (?,?,?,'JOD','pending',?,?)""",
            (uid, plan_id, plan_price, file_id, f"{full_name} @{username}"))
        payment_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    await state.clear()

    # إشعار الأدمن
    if BOT_TOKEN and ADMIN_IDS:
        try:
            bot = Bot(token=BOT_TOKEN,
                      default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            admin_text = (
                f"💳 <b>طلب اشتراك جديد!</b>\n\n"
                f"👤 {full_name} (@{username})\n"
                f"🆔 <code>{uid}</code>\n"
                f"📦 الباقة: <b>{plan_name}</b>\n"
                f"💰 المبلغ: <b>{plan_price:,.0f} {CURRENCY}</b>\n"
                f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            kb = InlineKeyboardBuilder()
            kb.button(text="✅ موافقة وتفعيل",
                      callback_data=f"admin_approve:{uid}:{plan_id}:{payment_id}")
            kb.button(text="❌ رفض",
                      callback_data=f"admin_reject:{uid}:{payment_id}")
            kb.adjust(1)

            for admin_id in ADMIN_IDS:
                try:
                    if is_photo:
                        await bot.send_photo(
                            admin_id, file_id,
                            caption=admin_text,
                            reply_markup=kb.as_markup()
                        )
                    else:
                        await bot.send_document(
                            admin_id, file_id,
                            caption=admin_text,
                            reply_markup=kb.as_markup()
                        )
                except Exception as e:
                    logger.warning(f"notify admin {admin_id}: {e}")
            await bot.session.close()
        except Exception as e:
            logger.error(f"admin notify error: {e}")

    # رسالة للطالب
    await message.answer(
        "✅ <b>تم استلام إيصالك!</b>\n\n"
        "🔍 جاري مراجعة طلبك من قبل الأدمن.\n"
        "📲 ستصلك رسالة تأكيد خلال دقائق قليلة.\n\n"
        f"شكراً لانضمامك لأكاديمية يامن! 🎓",
        parse_mode="HTML"
    )


# ══ موافقة الأدمن ════════════════════════════
@router.callback_query(F.data.startswith("admin_approve:"))
async def admin_approve(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ غير مصرح", show_alert=True)
        return

    parts      = cb.data.split(":")
    uid        = int(parts[1])
    plan_id    = int(parts[2])
    payment_id = int(parts[3])

    conn = get_db()
    try:
        plan = conn.execute(
            "SELECT * FROM subscription_plans WHERE id=?", (plan_id,)).fetchone()
        plan = dict(plan) if plan else {}
        days     = plan.get("duration_days", 30)
        name_ar  = plan.get("name_ar", "الباقة")
        end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        conn.execute(
            "UPDATE students SET is_paid=1, is_active=1, subscription_type=?, package_end=? WHERE telegram_id=?", (name_ar, end_date, uid))
        conn.execute(
            "UPDATE payments SET status='verified', verified_at=CURRENT_TIMESTAMP WHERE id=?",
            (payment_id,))
        conn.commit()
    finally:
        conn.close()

    # إبلاغ الطالب
    try:
        bot = Bot(token=BOT_TOKEN,
                  default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        await bot.send_message(
            uid,
            f"🎉 <b>تم تفعيل اشتراكك!</b>\n\n"
            f"📦 الباقة: <b>{name_ar}</b>\n"
            f"📅 تنتهي في: <b>{end_date}</b>\n\n"
            f"✨ جميع الأقسام مفتوحة الآن!\n"
            f"اكتب /start لبدء التعلم 🚀"
        )
        await bot.session.close()
    except Exception as e:
        logger.warning(f"notify student: {e}")

    # تحديث رسالة الأدمن + إظهار زر إلغاء الاشتراك
    try:
        new_caption = (cb.message.caption or "") + \
                      f"\n\n✅ <b>تم التفعيل بواسطة {cb.from_user.full_name}</b>"
        _cancel_kb = InlineKeyboardBuilder()
        _cancel_kb.button(text="🚫 إلغاء الاشتراك",
                          callback_data=f"admin_cancel:{uid}:{payment_id}")
        _cancel_kb.adjust(1)
        if cb.message.caption:
            await cb.message.edit_caption(caption=new_caption, parse_mode="HTML",
                                          reply_markup=_cancel_kb.as_markup())
        else:
            await cb.message.edit_text(new_caption, parse_mode="HTML",
                                       reply_markup=_cancel_kb.as_markup())
    except Exception:
        pass

    await cb.answer("✅ تم تفعيل الاشتراك وإبلاغ الطالب!")


# ══ إلغاء الاشتراك (بعد الموافقة) ═════════════
@router.callback_query(F.data.startswith("admin_cancel:"))
async def admin_cancel(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ غير مصرح", show_alert=True)
        return

    parts      = cb.data.split(":")
    uid        = int(parts[1])
    payment_id = int(parts[2]) if len(parts) > 2 else 0

    # إلغاء عبر دالة النظام الموحدة + ضبط is_active=0
    try:
        from bot_database import deactivate_paid
        deactivate_paid(uid)
    except Exception as e:
        logger.warning(f"deactivate_paid: {e}")

    conn = get_db()
    try:
        conn.execute(
            "UPDATE students SET is_paid=0, is_active=0 WHERE telegram_id=?", (uid,))
        if payment_id:
            conn.execute(
                "UPDATE payments SET status='cancelled' WHERE id=?", (payment_id,))
        conn.commit()
    finally:
        conn.close()

    # إبلاغ الطالب
    try:
        bot = Bot(token=BOT_TOKEN,
                  default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        await bot.send_message(
            uid,
            "⚠️ <b>تم إلغاء اشتراكك.</b>\n\n"
            "للاستفسار يرجى التواصل مع الأدمن.\n"
            f"📱 {ADMIN_PHONE}"
        )
        await bot.session.close()
    except Exception as e:
        logger.warning(f"cancel notify: {e}")

    # تحديث رسالة الأدمن
    try:
        new_text = (cb.message.caption or cb.message.text or "") + \
                   f"\n\n🚫 <b>تم إلغاء الاشتراك بواسطة {cb.from_user.full_name}</b>"
        if cb.message.caption:
            await cb.message.edit_caption(caption=new_text, parse_mode="HTML")
        else:
            await cb.message.edit_text(new_text, parse_mode="HTML")
    except Exception:
        pass

    await cb.answer("🚫 تم إلغاء الاشتراك وإبلاغ الطالب!")


# ══ رفض الأدمن ═══════════════════════════════
@router.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ غير مصرح", show_alert=True)
        return

    parts      = cb.data.split(":")
    uid        = int(parts[1])
    payment_id = int(parts[2])

    conn = get_db()
    try:
        conn.execute(
            "UPDATE payments SET status='rejected' WHERE id=?", (payment_id,))
        conn.commit()
    finally:
        conn.close()

    try:
        bot = Bot(token=BOT_TOKEN,
                  default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        await bot.send_message(
            uid,
            "❌ <b>تم رفض طلب الاشتراك.</b>\n\n"
            "يرجى التواصل مع الأدمن للمزيد من المعلومات.\n"
            f"📱 {ADMIN_PHONE}"
        )
        await bot.session.close()
    except Exception as e:
        logger.warning(f"reject notify: {e}")

    try:
        new_text = (cb.message.caption or cb.message.text or "") + \
                   f"\n\n❌ <b>تم الرفض بواسطة {cb.from_user.full_name}</b>"
        if cb.message.caption:
            await cb.message.edit_caption(caption=new_text, parse_mode="HTML")
        else:
            await cb.message.edit_text(new_text, parse_mode="HTML")
    except Exception:
        pass

    await cb.answer("تم الرفض وإبلاغ الطالب.")
