import re

with open("templates/admin_dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. nav items
if "page-lessons" not in html:
    html = html.replace(
        '<div class="nav-section">المحتوى</div>',
        '<div class="nav-section">المحتوى</div>\n  <div class="nav-item" onclick="showPage(\'lessons\',this)"><span class="icon">📚</span> الدروس</div>'
    )

if "page-broadcast" not in html:
    html = html.replace(
        '<div class="nav-section">التشغيل</div>',
        '<div class="nav-section">التشغيل</div>\n  <div class="nav-item" onclick="showPage(\'broadcast\',this)"><span class="icon">📨</span> رسائل جماعية</div>\n  <div class="nav-item" onclick="showPage(\'messages\',this)"><span class="icon">💬</span> رسائل الطلاب <span class="nav-badge" id="badge-messages">0</span></div>'
    )

# 2. pages HTML
lessons_page = '''
    <div class="page" id="page-lessons">
      <div class="card">
        <div class="card-header">
          <span class="card-title">📚 إدارة الدروس</span>
          <button class="btn btn-primary" onclick="openLessonModal()">➕ إضافة درس</button>
        </div>
        <div style="overflow-x:auto">
          <table class="tbl" id="tbl-lessons">
            <thead><tr><th>#</th><th>العنوان</th><th>المهارة</th><th>المرحلة</th><th>الترتيب</th><th>XP</th><th>الحالة</th><th>إجراءات</th></tr></thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>'''

broadcast_page = '''
    <div class="page" id="page-broadcast">
      <div class="card">
        <div class="card-header"><span class="card-title">📨 إرسال رسائل Telegram</span></div>
        <div class="form-group">
          <label class="form-label">المستهدف</label>
          <select class="form-control" id="bc-target" onchange="toggleBcTarget()" style="max-width:300px">
            <option value="all">جميع الطلاب</option>
            <option value="single">طالب محدد</option>
          </select>
        </div>
        <div class="form-group" id="bc-uid-group" style="display:none;max-width:300px">
          <label class="form-label">Telegram ID</label>
          <input class="form-control" id="bc-uid" placeholder="123456789"/>
        </div>
        <div class="form-group">
          <label class="form-label">الرسالة</label>
          <textarea class="form-control" id="bc-message" rows="5" placeholder="اكتب رسالتك هنا..."></textarea>
        </div>
        <div style="display:flex;gap:10px;align-items:center">
          <button class="btn btn-primary" onclick="sendBroadcast()">📨 إرسال</button>
          <span id="bc-status" style="font-size:13px;color:#64748b"></span>
        </div>
      </div>
      <div class="card" style="margin-top:16px">
        <div class="card-header"><span class="card-title">📋 سجل الإرسال</span></div>
        <table class="tbl" id="tbl-broadcasts">
          <thead><tr><th>الرسالة</th><th>المستهدف</th><th>أُرسلت لـ</th><th>الحالة</th><th>التاريخ</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </div>'''

messages_page = '''
    <div class="page" id="page-messages">
      <div class="card">
        <div class="card-header">
          <span class="card-title">💬 رسائل الطلاب</span>
          <button class="btn btn-ghost btn-sm" onclick="loadMessages()">🔄 تحديث</button>
        </div>
        <div id="messages-container"></div>
      </div>
    </div>'''

# أضف الصفحات قبل </div><!-- /content -->
if "page-lessons" not in html:
    html = html.replace('</div><!-- /content -->', lessons_page + '\n' + broadcast_page + '\n' + messages_page + '\n</div><!-- /content -->')
elif "page-broadcast" not in html:
    html = html.replace('</div><!-- /content -->', broadcast_page + '\n' + messages_page + '\n</div><!-- /content -->')

# 3. modal الدرس
lesson_modal = '''
<div class="modal-backdrop" id="modal-lesson">
  <div class="modal" style="max-width:640px">
    <div class="modal-header">
      <span class="modal-title" id="lesson-modal-title">➕ إضافة درس</span>
      <button class="btn-icon" onclick="closeModal(\'modal-lesson\')">✕</button>
    </div>
    <div class="modal-body">
      <input type="hidden" id="lesson-edit-id"/>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div class="form-group" style="grid-column:1/-1">
          <label class="form-label">عنوان الدرس</label>
          <input class="form-control" id="lesson-title" placeholder="مقدمة في القراءة..."/>
        </div>
        <div class="form-group">
          <label class="form-label">المهارة</label>
          <select class="form-control" id="lesson-skill">
            <option value="reading">قراءة</option>
            <option value="listening">استماع</option>
            <option value="speaking">محادثة</option>
            <option value="writing">كتابة</option>
            <option value="grammar">قواعد</option>
            <option value="vocabulary">مفردات</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">المرحلة</label>
          <select class="form-control" id="lesson-phase">
            <option value="1">المرحلة 1 - مبتدئ</option>
            <option value="2">المرحلة 2 - متوسط</option>
            <option value="3">المرحلة 3 - متقدم</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">الترتيب</label>
          <input class="form-control" id="lesson-order" type="number" value="0"/>
        </div>
        <div class="form-group">
          <label class="form-label">مكافأة XP</label>
          <input class="form-control" id="lesson-xp" type="number" value="10"/>
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label class="form-label">الوصف</label>
          <input class="form-control" id="lesson-desc" placeholder="وصف مختصر..."/>
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label class="form-label">المحتوى</label>
          <textarea class="form-control" id="lesson-content" rows="5" placeholder="محتوى الدرس..."></textarea>
        </div>
      </div>
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;color:#94a3b8;margin-top:8px">
        <input type="checkbox" id="lesson-active" checked style="width:16px;height:16px;accent-color:#6366f1"/>
        درس نشط
      </label>
    </div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal(\'modal-lesson\')">إلغاء</button>
      <button class="btn btn-primary" onclick="submitLesson()">💾 حفظ</button>
    </div>
  </div>
</div>'''

if "modal-lesson" not in html:
    html = html.replace('<div id="toast"', lesson_modal + '\n<div id="toast"')

with open("templates/admin_dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
print("HTML updated OK")
