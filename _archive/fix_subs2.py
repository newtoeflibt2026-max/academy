import os

BASE = r'C:\yamen_academy'

content = r'''
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import add_payment, _safe_exec, dict_rows

router = Router()

def get_plans():
    cur = _safe_exec("SELECT * FROM subscription_plans WHERE active=1 ORDER BY price")
    return dict_rows(cur.fetchall())

@router.callback_query(F.data == "menu_subscribe")
async def menu_subscribe(callback: types.CallbackQuery):
    plans = get_plans()
    if not plans:
        await callback.message.edit_text("\u26a0\ufe0f \u0644\u0627 \u062a\u0648\u062c\u062f \u062e\u0637\u0637 \u0645\u062a\u0627\u062d\u0629 \u062d\u0627\u0644\u064a\u0627\u064b.")
        await callback.answer(); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p['name']} \u2014 {p['price']}\$", callback_data=f"plan_{p['key']}")]
        for p in plans
    ] + [[InlineKeyboardButton(text="\U0001f519 \u0631\u062c\u0648\u0639", callback_data="student_menu")]])
    await callback.message.edit_text("\U0001f48e *\u062e\u0637\u0637 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643*\n\u0627\u062e\u062a\u0631 \u062e\u0637\u062a\u0643:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("plan_"))
async def show_plan(callback: types.CallbackQuery):
    key = callback.data.split("_")[1]
    plans = get_plans()
    plan = next((p for p in plans if p['key'] == key), None)
    if not plan:
        await callback.answer("\u274c \u062e\u0637\u0629 \u063a\u064a\u0631 \u0645\u0648\u062c\u0648\u062f\u0629", show_alert=True); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f4f8 \u0625\u0631\u0633\u0627\u0644 \u0625\u064a\u0635\u0627\u0644 \u0627\u0644\u062f\u0641\u0639", callback_data=f"pay_{key}")],
        [InlineKeyboardButton(text="\U0001f519 \u0631\u062c\u0648\u0639", callback_data="menu_subscribe")],
    ])
    await callback.message.edit_text(
        f"*{plan['name']}* \u2014 {plan['price']}\$ \u0644\u0645\u062f\u0629 {plan['days']} \u064a\u0648\u0645\n\n"
        "\u0644\u0644\u0627\u0634\u062a\u0631\u0627\u0643:\n1\ufe0f\u20e3 \u062d\u0648\u0651\u0644 \u0627\u0644\u0645\u0628\u0644\u063a\n2\ufe0f\u20e3 \u0623\u0631\u0633\u0644 \u0635\u0648\u0631\u0629 \u0627\u0644\u0625\u064a\u0635\u0627\u0644 \u0647\u0646\u0627",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pay_"))
async def request_receipt(callback: types.CallbackQuery):
    key = callback.data.split("_")[1]
    plans = get_plans()
    plan = next((p for p in plans if p['key'] == key), None)
    await callback.message.edit_text(
        f"\U0001f4f8 \u0623\u0631\u0633\u0644 \u0635\u0648\u0631\u0629 \u0625\u064a\u0635\u0627\u0644 \u0627\u0644\u062f\u0641\u0639 \u0627\u0644\u0622\u0646\n\u0627\u0644\u062e\u0637\u0629: *{plan['name']}* \u2014 {plan['price']}\$",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(F.photo)
async def handle_receipt_photo(message: types.Message):
    file_id = message.photo[-1].file_id
    add_payment(message.from_user.id, 'subscription', 0, file_id)
    await message.answer("\u2705 \u062a\u0645 \u0627\u0633\u062a\u0644\u0627\u0645 \u0627\u0644\u0625\u064a\u0635\u0627\u0644! \u0633\u064a\u0631\u0627\u062c\u0639\u0647 \u0627\u0644\u0623\u062f\u0645\u0646 \u0642\u0631\u064a\u0628\u0627\u064b.")
'''

path = os.path.join(BASE, 'handlers', 'subscriptions.py')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content.strip() + '\n')
print('✅ subscriptions.py UPDATED — DB-driven plans')
