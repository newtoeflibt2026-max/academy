import os, json

BASE = r"C:\yamen_academy"
WEB_DIR = os.path.join(BASE, "webapp")
os.makedirs(WEB_DIR, exist_ok=True)

# ============================================================
# 1. CONFIG — Bot Token for WebApp
# ============================================================
config_js = """// Telegram Mini App Config
const CONFIG = {
    BOT_TOKEN: "8518957777:AAFgLsnfJTeqPxI57F8RO2-o4SKeyi2Q7qM",
    API_BASE: "https://yamen-academy.onrender.com",
    ADMIN_IDS: [469136626, 5572314718],
    COLORS: {
        primary: "#3B82F6",
        gold: "#F59E0B",
        bg: "#F8FAFC",
        card: "#FFFFFF",
        text: "#1E293B",
        muted: "#94A3B8",
        success: "#10B981",
        danger: "#EF4444"
    }
};
"""
with open(os.path.join(WEB_DIR, "config.js"), "w", encoding="utf-8") as f:
    f.write(config_js)

# ============================================================
# 2. MAIN HTML — Single Page App
# ============================================================
index_html = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yamen Academy</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
</head>
<body>
    <!-- Loading -->
    <div id="loading" class="loading-screen">
        <div class="loader"></div>
        <p>جاري التحميل...</p>
    </div>

    <!-- Student App -->
    <div id="studentApp" class="app-container" style="display:none">
        <nav class="bottom-nav" id="studentNav">
            <button class="nav-item active" data-page="home">
                <span class="nav-icon">🏠</span>
                <span class="nav-label">الرئيسية</span>
            </button>
            <button class="nav-item" data-page="courses">
                <span class="nav-icon">📚</span>
                <span class="nav-label">دوراتي</span>
            </button>
            <button class="nav-item" data-page="spelling">
                <span class="nav-icon">✍️</span>
                <span class="nav-label">تهجئة</span>
            </button>
            <button class="nav-item" data-page="progress">
                <span class="nav-icon">📊</span>
                <span class="nav-label">تقدمي</span>
            </button>
        </nav>
        
        <!-- Student Pages -->
        <main id="studentPages">
            <div id="page-home" class="page active">
                <div class="hero-card">
                    <div class="hero-avatar">👤</div>
                    <h1 class="hero-name" id="studentName">...</h1>
                    <p class="hero-level" id="studentLevel">المستوى: --</p>
                    <div class="xp-bar-container">
                        <div class="xp-bar" id="xpBar"></div>
                        <span class="xp-text" id="xpText">0 XP</span>
                    </div>
                </div>
                <div class="quick-actions">
                    <button class="action-card" onclick="navigate('courses')">
                        <span class="action-icon">📖</span>
                        <span class="action-label">متابعة التعلم</span>
                    </button>
                    <button class="action-card" onclick="navigate('challenge')">
                        <span class="action-icon">⚡</span>
                        <span class="action-label">تحدي 60 ثانية</span>
                    </button>
                    <button class="action-card" onclick="openGroup()">
                        <span class="action-icon">💬</span>
                        <span class="action-label">مجموعة النقاش</span>
                    </button>
                </div>
            </div>

            <div id="page-courses" class="page">
                <h2 class="page-title">دوراتي</h2>
                <div id="coursesList" class="courses-grid"></div>
            </div>

            <div id="page-lesson" class="page">
                <div id="lessonContent"></div>
            </div>

            <div id="page-quiz" class="page">
                <div id="quizContent"></div>
            </div>

            <div id="page-spelling" class="page">
                <h2 class="page-title">تدريب التهجئة</h2>
                <div id="spellingCard" class="spelling-card">
                    <p class="spelling-hint" id="spellingHint">...</p>
                    <input type="text" id="spellingInput" class="spelling-input" placeholder="اكتب الكلمة..." autocomplete="off">
                    <button class="btn-primary" onclick="checkSpelling()">تحقق</button>
                    <p class="spelling-result" id="spellingResult"></p>
                </div>
            </div>

            <div id="page-progress" class="page">
                <h2 class="page-title">تقدمي</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <span class="stat-value" id="statXp">0</span>
                        <span class="stat-label">XP</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value" id="statLessons">0</span>
                        <span class="stat-label">درس</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value" id="statWords">0</span>
                        <span class="stat-label">كلمة</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value" id="statStreak">0</span>
                        <span class="stat-label">يوم متتالي</span>
                    </div>
                </div>
                <h3>سجل النشاط</h3>
                <div id="xpLog" class="log-list"></div>
            </div>
        </main>
    </div>

    <!-- Admin App -->
    <div id="adminApp" class="app-container" style="display:none">
        <nav class="bottom-nav" id="adminNav">
            <button class="nav-item active" data-page="dashboard">
                <span class="nav-icon">📊</span>
                <span class="nav-label">لوحة التحكم</span>
            </button>
            <button class="nav-item" data-page="adminLessons">
                <span class="nav-icon">📚</span>
                <span class="nav-label">الدروس</span>
            </button>
            <button class="nav-item" data-page="adminWords">
                <span class="nav-icon">✍️</span>
                <span class="nav-label">الكلمات</span>
            </button>
            <button class="nav-item" data-page="adminStudents">
                <span class="nav-icon">👥</span>
                <span class="nav-label">الطلاب</span>
            </button>
            <button class="nav-item" data-page="adminSettings">
                <span class="nav-icon">⚙️</span>
                <span class="nav-label">الإعدادات</span>
            </button>
        </nav>
        
        <main id="adminPages">
            <div id="page-dashboard" class="page active">
                <h2 class="page-title">لوحة التحكم</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <span class="stat-value" id="dashStudents">0</span>
                        <span class="stat-label">طالب</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value" id="dashActive">0</span>
                        <span class="stat-label">نشط</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value" id="dashPending">0</span>
                        <span class="stat-label">مدفوعات معلقة</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value" id="dashRevenue">0$</span>
                        <span class="stat-label">الإيرادات</span>
                    </div>
                </div>
                <div id="pendingPayments" class="pending-list"></div>
            </div>

            <div id="page-adminLessons" class="page">
                <h2 class="page-title">إدارة الدروس</h2>
                <button class="btn-primary" onclick="showAddLesson()">+ إضافة درس</button>
                <div id="adminLessonsList" class="admin-list"></div>
            </div>

            <div id="page-adminWords" class="page">
                <h2 class="page-title">إدارة الكلمات</h2>
                <button class="btn-primary" onclick="showAddWord()">+ إضافة كلمة</button>
                <div id="adminWordsList" class="admin-list"></div>
            </div>

            <div id="page-adminStudents" class="page">
                <h2 class="page-title">الطلاب</h2>
                <input type="text" id="studentSearch" class="search-input" placeholder="بحث عن طالب..." oninput="searchStudents()">
                <div id="adminStudentsList" class="admin-list"></div>
            </div>

            <div id="page-adminSettings" class="page">
                <h2 class="page-title">الإعدادات</h2>
                <div class="settings-form">
                    <label>رابط مجموعة النقاش</label>
                    <input type="text" id="groupLinkInput" class="form-input">
                    <button class="btn-primary" onclick="saveGroupLink()">حفظ</button>
                </div>
            </div>
        </main>
    </div>

    <script src="config.js"></script>
    <script src="app.js"></script>
