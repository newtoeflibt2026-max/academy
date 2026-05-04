async function loadGamification() {
    const data = await api('/gamification');
    if (!data) return;
    document.getElementById('set-challenge-timer').value = data.challenge_timer || 5;
    document.getElementById('set-xp-multiplier').value = data.xp_multiplier || 1;
    
    // Leaderboard
    const lb = data.leaderboard || [];
    document.getElementById('leaderboard-admin').innerHTML = lb.length === 0
        ? '<p class="text-center">لا يوجد متصدرين بعد</p>'
        : lb.map((r, i) => 
            '<div class="leader-row">' +
            '<span class="leader-rank">' + (i+1) + '</span>' +
            '<span class="leader-name">' + r.full_name + '</span>' +
            '<span class="leader-xp">' + r.xp + ' XP</span>' +
            '</div>'
        ).join('');
}

async function sendDailyChallenge() {
    const result = await api('/send_challenge');
    if (result && result.success) showToast('📨 تم إرسال تحدي اليوم');
    else showToast('❌ فشل الإرسال');
}

async function saveSetting(key) {
    const el = document.getElementById('set-' + key);
    if (!el) return;
    await api('/save_setting', { key, value: el.value });
    showToast('✅ تم الحفظ');
}
