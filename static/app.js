const API = window.location.origin + '/api';
let USER_ID = null;
if (window.Telegram && window.Telegram.WebApp) { const tg = window.Telegram.WebApp; tg.ready(); USER_ID = tg.initDataUnsafe?.user?.id || null; }
if (!USER_ID) USER_ID = 5602495831;
console.log('[Yamen] USER_ID:', USER_ID);

async function apiGet(path) { try { const r = await fetch(API+path); return r.ok ? await r.json() : null; } catch(e) { console.error(e); return null; } }

function toast(msg) { const el = document.createElement('div'); el.className='toast'; el.style.cssText='background:#2e7d32;color:white'; el.textContent=msg; document.body.appendChild(el); setTimeout(()=>el.remove(),3000); }

async function loadDashboard() {
  const profile = await apiGet('/admin/students');
  let student = profile?.students?.find(s => s.user_id == USER_ID);
  if (student) {
    document.getElementById('welcomeName').textContent = 'أهلاً بك يا ' + (student.first_name || 'بطل') + '!';
    document.getElementById('welcomeMsg').textContent = 'طريق الـ 90 يبدأ من هنا! 💪';
    document.getElementById('xpValue').textContent = (student.xp || 0) + ' XP';
    document.getElementById('levelValue').textContent = ['مبتدئ','متوسط','متقدم','خبير'][Math.min((student.level||1)-1,3)];
  } else {
    document.getElementById('welcomeName').textContent = 'أهلاً بك في أول يوم في طريق النجاح! 🌟';
    document.getElementById('xpValue').textContent = '0 XP';
    document.getElementById('levelValue').textContent = 'مبتدئ';
  }

  // Leaderboard
  const lb = await apiGet('/leaderboard');
  const lbList = document.getElementById('leaderboardList');
  if (lb?.leaderboard?.length) {
    const medals = ['🥇','🥈','🥉','4️⃣','5️⃣']; const cls = ['lb-gold','lb-silver','lb-bronze','',''];
    lbList.innerHTML = lb.leaderboard.map((s,i) => `<div class="lb-row ${cls[i]||''} flex items-center gap-3 px-4 py-3"><div class="w-8 h-8 rounded-full bg-gold/20 flex items-center justify-center text-xs font-black">${i+1}</div><span class="flex-1 font-bold text-white text-sm">${s.first_name||'طالب'}</span><span class="text-gold font-black">${s.xp||0} XP</span></div>`).join('');
    document.getElementById('rankValue').textContent = lb.leaderboard.findIndex(s=>s.user_id==USER_ID)+1 || '---';
  } else lbList.innerHTML = '<p class="text-center text-white/30 py-8">🎓 كن الأول!</p>';

  // Error bank
  const errs = await apiGet('/error_bank/'+USER_ID);
  document.getElementById('errorCount').textContent = errs?.reviews?.length || 0;
  if (errs?.reviews?.length) {
    const cats = {}; errs.reviews.forEach(e=>{ cats[e.skill_type] = (cats[e.skill_type]||0)+1 });
    document.getElementById('errorCategories').innerHTML = Object.entries(cats).map(([k,v])=>`<div class="flex items-center gap-3 p-3 rounded-xl" style="background:rgba(239,68,68,.08)"><span class="text-lg">${k==='speaking'?'🗣️':k==='writing'?'📝':'📚'}</span><span class="text-sm text-white">${k}</span><span class="mr-auto text-red-400 font-bold">${v}</span></div>`).join('');
    document.getElementById('reviewBtn').textContent = '🔥 ابدأ مراجعة الأخطاء الآن';
    document.getElementById('reviewBtn').style.background = 'linear-gradient(135deg,#ef4444,#dc2626)';
  } else {
    document.getElementById('errorCategories').innerHTML = '<p class="text-green-400 text-sm py-2">✅ لا توجد أخطاء — أحسنت!</p>';
    document.getElementById('reviewBtn').textContent = '✅ ممتاز!';
    document.getElementById('reviewBtn').style.background = 'linear-gradient(135deg,#22c55e,#16a34a)';
  }

  updateProgress(student);
}

