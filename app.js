// Yamen Academy LMS - Full UI Activation vFINAL
(function() {
    console.log('[LMS] START - Forced render mode');

    const CONFIG = {
        API_BASE: window.location.origin || '',
        ADMIN_IDS: [469136626, 5572314718]
    };

    // ===== FORCE SHOW UI IMMEDIATELY =====
    function hideLoading() {
        var el = document.getElementById('loading');
        if (el) { el.style.display = 'none'; }
        el = document.getElementById('loading-screen');
        if (el) { el.style.display = 'none'; }
        console.log('[LMS] Loading hidden');
    }

    function showApp() {
        var el = document.getElementById('app');
        if (el) {
            el.style.display = 'block';
            el.style.opacity = '1';
            el.style.visibility = 'visible';
        }
        console.log('[LMS] App shown');
    }

    function showAdmin() {
        var el = document.getElementById('adminApp');
        if (el) { el.style.display = 'block'; }
    }

    // ===== RENDER COURSES =====
    function renderCourses(data) {
        var el = document.getElementById('coursesList');
        if (!el) return;

        if (data && data.length > 0) {
            var html = '';
            data.forEach(function(c) {
                html += '<div class="course-card" style="background:#fff;border-radius:12px;padding:20px;margin:10px 0;box-shadow:0 2px 8px rgba(0,0,0,0.08)">' +
                    '<h3 style="color:#3B82F6;margin:0 0 10px">' + (c.title || 'دورة') + '</h3>' +
                    '<p style="color:#666">' + (c.description || '') + '</p>' +
                    '<span style="display:inline-block;background:#3B82F6;color:#fff;padding:4px 12px;border-radius:20px;font-size:12px">' + (c.level || 'A1') + '</span>' +
                    '</div>';
            });
            el.innerHTML = html;
        } else {
            el.innerHTML = '<div style="text-align:center;padding:40px">' +
                '<h2 style="color:#10B981;font-size:32px">✅ الأكاديمية تعمل!</h2>' +
                '<p style="color:#666;font-size:18px;margin:10px 0">الواجهة جاهزة لاستقبال الدورات</p>' +
                '<p style="color:#999">يمكنك إضافة دورات من لوحة التحكم</p>' +
                '<a href="/admin" style="display:inline-block;margin-top:15px;padding:12px 24px;background:#3B82F6;color:#fff;border-radius:10px;text-decoration:none;font-size:16px">🔧 لوحة التحكم</a>' +
                '</div>';
        }
    }

    // ===== LOAD COURSES =====
    function loadCourses() {
        var apiUrl = CONFIG.API_BASE + '/api/courses';

        fetch(apiUrl, { signal: AbortSignal.timeout(5000) })
            .then(function(r) { return r.json(); })
            .then(function(data) { renderCourses(data); })
            .catch(function() {
                // Fallback: try /api/data
                fetch(CONFIG.API_BASE + '/api/data', { signal: AbortSignal.timeout(3000) })
                    .then(function(r) { return r.json(); })
                    .then(function(data) { renderCourses(data.courses || []); })
                    .catch(function() {
                        renderCourses([]); // Show welcome message
                    });
            });
    }

    // ===== MAIN INIT - NO CONDITIONS =====
    function init() {
        console.log('[LMS] init() - force rendering');

        // 1. Hide loading immediately
        hideLoading();

        // 2. Show main app ALWAYS
        showApp();

        // 3. Load courses
        loadCourses();

        // 4. Check admin
        try {
            if (window.Telegram && window.Telegram.WebApp) {
                var tg = window.Telegram.WebApp;
                tg.ready();
                tg.expand();
                var user = tg.initDataUnsafe && tg.initDataUnsafe.user;
                if (user && CONFIG.ADMIN_IDS.indexOf(user.id) >= 0) {
                    showAdmin();
                }
            }
        } catch(e) { console.log('[LMS] No Telegram'); }

        console.log('[LMS] READY - UI fully rendered');
    }

    // ===== START =====
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Ultimate fallback: force show after 2 seconds
    setTimeout(function() {
        hideLoading();
        showApp();
    }, 2000);

})();
