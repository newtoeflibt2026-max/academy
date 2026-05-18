from aiogram import Router, F
from aiogram.types import CallbackQuery
from config import settings
from bot_database import approve_payment, get_db

router = Router(name="admin")

@router.callback_query(F.data.startswith("adm_approve:"))
async def admin_approve(cb: CallbackQuery):
    if cb.from_user.id not in settings.ADMIN_IDS:
        await cb.answer("غير مصرح", show_alert=True)
        return
    parts = cb.data.split(":")
    payment_id = int(parts[1])
    plan_key   = parts[2]
    user_id    = int(parts[3])
    days       = int(parts[4]) if len(parts) > 4 else 30
    try:
        await approve_payment(payment_id, plan_key, user_id, days)
        await cb.message.edit_caption(cb.message.caption + "\n\n✅ تم التفعيل", reply_markup=None)
        await cb.bot.send_message(user_id,
            f"🎉 <b>تم تفعيل اشتراكك!</b>\nالباقة: <b>{plan_key}</b>\nالمدة: <b>{days} يوم</b>\n\nابدأ دراستك الآن! 📚")
        await cb.answer("✅ تم التفعيل")
    except Exception as e:
        await cb.answer(f"خطأ: {e}", show_alert=True)

@router.callback_query(F.data.startswith("adm_reject:"))
async def admin_reject(cb: CallbackQuery):
    if cb.from_user.id not in settings.ADMIN_IDS:
        await cb.answer("غير مصرح", show_alert=True)
        return
    parts = cb.data.split(":")
    payment_id = int(parts[1])
    user_id    = int(parts[2])
    conn = get_db()
    conn.execute("UPDATE payments SET status='rejected' WHERE id=?", (payment_id,))
    conn.commit()
    conn.close()
    await cb.message.edit_caption(cb.message.caption + "\n\n❌ تم الرفض", reply_markup=None)
    await cb.bot.send_message(user_id, "❌ <b>تم رفض طلب الدفع.</b>\n\nللاستفسار تواصل معنا.")
    await cb.answer("تم الرفض")
