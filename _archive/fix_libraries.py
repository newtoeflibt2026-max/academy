import os

path = r"C:\yamen_academy\handlers\subscriptions.py"
content = open(path, "r", encoding="utf-8").read()

# البحث عن تعريف دراسة ذاتية وإضافة قائمة المكتبات
old = '''    "self_study": {
        "name": "📖 دراسة ذاتية", "price": 15, "days": 120,
        "desc": "كتاب يامن للآيلتس من المكتبات المعتمدة — دراسة على راحتك",
        "features": ["✅ كتاب يامن للآيلتس", "✅ خطة دراسة 4 شهور", "✅ تمارين ذاتية"],
        "is_self_study": True,
    },'''

new = '''    "self_study": {
        "name": "📖 دراسة ذاتية", "price": 15, "days": 120,
        "desc": "كتاب يامن للآيلتس من المكتبات المعتمدة — دراسة على راحتك",
        "features": ["✅ كتاب يامن للآيلتس", "✅ خطة دراسة 4 شهور", "✅ تمارين ذاتية"],
        "is_self_study": True,
        "libraries": [
            "🏅 خدمة التوصيل: 0798919150",
            "",
            "🎯 محافظة العاصمة / عمان",
            "🎖 الجامعة الأردنية:",
            "  🥇 مكتبة الجامعة — مقابل البوابة الرئيسية للجامعة",
            "  🥇 مكتبة ABC — مقابل بوابة الزراعة — 0797310006",
            "🏅 شفا بدران: مكتبة هدف المعرفة — 0796668494",
            "🎖 صويلح: مكتبة التاريخ — 0790096290",
            "🎖 طبربور: مكتبة اللوتس — 0799350333",
            "🏅 جبل الحسين: مكتبة قص ولصق — 0792525315",
            "🎖 مرج الحمام:",
            "  🥇 مكتبة زاد الفكر — 0775733882",
            "  🥈 مكتبة العوسج — 0795941626",
            "🎖 البيادر: مكتبة النرجس — 0787674121",
            "🎖 مجمع الجنوب: مكتبة أبو طوق — 0796465131",
            "🥇 الوحدات: مكتبة البراق — 0796805776",
            "🎖 جبل النصر: مكتبة الشهداء الإسلامية — 0795925393",
            "🥇 سحاب: مكتبة الإيمان — 0787364742",
            "",
            "🎯 مادبا: مكتبة راضي — 0775244394",
            "🎯 السلط: مكتبة أمين العناسوة — 0777782070",
            "",
            "🎯 محافظة الزرقاء",
            "  🥇 مكتبة بلوماكس — المجمع القديم",
            "  🥈 مكتبة سلسبيلا — المجمع الجديد — 0785071823",
            "  🥈 مكتبة صناع الحياة — الجبل الشمالي — 053757033",
            "",
            "🎯 المفرق: مكتبة الأقصى — 0786077111",
            "🎯 جرش: مكتبة أكاديميا — 0777503412",
            "",
            "🎯 إربد:",
            "  🥉 مكتبة الوفاء — شارع الجامعة — 0795657090",
            "",
            "🎯 الكرك: مكتبة تقوى — 0796453461",
            "🎯 الطفيلة: مكتبة عروة — 0776614558",
            "🎯 معان: مكتبة التيسير — 0777875963",
            "🎯 العقبة: مكتبة الرسالة العالمية — 0791913334",
        ],
    },'''

content = content.replace(old, new)

# إضافة دالة عرض المكتبات بعد show_plans_msg
lib_func = '''

async def show_libraries(message):
    """يعرض قائمة المكتبات المعتمدة لكتاب يامن للآيلتس."""
    text = (
        "📖 <b>النسخة الأصلية من كتاب يامن للآيلتس</b>\\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
        "الكتاب متوفر حصراً في المكتبات المعتمدة التالية:\\n\\n"
    )
    libs = PLANS["self_study"].get("libraries", [])
    for line in libs:
        if line == "":
            text += "\\n"
        elif line.startswith("🎯"):
            text += f"\\n<b>{line}</b>\\n"
        elif line.startswith("🎖") or line.startswith("🏅"):
            text += f"<b>{line}</b>\\n"
        else:
            text += f"{line}\\n"
    
    text += (
        "\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
        "📱 للاستفسار: <code>0798919150</code>\\n"
        "🏅 خدمة التوصيل متوفرة 🚚"
    )
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💳 متابعة للدفع", callback_data="sub:plan:self_study"))
    kb.row(InlineKeyboardButton(text="🔙 رجوع للباقات", callback_data="menu:subscribe"))
    
    await message.edit_text(text, reply_markup=kb.as_markup())
'''

# إدراج الدالة قبل آخر سطر
content = content.replace(
    '# ═══ القائمة الرئيسية ═══',
    lib_func + '\n# ═══ القائمة الرئيسية ═══'
)

# إضافة callback لعرض المكتبات
content = content.replace(
    '@router.callback_query(F.data == "menu:subscribe")',
    '''@router.callback_query(F.data == "sub:show_libraries")
async def cb_show_libraries(callback: CallbackQuery):
    await show_libraries(callback.message)
    await callback.answer()

@router.callback_query(F.data == "menu:subscribe")'''
)

# تعديل زر الدراسة الذاتية ليفتح المكتبات أولاً
content = content.replace(
    'callback_data=f"sub:plan:{key}"',
    'callback_data=f"sub:plan:{key}" if key != "self_study" else f"sub:show_libraries"'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ تم إضافة قائمة المكتبات المعتمدة!")
