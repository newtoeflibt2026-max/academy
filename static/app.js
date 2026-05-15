// ============================================================
// Yamen Academy — Student Dashboard (Live Data Binding)
// ============================================================
const API = window.location.origin + '/api';
let USER_ID = null;

// Try to get user ID from Telegram WebApp
if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    tg.ready();
    USER_ID = tg.initDataUnsafe?.user?.id || null;
    if (!USER_ID) USER_ID = 5602495831; // fallback
} else {
    USER_ID = 5602495831; // default for development
}

console.log('[Yamen] USER_ID:', USER_ID);

// ═══════ API HELPERS ═══════
async function apiGet(path) {
    try {
        const res = await fetch(API + path);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch(e) {
        console.error('[Yamen] API Error:', path, e.message);
        return null;
    }
}

function toast(msg, type='success') {
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(()=>el.remove(), 3000);
}

// ═══════ LOAD ALL DATA ═══════
async function loadDashboard() {
    // 1. Student profile
    const profile = await apiGet(`/admin/students`);
    let student = null;
    if (profile && profile.students) {
        student = profile.students.find(s => s.user_id == USER_ID);
    }

    if (student) {
        document.getElementById('welcomeName').innerHTML = `أهلاً بك يا ${student.first_name || 'بطل'}!`;
        document.getElementById('welcomeMsg').textContent = 'طريق الـ 90 يبدأ من هنا! 💪';
        document.getElementById('xpValue').textContent = `${student.xp || 0} XP`;
        document.getElementById('streakValue').textContent = `${student.level || 1} أيام`;
        document.getElementById('levelValue').textContent = student.level >= 5 ? 'متقدم' : student.level >= 3 ? 'متوسط' : 'مبتدئ';
    } else {
        document.getElementById('welcomeName').textContent = 'أهلاً بك في أول يوم في طريق النجاح! 🌟';
        document.getElementById('welcomeMsg').textContent = 'ابدأ رحلتك التعليمية الآن';
        document.getElementById('xpValue').textContent = '0 XP';
        document.getElementById('streakValue').textContent = 'اليوم 1';
        document.getElementById('levelValue').textContent = 'مبتدئ';
    }

    // 2. Leaderboard
    const lb = await apiGet('/leaderboard');
    const lbList = document.getElementById('leaderboardList');
    if (lb && lb.leaderboard && lb.leaderboard.length > 0) {
        const medals = ['🥇','🥈','🥉','4️⃣','5️⃣'];
        const rowClasses = ['lb-gold','lb-silver','lb-bronze','',''];
        lbList.innerHTML = lb.leaderboard.map((s,i) => `
            <div class="lb-row ${rowClasses[i]||''} flex items-center gap-3 px-4 py-3.5">
                <div class="relative flex-shrink-0">
                    <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xl bg-white/10">${['👸','🧑‍🎓','👩‍🏫','🧔','👩'][i]||'👤'}</div>
                    <div class="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-gold flex items-center justify-center text-navy text-xs font-black border-2 border-navy">${i+1}</div>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="font-bold text-white text-sm truncate">${s.first_name || 'طالب'}</p>
                    <span class="text-xs text-gold/60">${i===0?'متفوق':i===1?'نشيط':'مثابر'}</span>
                </div>
                <div class="text-left flex-shrink-0">
                    <p class="text-gold font-black text-base">${s.xp||0}</p>
                    <p class="text-xs text-gold/50">XP</p>
                </div>
            </div>
        `).join('');
    } else {
        lbList.innerHTML = '<p class="text-center text-white/30 text-sm py-8">🎓 لا يوجد طلاب بعد. كن الأول!</p>';
    }

    // 3. Error bank
    const errors = await apiGet(`/error_bank/${USER_ID}`);
    const errCount = document.getElementById('errorCount');
    if (errors && errors.reviews) {
        errCount.textContent = errors.reviews.length;
        const cats = {};
        errors.reviews.forEach(e => { cats[e.skill_type] = (cats[e.skill_type]||0)+1; });
        document.getElementById('errorCategories').innerHTML = Object.entries(cats).map(([k,v]) =>
            `<div class="flex items-center gap-3 p-3 rounded-xl" style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.15)">
                <div class="w-9 h-9 rounded-lg bg-red-500/15 flex items-center justify-center text-lg flex-shrink-0">${k==='speaking'?'🗣️':k==='writing'?'📝':'📚'}</div>
                <div class="flex-1 min-w-0"><p class="text-sm font-semibold text-white">${k}</p></div>
                <span class="text-xs font-bold text-red-400">${v} خطأ</span>
            </div>`
        ).join('') || '<p class="text-sm text-red-300/50">✅ لا توجد أخطاء!</p>';

        if (errors.reviews.length === 0) {
            document.getElementById('reviewBtn').textContent = '✅ لا توجد أخطاء للمراجعة';
            document.getElementById('reviewBtn').style.background = 'linear-gradient(135deg,#22c55e,#16a34a)';
        }
    } else {
        errCount.textContent = '0';
        document.getElementById('errorCategories').innerHTML = '<p class="text-sm text-green-400/70">✅ لا توجد أخطاء مسجلة — أحسنت!</p>';
        document.getElementById('reviewBtn').textContent = '✅ ممتاز! لا أخطاء';
        document.getElementById('reviewBtn').style.background = 'linear-gradient(135deg,#22c55e,#16a34a)';
    }

    // 4. Progress
    updateProgress(student);
}

function updateProgress(student) {
    const xp = student?.xp || 0;
    const target = 90;
    const pct = Math.min(xp / 10, 90);
    const score = Math.round(pct);
    const r = 80;
    const circ = 2 * Math.PI * r;

    document.getElementById('progressScore').textContent = score;
    document.getElementById('progressPct').textContent = `${Math.round(score/90*100)}%`;
    document.getElementById('neededScore').textContent = `${target - score} درجة إضافية`;

    setTimeout(() => {
        const arc = document.getElementById('progressArc');
        if (arc) {
            arc.style.strokeDasharray = circ;
            arc.style.strokeDashoffset = circ * (1 - score/90);
        }
        document.getElementById('bar1').style.width = `${Math.min(score/90*100, 100)}%`;
        document.getElementById('bar2').style.width = `${Math.min((score-10)/90*100, 100)}%`;
        document.getElementById('bar3').style.width = `${Math.min((score-20)/90*100, 100)}%`;
        document.getElementById('skill1').textContent = `${Math.round(score/5)}/18`;
        document.getElementById('skill2').textContent = `${Math.round(score/4)}/22`;
        document.getElementById('skill3').textContent = `${Math.round(score/4.5)}/20`;
    }, 500);
}

// ═══════ SKILL ACTIONS ═══════
async function startSkill(skillType) {
    toast(`🎯 جاري تحميل تمرين: ${skillType}...`, 'success');
    try {
        const courses = await apiGet('/courses');
        if (!courses || !courses.courses || courses.courses.length === 0) {
            toast('📚 لا توجد دورات بعد. تواصل مع الأدمن.', 'error');
            return;
        }
        const match = courses.courses.find(c => c.skill_type === skillType && c.is_active);
        if (!match) {
            toast(`⚠️ لا توجد تمارين "${skillType}" متاحة حالياً`, 'error');
            return;
        }
        // Timer beep logic
        const timeLimit = match.time_limit || 45;
        showSkillModal(skillType, timeLimit, match);
    } catch(e) {
        toast('⚠️ خطأ في تحميل التمرين', 'error');
    }
}

function showSkillModal(skillType, timeLimit, course) {
    const modal = document.createElement('div');
    modal.className = 'skill-modal';
    modal.innerHTML = `
        <div>
            <h2 class="text-xl font-black text-gold mb-2">🎯 ${skillType === 'speaking' ? 'تحدّث' : skillType === 'spelling' ? 'إكمال كلمة' : skillType === 'writing' ? 'ترتيب جمل' : skillType === 'email' ? 'كتابة إيميل' : 'استماع وترديد'}</h2>
            <p class="text-white/70 mb-4">${course.name || ''}</p>
            <div class="countdown" id="timer">${timeLimit}</div>
            <p class="text-xs text-white/40 mt-2">ثانية متبقية</p>
            <p class="text-sm text-white/60 mt-4">⏳ استعد... سيبدأ التمرين قريباً</p>
            <button onclick="this.closest('.skill-modal').remove()" class="mt-4 px-6 py-2 rounded-xl bg-red-500/20 text-red-300 border border-red-500/30 hover:bg-red-500/30 transition">إلغاء</button>
        </div>`;
    document.body.appendChild(modal);

    // Countdown + beep at 5s
    let remaining = timeLimit;
    const timerEl = modal.querySelector('#timer');
    const interval = setInterval(() => {
        remaining--;
        timerEl.textContent = remaining;
        if (remaining <= 5 && remaining > 0) {
            timerEl.classList.add('timer-warning');
            playBeep();
        }
        if (remaining <= 0) {
            clearInterval(interval);
            timerEl.textContent = '⏰ انتهى الوقت!';
            playBeep();
            setTimeout(() => modal.remove(), 2000);
        }
    }, 1000);

    modal.addEventListener('click', (e) => { if (e.target === modal) { clearInterval(interval); modal.remove(); } });
}

function playBeep() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.frequency.value = 880;
        osc.type = 'sine';
        gain.gain.value = 0.3;
        osc.start(); osc.stop(ctx.currentTime + 0.15);
    } catch(e) { /* AudioContext may not be available */ }
}

