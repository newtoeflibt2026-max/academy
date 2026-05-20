import os
path = r"C:\yamen_academy\handlers\subscriptions.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# نضيف add_subscription في دالة approve_payment
old_approve = """    update_payment_status(payment_id, "approved")

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ تم التفعيل", callback_data="done")"""
    
new_approve = """    update_payment_status(payment_id, "approved")
    
    # إضافة اشتراك فعلي
    from database import get_conn
    conn = get_conn()
    payment = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
    if payment:
        add_subscription(payment["user_id"], payment.get("plan_name", "Flexible"), 30)
        student = get_student(payment["user_id"])
        if student and student.get("level"):
            pass  # already has level
        print(f"✅ Subscription added for user {payment['user_id']}")

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ تم التفعيل", callback_data="done")"""

if old_approve in content:
    content = content.replace(old_approve, new_approve)
    print("✅ Added subscription creation in approve")
else:
    print("⚠️ approve pattern not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ subscriptions.py FIXED")