</body>
</html>
"""
with open(os.path.join(WEB_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(index_html)

# ============================================================
# 3. CSS — Professional Light Theme
# ============================================================
css = """/* ====== YAMEN ACADEMY — Light Theme ====== */
:root {
    --primary: #3B82F6;
    --primary-light: #DBEAFE;
    --gold: #F59E0B;
    --gold-light: #FEF3C7;
    --bg: #F8FAFC;
    --card: #FFFFFF;
    --text: #1E293B;
    --muted: #94A3B8;
    --success: #10B981;
    --success-light: #D1FAE5;
    --danger: #EF4444;
    --danger-light: #FEE2E2;
    --radius: 16px;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-lg: 0 10px 40px rgba(0,0,0,0.08);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Cairo', 'Inter', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
    -webkit-tap-highlight-color: transparent;
}

.loading-screen {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    height: 100vh; gap: 16px;
}
.loader {
    width: 48px; height: 48px;
    border: 4px solid var(--primary-light);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.app-container { padding-bottom: 80px; }

/* ====== BOTTOM NAV ====== */
.bottom-nav {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: var(--card); border-top: 1px solid #E2E8F0;
    display: flex; justify-content: space-around; padding: 8px 4px;
    z-index: 100; box-shadow: 0 -2px 10px rgba(0,0,0,0.04);
}
.nav-item {
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    background: none; border: none; padding: 8px 12px;
    cursor: pointer; color: var(--muted); transition: all 0.2s;
    font-family: 'Cairo', sans-serif; font-size: 12px;
}
.nav-item .nav-icon { font-size: 22px; }
.nav-item.active { color: var(--primary); font-weight: 700; }

/* ====== PAGES ====== */
.page { display: none; padding: 20px 16px; animation: fadeIn 0.3s; }
.page.active { display: block; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.page-title { font-size: 24px; font-weight: 800; margin-bottom: 20px; color: var(--text); }

/* ====== HERO CARD ====== */
.hero-card {
    background: linear-gradient(135deg, var(--primary), #2563EB);
    border-radius: var(--radius); padding: 32px 24px;
    text-align: center; color: white; margin-bottom: 24px;
    box-shadow: var(--shadow-lg);
}
.hero-avatar { font-size: 56px; margin-bottom: 12px; }
.hero-name { font-size: 22px; font-weight: 800; }
.hero-level { font-size: 14px; opacity: 0.85; margin-bottom: 16px; }
.xp-bar-container {
    background: rgba(255,255,255,0.2); border-radius: 10px;
    height: 8px; position: relative; overflow: hidden;
}
.xp-bar {
    height: 100%; background: var(--gold); border-radius: 10px;
    transition: width 0.5s ease; width: 0%;
}
.xp-text { font-size: 12px; margin-top: 6px; display: block; opacity: 0.9; }

/* ====== QUICK ACTIONS ====== */
.quick-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.action-card {
    background: var(--card); border: 1px solid #E2E8F0; border-radius: var(--radius);
    padding: 20px 16px; text-align: center; cursor: pointer;
    transition: all 0.2s; box-shadow: var(--shadow);
    font-family: 'Cairo', sans-serif; font-size: 14px; color: var(--text);
}
.action-card:active { transform: scale(0.97); background: var(--primary-light); }
.action-icon { font-size: 32px; display: block; margin-bottom: 8px; }
.action-label { font-weight: 600; }

/* ====== COURSES GRID ====== */
.courses-grid { display: flex; flex-direction: column; gap: 12px; }
.course-card {
    background: var(--card); border-radius: var(--radius); padding: 20px;
    box-shadow: var(--shadow); cursor: pointer; transition: all 0.2s;
    border-right: 4px solid var(--primary);
}
.course-card:active { transform: scale(0.98); }
.course-name { font-size: 18px; font-weight: 700; }
.course-level { font-size: 13px; color: var(--muted); }
.course-progress { height: 4px; background: #E2E8F0; border-radius: 2px; margin-top: 8px; }
.course-progress-bar { height: 100%; background: var(--primary); border-radius: 2px; }

/* ====== LESSON VIEW ====== */
.lesson-media { width: 100%; border-radius: var(--radius); margin-bottom: 16px; }
.lesson-text { line-height: 1.8; font-size: 16px; color: var(--text); white-space: pre-wrap; }
.lesson-actions { display: flex; flex-direction: column; gap: 10px; margin-top: 20px; }

/* ====== SPELLING ====== */
.spelling-card {
    background: var(--card); border-radius: var(--radius); padding: 32px 24px;
    text-align: center; box-shadow: var(--shadow);
}
.spelling-hint { font-size: 16px; color: var(--muted); margin-bottom: 20px; }
.spelling-input {
    width: 100%; padding: 14px 16px; border: 2px solid #E2E8F0;
    border-radius: 12px; font-size: 18px; text-align: center;
    font-family: 'Cairo', sans-serif; outline: none; transition: border 0.2s;
}
.spelling-input:focus { border-color: var(--primary); }
.spelling-result { margin-top: 12px; font-size: 18px; font-weight: 700; }

/* ====== STATS ====== */
.stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; }
.stat-card {
    background: var(--card); border-radius: var(--radius); padding: 20px;
    text-align: center; box-shadow: var(--shadow);
}
.stat-value { font-size: 28px; font-weight: 800; color: var(--primary); display: block; }
.stat-label { font-size: 13px; color: var(--muted); }

/* ====== BUTTONS ====== */
.btn-primary {
    background: var(--primary); color: white; border: none;
    padding: 12px 24px; border-radius: 12px; font-size: 16px;
    font-weight: 700; cursor: pointer; transition: all 0.2s;
    font-family: 'Cairo', sans-serif; width: 100%; margin-bottom: 12px;
}
.btn-primary:active { transform: scale(0.97); opacity: 0.9; }
.btn-success { background: var(--success); }
.btn-danger { background: var(--danger); }
.btn-gold { background: var(--gold); color: white; }
.btn-sm { padding: 8px 16px; font-size: 13px; width: auto; }

/* ====== ADMIN LISTS ====== */
.admin-list { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; }
.admin-item {
    background: var(--card); border-radius: var(--radius); padding: 16px;
    box-shadow: var(--shadow); display: flex; justify-content: space-between;
    align-items: center;
}
.search-input, .form-input {
    width: 100%; padding: 12px 16px; border: 2px solid #E2E8F0;
    border-radius: 12px; font-size: 15px; font-family: 'Cairo', sans-serif;
    margin-bottom: 12px; outline: none;
}
.search-input:focus, .form-input:focus { border-color: var(--primary); }
.settings-form { background: var(--card); padding: 20px; border-radius: var(--radius); box-shadow: var(--shadow); }
.settings-form label { font-weight: 600; display: block; margin-bottom: 8px; }

/* ====== PENDING PAYMENTS ====== */
.pending-list { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; }
.pending-item {
    background: var(--card); border-radius: var(--radius); padding: 16px;
    box-shadow: var(--shadow); display: flex; justify-content: space-between;
    align-items: center;
}
.pending-actions { display: flex; gap: 8px; }

/* ====== LOG ====== */
.log-list { display: flex; flex-direction: column; gap: 8px; }
.log-item {
    background: var(--card); padding: 12px 16px; border-radius: 12px;
    font-size: 14px; display: flex; justify-content: space-between;
}
.log-xp { color: var(--success); font-weight: 700; }

/* ====== RESPONSIVE ====== */
@media (min-width: 768px) {
    .quick-actions { grid-template-columns: 1fr 1fr 1fr; }
    .stats-grid { grid-template-columns: 1fr 1fr 1fr 1fr; }
    .courses-grid { max-width: 600px; margin: 0 auto; }
}
"""
with open(os.path.join(WEB_DIR, "style.css"), "w", encoding="utf-8") as f:
    f.write(css)

# ============================================================
# 4. JAVASCRIPT — Full App Logic
# ============================================================
app_js = """// Yamen Academy WebApp
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
"""
with open(os.path.join(WEB_DIR, "app.js"), "w", encoding="utf-8") as f:
    f.write(app_js)

# ============================================================
# 5. BACKEND API — Simple Flask server
# ============================================================
api_code = '''"""Yamen Academy API Server"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3, json, os, asyncio

app = Flask(__name__)
CORS(app)
DB_PATH = r"C:\\yamen_academy\\data\\academy.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def dict_rows(rows):
    return [dict(r) for r in rows] if rows else []

# ====== STUDENT APIs ======
@app.route("/api/student/me")
def student_me():
    uid = json.loads(request.headers.get("X-Telegram-User", "{}")).get("id")
    conn = get_conn()
    row = conn.execute("SELECT * FROM students WHERE user_id=?", (uid,)).fetchone()
    if row: return jsonify(dict(row))
    return jsonify({"xp": 0, "level": "A1"})

@app.route("/api/courses")
def courses():
    uid = json.loads(request.headers.get("X-Telegram-User", "{}")).get("id")
    conn = get_conn()
    student = conn.execute("SELECT level FROM students WHERE user_id=?", (uid,)).fetchone()
    level = student["level"] if student else "A1"
    rows = conn.execute("SELECT * FROM courses WHERE level=? ORDER BY id", (level,)).fetchall()
    return jsonify(dict_rows(rows))

@app.route("/api/courses/<int:cid>/lessons")
def course_lessons(cid):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM lessons WHERE course_id=? ORDER BY order_num", (cid,)).fetchall()
    return jsonify(dict_rows(rows))

@app.route("/api/lessons/<int:lid>")
def get_lesson(lid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM lessons WHERE id=?", (lid,)).fetchone()
    if not row: return jsonify({}), 404
    lesson = dict(row)
    quiz = conn.execute("SELECT id FROM lesson_quizzes WHERE lesson_id=?", (lid,)).fetchone()
    lesson["has_quiz"] = quiz is not None
    return jsonify(lesson)

@app.route("/api/spelling/next")
def spelling_next():
    uid = json.loads(request.headers.get("X-Telegram-User", "{}")).get("id")
    conn = get_conn()
    row = conn.execute("SELECT * FROM spelling_words ORDER BY RANDOM() LIMIT 1").fetchone()
    return jsonify(dict(row)) if row else jsonify({})

@app.route("/api/spelling/answer", methods=["POST"])
def spelling_answer():
    data = request.json
    conn = get_conn()
    conn.execute("INSERT INTO xp_log(user_id,amount,reason) VALUES(?,?,?)",
                 (data.get("user_id"), 10 if data.get("correct") else 0, "spelling"))
    conn.commit()
    return jsonify({"ok": True})

@app.route("/api/student/xp-log")
def xp_log():
    uid = json.loads(request.headers.get("X-Telegram-User", "{}")).get("id")
    conn = get_conn()
    rows = conn.execute("SELECT * FROM xp_log WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (uid,)).fetchall()
    return jsonify(dict_rows(rows))

# ====== ADMIN APIs ======
@app.route("/api/admin/stats")
def admin_stats():
    conn = get_conn()
    total = conn.execute("SELECT count(*) as c FROM students").fetchone()["c"]
    active = conn.execute("SELECT count(*) as c FROM subscriptions WHERE active=1").fetchone()["c"]
    pending = conn.execute("SELECT count(*) as c FROM payments WHERE status='pending'").fetchone()["c"]
    return jsonify({"total_students": total, "active_subs": active, "pending_payments": pending, "revenue": 0})

@app.route("/api/admin/pending-payments")
def pending_payments():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM payments WHERE status='pending' ORDER BY created_at DESC").fetchall()
    return jsonify(dict_rows(rows))

@app.route("/api/admin/payments/<int:pid>/approve", methods=["POST"])
def approve_payment(pid):
    conn = get_conn()
    conn.execute("UPDATE payments SET status='approved' WHERE id=?", (pid,))
    payment = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
    if payment:
        conn.execute("INSERT OR REPLACE INTO subscriptions(user_id,plan_name,end_date,active) VALUES(?,?,datetime('now','+30 days'),1)",
                     (payment["user_id"], payment.get("plan_name", "شهري")))
    conn.commit()
    return jsonify({"ok": True})

@app.route("/api/admin/payments/<int:pid>/reject", methods=["POST"])
def reject_payment(pid):
    conn = get_conn()
    conn.execute("UPDATE payments SET status='rejected' WHERE id=?", (pid,))
    conn.commit()
    return jsonify({"ok": True})

@app.route("/api/admin/lessons")
def admin_lessons():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM lessons ORDER BY id DESC LIMIT 50").fetchall()
    return jsonify(dict_rows(rows))

@app.route("/api/admin/words")
def admin_words():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM spelling_words ORDER BY id DESC LIMIT 100").fetchall()
    return jsonify(dict_rows(rows))

@app.route("/api/admin/students")
def admin_students():
    q = request.args.get("q", "")
    conn = get_conn()
    if q:
        rows = conn.execute("SELECT * FROM students WHERE full_name LIKE ? OR user_id LIKE ? LIMIT 50",
                           (f"%{q}%", f"%{q}%")).fetchall()
    else:
        rows = conn.execute("SELECT * FROM students ORDER BY xp DESC LIMIT 50").fetchall()
    return jsonify(dict_rows(rows))

@app.route("/api/settings/group-link")
def group_link():
    conn = get_conn()
    row = conn.execute("SELECT value FROM group_settings WHERE key='discussion_group'").fetchone()
    return jsonify({"link": row["value"] if row else "https://t.me/+2NkF901AApcyODk0"})

@app.route("/api/admin/settings/group-link", methods=["POST"])
def save_group_link():
    link = request.json.get("link", "")
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO group_settings(key,value) VALUES('discussion_group',?)", (link,))
    conn.commit()
    return jsonify({"ok": True})

@app.route("/api/quizzes/lesson/<int:lid>")
def lesson_quiz(lid):
    conn = get_conn()
    quiz = conn.execute("SELECT id FROM lesson_quizzes WHERE lesson_id=?", (lid,)).fetchone()
    if not quiz: return jsonify([])
    rows = conn.execute("SELECT * FROM quiz_questions WHERE quiz_id=?", (quiz["id"],)).fetchall()
    return jsonify(dict_rows(rows))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
'''

api_path = os.path.join(BASE, "api_server.py")
with open(api_path, "w", encoding="utf-8") as f:
    f.write(api_code)

print("========== BUILD COMPLETE ==========")
print(f"WebApp: {os.path.join(WEB_DIR, 'index.html')}")
print(f"API: {api_path}")
print("""
Next steps:
1. Install: pip install flask flask-cors
2. Run API: python api_server.py
3. Serve WebApp: python -m http.server 8080 --directory webapp
4. Set bot menu button in BotFather: https://your-domain.com/webapp/
""")

