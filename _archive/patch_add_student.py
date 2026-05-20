import re

with open("templates/admin_dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# زر إضافة طالب بجانب قسم الطلاب
add_btn = """<button onclick="openAddStudent()" style="padding:10px 20px;background:linear-gradient(135deg,#4f7ef7,#818cf8);color:#fff;border:none;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;margin-bottom:16px">
  ➕ إضافة طالب يدوياً
</button>"""

# مودال إضافة طالب
add_modal = """
<!-- Modal: Add Student -->
<div id="modal-add-student" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;align-items:center;justify-content:center">
  <div style="background:#fff;border-radius:20px;padding:32px;width:100%;max-width:420px;margin:20px">
    <h3 style="margin-bottom:20px;font-size:18px;font-weight:800">➕ إضافة طالب جديد</h3>
    <input id="add-tid" type="number" placeholder="معرف تلغرام *" style="width:100%;padding:12px;border:2px solid #e2e8f0;border-radius:10px;margin-bottom:10px;font-family:Cairo,sans-serif;font-size:14px"/>
    <input id="add-name" type="text" placeholder="الاسم الكامل" style="width:100%;padding:12px;border:2px solid #e2e8f0;border-radius:10px;margin-bottom:10px;font-family:Cairo,sans-serif;font-size:14px"/>
    <input id="add-user" type="text" placeholder="يوزرنيم تلغرام" style="width:100%;padding:12px;border:2px solid #e2e8f0;border-radius:10px;margin-bottom:10px;font-family:Cairo,sans-serif;font-size:14px"/>
    <label style="display:flex;align-items:center;gap:8px;margin-bottom:20px;font-size:14px;cursor:pointer">
      <input type="checkbox" id="add-paid" style="width:18px;height:18px"/> تفعيل الاشتراك المدفوع فوراً
    </label>
    <div style="display:flex;gap:10px">
      <button onclick="submitAddStudent()" style="flex:1;padding:13px;background:linear-gradient(135deg,#4f7ef7,#818cf8);color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;font-family:Cairo,sans-serif">حفظ</button>
      <button onclick="document.getElementById('modal-add-student').style.display='none'" style="flex:1;padding:13px;background:#f1f5f9;color:#475569;border:none;border-radius:10px;font-size:15px;cursor:pointer;font-family:Cairo,sans-serif">إلغاء</button>
    </div>
  </div>
</div>"""

# JS للإضافة
add_js = """
function openAddStudent(){
  document.getElementById('modal-add-student').style.display='flex';
}
async function submitAddStudent(){
  const tid  = document.getElementById('add-tid').value.trim();
  const name = document.getElementById('add-name').value.trim();
  const user = document.getElementById('add-user').value.trim();
  const paid = document.getElementById('add-paid').checked ? 1 : 0;
  if(!tid){ alert('معرف تلغرام مطلوب'); return; }
  const r = await fetch('/api/admin/students/add',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({telegram_id:parseInt(tid), full_name:name, username:user, is_paid:paid})
  });
  const d = await r.json();
  if(d.ok){
    document.getElementById('modal-add-student').style.display='none';
    showToast('✅ تم إضافة الطالب');
    loadStudents();
  } else {
    alert('خطأ: '+(d.error||'unknown'));
  }
}
"""

# أدرج الزر قبل جدول الطلاب
if 'students-table' in html or 'students-container' in html:
    html = html.replace('<div id="page-students">', '<div id="page-students">\n' + add_btn, 1)
else:
    # أضف الزر بعد أول h2 في صفحة الطلاب
    html = html.replace('الطلاب</h2>', 'الطلاب</h2>\n' + add_btn, 1)

# أدرج المودال قبل نهاية body
html = html.replace('</body>', add_modal + '\n</body>', 1)

# أدرج JS قبل نهاية script أو body
html = html.replace('</script>\n</body>', add_js + '\n</script>\n</body>', 1)
if add_js not in html:
    html = html.replace('</body>', '<script>' + add_js + '</script>\n</body>', 1)

with open("templates/admin_dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Dashboard updated - size:", len(html))
