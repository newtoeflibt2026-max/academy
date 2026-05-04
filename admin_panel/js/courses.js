async function loadCourses() {
    const data = await api('/courses');
    if (!data) return;
    document.getElementById('courses-list').innerHTML = data.courses.map(c => 
        '<div class="card" style="margin-bottom:12px">' +
        '<div class="card-header">' + c.name + ' <span style="color:var(--text-light);font-weight:400">' + c.level + ' • ' + c.price + ' دينار • ' + c.duration_days + ' يوم</span></div>' +
        '<div class="card-body">' +
        '<button class="btn btn-sm btn-primary" onclick="showToast(\'قيد التطوير\')">➕ إضافة درس</button> ' +
        '<button class="btn btn-sm btn-secondary" onclick="showToast(\'قيد التطوير\')">📋 عرض الدروس</button> ' +
        '<button class="btn btn-sm btn-danger" onclick="deleteCourse(' + c.id + ')">🗑️ حذف</button>' +
        '</div></div>'
    ).join('');
}

function showAddCourseModal() { openModal('modal-course'); }

async function addCourse() {
    const name = document.getElementById('course-name').value;
    const level = document.getElementById('course-level').value;
    const price = document.getElementById('course-price').value;
    const duration = document.getElementById('course-duration').value;
    const vip = document.getElementById('course-vip').value;
    
    if (!name) { showToast('❌ الرجاء إدخال اسم الدورة'); return; }
    
    const result = await api('/add_course', { name, level, price: parseFloat(price), duration_days: parseInt(duration), is_vip: parseInt(vip) });
    if (result && result.success) {
        showToast('✅ تمت إضافة الدورة');
        closeModal('modal-course');
        loadCourses();
    }
}

async function deleteCourse(id) {
    if (!confirm('حذف هذه الدورة؟')) return;
    await api('/delete_course', { id });
    showToast('✅ تم الحذف');
    loadCourses();
}
