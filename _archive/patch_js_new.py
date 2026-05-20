import re

with open("templates/admin_dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

new_js = """
pageTitles['lessons'] = 'الدروس';
pageTitles['broadcast'] = 'رسائل جماعية';
pageTitles['messages'] = 'رسائل الطلاب';
pageLoaders['lessons'] = loadLessons;
pageLoaders['broadcast'] = loadBroadcastHistory;
pageLoaders['messages'] = loadMessages;

async function loadLessons(){
  const data = await API('/api/admin/lessons');
  const tbody = document.querySelector('#tbl-lessons tbody');
  if(!tbody) return;
  tbody.innerHTML = '';
  const sc = {reading:'blue',listening:'purple',speaking:'yellow',writing:'green',grammar:'red',vocabulary:'yellow'};
  (data.lessons||[]).forEach(l => {
    tbody.innerHTML += '<tr><td style="color:#64748b">'+l.id+'</td><td><b>'+l.title+'</b><br><small style="color:#64748b">'+(l.description||'')+'</small></td><td><span class="badge badge-'+(sc[l.skill]||'blue')+'">'+l.skill+'</span></td><td>م'+l.phase+'</td><td>'+l.order_num+'</td><td><span class="badge badge-purple">+'+l.xp_reward+' XP</span></td><td><span class="badge badge-'+(l.is_active?'green':'red')+'">'+(l.is_active?'نشط':'موقوف')+'</span></td><td style="display:flex;gap:6px"><button class="btn btn-ghost btn-sm" onclick="editLesson('+l.id+')">✏️</button><button class="btn btn-danger btn-sm" onclick="deleteLesson('+l.id+')">🗑️</button></td></tr>';
  });
}

function openLessonModal(reset){
  if(reset !== false){
    document.getElementById('lesson-modal-title').textContent = '➕ إضافة درس جديد';
    document.getElementById('lesson-edit-id').value = '';
    ['lesson-title','lesson-desc','lesson-content'].forEach(function(id){ document.getElementById(id).value = ''; });
    document.getElementById('lesson-skill').value = 'reading';
    document.getElementById('lesson-phase').value = '1';
    document.getElementById('lesson-order').value = '0';
    document.getElementById('lesson-xp').value = '10';
    document.getElementById('lesson-active').checked = true;
  }
  openModal('modal-lesson');
}

async function editLesson(id){
  const data = await API('/api/admin/lessons');
  const l = (data.lessons||[]).find(function(x){ return x.id===id; });
  if(!l) return;
  document.getElementById('lesson-modal-title').textContent = '✏️ تعديل الدرس';
  document.getElementById('lesson-edit-id').value = id;
  document.getElementById('lesson-title').value = l.title||'';
  document.getElementById('lesson-desc').value = l.description||'';
  document.getElementById('lesson-content').value = l.content||'';
  document.getElementById('lesson-skill').value = l.skill||'reading';
  document.getElementById('lesson-phase').value = l.phase||1;
  document.getElementById('lesson-order').value = l.order_num||0;
  document.getElementById('lesson-xp').value = l.xp_reward||10;
  document.getElementById('lesson-active').checked = !!l.is_active;
  openLessonModal(false);
}

async function submitLesson(){
  const title = document.getElementById('lesson-title').value.trim();
  if(!title){ toast('العنوان مطلوب','error'); return; }
  const editId = document.getElementById('lesson-edit-id').value;
  const payload = {
    title: title,
    description: document.getElementById('lesson-desc').value.trim(),
    content: document.getElementById('lesson-content').value.trim(),
    skill: document.getElementById('lesson-skill').value,
    phase: parseInt(document.getElementById('lesson-phase').value)||1,
    order_num: parseInt(document.getElementById('lesson-order').value)||0,
    xp_reward: parseInt(document.getElementById('lesson-xp').value)||10,
    is_active: document.getElementById('lesson-active').checked ? 1 : 0
  };
  const url = editId ? '/api/admin/lessons/'+editId : '/api/admin/lessons';
  const method = editId ? 'PUT' : 'POST';
  const r = await API(url, method, payload);
  if(r.ok){ toast(editId?'✅ تم التحديث':'✅ تمت الإضافة'); closeModal('modal-lesson'); loadLessons(); }
  else toast('خطأ: '+(r.error||''), 'error');
}

async function deleteLesson(id){
  if(!confirm('حذف هذا الدرس؟')) return;
  const r = await API('/api/admin/lessons/'+id,'DELETE');
  if(r.ok){ toast('🗑️ تم الحذف'); loadLessons(); }
}

function toggleBcTarget(){
  var t = document.getElementById('bc-target').value;
  document.getElementById('bc-uid-group').style.display = t==='single' ? 'block' : 'none';
}

async function sendBroadcast(){
  var message = document.getElementById('bc-message').value.trim();
  var target = document.getElementById('bc-target').value;
  var uid = document.getElementById('bc-uid').value.trim();
  if(!message){ toast('اكتب رسالة أولاً','error'); return; }
  if(target==='single' && !uid){ toast('أدخل Telegram ID','error'); return; }
  var status = document.getElementById('bc-status');
  status.textContent = '⏳ جاري الإرسال...';
  var payload = {message: message, target: target};
  if(target==='single') payload.user_id = parseInt(uid);
  var r = await API('/api/admin/broadcast','POST',payload);
  if(r.ok){
    toast('✅ أُرسلت لـ '+r.sent+' طالب');
    status.textContent = 'أُرسلت: '+r.sent+' | فشل: '+r.failed;
    loadBroadcastHistory();
  } else {
    toast('خطأ: '+(r.error||''), 'error');
    status.textContent = 'فشل الإرسال';
  }
}

async function loadBroadcastHistory(){
  var data = await API('/api/admin/broadcast/history');
  var tbody = document.querySelector('#tbl-broadcasts tbody');
  if(!tbody) return;
  tbody.innerHTML = '';
  (data.history||[]).forEach(function(b){
    tbody.innerHTML += '<tr><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+b.message+'</td><td><span class="badge badge-blue">'+(b.target==='all'?'الكل':'فردي')+'</span></td><td>'+(b.sent_count||0)+' طالب</td><td><span class="badge badge-'+(b.status==='sent'?'green':'yellow')+'">'+b.status+'</span></td><td style="color:#64748b">'+((b.created_at||'').slice(0,16))+'</td></tr>';
  });
}

async function loadMessages(){
  var data = await API('/api/admin/messages');
  var container = document.getElementById('messages-container');
  if(!container) return;
  var msgs = data.messages||[];
  var unread = msgs.filter(function(m){ return !m.is_read; }).length;
  var badge = document.getElementById('badge-messages');
  if(badge) badge.textContent = unread;
  if(msgs.length === 0){
    container.innerHTML = '<p style="text-align:center;color:#64748b;padding:40px">لا توجد رسائل بعد</p>';
    return;
  }
  container.innerHTML = msgs.map(function(m){
    return '<div style="padding:16px;border-bottom:1px solid #334155;background:'+(m.is_read?'transparent':'rgba(99,102,241,0.05)')+'"><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px"><div><div style="font-weight:600;color:#f1f5f9">'+(m.full_name||m.username||'مجهول')+'</div><div style="font-size:11px;color:#64748b">ID: '+m.user_id+' - '+((m.created_at||'').slice(0,16))+'</div></div><div style="display:flex;gap:8px">'+(!m.is_read?'<span class="badge badge-blue">جديد</span>':'')+(!m.is_read?'<button class="btn btn-ghost btn-sm" onclick="markRead('+m.id+')">✓</button>':'')+'<button class="btn btn-primary btn-sm" onclick="replyTo('+m.user_id+')">↩️ رد</button></div></div><div style="background:#0f172a;padding:12px;border-radius:10px;font-size:13px;color:#cbd5e1">'+m.message+'</div></div>';
  }).join('');
}

async function markRead(id){
  await API('/api/admin/messages/'+id+'/read','POST');
  loadMessages();
}

function replyTo(uid){
  document.getElementById('bc-target').value = 'single';
  document.getElementById('bc-uid').value = uid;
  document.getElementById('bc-uid-group').style.display = 'block';
  document.getElementById('bc-message').value = '';
  showPage('broadcast', null);
}
"""

if "loadLessons" not in html:
    html = html.replace("loadDashboard();", new_js + "\nloadDashboard();")
    print("JS added")
else:
    print("JS already exists")

with open("templates/admin_dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
print("DONE")
