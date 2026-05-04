from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import add_payment, add_subscription, _safe_exec, dict_rows, get_payment, update_payment_status

router = Router()
ADMIN_IDS = {469136626, 5572314718}

def is_admin(uid): return uid in ADMIN_IDS

def get_plans():
    cur = _safe_exec("SELECT * FROM subscription_plans WHERE active=1 ORDER BY price")
    return dict_rows(cur.fetchall())

@router.callback_query(F.data == "menu_subscribe")
async def menu_subscribe(cb: types.CallbackQuery):
    plans = get_plans()
    if not plans:
        await cb.message.edit_text("No plans available.")
        await cb.answer(); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p['name']} - {p['price']}$", callback_data=f"plan_{p['key']}")]
        for p in plans
    ] + [[InlineKeyboardButton(text="Back", callback_data="student_menu")]])
    await cb.message.edit_text("Plans:", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("plan_"))
async def show_plan(cb: types.CallbackQuery):
    key = cb.data.split("_", 1)[1]
    plan = next((p for p in get_plans() if p['key'] == key), None)
    if not plan:
        await cb.answer("Not found", show_alert=True); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Send Receipt", callback_data=f"pay_{key}")],
        [InlineKeyboardButton(text="Back", callback_data="menu_subscribe")],
    ])
    await cb.message.edit_text(f"{plan['name']} - {plan['price']}$ / {plan['days']} days\n\nSend payment receipt:", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("pay_"))
async def request_receipt(cb: types.CallbackQuery):
    key = cb.data.split("_", 1)[1]
    plan = next((p for p in get_plans() if p['key'] == key), None)
    await cb.message.edit_text(f"Send receipt now for: {plan['name']} - {plan['price']}$")
    await cb.answer()

@router.message(F.photo)
async def handle_receipt_photo(msg: types.Message):
    file_id = msg.photo[-1].file_id
    pid = add_payment(msg.from_user.id, 'subscription', 0, file_id)
    await msg.answer("Receipt received! Admin will review.")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Approve", callback_data=f"appr_{pid}"),
         InlineKeyboardButton(text="Reject", callback_data=f"rej_{pid}")]
    ])
    for aid in ADMIN_IDS:
        try:
            await msg.bot.send_photo(aid, file_id,
                caption=f"New receipt\nUser: {msg.from_user.id}\nPayment: {pid}",
                reply_markup=kb)
        except: pass

@router.callback_query(F.data.startswith("appr_"))
async def approve_payment(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("Unauthorized", show_alert=True); return
    pid = int(cb.data.split("_")[1])
    payment = get_payment(pid)
    if not payment:
        await cb.answer("Not found", show_alert=True); return
    update_payment_status(pid, 'approved')
    add_subscription(payment['user_id'], payment.get('plan_name', 'Monthly'), 30)
    try:
        await cb.bot.send_message(payment['user_id'], "Your subscription is now active!")
    except: pass
    await cb.message.edit_caption(caption=cb.message.caption + "\n\nAPPROVED", reply_markup=None)
    await cb.answer("Approved")

@router.callback_query(F.data.startswith("rej_"))
async def reject_payment(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("Unauthorized", show_alert=True); return
    pid = int(cb.data.split("_")[1])
    update_payment_status(pid, 'rejected')
    payment = get_payment(pid)
    if payment:
        try: await cb.bot.send_message(payment['user_id'], "Receipt rejected. Contact support.")
        except: pass
    await cb.message.edit_caption(caption=cb.message.caption + "\n\nREJECTED", reply_markup=None)
    await cb.answer("Rejected")