// ═══════ ERROR BANK REVIEW ═══════
async function startReview() {
    toast('🔬 جاري تحميل أخطائك للمراجعة...', 'success');
    const data = await apiGet(`/error_bank/${USER_ID}`);
    if (!data || !data.reviews || data.reviews.length === 0) {
        toast('✅ لا توجد أخطاء للمراجعة!', 'success');
        return;
    }
    const first = data.reviews[0];
    showReviewModal(first);
}

function showReviewModal(error) {
    const modal = document.createElement('div');
    modal.className = 'skill-modal';
    modal.innerHTML = `
        <div>
            <h2 class="text-xl font-black text-red-400 mb-2">🔬 مراجعة الأخطاء</h2>
            <p class="text-white/80 mb-3 text-lg">${error.question_text || 'سؤال'}</p>
            <p class="text-xs text-red-300/70 mb-4">إجابتك السابقة: <span class="text-white">${error.wrong_answer || '---'}</span></p>
            <div class="flex gap-3 justify-center">
                <button onclick="this.closest('.skill-modal').remove();reviewCorrect(${error.id})" class="px-6 py-3 rounded-xl bg-green-500/20 text-green-400 border border-green-500/30 font-bold">✅ صحيح</button>
                <button onclick="this.closest('.skill-modal').remove()" class="px-6 py-3 rounded-xl bg-red-500/20 text-red-300 border border-red-500/30 font-bold">❌ خطأ</button>
            </div>
        </div>`;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
}

