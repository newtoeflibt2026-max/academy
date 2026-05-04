// app.js - Navigation
function navigate(screen) {
    // إخفاء كل الشاشات
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    // إظهار الشاشة المطلوبة
    const target = document.getElementById('screen-' + screen);
    if (target) {
        target.classList.add('active');
        // تحميل محتوى الشاشة
        if (screen === 'placement') loadPlacement();
        else if (screen === 'courses') loadCourses();
        else if (screen === 'writing') loadWriting();
        else if (screen === 'speaking') loadSpeaking();
        else if (screen === 'daily') loadDaily();
        else if (screen === 'leaderboard') loadLeaderboard();
        else if (screen === 'subscribe') loadSubscribe();
    }
}
