import re

with open("templates/admin_dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. اضف الباقات في السايدبار
html = html.replace(
    '<div class="nav-section">المالية</div>',
    '<div class="nav-section">المالية</div>\n  <div class="nav-item" onclick="showPage(\'plans\',this)"><span class="icon">📦</span> الباقات</div>'
)

# 2. اضف صفحة الباقات قبل صفحة المدفوعات
plans_page = """
    <!-- PLANS PAGE -->
    <div class="page" id="page-plans">
      <div class="card">
        <div class="card-header">
          <span class="card-title">📦 إدارة الباقات</span>
          <button class="btn btn-primary" onclick="openPlanModal()">➕ إضافة باقة</button>
        </div>
        <div id="plans-container" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;margin-top:8px"></div>
      </div>
    </div>
"""
html = html.replace('<!-- ─── PAYMENTS ─── -->', plans_page + '\n    <!-- ─── PAYMENTS ─── -->')

# 3. اضف modal الباقات قبل modal الاسئلة
plan_modal = """
<!-- Modal: Plan -->
<div class="modal-backdrop" id="modal-plan">
  <div class="modal">
    <div class="modal-header">
      <span class="modal-title" id="plan-modal-title">➕ إضافة باقة</span>
      <button class="btn-icon" onclick="closeModal('modal-plan')">✕</button>
    </div>
    <div class="modal-body">
      <input type="hidden" id="plan-edit-id" value=""/>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div class="form-group">
          <label class="form-label">الاسم (English)</label>
          <input class="form-control" id="plan-name" placeholder="basic"/>
        </div>
        <div class="form-group">
          <label class="form-label">الاسم بالعربي</label>
          <input class="form-control" id="plan-name-ar" placeholder="الباقة الأساسية"/>
        </div>
        <div class="form-group">
          <label class="form-label">السعر (دينار عراقي)</label>
          <input class="form-control" id="plan-price" type="number" placeholder="25000"/>
        </div>
        <div class="form-group">
          <label class="form-label">المدة (أيام)</label>
          <input class="form-control" id="plan-days" type="number" placeholder="30"/>
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">الوصف</label>
        <input class="form-control" id="plan-desc" placeholder="وصف مختصر للباقة"/>
      </div>
      <div class="form-group">
        <label class="form-label">المميزات (كل ميزة في سطر)</label>
        <textarea class="form-control" id="plan-features" rows="4" placeholder="الوصول للدروس&#10;المهام اليومية&#10;Mock Exam"></textarea>
      </div>
      <div style="display:flex;gap:24px;margin-top:8px">
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;color:#94a3b8">
          <input type="checkbox" id="plan-active" checked style="width:16px;height:16px;accent-color:#6366f1"/>
          باقة نشطة
        </label>
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;color:#94a3b8">
          <input type="checkbox" id="plan-featured" style="width:16px;height:16px;accent-color:#f59e0b"/>
          موصى بها ⭐
        </label>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal('modal-plan')">إلغاء</button>
      <button class="btn btn-primary" onclick="submitPlan()">💾 حفظ</button>
    </div>
  </div>
</div>
"""
html = html.replace('<!-- Modal: Add Question -->', plan_modal + '\n<!-- Modal: Add Question -->')

# 4. اضف JavaScript الباقات قبل // ═══ Init ═══
plans_js = """
// ═══ Plans ═══
pageTitles['plans'] = 'الباقات';
pageLoaders['plans'] = loadPlans;

async function loadPlans(){
  const data = await API('/api/admin/plans');
  const container = document.getElementById('plans-container');
  if(!container) return;
  container.innerHTML = '';
  if(!data.plans || data.plans.length === 0){
    container.innerHTML = '<p style="color:#64748b;text-align:center;padding:40px">لا توجد باقات — اضغط إضافة باقة</p>';
    return;
  }
  data.plans.forEach(p => {
    let features = [];
    try { features = JSON.parse(p.features || '[]'); } catch(e){}
    const featHtml = features.map(f =>
      '<div style="display:flex;align-items:center;gap:6px;padding:3px 0;font-size:13px;color:#94a3b8"><span style="color:#4ade80">✓</span>' + f + '</div>'
    ).join('');
    container.innerHTML += `
    <div style="background:#0f172a;border:${p.is_featured?'2px solid #f59e0b':'1px solid #334155'};border-radius:16px;padding:20px;position:relative">
      ${p.is_featured ? '<div style="position:absolute;top:-12px;right:16px;background:#f59e0b;color:#000;padding:2px 12px;border-radius:99px;font-size:11px;font-weight:700">موصى بها ⭐</div>' : ''}
      <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:10px">
        <div>
          <div style="font-size:16px;font-weight:700;color:#f1f5f9">${p.name_ar}</div>
          <div style="font-size:11px;color:#64748b;margin-top:2px">${p.name}</div>
        </div>
        <span class="badge ${p.is_active ? 'badge-green' : 'badge-red'}">${p.is_active ? 'نشطة' : 'موقوفة'}</span>
      </div>
      <div style="font-size:26px;font-weight:800;color:#6366f1;margin-bottom:2px">
        ${Number(p.price).toLocaleString()} <span style="font-size:13px;color:#94a3b8;font-weight:500">د.ع</span>
      </div>
      <div style="font-size:12px;color:#64748b;margin-bottom:10px">لمدة ${p.duration_days} يوم</div>
      ${p.description ? '<div style="font-size:12px;color:#94a3b8;margin-bottom:10px;padding:8px;background:#1e293b;border-radius:8px">' + p.description + '</div>' : ''}
      <div style="margin-bottom:14px;min-height:20px">${featHtml}</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-ghost btn-sm" onclick="editPlan(${p.id})">✏️ تعديل</button>
        <button class="btn btn-sm" style="background:${p.is_active?'#451a03':'#052e16'};color:${p.is_active?'#fb923c':'#4ade80'}" onclick="togglePlan(${p.id})">${p.is_active ? '⏸ إيقاف' : '▶ تنشيط'}</button>
        <button class="btn btn-danger btn-sm" onclick="deletePlan(${p.id})">🗑️ حذف</button>
      </div>
    </div>`;
  });
}

function openPlanModal(reset=true){
  if(reset){
    document.getElementById('plan-modal-title').textContent = '➕ إضافة باقة جديدة';
    document.getElementById('plan-edit-id').value = '';
    document.getElementById('plan-name').value = '';
    document.getElementById('plan-name-ar').value = '';
    document.getElementById('plan-price').value = '';
    document.getElementById('plan-days').value = '30';
    document.getElementById('plan-desc').value = '';
    document.getElementById('plan-features').value = '';
    document.getElementById('plan-active').checked = true;
    document.getElementById('plan-featured').checked = false;
  }
  openModal('modal-plan');
}

async function editPlan(id){
  const data = await API('/api/admin/plans');
  const plan = (data.plans||[]).find(p=>p.id===id);
  if(!plan) return;
  document.getElementById('plan-modal-title').textContent = '✏️ تعديل الباقة';
  document.getElementById('plan-edit-id').value = id;
  document.getElementById('plan-name').value = plan.name || '';
  document.getElementById('plan-name-ar').value = plan.name_ar || '';
  document.getElementById('plan-price').value = plan.price || '';
  document.getElementById('plan-days').value = plan.duration_days || 30;
  document.getElementById('plan-desc').value = plan.description || '';
  let features = [];
  try { features = JSON.parse(plan.features||'[]'); } catch(e){}
  document.getElementById('plan-features').value = features.join('\\n');
  document.getElementById('plan-active').checked = !!plan.is_active;
  document.getElementById('plan-featured').checked = !!plan.is_featured;
  openPlanModal(false);
}

async function submitPlan(){
  const name = document.getElementById('plan-name').value.trim();
  const nameAr = document.getElementById('plan-name-ar').value.trim();
  const price = document.getElementById('plan-price').value;
  if(!name || !nameAr || !price){ toast('يرجى تعبئة الاسم والسعر', 'error'); return; }
  const features = document.getElementById('plan-features').value
    .split('\\n').map(s=>s.trim()).filter(Boolean);
  const payload = {
    name, name_ar: nameAr,
    price: parseFloat(price)||0,
    currency: 'IQD',
    duration_days: parseInt(document.getElementById('plan-days').value)||30,
    description: document.getElementById('plan-desc').value.trim(),
    features,
    is_active: document.getElementById('plan-active').checked ? 1 : 0,
    is_featured: document.getElementById('plan-featured').checked ? 1 : 0,
  };
  const editId = document.getElementById('plan-edit-id').value;
  const url = editId ? '/api/admin/plans/' + editId : '/api/admin/plans';
  const method = editId ? 'PUT' : 'POST';
  const r = await API(url, method, payload);
  if(r.ok){
    toast(editId ? '✅ تم تحديث الباقة' : '✅ تمت إضافة الباقة');
    closeModal('modal-plan');
    loadPlans();
  } else {
    toast('خطأ: ' + (r.error||'مجهول'), 'error');
  }
}

async function togglePlan(id){
  const r = await API('/api/admin/plans/' + id + '/toggle', 'POST');
  if(r.ok){ toast(r.is_active ? '▶ تم التنشيط' : '⏸ تم الإيقاف'); loadPlans(); }
  else toast('خطأ', 'error');
}

async function deletePlan(id){
  if(!confirm('حذف هذه الباقة نهائياً؟')) return;
  const r = await API('/api/admin/plans/' + id, 'DELETE');
  if(r.ok){ toast('🗑️ تم الحذف'); loadPlans(); }
  else toast('خطأ', 'error');
}

"""

# ابحث عن موضع // ═══ Init ═══
marker = "// ═══ Init ═══"
if marker in html:
    html = html.replace(marker, plans_js + marker)
    print("JS added before Init")
else:
    # ابحث عن loadDashboard() وضع قبله
    html = html.replace("loadDashboard();", plans_js + "\nloadDashboard();")
    print("JS added before loadDashboard")

with open("templates/admin_dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)

print("ALL DONE")
