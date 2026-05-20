with open("handlers/start.py", "r", encoding="utf-8") as f:
    text = f.read()

# إصلاح 1: عمود stage غير موجود
text = text.replace(
    "SELECT * FROM lessons WHERE is_active=1 ORDER BY stage, order_num LIMIT 10",
    "SELECT * FROM lessons WHERE is_active=1 ORDER BY phase, order_num LIMIT 20"
)

# إصلاح 2: subscription_plans - عمود plan_name غير موجود
text = text.replace(
    "p.get(\"plan_name\"",
    "p.get(\"name_ar\", p.get(\"plan_name\""
)
text = text.replace(
    "p.get('plan_name'",
    "p.get('name_ar', p.get('plan_name', 'باقة')"
)

# إصلاح 3: lessons_per_day غير موجود
text = text.replace(
    "p.get(\"lessons_per_day\") or p.get(\"speed\", 1)",
    "p.get(\"duration_days\", 30)"
)
text = text.replace(
    "p.get('lessons_per_day') or p.get('speed', 1)",
    "p.get('duration_days', 30)"
)

with open("handlers/start.py", "w", encoding="utf-8") as f:
    f.write(text)
print("handlers/start.py fixed")
