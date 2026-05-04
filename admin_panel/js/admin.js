// admin.js - Core Dashboard Logic
let currentPage = 'dashboard';

function switchPage(page) {
    currentPage = page;
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + page).classList.add('active');
    
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector('[data-page="' + page + '"]').classList.add('active');
    
    document.getElementById('page-title').textContent = 
        document.querySelector('[data-page="' + page + '"]').textContent.trim();
    
    // Auto-load page content
    if (page === 'dashboard') loadDashboard();
    else if (page === 'students') loadStudents();
    else if (page === 'courses') loadCourses();
    else if (page === 'payments') loadPayments();
    else if (page === 'vault') loadVault();
    else if (page === 'gamification') loadGamification();
    else if (page === 'settings') loadSettings();
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

async function refreshAll() {
    showToast('🔄 جاري التحديث...');
    if (currentPage === 'dashboard') await loadDashboard();
    else switchPage(currentPage);
    showToast('✅ تم التحديث');
}

async function loadDashboard() {
    const stats = await api('/stats');
    if (!stats) return;
    document.getElementById('stat-students').textContent = stats.total_students || 0;
    document.getElementById('stat-active').textContent = stats.active_students || 0;
    document.getElementById('stat-blocked').textContent = stats.blocked_students || 0;
    document.getElementById('stat-pending').textContent = stats.pending_payments || 0;
    document.getElementById('stat-subs').textContent = stats.active_subscriptions || 0;
    document.getElementById('stat-xp').textContent = stats.total_xp || 0;
    document.getElementById('pending-count').textContent = (stats.pending_payments || 0) + ' معلقة';
}

// Load on startup
document.addEventListener('DOMContentLoaded', () => loadDashboard());
