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
from subscription_helpers import activate_subscription

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
        row  = conn.execute("SELECT * FROM subscription_plans WHERE id=? AND is_active=1", (pid,)).fetchone()
        plan = dict(row) if row else None
    finally:
        conn.close()

    if not plan:
        await cb.message.answer("❌ الباقة غير موجودة أو معطّلة.")
        return

    price        = float(plan.get("price", 0))
    name_ar      = plan.get("name_ar", "باقة")
    plan_name    = plan.get("name", "")
    section_code = plan.get("section_code", "")
    needs_promo  = int(plan.get("requires_promo_task", 0))
    uid          = cb.from_user.id

    # ── باقة مجانية: تتطلب موافقة الأدمن ──────────────────
    if price == 0 or needs_promo:
        # سجّل طلب pending
        conn = get_db()
        try:
            # تحقق إن الطالب لم يستخدم المجانية سابقاً
            row = conn.execute(
                "SELECT free_plan_used FROM students WHERE telegram_id=?", (uid,)
            ).fetchone()
            if row and row[0]:
                await cb.message.answer(
                    "⚠️ <b>لقد استخدمت الباقة المجانية سابقاً.</b>\n\n"
                    "الباقة المجانية متاحة مرة واحدة فقط لكل حساب.\n"
                    "اختر باقة مدفوعة للاستمرار 👇",
                    parse_mode="HTML"
                )
                return

            # سجّل طلب
            conn.execute("""
                UPDATE students
                SET promo_task_status='pending'
                WHERE telegram_id=?
            """, (uid,))
            conn.execute("""
                INSERT INTO payments (user_id, telegram_id, plan_id, plan_name, amount, currency, status, notes, created_at)
                VALUES (?, ?, ?, ?, 0, 'JOD', 'pending_free', ?, CURRENT_TIMESTAMP)
            """, (uid, uid, pid, name_ar, "طلب باقة مجانية - بانتظار موافقة الأدمن"))
            payment_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()
        finally:
            conn.close()

        # أرسل رسالة للطالب
        await cb.message.answer(
            f"⏳ <b>تم استلام طلبك للباقة المجانية</b>\n\n"
            f"📦 الباقة: <b>{name_ar}</b>\n\n"
            "🔍 سيراجع الأدمن طلبك ويوافق عليه قريباً.\n"
            "📲 ستصلك رسالة تأكيد فور التفعيل.\n\n"
            "💡 <i>تذكير: الباقة المجانية تتطلب إنجاز مهمة دعائية بسيطة.</i>",
            parse_mode="HTML"
        )

        # إشعار الأدمن
        try:
            bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            kb_admin = InlineKeyboardBuilder()
            kb_admin.button(text="✅ موافقة وتفعيل", callback_data=f"admin_approve_free:{uid}:{pid}:{payment_id}")
            kb_admin.button(text="❌ رفض", callback_data=f"admin_reject:{uid}:{payment_id}")
            kb_admin.adjust(2)
            user_name = cb.from_user.full_name or ""
            user_un   = f"@{cb.from_user.username}" if cb.from_user.username else "(no username)"
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"🆓 <b>طلب باقة مجانية جديد</b>\n\n"
                        f"👤 الطالب: <b>{user_name}</b>\n"
                        f"🆔 ID: <code>{uid}</code>\n"
                        f"💬 Username: {user_un}\n"
                        f"📦 الباقة: <b>{name_ar}</b>\n"
                        f"⏰ التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"اختر الإجراء:",
                        reply_markup=kb_admin.as_markup()
                    )
                except Exception as e:
                    logger.warning(f"notify admin {admin_id}: {e}")
            await bot.session.close()
        except Exception as e:
            logger.warning(f"admin notification failed: {e}")
        return

    # ── باقة مدفوعة: طلب الوصل ─────────────────────────────
    await state.update_data(plan_id=pid, plan_name=name_ar, plan_price=price)
    await state.set_state(PayStates.waiting_receipt)

    kb = InlineKeyboardBuilder()
    kb.button(text="❌ إلغاء", callback_data="menu_subscriptions")
    kb.adjust(1)

    await cb.message.answer(
        f"💳 <b>تفعيل باقة: {name_ar}</b>\n\n"
        f"💰 السعر: <b>{price:,.0f} {CURRENCY}</b>\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📲 <b>طريقة الدفع:</b>\n\n"
        f"حوّل المبلغ عبر CliQ أو تحويل بنكي إلى:\n"
        f"📱 <code>0797702930</code>\n\n"
        f"ثم أرسل صورة الإيصال هنا 👇",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
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

    # اجلب اسم الباقة (name الإنجليزي) من plan_id
    conn = get_db()
    try:
        plan_row = conn.execute(
            "SELECT name, name_ar, duration_days FROM subscription_plans WHERE id=?",
            (plan_id,)
        ).fetchone()
        plan_dict = dict(plan_row) if plan_row else {}
    finally:
        conn.close()

    plan_name = plan_dict.get("name", "")
    name_ar   = plan_dict.get("name_ar", "الباقة")

    if not plan_name:
        await cb.answer("❌ الباقة غير موجودة", show_alert=True)
        return

    # استخدم activate_subscription المركزية
    ok, result = activate_subscription(uid, plan_name)
    if not ok:
        await cb.answer(f"❌ خطأ: {result}", show_alert=True)
        return

    # حدّث حالة الإيصال
    conn = get_db()
    try:
        conn.execute(
            "UPDATE payments SET status='verified', verified_at=CURRENT_TIMESTAMP WHERE id=?",
            (payment_id,)
        )
        conn.commit()
    finally:
        conn.close()

    end_date = result.get("package_end") if isinstance(result, dict) else None
    if not end_date:
        days = plan_dict.get("duration_days", 30)
        end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    # ═══ إبلاغ الطالب + إرسال القائمة الكاملة فوراً ═══
    try:
        from handlers.start import get_main_keyboard
    except Exception:
        get_main_keyboard = None
        get_setting = None

    try:
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

        # رسالة التهنئة
        await bot.send_message(
            uid,
            f"🎉 <b>تم تفعيل اشتراكك!</b>\n\n"
            f"📦 الباقة: <b>{name_ar}</b>\n"
            f"📅 تنتهي في: <b>{str(end_date)[:10]}</b>\n\n"
            f"✨ <b>الأقسام مفتوحة الآن:</b>"
        )

        # أرسل القائمة الرئيسية فوراً (بدون الحاجة لـ /start)
        if get_main_keyboard:
            try:
                kb = get_main_keyboard(is_paid=True, user_id=uid)
                await bot.send_message(
                    uid,
                    "👇 اختر القسم الذي تريد البدء به:",
                    reply_markup=kb
                )
            except Exception as e:
                logger.warning(f"send main menu failed: {e}")
                # fallback
                await bot.send_message(uid, "اكتب /start لرؤية الأقسام 🚀")
        else:
            await bot.send_message(uid, "اكتب /start لرؤية الأقسام 🚀")

        await bot.session.close()
    except Exception as e:
        logger.warning(f"notify student failed: {e}")

    # تحديث رسالة الأدمن
    try:
        new_caption = (cb.message.caption or cb.message.text or "") + \
                      f"\n\n✅ <b>تم التفعيل بواسطة {cb.from_user.full_name}</b>"
        if cb.message.caption:
            await cb.message.edit_caption(caption=new_caption, parse_mode="HTML")
        else:
            await cb.message.edit_text(new_caption, parse_mode="HTML")
    except Exception:
        pass

    await cb.answer("✅ تم تفعيل الاشتراك وإبلاغ الطالب!")


# ══ موافقة الأدمن على الباقة المجانية ════════════════
@router.callback_query(F.data.startswith("admin_approve_free:"))
async def admin_approve_free(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ غير مصرح", show_alert=True)
        return

    parts      = cb.data.split(":")
    uid        = int(parts[1])
    plan_id    = int(parts[2])
    payment_id = int(parts[3])

    # اجلب الباقة
    conn = get_db()
    try:
        plan_row = conn.execute(
            "SELECT name, name_ar FROM subscription_plans WHERE id=?", (plan_id,)
        ).fetchone()
        plan_dict = dict(plan_row) if plan_row else {}
    finally:
        conn.close()

    plan_name = plan_dict.get("name", "free_15d")
    name_ar   = plan_dict.get("name_ar", "🆓 الباقة المجانية")

    # فعّل + علّم promo_task_status=approved + free_plan_used=1
    ok, result = activate_subscription(uid, plan_name)
    if not ok:
        await cb.answer(f"❌ خطأ: {result}", show_alert=True)
        return

    conn = get_db()
    try:
        conn.execute("""
            UPDATE students
            SET promo_task_status='approved', free_plan_used=1, free_plan_used_at=CURRENT_TIMESTAMP
            WHERE telegram_id=?
        """, (uid,))
        conn.execute(
            "UPDATE payments SET status='verified', verified_at=CURRENT_TIMESTAMP WHERE id=?",
            (payment_id,)
        )
        conn.commit()
    finally:
        conn.close()

    # ═══ إبلاغ الطالب + قائمة فورية ═══
    try:
        from handlers.start import get_main_keyboard
    except Exception:
        get_main_keyboard = None

    try:
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        await bot.send_message(
            uid,
            f"🎉 <b>تم تفعيل باقتك المجانية!</b>\n\n"
            f"📦 الباقة: <b>{name_ar}</b>\n"
            f"📅 المدة: <b>15 يوم</b> (درس واحد يومياً)\n\n"
            f"💡 سيتم تذكيرك بإنجاز المهمة الدعائية لاحقاً."
        )
        if get_main_keyboard:
            try:
                kb = get_main_keyboard(is_paid=True, user_id=uid)
                await bot.send_message(uid, "👇 ابدأ التعلم الآن:", reply_markup=kb)
            except Exception as e:
                logger.warning(f"send menu fail: {e}")
                await bot.send_message(uid, "اكتب /start للبدء 🚀")
        else:
            await bot.send_message(uid, "اكتب /start للبدء 🚀")
        await bot.session.close()
    except Exception as e:
        logger.warning(f"notify free student failed: {e}")

    # تحديث رسالة الأدمن
    try:
        await cb.message.edit_text(
            (cb.message.text or "") + f"\n\n✅ <b>تم التفعيل المجاني بواسطة {cb.from_user.full_name}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await cb.answer("✅ تم تفعيل الباقة المجانية!")




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


# ============================================================
#  Admin inline callbacks: approve / reject payments from chat
# ============================================================
from aiogram import F as _F
from aiogram.types import CallbackQuery as _CBQ
import urllib.request as _urlreq
import json as _json
from config import settings as _stg

def _admin_only(uid):
    try:
        return int(uid) in (_stg.ADMIN_IDS or [])
    except Exception:
        return False

@router.callback_query(_F.data.startswith("pay_approve:"))
async def _cb_pay_approve(cb: _CBQ):
    if not _admin_only(cb.from_user.id):
        await cb.answer("غير مصرح", show_alert=True); return
    pid = cb.data.split(":",1)[1]
    try:
        req = _urlreq.Request(
            f"http://127.0.0.1:8080/api/admin/payments/{pid}/approve",
            data=b"{}", headers={"Content-Type":"application/json"}, method="POST"
        )
        resp = _json.loads(_urlreq.urlopen(req, timeout=15).read().decode())
    except Exception as e:
        await cb.answer(f"خطأ: {e}", show_alert=True); return
    if resp.get("ok"):
        await cb.message.edit_caption(
            (cb.message.caption or "") + "\n\n✅ <b>تمت الموافقة</b>",
            reply_markup=None
        )
        await cb.answer("تمت الموافقة ✅")
    else:
        await cb.answer(f"فشل: {resp.get('error','?')}", show_alert=True)

@router.callback_query(_F.data.startswith("pay_reject:"))
async def _cb_pay_reject(cb: _CBQ):
    if not _admin_only(cb.from_user.id):
        await cb.answer("غير مصرح", show_alert=True); return
    pid = cb.data.split(":",1)[1]
    try:
        req = _urlreq.Request(
            f"http://127.0.0.1:8080/api/admin/payments/{pid}/reject",
            data=b"{}", headers={"Content-Type":"application/json"}, method="POST"
        )
        resp = _json.loads(_urlreq.urlopen(req, timeout=15).read().decode())
    except Exception as e:
        await cb.answer(f"خطأ: {e}", show_alert=True); return
    if resp.get("ok"):
        await cb.message.edit_caption(
            (cb.message.caption or "") + "\n\n❌ <b>تم الرفض</b>",
            reply_markup=None
        )
        await cb.answer("تم الرفض")
    else:
        await cb.answer(f"فشل: {resp.get('error','?')}", show_alert=True)
