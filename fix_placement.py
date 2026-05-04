import os
path = r"C:\yamen_academy\handlers\placement_test.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# نضيف استيراد get_student
if "from database import set_student_level" in content and "get_student" not in content.split("from database import")[1].split("\n")[0]:
    content = content.replace(
        "from database import set_student_level",
        "from database import set_student_level, get_student"
    )
    print("✅ Added get_student import")

# نضيف التحقق في بداية start_test
old_start = "@router.callback_query(F.data == \"start_test\")\nasync def start_test(callback: types.CallbackQuery, state: FSMContext):"
new_start = """@router.callback_query(F.data == "start_test")
async def start_test(callback: types.CallbackQuery, state: FSMContext):
    student = get_student(callback.from_user.id)
    if student and student.get("placement_done"):
        await callback.answer("⚠️ لقد أكملت اختبار تحديد المستوى مسبقاً", show_alert=True)
        return"""

if old_start in content:
    content = content.replace(old_start, new_start)
    print("✅ Added placement_done check")
else:
    print("⚠️ start_test pattern not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ placement_test.py FIXED")
