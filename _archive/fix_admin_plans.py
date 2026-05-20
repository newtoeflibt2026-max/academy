import os

BASE = r'C:\yamen_academy'

# Read existing admin.py
with open(os.path.join(BASE, 'handlers', 'admin.py'), 'r', encoding='utf-8') as f:
    admin = f.read()

# Add subscription plans management section right before the last line
insert_code = '''

# ─── SUBSCRIPTION PLANS MANAGEMENT (DB-driven) ───
class AddPlan(StatesGroup):
    waiting_for_plan = State()

@router.callback_query(F.data == "admin_plans")
async def admin_plans(callback: types.CallbackQuery):
    from database import _safe_exec, dict_rows
    plans = dict_rows(_safe_exec("SELECT * FROM subscription_plans ORDER BY price").fetchall())
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ إضافة خطة", callback_data="add_plan")],
        *([[
            InlineKeyboardButton(
                text=f"❌ {p['name']} — {p['price']}$",
                callback_data=f"delplan_{p['id']}"
            )
        ] for p in plans]),
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_back")],
    ])
    await callback.message.edit_text(
        f"💎 *خطط الاشتراك* ({len(plans)} خطة)",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "add_plan")
async def add_plan_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddPlan.waiting_for_plan)
    await callback.message.edit_text(
        "أرسل الخطة بهذا الشكل:\n
ame|key|price|days\n\n"
        "مثال: 🥇 شهر|1month|10|30",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AddPlan.waiting_for_plan)
async def add_plan_save(message: types.Message, state: FSMContext):
    parts = message.text.split("|")
    name, key = parts[0].strip(), parts[1].strip()
    price, days = float(parts[2].strip()), int(parts[3].strip())
    from database import _safe_exec
    _safe_exec("INSERT OR REPLACE INTO subscription_plans(name,key,price,days) VALUES(?,?,?,?)",
               (name, key, price, days))
    await state.clear()
    await message.answer(f"✅ أضيفت الخطة: *{name}* — {price}$ / {days} يوم", parse_mode="Markdown")

@router.callback_query(F.data.startswith("delplan_"))
async def del_plan(callback: types.CallbackQuery):
    pid = int(callback.data.split("_")[1])
    from database import _safe_exec
    _safe_exec("DELETE FROM subscription_plans WHERE id=?", (pid,))
    await callback.message.edit_text("✅ حذفت الخطة.")
    await callback.answer()
'''

# Insert before the PAYMENTS section marker
if '# ─── PAYMENTS ───' in admin:
    admin = admin.replace('# ─── PAYMENTS ───', insert_code + '\n# ─── PAYMENTS ───')
else:
    # Append at end before last router definition ends
    admin = admin.rstrip() + insert_code

# Add admin_plans button to admin panel
old_kb = '[InlineKeyboardButton(text="💳 المدفوعات", callback_data="admin_payments")]'
new_kb = '''[InlineKeyboardButton(text="💎 خطط الاشتراك", callback_data="admin_plans")],
        [InlineKeyboardButton(text="💳 المدفوعات", callback_data="admin_payments")]'''
admin = admin.replace(old_kb, new_kb)

with open(os.path.join(BASE, 'handlers', 'admin.py'), 'w', encoding='utf-8') as f:
    f.write(admin)
print('✅ admin.py UPDATED — plans management section')
