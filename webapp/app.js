// Yamen Academy WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

let currentUser = null;
let isAdmin = false;

// ====== INIT ======
document.addEventListener('DOMContentLoaded', async () => {
    const initData = tg.initDataUnsafe;
    if (initData && initData.user) {
        currentUser = initData.user;
        isAdmin = CONFIG.ADMIN_IDS.includes(currentUser.id);
        await loadUserData();
    }
    document.getElementById('loading').style.display = 'none';
    
    if (isAdmin) {
        document.getElementById('adminApp').style.display = 'block';
        setupAdminNav();
        loadDashboard();
    } else {
        document.getElementById('studentApp').style.display = 'block';
        setupStudentNav();
        loadStudentHome();
    }
    
    tg.MainButton.hide();
});

// ====== API ======
async function api(endpoint, method='GET', body=null) {
    const url = `${CONFIG.API_BASE}/api${endpoint}`;
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json', 'X-Telegram-User': JSON.stringify(currentUser) }
    };
    if (body) opts.body = JSON.stringify(body);
    try {
        const res = await fetch(url, opts);
        return await res.json();
    } catch(e) {
        console.error('API Error:', e);
        return null;
    }
}

// ====== NAVIGATION ======
function setupStudentNav() {
    document.querySelectorAll('#studentNav .nav-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('#studentNav .nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            const page = item.dataset.page;
            document.querySelectorAll('#studentPages .page').forEach(p => p.classList.remove('active'));
            const target = document.getElementById(`page-${page}`);
            if (target) target.classList.add('active');
            if (page === 'home') loadStudentHome();
            if (page === 'courses') loadCourses();
            if (page === 'spelling') loadSpelling();
            if (page === 'progress') loadProgress();
        });
    });
}

function setupAdminNav() {
    document.querySelectorAll('#adminNav .nav-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('#adminNav .nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            const page = item.dataset.page;
            document.querySelectorAll('#adminPages .page').forEach(p => p.classList.remove('active'));
            document.getElementById(`page-${page}`).classList.add('active');
            if (page === 'dashboard') loadDashboard();
            if (page === 'adminLessons') loadAdminLessons();
            if (page === 'adminWords') loadAdminWords();
            if (page === 'adminStudents') loadAdminStudents();
            if (page === 'adminSettings') loadSettings();
        });
    });
}

function navigate(page) {
    const btn = document.querySelector(`[data-page="${page}"]`);
    if (btn) btn.click();
}

// ====== STUDENT: HOME ======
async function loadStudentHome() {
    document.getElementById('studentName').textContent = currentUser?.first_name || 'طالب';
    const data = await api('/student/me');
    if (data) {
        document.getElementById('studentLevel').textContent = `المستوى: ${data.level || '--'}`;
        document.getElementById('xpBar').style.width = `${Math.min((data.xp||0) % 1000 / 10, 100)}%`;
        document.getElementById('xpText').textContent = `${data.xp || 0} XP`;
    }
}

// ====== STUDENT: COURSES ======
async function loadCourses() {
    const data = await api('/courses');
    const container = document.getElementById('coursesList');
    if (!data || !data.length) {
        container.innerHTML = '<p style="text-align:center;color:var(--muted)">لا توجد دورات متاحة</p>';
        return;
    }
    container.innerHTML = data.map(c => `
        <div class="course-card" onclick="loadLessons(${c.id})">
            <div class="course-name">${c.name}</div>
            <div class="course-level">${c.level}</div>
            <div class="course-progress"><div class="course-progress-bar" style="width:${c.progress||0}%"></div></div>
        </div>
    `).join('');
}

async function loadLessons(courseId) {
    const data = await api(`/courses/${courseId}/lessons`);
    document.querySelectorAll('#studentPages .page').forEach(p => p.classList.remove('active'));
    const page = document.getElementById('page-lesson');
    page.classList.add('active');
    if (!data || !data.length) {
        document.getElementById('lessonContent').innerHTML = '<p>لا توجد دروس</p>';
        return;
    }
    document.getElementById('lessonContent').innerHTML = `
        <h2 class="page-title">الدروس</h2>
        ${data.map(l => `
            <div class="course-card" onclick="viewLesson(${l.id})">
                <div class="course-name">${l.title}</div>
                ${l.media_type ? `<span style="font-size:12px;color:var(--muted)">${l.media_type}</span>` : ''}
            </div>
        `).join('')}
        <button class="btn-primary" onclick="navigate('courses')" style="margin-top:16px">رجوع</button>
    `;
}