function updateProgress(s) {
  const xp = s?.xp || 0, target = 90, score = Math.min(Math.round(xp/10), 90), pct = score/90;
  document.getElementById('progressScore').textContent = score;
  document.getElementById('progressPct').textContent = Math.round(pct*100)+'%';
  document.getElementById('neededScore').textContent = (target-score)+' درجة';
  setTimeout(()=>{
    const arc = document.getElementById('progressArc'); if (arc) { const c=502; arc.style.strokeDasharray=c; arc.style.strokeDashoffset=c*(1-pct); }
    document.getElementById('bar1').style.width = Math.min(pct*100,100)+'%';
    document.getElementById('bar2').style.width = Math.min(Math.max(pct-.15,0)*100,100)+'%';
    document.getElementById('bar3').style.width = Math.min(Math.max(pct-.3,0)*100,100)+'%';
    document.getElementById('skill1').textContent = Math.round(score/5)+'/18';
    document.getElementById('skill2').textContent = Math.round(score/4)+'/22';
    document.getElementById('skill3').textContent = Math.round(score/4.5)+'/20';
  },500);
}

async function startSkill(type) {
  toast('🎯 جاري تحميل تمرين: '+type);
  const cs = await apiGet('/courses');
  const match = cs?.courses?.find(c => c.skill_type === type && c.is_active);
  if (!match) return toast('⚠️ لا توجد تمارين متاحة');
  showTimer(match.time_limit||45, match.name);
}

function showTimer(limit, name) {
  const m = document.createElement('div'); m.className='skill-modal';
  m.innerHTML=`<div><h2 class="text-xl font-black text-gold mb-2">⏱️ ${name||''}</h2><div class="countdown" id="timer">${limit}</div><p class="text-white/50 mt-2">ثانية متبقية</p><button onclick="this.closest('.skill-modal').remove()" class="mt-4 px-6 py-2 rounded-xl bg-red-500/20 text-red-300 border border-red-500/30">إلغاء</button></div>`;
  document.body.appendChild(m);
  let t=limit; const el=m.querySelector('#timer'), iv=setInterval(()=>{ t--; el.textContent=t; if(t<=5){el.classList.add('timer-warning');playBeep()} if(t<=0){clearInterval(iv);el.textContent='⏰ انتهى!';setTimeout(()=>m.remove(),2000)} },1000);
  m.addEventListener('click',e=>{if(e.target===m){clearInterval(iv);m.remove()}});
}

function playBeep(){try{const a=new (window.AudioContext||window.webkitAudioContext)(),o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.frequency.value=880;g.gain.value=.3;o.start();o.stop(a.currentTime+.15)}catch(e){}}

async function startReview() {
  const d = await apiGet('/error_bank/'+USER_ID);
  if (!d?.reviews?.length) return toast('✅ لا أخطاء!');
  const r = d.reviews[0];
  const m = document.createElement('div'); m.className='skill-modal';
  m.innerHTML=`<div><h2 class="text-xl font-black text-red-400 mb-2">🔬 مراجعة</h2><p class="text-white text-lg mb-3">${r.question_text||'سؤال'}</p><div class="flex gap-3 justify-center"><button onclick="this.closest('.skill-modal').remove();reviewCorrect(${r.id})" class="px-6 py-3 rounded-xl bg-green-500/20 text-green-400 font-bold">✅ صحيح</button><button onclick="this.closest('.skill-modal').remove()" class="px-6 py-3 rounded-xl bg-red-500/20 text-red-300 font-bold">❌ خطأ</button></div></div>`;
  document.body.appendChild(m);
  m.addEventListener('click',e=>{if(e.target===m)m.remove()});
}

async function reviewCorrect(id){try{await fetch(API+'/error_bank/correct',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:USER_ID,error_bank_id:id})});toast('✅ تم!');loadDashboard()}catch(e){}}

function setNav(btn){document.querySelectorAll('.nav-item').forEach(n=>{n.classList.remove('active');n.querySelector('span').classList.remove('text-gold');n.querySelector('span').classList.add('text-white/40')});btn.classList.add('active');btn.querySelector('span').classList.remove('text-white/40');btn.querySelector('span').classList.add('text-gold')}

window.addEventListener('load',()=>{console.log('[Yamen] Loaded');loadDashboard()});
setInterval(loadDashboard,60000);
