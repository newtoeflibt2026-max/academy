// v10 - No localStorage, no sessionStorage, instant UI
console.log('[app] v10 - Direct injection mode');

const CONFIG = window.CONFIG || { API_BASE: window.location.origin, ADMIN_IDS: [469136626, 5572314718] };
let isAdmin = false;

// Show UI after max 1.5 seconds - NO exceptions
setTimeout(function() {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    if (isAdmin) document.getElementById('adminApp').style.display = 'block';
    console.log('[app] UI forced visible');
}, 1500);

// Init
(async function() {
    // Telegram (optional)
    try {
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
            var u = window.Telegram.WebApp.initDataUnsafe;
            if (u && u.user) isAdmin = CONFIG.ADMIN_IDS.indexOf(u.user.id) >= 0;
        }
    } catch(e) { console.warn('[app] No Telegram'); }

    // Show immediately
    document.getElementById('loading').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    if (isAdmin) document.getElementById('adminApp').style.display = 'block';

    // Load courses (non-blocking)
    try {
        var r = await fetch(CONFIG.API_BASE + '/api/courses', { signal: AbortSignal.timeout(3000) });
        var data = await r.json();
        var el = document.getElementById('coursesList');
        if (data && data.length) {
            el.innerHTML = data.map(function(c) {
                return '<div style="padding:15px;border-bottom:1px solid #eee">'
                    + '<h3>' + (c.title || 'دورة') + '</h3>'
                    + '<p>' + (c.description || '') + '</p>'
                    + '<span style="color:#3B82F6">مستوى: ' + (c.level || 'A1') + '</span>'
                    + '</div>';
            }).join('');
        } else {
            el.innerHTML = '<p style="text-align:center;color:#666">لا توجد دورات حالياً. <a href="/admin" style="color:#3B82F6">أضف دورة</a></p>';
        }
    } catch(e) {
        console.warn('[app] Courses load failed, but UI is visible');
        document.getElementById('coursesList').innerHTML = '<p style="color:#3B82F6">الدورات غير متاحة مؤقتاً - لكن التطبيق يعمل!</p>';
    }

    console.log('[app] Ready');
})();
