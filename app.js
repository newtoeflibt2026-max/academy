// ====== Yamen Academy v9 - DB Lock Proof ======
console.log('[app] v9 START');

const FORCE_SHOW_TIMEOUT = 3000;
const CONFIG = window.CONFIG || { API_BASE: window.location.origin, ADMIN_IDS: [469136626, 5572314718] };
let currentUser = null;
let isAdmin = false;

// Force show UI after timeout - NEVER stay on loading
setTimeout(() => {
    console.log('[app] Force timeout - showing UI');
    document.getElementById('loading').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    document.getElementById('app').style.opacity = '1';
    document.getElementById('app').style.visibility = 'visible';
    if (isAdmin) document.getElementById('adminApp').style.display = 'block';
}, FORCE_SHOW_TIMEOUT);

// Telegram init
try {
    if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
        const user = window.Telegram.WebApp.initDataUnsafe?.user;
        if (user) {
            currentUser = user;
            isAdmin = CONFIG.ADMIN_IDS.includes(user.id);
        }
    }
} catch(e) { console.warn('[app] No Telegram'); }

// Safe fetch - never throws
async function safeFetch(url) {
    try {
        const resp = await fetch(url, { signal: AbortSignal.timeout(4000) });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return await resp.json();
    } catch(e) {
        console.warn('[app] Fetch failed:', url, e.message);
        return null;
    }
}

// Load courses - fallback on fail
async function loadCourses() {
    const data = await safeFetch(CONFIG.API_BASE + '/api/courses');
    const el = document.getElementById('coursesList');
    if (!el) return;
    
    if (data && Array.isArray(data) && data.length > 0) {
        el.innerHTML = data.map(c => 
            '<div style="padding:15px;border-bottom:1px solid #eee;">' +
            '<h3>' + (c.title || 'دورة') + '</h3>' +
            '<p>' + (c.description || '') + '</p>' +
            '<span style="color:#3B82F6">مستوى: ' + (c.level || 'A1') + '</span>' +
            '</div>'
        ).join('');
    } else {
        el.innerHTML = 
            '<div style="text-align:center;padding:30px;">' +
            '<h2 style="color:#10B981;">✅ الأكاديمية تعمل!</h2>' +
            '<p style="color:#666;">لا توجد دورات حالياً. أضف دورات من لوحة التحكم.</p>' +
            '<a href="/admin" style="color:#3B82F6;">🔧 لوحة التحكم</a>' +
            '</div>';
    }
}

// Main init
async function init() {
    console.log('[app] init');
    
    // Show UI immediately
    document.getElementById('loading').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    document.getElementById('app').style.opacity = '1';
    document.getElementById('app').style.visibility = 'visible';
    
    if (isAdmin) document.getElementById('adminApp').style.display = 'block';
    
    // Load data (won't block UI)
    loadCourses();
    
    // SW
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').catch(()=>{});
    }
    
    console.log('[app] Ready');
}

document.addEventListener('DOMContentLoaded', init);
