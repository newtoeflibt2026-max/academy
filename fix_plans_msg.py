with open("handlers/start.py", "r", encoding="utf-8") as f:
    text = f.read()

# إصلاح 1: حد الباقات بـ 5 فقط
text = text.replace(
    'f"SELECT * FROM subscription_plans WHERE is_active=1 ORDER BY price"',
    '"SELECT * FROM subscription_plans WHERE is_active=1 ORDER BY price LIMIT 5"'
)

# إصلاح 2: تقليل النص لكل باقة
old_plan_text = '''        text += (
            f"{emoji} <b>{name}</b>\\n"
            f"💰 السعر: {price:,} دينار\\n"
            f"📅 المدة: {days} يوم\\n"
            f"📖 {speed} درس/يوم\\n"
            f"📝 {desc}\\n"
            f"━━━━━━━━━━━━\\n\\n"
        )'''

new_plan_text = '''        price_text = "مجاني 🎁" if price == 0 else f"{price:,.0f} د.أ"
        text += f"{emoji} <b>{name}</b> — {price_text} | {days} يوم\\n"'''

text = text.replace(old_plan_text, new_plan_text)

with open("handlers/start.py", "w", encoding="utf-8") as f:
    f.write(text)
print("start.py fixed")
