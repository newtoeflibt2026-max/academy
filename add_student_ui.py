# -*- coding: utf-8 -*-
import re

# ============================================================
# 1. إضافة زر + modal إضافة طالب في admin_dashboard.html
# ============================================================
with open("templates/admin_dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# أضف زر إضافة طالب بجانب عنوان قسم الطلاب
ADD_BTN = '''<button class="btn btn-p btn-sm" onclick="document.getElementById('modalAddStudent').classList.add('open')">
  &#43; إضافة طالب
</button>'''

# ابحث عن عنوان قسم الطلاب وأضف الزر بجانبه
html = re.sub(
    r'(id=["\']sec-students["\'][^>]*>.*?</div>)',
    lambda m: m.group(0).replace('</div>', ADD_BTN + '</div>', 1),
    html, count=1, flags=re.DOTALL
)

# أضف الـ modal قبل </body>
MODAL_HTML = """
<!-- Modal إضافة طالب -->
<div class="modal-bg" id="modalAddStudent">
  <div class="modal" style="max-width:420px">
    <div class="mh">
      <span style="font-weight:700;font-size:15px">&#x1F4CB; إضافة طالب يدوياً</span>
      <button onclick="document.getElementById('modalAddStudent').classList.remove('open')"
        style="background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer">&times;</button>
    </div>
    <div class="mb" style="display:flex;flex-direction:column;gap:12px">
      <div>
        <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px">Telegram ID *</label>
        <input class="fc" id="as_tid" type="number" placeholder="مثال: 5572314718">
      </div>
      <div>
        <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px">الاسم الكامل</label>
        <input class="fc" id="as_name" type="text" placeholder="اسم الطالب">
      </div>
      <div>
        <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px">يوزرنيم تيليجرام</label>
        <input class="fc" id="as_user" type="text" placeholder="@username (اختياري)">
      </div>
      <div style="display:flex;align-items:center;gap:8px">
        <input type="checkbox" id="as_paid" style="width:16px;height:16px">
        <label for="as_paid" style="font-size:13px;color:#cbd5e1">اشتراك مدفوع مفعّل</label>
      </div>
    </div>
    <div class="mf">
      <button class="btn btn-gh" onclick="document.getElementById('modalAddStudent').classList.remove('open')">إلغاء</button>
      <button class="btn btn-p" onclick="doAddStudent()">&#x2714; إضافة</button>
    </div>
  </div>
</div>

<script>
async function doAddStudent() {
  const tid  = document.getElementById('as_tid').value.trim();
  const name = document.getElementById('as_name').value.trim();
  const user = document.getElementById('as_user').value.trim();
  const paid = document.getElementById('as_paid').checked ? 1 : 0;
  if (!tid) { showToast('أدخل Telegram ID'); return; }
  try {
    const r = await fetch('/api/admin/students/add', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({telegram_id: parseInt(tid), full_name: name, username: user, is_paid: paid})
    });
    const d = await r.json();
    if (d.ok) {
      showToast('تم إضافة الطالب بنجاح');
      document.getElementById('modalAddStudent').classList.remove('open');
      document.getElementById('as_tid').value = '';
      document.getElementById('as_name').value = '';
      document.getElementById('as_user').value = '';
      document.getElementById('as_paid').checked = false;
      if (typeof loadStudents === 'function') loadStudents();
      else setTimeout(() => location.reload(), 1000);
    } else {
      showToast('خطأ: ' + (d.error || 'غير معروف'));
    }
  } catch(e) {
    showToast('خطأ في الاتصال');
  }
}
</script>
"""

if "</body>" in html:
    html = html.replace("</body>", MODAL_HTML + "\n</body>")
    print("Modal added before </body>")
else:
    html += MODAL_HTML
    print("Modal appended to end")

with open("templates/admin_dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)

print("admin_dashboard.html updated")

# ============================================================
# 2. إصلاح /admin في handlers/admin.py
# ============================================================
import os
admin_path = "handlers/admin.py"
if os.path.exists(admin_path):
    with open(admin_path, "r", encoding="utf-8") as f:
        admin_code = f.read()
    lines_count = admin_code.count("\n")
    print(f"handlers/admin.py: {lines_count} lines")
    
    # تحقق من وجود أمر /admin
    if "/admin" in admin_code or "cmd_admin" in admin_code:
        print("  /admin command found OK")
    else:
        print("  WARNING: /admin command not found in handlers/admin.py")
        print("  Adding /admin command...")
        
        admin_cmd = '''
from aiogram.filters import Command

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    import os
    admin_ids = [int(x) for x in os.environ.get("ADMIN_IDS","5572314718").split(",") if x.strip().isdigit()]
    if message.from_user.id not in admin_ids:
        await message.answer("غير مصرح لك.")
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="🌐 لوحة الأدمن", url="http://127.0.0.1:8080")
    kb.adjust(1)
    await message.answer(
        "👑 <b>لوحة تحكم الأدمن</b>\\n\\nافتح لوحة الأدمن من الرابط أدناه:",
        reply_markup=kb.as_markup()
    )
'''
        admin_code += admin_cmd
        with open(admin_path, "w", encoding="utf-8") as f:
            f.write(admin_code)
        print("  /admin command added")
else:
    print(f"WARNING: {admin_path} not found")

print("\nALL DONE")
