// students.js
async function loadStudents() {
    const data = await api('/students');
    if (!data) return;
    const tbody = document.getElementById('students-tbody');
    tbody.innerHTML = data.students.map(s => 
        '<tr>' +
        '<td>' + s.user_id + '</td>' +
        '<td>' + s.full_name + '</td>' +
        '<td>' + (s.level || '-') + '</td>' +
        '<td>' + s.xp + '</td>' +
        '<td><span class="' + (s.is_active ? 'status-active' : 'status-blocked') + '">' + (s.is_active ? 'نشط' : 'محظور') + '</span></td>' +
        '<td>' +
        '<button class="btn btn-sm ' + (s.is_active ? 'btn-danger' : 'btn-success') + '" onclick="toggleStudent(' + s.user_id + ')">' + (s.is_active ? '🚫 حظر' : '✅ تفعيل') + '</button>' +
        '</td>' +
        '</tr>'
    ).join('');
}

async function toggleStudent(userId) {
    await api('/toggle_student', { user_id: userId });
    showToast('✅ تم تغيير حالة الطالب');
    loadStudents();
}

function filterStudents(query) {
    const rows = document.querySelectorAll('#students-tbody tr');
    rows.forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(query.toLowerCase()) ? '' : 'none';
    });
}
