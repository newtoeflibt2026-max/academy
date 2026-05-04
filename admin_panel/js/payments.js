let paymentFilter = 'pending';

async function loadPayments() {
    const data = await api('/payments', { filter: paymentFilter });
    if (!data) return;
    document.getElementById('payments-list').innerHTML = data.payments.length === 0 
        ? '<p class="text-center">لا توجد مدفوعات</p>'
        : data.payments.map(p => 
            '<div class="card" style="margin-bottom:10px">' +
            '<div class="card-header">#' + p.id + ' | ' + p.user_id + ' | <span class="status-' + p.status + '">' + p.status + '</span></div>' +
            '<div class="card-body">' +
            '<div>' + p.plan_name + ' • ' + p.amount + ' دينار • ' + p.created_at + '</div>' +
            (p.status === 'pending' ? '<button class="btn btn-sm btn-success" onclick="approvePayment(' + p.id + ')" style="margin-top:8px">✅ موافقة</button> <button class="btn btn-sm btn-danger" onclick="rejectPayment(' + p.id + ')" style="margin-top:8px">❌ رفض</button>' : '') +
            '</div></div>'
        ).join('');
}

function filterPayments(type) {
    paymentFilter = type;
    document.querySelectorAll('#page-payments .tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    loadPayments();
}

async function approvePayment(id) {
    await api('/approve_payment', { id });
    showToast('✅ تمت الموافقة');
    loadPayments();
    loadDashboard();
}

async function rejectPayment(id) {
    await api('/reject_payment', { id });
    showToast('❌ تم الرفض');
    loadPayments();
    loadDashboard();
}
