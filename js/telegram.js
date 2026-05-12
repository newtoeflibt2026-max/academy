// telegram.js - Telegram WebApp API wrapper
const tg = window.Telegram.WebApp;

// تهيئة التطبيق
tg.ready();
tg.expand();
tg.enableClosingConfirmation();

// بيانات المستخدم من تيليجرام
const user = tg.initDataUnsafe?.user || {};
const userId = user.id || 0;
const userName = user.first_name || 'طالب';

// ألوان الثيم
document.documentElement.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#f5f5f5');
document.documentElement.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#1a1a1a');
document.documentElement.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#007AFF');
document.documentElement.style.setProperty('--tg-theme-secondary-bg-color', tg.themeParams.secondary_bg_color || '#ffffff');
document.documentElement.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color || '#e0e0e0');

// API URL (الخادم)
const API_URL = 'https://yamen-academy-api.vercel.app/api';

// دالة مساعدة للطلبات
async function apiRequest(endpoint, data = {}) {
    showLoading();
    try {
        const res = await fetch(API_URL + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, user_name: userName, ...data })
        });
        hideLoading();
        return await res.json();
    } catch (e) {
        hideLoading();
        return { error: 'تعذر الاتصال بالخادم' };
    }
}

function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

// مشاركة النتيجة
function shareResult(text) {
    if (tg.isVersionAtLeast('7.8')) {
        tg.shareToStory('', { text });
    }
}
