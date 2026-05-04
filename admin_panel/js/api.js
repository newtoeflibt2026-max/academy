// api.js - رابط مع Flask API
const API = 'http://127.0.0.1:5050/api/admin';

async function api(endpoint, data = {}) {
    try {
        const res = await fetch(API + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error('Server error: ' + res.status);
        return await res.json();
    } catch (e) {
        console.error('API Error:', e);
        showToast('تعذر الاتصال بالخادم - تأكد من تشغيل server_admin.py');
        return null;
    }
}

function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.remove('hidden');
    setTimeout(() => t.classList.add('hidden'), 3000);
}

function closeModal(id) {
    document.getElementById(id).classList.add('hidden');
}

function openModal(id) {
    document.getElementById(id).classList.remove('hidden');
}