async function viewLesson(lessonId) {
    const data = await api(`/lessons/${lessonId}`);
    if (!data) return;
    
    let html = `<h2 class="page-title">${data.title}</h2>`;
    
    if (data.image_file_id) {
        html += `<img src="https://api.telegram.org/file/bot${CONFIG.BOT_TOKEN}/${data.image_file_id}" class="lesson-media">`;
    }
    if (data.image_url) {
        html += `<img src="${data.image_url}" class="lesson-media">`;
    }
    
    html += `<div class="lesson-text">${data.content || ''}</div>`;
    html += '<div class="lesson-actions">';
    
    if (data.audio_file_id) {
        html += `<audio controls style="width:100%"><source src="https://api.telegram.org/file/bot${CONFIG.BOT_TOKEN}/${data.audio_file_id}"></audio>`;
    }
    if (data.audio_url) {
        html += `<audio controls style="width:100%"><source src="${data.audio_url}"></audio>`;
    }
    
    if (data.has_quiz) {
        html += `<button class="btn-primary btn-gold" onclick="takeQuiz(${data.id})">اختبار الدرس</button>`;
    }
    
    html += `<button class="btn-primary" onclick="openGroup()">💬 ناقش في المجموعة</button>`;
    html += `<button class="btn-primary" onclick="navigate('courses')">رجوع</button>`;
    html += '</div>';
    
    document.getElementById('lessonContent').innerHTML = html;
}

// ====== STUDENT: SPELLING ======
async function loadSpelling() {
    const data = await api('/spelling/next');
    if (data) {
        document.getElementById('spellingHint').textContent = data.hint || data.definition || 'اكتب الكلمة';
        window.currentSpellingWord = data;
    }
}

async function checkSpelling() {
    const input = document.getElementById('spellingInput').value.trim();
    const result = document.getElementById('spellingResult');
    if (!window.currentSpellingWord) return;
    
    const correct = input.toLowerCase() === window.currentSpellingWord.word.toLowerCase();
    result.textContent = correct ? '✅ صحيح! +10 XP' : `❌ خطأ! الإجابة: ${window.currentSpellingWord.word}`;
    result.style.color = correct ? 'var(--success)' : 'var(--danger)';
    
    await api('/spelling/answer', 'POST', {
        word_id: window.currentSpellingWord.id,
        answer: input,
        correct: correct
    });
    
    document.getElementById('spellingInput').value = '';
    setTimeout(loadSpelling, 1500);
}

// ====== STUDENT: PROGRESS ======
async function loadProgress() {
    const data = await api('/student/me');
    if (data) {
        document.getElementById('statXp').textContent = data.xp || 0;
        document.getElementById('statLessons').textContent = data.lessons_completed || 0;
        document.getElementById('statWords').textContent = data.words_learned || 0;
        document.getElementById('statStreak').textContent = data.streak || 0;
    }
    
    const log = await api('/student/xp-log');
    const container = document.getElementById('xpLog');
    if (log && log.length) {
        container.innerHTML = log.map(l => `
            <div class="log-item">
                <span>${l.reason}</span>
                <span class="log-xp">+${l.amount} XP</span>
            </div>
        `).join('');
    }
}

// ====== STUDENT: QUIZ ======
async function takeQuiz(lessonId) {
    const data = await api(`/quizzes/lesson/${lessonId}`);
    if (!data) return;
    
    let html = '<h2 class="page-title">اختبار الدرس</h2>';
    window.quizData = data;
    window.quizIndex = 0;
    window.quizScore = 0;
    
    showQuizQuestion();
}

