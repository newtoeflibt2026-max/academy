async function loadVault() {
    const data = await api('/vault');
    if (!data) return;
    document.getElementById('vault-list').innerHTML = data.items.length === 0
        ? '<p class="text-center">خزنة الأسرار فارغة</p>'
        : data.items.map(v => 
            '<div class="card" style="margin-bottom:10px">' +
            '<div class="card-header">' + v.title + ' | يفتح: ' + v.unlock_level + '</div>' +
            '<div class="card-body">' + v.content.substring(0, 200) + '... ' +
            '<button class="btn btn-sm btn-danger" onclick="deleteVaultItem(' + v.id + ')" style="margin-top:8px">🗑️ حذف</button></div></div>'
        ).join('');
}

function showAddVaultModal() { openModal('modal-vault'); }

async function addVaultItem() {
    const title = document.getElementById('vault-title').value;
    const content = document.getElementById('vault-content').value;
    const unlock = document.getElementById('vault-level').value;
    if (!title || !content) { showToast('❌ الرجاء ملء جميع الحقول'); return; }
    const result = await api('/add_vault', { title, content, unlock_level: unlock });
    if (result && result.success) {
        showToast('✅ تمت الإضافة للخزنة');
        closeModal('modal-vault');
        loadVault();
    }
}

async function deleteVaultItem(id) {
    if (!confirm('حذف هذا المحتوى؟')) return;
    await api('/delete_vault', { id });
    showToast('✅ تم الحذف');
    loadVault();
}