async function reviewCorrect(errorBankId) {
    try {
        await fetch(API + '/error_bank/correct', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({user_id: USER_ID, error_bank_id: errorBankId})
        });
        toast('✅ تم تسجيل الإجابة الصحيحة!');
        loadDashboard(); // refresh
    } catch(e) {
        console.error(e);
    }
}

// ═══════ BOTTOM NAV ═══════
function setNav(btn) {
    document.querySelectorAll('.nav-item').forEach(n => {
        n.classList.remove('active');
        n.querySelector('span').classList.remove('text-gold'); n.querySelector('span').classList.add('text-white/40');
        const icon = n.querySelector('svg');
        if (icon) { icon.classList.remove('text-gold'); icon.classList.add('text-white/40'); }
    });
    btn.classList.add('active');
    const s = btn.querySelector('span');
    s.classList.remove('text-white/40'); s.classList.add('text-gold');
    const icon = btn.querySelector('svg');
    if (icon) { icon.classList.remove('text-white/40'); icon.classList.add('text-gold'); }
}

// ═══════ INIT ═══════
window.addEventListener('load', () => {
    console.log('[Yamen] Dashboard loaded. Fetching data...');
    loadDashboard();
});

// Auto-refresh every 60s
setInterval(loadDashboard, 60000);
