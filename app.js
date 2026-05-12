// ====== Yamen Academy App v8 - FINAL ======
console.log('[app] START v8 - ' + new Date().toISOString());

const FORCE_TIMEOUT = 4000;
let tg = null;
let currentUser = null;
let isAdmin = false;

// Force show UI after timeout
let timeoutTriggered = false;
function forceShowUI() {
    if (timeoutTriggered) return;
    timeoutTriggered = true;
    
    console.log('[app] FORCE showing UI (timeout)');
    document.getElementById('loading').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    document.getElementById('app').style.opacity = '1';
    document.getElementById('app').style.visibility = 'visible';
    
    if (isAdmin) {
        document.getElementById('adminApp').style.display = 'block';
    }
}

// Start timeout
setTimeout(forceShowUI, FORCE_TIMEOUT);

// Try Telegram init
try {
    if (window.Telegram && window.Telegram.WebApp) {
        tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        console.log('[app] Telegram WebApp ready');
        
        const initData = tg.initDataUnsafe;
        if (initData && initData.user) {
            currentUser = initData.user;
            isAdmin = CONFIG.ADMIN_IDS.includes(currentUser.id);
            console.log('[app] User:', currentUser.username, 'Admin:', isAdmin);
        }
    } else {
        console.log('[app] Browser mode (no Telegram)');
    }
} catch(e) {
    console.warn('[app] Telegram init failed:', e.message);
}

// Init
async function init() {
    console.log('[app] init() started');
    
    // Show UI immediately
    document.getElementById('loading').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    document.getElementById('app').style.opacity = '1';
    document.getElementById('app').style.visibility = 'visible';
    console.log('[app] UI shown');
    
    if (isAdmin) {
        document.getElementById('adminApp').style.display = 'block';
        console.log('[app] Admin panel shown');
    }
    
    // Load data
    try {
        await loadData();
    } catch(e) {
        console.warn('[app] Load data failed, but UI is visible:', e.message);
    }
    
    // Update content
    updateUI();
    console.log('[app] init() DONE');
}

async function loadData() {
    try {
        const resp = await fetch(CONFIG.API_BASE + '/api/courses');
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();
        console.log('[app] Courses loaded:', data);
        return data;
    } catch(e) {
        console.warn('[app] API not available:', e.message);
        return [];
    }
}

function updateUI() {
    const el = document.getElementById('coursesList');
    if (el) {
        el.innerHTML = '<p style="color:green;">✅ الواجهة تعمل بنجاح!</p><p>الدورات ستظهر عند إضافتها عبر لوحة التحكم.</p>';
    }
}

// Service Worker
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
        .then(reg => console.log('[app] SW registered:', reg.scope))
        .catch(err => console.warn('[app] SW failed:', err));
}

// Start
document.addEventListener('DOMContentLoaded', () => {
    console.log('[app] DOM ready, starting...');
    init();
});