function showQuizQuestion() {
    const q = window.quizData[window.quizIndex];
    if (!q) {
        document.getElementById('lessonContent').innerHTML = 
            `<h2 class="page-title">انتهى الاختبار!</h2>
             <p style="font-size:24px;text-align:center">${window.quizScore}/${window.quizData.length}</p>
             <button class="btn-primary" onclick="navigate('courses')">رجوع</button>`;
        return;
    }
    
    let html = `<p style="font-size:18px;margin-bottom:16px">${q.question_text}</p>`;
    if (q.options) {
        const opts = JSON.parse(q.options);
        html += opts.map((opt, i) => 
            `<button class="btn-primary" onclick="answerQuiz(${i})">${opt}</button>`
        ).join('');
    }
    document.getElementById('lessonContent').innerHTML = html;
}

function answerQuiz(idx) {
    const q = window.quizData[window.quizIndex];
    const opts = JSON.parse(q.options);
    if (opts[idx] === q.correct_answer) window.quizScore++;
    window.quizIndex++;
    showQuizQuestion();
}

// ====== GROUP ======
async function openGroup() {
    const data = await api('/settings/group-link');
    if (data && data.link) {
        tg.openTelegramLink(data.link);
    }
}

// ====== ADMIN: DASHBOARD ======
async function loadDashboard() {
    const data = await api('/admin/stats');
    if (data) {
        document.getElementById('dashStudents').textContent = data.total_students || 0;
        document.getElementById('dashActive').textContent = data.active_subs || 0;
        document.getElementById('dashPending').textContent = data.pending_payments || 0;
        document.getElementById('dashRevenue').textContent = (data.revenue || 0) + '$';
    }
    
    const pending = await api('/admin/pending-payments');
    const container = document.getElementById('pendingPayments');
    if (pending && pending.length) {
        container.innerHTML = '<h3>مدفوعات معلقة</h3>' + pending.map(p => `
            <div class="pending-item">
                <span>#${p.id} | طالب: ${p.user_id}</span>
                <div class="pending-actions">
                    <button class="btn-primary btn-success btn-sm" onclick="approvePayment(${p.id})">تفعيل</button>
                    <button class="btn-primary btn-danger btn-sm" onclick="rejectPayment(${p.id})">رفض</button>
                </div>
            </div>
        `).join('');
    }
}

async function approvePayment(pid) {
    await api(`/admin/payments/${pid}/approve`, 'POST');
    loadDashboard();
}

async function rejectPayment(pid) {
    await api(`/admin/payments/${pid}/reject`, 'POST');
    loadDashboard();
}

// ====== ADMIN: LESSONS ======
async function loadAdminLessons() {
    const data = await api('/admin/lessons');
    document.getElementById('adminLessonsList').innerHTML = (data || []).map(l => `
        <div class="admin-item">
            <span>${l.title} (${l.level || '?'})</span>
            <button class="btn-primary btn-danger btn-sm" onclick="deleteLesson(${l.id})">حذف</button>
        </div>
    `).join('');
}

// ====== ADMIN: WORDS ======
async function loadAdminWords() {
    const data = await api('/admin/words');
    document.getElementById('adminWordsList').innerHTML = (data || []).map(w => `
        <div class="admin-item">
            <span>${w.word} — ${w.definition || ''}</span>
        </div>
    `).join('');
}

// ====== ADMIN: STUDENTS ======
async function loadAdminStudents() {
    const data = await api('/admin/students');
    document.getElementById('adminStudentsList').innerHTML = (data || []).map(s => `
        <div class="admin-item">
            <span>${s.full_name || s.user_id} | ${s.level || '--'}</span>
            <span style="color:var(--muted)">${s.xp || 0} XP</span>
        </div>
    `).join('');
}

// ====== ADMIN: SETTINGS ======
async function loadSettings() {
    const data = await api('/settings/group-link');
    if (data) document.getElementById('groupLinkInput').value = data.link || '';
}

async function saveGroupLink() {
    const link = document.getElementById('groupLinkInput').value;
    await api('/admin/settings/group-link', 'POST', { link });
    alert('تم الحفظ!');
}

// ====== SEARCH ======
async function searchStudents() {
    const q = document.getElementById('studentSearch').value;
    const data = await api(`/admin/students?q=${q}`);
    document.getElementById('adminStudentsList').innerHTML = (data || []).map(s => `
        <div class="admin-item"><span>${s.full_name || s.user_id}</span></div>
    `).join('');
}
