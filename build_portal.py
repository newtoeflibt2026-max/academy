import os

html = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>أكاديمية يامن للتوفل - بوابة الطالب</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800;900&display=swap" rel="stylesheet"/>
<style>
*{font-family:'Cairo',sans-serif;box-sizing:border-box;margin:0;padding:0}
:root{
  --primary:#4f7ef7;--primary-light:#eef2ff;--primary-dark:#3a5fd4;
  --success:#22c55e;--success-light:#f0fdf4;
  --warning:#f59e0b;--warning-light:#fffbeb;
  --danger:#ef4444;--danger-light:#fef2f2;
  --gray-50:#f8fafc;--gray-100:#f1f5f9;--gray-200:#e2e8f0;
  --gray-400:#94a3b8;--gray-600:#475569;--gray-800:#1e293b;
  --white:#ffffff;--shadow:0 4px 24px rgba(79,126,247,.10);
}
body{background:var(--gray-50);color:var(--gray-800);min-height:100vh}

/* ── Login Screen ── */
#login-screen{display:flex;align-items:center;justify-content:center;min-height:100vh;
  background:linear-gradient(135deg,#eef2ff 0%,#f0fdf4 100%)}
.login-box{background:var(--white);border-radius:24px;padding:48px 40px;width:100%;max-width:420px;
  box-shadow:0 20px 60px rgba(79,126,247,.15);text-align:center}
.login-logo{width:80px;height:80px;background:linear-gradient(135deg,var(--primary),#818cf8);
  border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:36px;margin:0 auto 20px}
.login-title{font-size:24px;font-weight:800;color:var(--gray-800);margin-bottom:8px}
.login-sub{font-size:14px;color:var(--gray-400);margin-bottom:32px;line-height:1.6}
.login-input{width:100%;padding:14px 18px;border:2px solid var(--gray-200);border-radius:12px;
  font-size:15px;font-family:'Cairo',sans-serif;outline:none;transition:.2s;text-align:center;
  background:var(--gray-50);color:var(--gray-800)}
.login-input:focus{border-color:var(--primary);background:var(--white);box-shadow:0 0 0 3px rgba(79,126,247,.1)}
.login-btn{width:100%;padding:14px;background:linear-gradient(135deg,var(--primary),#818cf8);
  color:var(--white);border:none;border-radius:12px;font-size:16px;font-weight:700;
  cursor:pointer;margin-top:16px;transition:.2s;font-family:'Cairo',sans-serif}
.login-btn:hover{transform:translateY(-1px);box-shadow:0 8px 24px rgba(79,126,247,.3)}
.login-note{margin-top:20px;font-size:12px;color:var(--gray-400);line-height:1.7}
.err-msg{background:var(--danger-light);color:var(--danger);padding:12px;border-radius:10px;
  font-size:13px;margin-top:12px;display:none}

/* ── Wait Screen ── */
#wait-screen{display:none;align-items:center;justify-content:center;min-height:100vh;
  background:linear-gradient(135deg,#fffbeb 0%,#fef2f2 100%)}
.wait-box{background:var(--white);border-radius:24px;padding:48px 40px;width:100%;max-width:420px;
  box-shadow:0 20px 60px rgba(245,158,11,.15);text-align:center}
.wait-icon{font-size:64px;margin-bottom:16px;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.1)}}
.wait-title{font-size:20px;font-weight:800;color:var(--gray-800);margin-bottom:12px}
.wait-sub{font-size:14px;color:var(--gray-400);line-height:1.8}

/* ── Main App ── */
#app{display:none}
.topbar{background:var(--white);border-bottom:2px solid var(--gray-100);padding:0 20px;
  position:sticky;top:0;z-index:100;box-shadow:0 2px 12px rgba(0,0,0,.06)}
.topbar-inner{max-width:900px;margin:0 auto;display:flex;align-items:center;
  justify-content:space-between;height:64px}
.top-logo{display:flex;align-items:center;gap:10px}
.top-logo-icon{width:38px;height:38px;background:linear-gradient(135deg,var(--primary),#818cf8);
  border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px}
.top-logo-text{font-size:15px;font-weight:800;color:var(--gray-800)}
.top-user{display:flex;align-items:center;gap:10px}
.top-avatar{width:36px;height:36px;background:linear-gradient(135deg,var(--success),#34d399);
  border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:14px;font-weight:700;color:var(--white)}
.top-name{font-size:13px;font-weight:600;color:var(--gray-800)}
.top-level{font-size:11px;color:var(--primary);font-weight:600}

.container{max-width:900px;margin:0 auto;padding:24px 20px}

/* ── Hero Card ── */
.hero{background:linear-gradient(135deg,var(--primary) 0%,#818cf8 50%,#a78bfa 100%);
  border-radius:20px;padding:28px;color:var(--white);margin-bottom:24px;position:relative;overflow:hidden}
.hero::before{content:'🎓';position:absolute;left:-10px;top:-10px;font-size:120px;opacity:.08}
.hero-greeting{font-size:13px;font-weight:600;opacity:.85;margin-bottom:4px}
.hero-name{font-size:26px;font-weight:900;margin-bottom:16px}
.hero-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.hero-stat{background:rgba(255,255,255,.18);border-radius:12px;padding:12px;text-align:center;backdrop-filter:blur(4px)}
.hero-stat-val{font-size:22px;font-weight:800}
.hero-stat-lbl{font-size:10px;opacity:.8;margin-top:2px}

/* ── XP Progress ── */
.xp-bar-wrap{background:var(--white);border-radius:16px;padding:20px;margin-bottom:24px;
  box-shadow:var(--shadow);border:1px solid var(--gray-100)}
.xp-bar-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.xp-label{font-size:14px;font-weight:700;color:var(--gray-800)}
.xp-val{font-size:13px;color:var(--primary);font-weight:700}
.xp-bar{height:14px;background:var(--gray-100);border-radius:99px;overflow:hidden;position:relative}
.xp-fill{height:100%;background:linear-gradient(90deg,var(--primary),#818cf8);
  border-radius:99px;transition:width 1.2s cubic-bezier(.4,0,.2,1);position:relative}
.xp-fill::after{content:'';position:absolute;top:0;left:0;right:0;bottom:0;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.3),transparent);
  animation:shimmer 2s infinite}
@keyframes shimmer{0%{transform:translateX(-100%)}100%{transform:translateX(100%)}}
.grad-target{font-size:11px;color:var(--gray-400);margin-top:8px;text-align:center}

/* ── Section Title ── */
.section-title{font-size:17px;font-weight:800;color:var(--gray-800);margin-bottom:16px;
  display:flex;align-items:center;gap:8px}
.section-title::after{content:'';flex:1;height:2px;background:var(--gray-100);border-radius:99px}

/* ── Skills Grid ── */
.skills-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-bottom:24px}
@media(max-width:600px){.skills-grid{grid-template-columns:1fr}}
.skill-card{background:var(--white);border-radius:16px;padding:20px;
  box-shadow:var(--shadow);border:2px solid var(--gray-100);
  cursor:pointer;transition:.2s;position:relative;overflow:hidden}
.skill-card:hover{border-color:var(--primary);transform:translateY(-2px);
  box-shadow:0 8px 32px rgba(79,126,247,.15)}
.skill-card.locked{opacity:.7;cursor:default}
.skill-card.locked:hover{transform:none;border-color:var(--gray-200)}
.skill-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px}
.skill-icon{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;
  justify-content:center;font-size:20px}
.skill-icon.reading{background:#eef2ff}
.skill-icon.writing{background:#f0fdf4}
.skill-icon.listening{background:#fffbeb}
.skill-icon.speaking{background:#fdf4ff}
.skill-badge{font-size:10px;font-weight:700;padding:3px 10px;border-radius:99px}
.badge-active{background:var(--primary-light);color:var(--primary)}
.badge-locked{background:var(--gray-100);color:var(--gray-400)}
.badge-done{background:var(--success-light);color:var(--success)}
.skill-name{font-size:15px;font-weight:800;color:var(--gray-800);margin-bottom:4px}
.skill-desc{font-size:11px;color:var(--gray-400);margin-bottom:12px}
.skill-progress-bar{height:8px;background:var(--gray-100);border-radius:99px;overflow:hidden;margin-bottom:8px}
.skill-progress-fill{height:100%;border-radius:99px;transition:width 1s ease}
.fill-reading{background:linear-gradient(90deg,var(--primary),#818cf8)}
.fill-writing{background:linear-gradient(90deg,var(--success),#34d399)}
.fill-listening{background:linear-gradient(90deg,var(--warning),#fbbf24)}
.fill-speaking{background:linear-gradient(90deg,#a855f7,#ec4899)}
.skill-progress-text{font-size:11px;color:var(--gray-400);display:flex;justify-content:space-between}
.skill-gate{margin-top:12px;padding:10px;border-radius:10px;text-align:center;font-size:12px;font-weight:700}
.gate-open{background:var(--primary-light);color:var(--primary);cursor:pointer}
.gate-locked{background:var(--gray-100);color:var(--gray-400)}
.gate-passed{background:var(--success-light);color:var(--success)}
.lock-overlay{position:absolute;top:12px;left:12px;font-size:20px}

/* ── Daily Missions ── */
.missions-wrap{background:var(--white);border-radius:16px;padding:20px;margin-bottom:24px;
  box-shadow:var(--shadow);border:1px solid var(--gray-100)}
.mission-item{display:flex;align-items:center;gap:12px;padding:12px;
  background:var(--gray-50);border-radius:10px;margin-bottom:8px}
.mission-item:last-child{margin-bottom:0}
.mission-icon{font-size:20px;width:36px;text-align:center}
.mission-info{flex:1}
.mission-name{font-size:13px;font-weight:700;color:var(--gray-800)}
.mission-prog{font-size:11px;color:var(--gray-400);margin-top:2px}
.mission-xp{font-size:12px;font-weight:700;color:var(--warning);white-space:nowrap}
.mission-check{width:22px;height:22px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:12px}
.check-done{background:var(--success-light);color:var(--success)}
.check-todo{background:var(--gray-100);color:var(--gray-400)}

/* ── Graduation ── */
.grad-card{background:linear-gradient(135deg,#fffbeb,#fef3c7);border:2px solid #fcd34d;
  border-radius:16px;padding:20px;margin-bottom:24px}
.grad-title{font-size:15px;font-weight:800;color:#92400e;margin-bottom:14px;
  display:flex;align-items:center;gap:8px}
.grad-checks{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.grad-check{background:var(--white);border-radius:10px;padding:12px;display:flex;
  align-items:center;gap:10px}
.grad-check-icon{font-size:18px}
.grad-check-info{flex:1}
.grad-check-label{font-size:11px;color:var(--gray-400)}
.grad-check-val{font-size:13px;font-weight:700}
.val-ok{color:var(--success)}
.val-no{color:var(--danger)}

/* ── Message Box ── */
.msg-card{background:var(--white);border-radius:16px;padding:20px;margin-bottom:24px;
  box-shadow:var(--shadow);border:1px solid var(--gray-100)}
.msg-textarea{width:100%;padding:14px;border:2px solid var(--gray-200);border-radius:12px;
  font-family:'Cairo',sans-serif;font-size:13px;resize:vertical;min-height:90px;
  outline:none;transition:.2s;background:var(--gray-50);color:var(--gray-800)}
.msg-textarea:focus{border-color:var(--primary);background:var(--white)}
.msg-send-btn{margin-top:10px;padding:12px 24px;background:linear-gradient(135deg,var(--primary),#818cf8);
  color:var(--white);border:none;border-radius:10px;font-size:14px;font-weight:700;
  cursor:pointer;font-family:'Cairo',sans-serif;transition:.2s}
.msg-send-btn:hover{transform:translateY(-1px)}

/* ── Quiz Modal ── */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);
  z-index:1000;align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(4px)}
.modal-overlay.open{display:flex}
.quiz-modal{background:var(--white);border-radius:24px;padding:32px;width:100%;
  max-width:560px;max-height:90vh;overflow-y:auto;position:relative}
.quiz-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.quiz-skill-tag{font-size:12px;font-weight:700;padding:4px 14px;border-radius:99px;
  background:var(--primary-light);color:var(--primary)}
.quiz-close{width:32px;height:32px;border-radius:50%;background:var(--gray-100);
  border:none;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center}
/* Timer */
.timer-wrap{display:flex;justify-content:center;margin-bottom:20px}
.timer-circle{width:80px;height:80px;border-radius:50%;display:flex;flex-direction:column;
  align-items:center;justify-content:center;border:4px solid var(--primary);
  font-size:22px;font-weight:800;color:var(--primary);position:relative;transition:.3s}
.timer-circle.warning{border-color:var(--warning);color:var(--warning)}
.timer-circle.danger{border-color:var(--danger);color:var(--danger);animation:shake .4s infinite}
@keyframes shake{0%,100%{transform:rotate(0)}25%{transform:rotate(-3deg)}75%{transform:rotate(3deg)}}
.timer-label{font-size:9px;color:var(--gray-400);margin-top:2px}
.quiz-progress{font-size:12px;color:var(--gray-400);text-align:center;margin-bottom:16px}
.quiz-q{font-size:16px;font-weight:700;color:var(--gray-800);margin-bottom:20px;
  line-height:1.7;text-align:center}
.options{display:grid;gap:10px}
.option-btn{padding:14px 18px;border:2px solid var(--gray-200);border-radius:12px;
  background:var(--gray-50);cursor:pointer;font-size:14px;font-weight:600;
  font-family:'Cairo',sans-serif;transition:.2s;text-align:right;color:var(--gray-800)}
.option-btn:hover{border-color:var(--primary);background:var(--primary-light);color:var(--primary)}
.option-btn.correct{border-color:var(--success);background:var(--success-light);color:var(--success)}
.option-btn.wrong{border-color:var(--danger);background:var(--danger-light);color:var(--danger)}
.option-btn:disabled{cursor:default}
.quiz-next{margin-top:16px;width:100%;padding:13px;background:linear-gradient(135deg,var(--primary),#818cf8);
  color:var(--white);border:none;border-radius:12px;font-size:15px;font-weight:700;
  cursor:pointer;font-family:'Cairo',sans-serif;display:none}

/* ── Result ── */
.result-wrap{text-align:center;padding:20px 0;display:none}
.result-emoji{font-size:64px;margin-bottom:12px}
.result-score{font-size:48px;font-weight:900;margin-bottom:4px}
.result-label{font-size:14px;color:var(--gray-400);margin-bottom:20px}
.result-xp{display:inline-flex;align-items:center;gap:6px;background:var(--warning-light);
  color:var(--warning);padding:8px 20px;border-radius:99px;font-size:14px;font-weight:700;margin-bottom:20px}
.result-close{width:100%;padding:13px;background:linear-gradient(135deg,var(--success),#34d399);
  color:var(--white);border:none;border-radius:12px;font-size:15px;font-weight:700;
  cursor:pointer;font-family:'Cairo',sans-serif}

/* ── Gate Modal ── */
.gate-modal{background:var(--white);border-radius:24px;padding:32px;width:100%;
  max-width:420px;text-align:center}
.gate-icon{font-size:64px;margin-bottom:16px}
.gate-title{font-size:20px;font-weight:800;margin-bottom:8px;color:var(--gray-800)}
.gate-desc{font-size:13px;color:var(--gray-400);line-height:1.8;margin-bottom:24px}
.gate-start-btn{width:100%;padding:14px;background:linear-gradient(135deg,var(--primary),#818cf8);
  color:var(--white);border:none;border-radius:12px;font-size:16px;font-weight:700;
  cursor:pointer;font-family:'Cairo',sans-serif;margin-bottom:10px}
.gate-cancel{width:100%;padding:12px;background:var(--gray-100);color:var(--gray-600);
  border:none;border-radius:12px;font-size:14px;cursor:pointer;font-family:'Cairo',sans-serif}

/* ── Toast ── */
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(100px);
  background:var(--gray-800);color:var(--white);padding:12px 24px;border-radius:12px;
  font-size:13px;font-weight:600;z-index:9999;transition:.3s;white-space:nowrap}
.toast.show{transform:translateX(-50%) translateY(0)}
.toast.success{background:var(--success)}
.toast.error{background:var(--danger)}

.hidden{display:none!important}
</style>
</head>
<body>

<!-- ══ LOGIN ══ -->
<div id="login-screen">
  <div class="login-box">
    <div class="login-logo">🎓</div>
    <div class="login-title">أكاديمية يامن للتوفل</div>
    <div class="login-sub">أدخل معرّف تلغرام الخاص بك للوصول إلى لوحتك التعليمية</div>
    <input class="login-input" type="number" id="tid-input" placeholder="مثال: 123456789"/>
    <button class="login-btn" onclick="doLogin()">🚀 دخول</button>
    <div class="err-msg" id="err-msg"></div>
    <div class="login-note">
      إذا لم يكن لديك حساب، ابدأ مع البوت أولاً<br/>
      ثم انتظر موافقة الأدمن على اشتراكك
    </div>
  </div>
</div>

<!-- ══ WAIT ══ -->
<div id="wait-screen">
  <div class="wait-box">
    <div class="wait-icon">⏳</div>
    <div class="wait-title">في انتظار الموافقة</div>
    <div class="wait-sub">
      تم العثور على حسابك بنجاح!<br/>
      لكن اشتراكك لم يُفعَّل بعد.<br/><br/>
      تواصل مع الأدمن عبر البوت لتفعيل حسابك.<br/>
      <strong style="color:var(--warning)">سيتم إعادة التوجيه تلقائياً بعد التفعيل</strong>
    </div>
  </div>
</div>

<!-- ══ MAIN APP ══ -->
<div id="app">

  <!-- TopBar -->
  <div class="topbar">
    <div class="topbar-inner">
      <div class="top-logo">
        <div class="top-logo-icon">🎓</div>
        <div class="top-logo-text">أكاديمية يامن</div>
      </div>
      <div class="top-user">
        <div>
          <div class="top-name" id="top-name">-</div>
          <div class="top-level" id="top-level">-</div>
        </div>
        <div class="top-avatar" id="top-avatar">؟</div>
      </div>
    </div>
  </div>

  <div class="container">

    <!-- Hero -->
    <div class="hero">
      <div class="hero-greeting">مرحباً بك 👋</div>
      <div class="hero-name" id="hero-name">جار التحميل...</div>
      <div class="hero-stats">
        <div class="hero-stat">
          <div class="hero-stat-val" id="h-xp">0</div>
          <div class="hero-stat-lbl">نقاط XP</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-val" id="h-streak">0</div>
          <div class="hero-stat-lbl">🔥 يوم متواصل</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-val" id="h-tasks">0</div>
          <div class="hero-stat-lbl">✅ مهمة أُنجزت</div>
        </div>
      </div>
    </div>

    <!-- XP Progress Bar -->
    <div class="xp-bar-wrap">
      <div class="xp-bar-header">
        <span class="xp-label">🏆 التقدم نحو التخرج</span>
        <span class="xp-val" id="xp-pct">0%</span>
      </div>
      <div class="xp-bar">
        <div class="xp-fill" id="xp-fill" style="width:0%"></div>
      </div>
      <div class="grad-target" id="grad-target">500 XP مطلوبة للتخرج</div>
    </div>

    <!-- Skills -->
    <div class="section-title">📚 أقسام الاختبار</div>
    <div class="skills-grid" id="skills-grid">

      <!-- Reading -->
      <div class="skill-card" id="card-reading" onclick="openSkill('reading')">
        <div class="skill-header">
          <div class="skill-icon reading">📖</div>
          <span class="skill-badge badge-active" id="badge-reading">نشط</span>
        </div>
        <div class="skill-name">Reading الفهم القرائي</div>
        <div class="skill-desc">تحليل النصوص والإجابة على الأسئلة الأكاديمية</div>
        <div class="skill-progress-bar">
          <div class="skill-progress-fill fill-reading" id="fill-reading" style="width:0%"></div>
        </div>
        <div class="skill-progress-text">
          <span id="prog-reading">0/10 سؤال</span>
          <span id="pct-reading">0%</span>
        </div>
        <div class="skill-gate gate-open" id="gate-reading" onclick="event.stopPropagation();openGate('reading')">
          🚪 بوابة القسم — ابدأ الاختبار
        </div>
      </div>

      <!-- Writing -->
      <div class="skill-card" id="card-writing" onclick="openSkill('writing')">
        <div class="skill-header">
          <div class="skill-icon writing">✍️</div>
          <span class="skill-badge badge-active" id="badge-writing">نشط</span>
        </div>
        <div class="skill-name">Writing الكتابة</div>
        <div class="skill-desc">كتابة مقالات أكاديمية وتكاملية</div>
        <div class="skill-progress-bar">
          <div class="skill-progress-fill fill-writing" id="fill-writing" style="width:0%"></div>
        </div>
        <div class="skill-progress-text">
          <span id="prog-writing">0/10 سؤال</span>
          <span id="pct-writing">0%</span>
        </div>
        <div class="skill-gate gate-open" id="gate-writing" onclick="event.stopPropagation();openGate('writing')">
          🚪 بوابة القسم — ابدأ الاختبار
        </div>
      </div>

      <!-- Listening -->
      <div class="skill-card" id="card-listening" onclick="openSkill('listening')">
        <div class="skill-header">
          <div class="skill-icon listening">🎧</div>
          <span class="skill-badge badge-active" id="badge-listening">نشط</span>
        </div>
        <div class="skill-name">Listening الاستماع</div>
        <div class="skill-desc">فهم المحاضرات والمحادثات الأكاديمية</div>
        <div class="skill-progress-bar">
          <div class="skill-progress-fill fill-listening" id="fill-listening" style="width:0%"></div>
        </div>
        <div class="skill-progress-text">
          <span id="prog-listening">0/10 سؤال</span>
          <span id="pct-listening">0%</span>
        </div>
        <div class="skill-gate gate-open" id="gate-listening" onclick="event.stopPropagation();openGate('listening')">
          🚪 بوابة القسم — ابدأ الاختبار
        </div>
      </div>

      <!-- Speaking -->
      <div class="skill-card" id="card-speaking" onclick="openSkill('speaking')">
        <div class="skill-header">
          <div class="skill-icon speaking">🎤</div>
          <span class="skill-badge badge-active" id="badge-speaking">نشط</span>
        </div>
        <div class="skill-name">Speaking التحدث</div>
        <div class="skill-desc">التعبير الشفهي والإجابات المنظمة</div>
        <div class="skill-progress-bar">
          <div class="skill-progress-fill fill-speaking" id="fill-speaking" style="width:0%"></div>
        </div>
        <div class="skill-progress-text">
          <span id="prog-speaking">0/10 سؤال</span>
          <span id="pct-speaking">0%</span>
        </div>
        <div class="skill-gate gate-open" id="gate-speaking" onclick="event.stopPropagation();openGate('speaking')">
          🚪 بوابة القسم — ابدأ الاختبار
        </div>
      </div>

    </div>

    <!-- Daily Missions -->
    <div class="section-title">⚡ المهام اليومية</div>
    <div class="missions-wrap" id="missions-wrap">
      <div style="text-align:center;color:var(--gray-400);padding:20px">جار التحميل...</div>
    </div>

    <!-- Graduation Status -->
    <div class="section-title">🎓 بوابة التخرج</div>
    <div class="grad-card">
      <div class="grad-title">🏆 متطلبات التخرج</div>
      <div class="grad-checks">
        <div class="grad-check">
          <div class="grad-check-icon">⚡</div>
          <div class="grad-check-info">
            <div class="grad-check-label">نقاط XP</div>
            <div class="grad-check-val" id="gc-xp">-</div>
          </div>
        </div>
        <div class="grad-check">
          <div class="grad-check-icon">✅</div>
          <div class="grad-check-info">
            <div class="grad-check-label">المهام المنجزة</div>
            <div class="grad-check-val" id="gc-tasks">-</div>
          </div>
        </div>
        <div class="grad-check">
          <div class="grad-check-icon">🔥</div>
          <div class="grad-check-info">
            <div class="grad-check-label">أيام متواصلة</div>
            <div class="grad-check-val" id="gc-streak">-</div>
          </div>
        </div>
        <div class="grad-check">
          <div class="grad-check-icon">📊</div>
          <div class="grad-check-info">
            <div class="grad-check-label">درجة الاختبار</div>
            <div class="grad-check-val" id="gc-mock">-</div>
          </div>
        </div>
      </div>
      <div id="grad-ready-msg" style="display:none;margin-top:16px;padding:14px;
        background:var(--success-light);border-radius:12px;text-align:center;
        font-size:14px;font-weight:700;color:var(--success)">
        🎉 مبروك! أنت مؤهل للتخرج — تواصل مع الأدمن
      </div>
    </div>

    <!-- Message Admin -->
    <div class="section-title">💬 تواصل مع الأدمن</div>
    <div class="msg-card">
      <textarea class="msg-textarea" id="msg-text" placeholder="اكتب رسالتك هنا..."></textarea>
      <button class="msg-send-btn" onclick="sendMsg()">📤 إرسال الرسالة</button>
    </div>

  </div><!-- /container -->
</div><!-- /app -->

<!-- ══ QUIZ MODAL ══ -->
<div class="modal-overlay" id="quiz-overlay">
  <div class="quiz-modal">
    <div class="quiz-header">
      <span class="quiz-skill-tag" id="quiz-skill-tag">Reading</span>
      <button class="quiz-close" onclick="closeQuiz()">✕</button>
    </div>

    <div id="quiz-body">
      <div class="timer-wrap">
        <div class="timer-circle" id="timer-circle">
          <span id="timer-val">30</span>
          <span class="timer-label">ثانية</span>
        </div>
      </div>
      <div class="quiz-progress" id="quiz-progress">السؤال 1 من 10</div>
      <div class="quiz-q" id="quiz-q">جار التحميل...</div>
      <div class="options" id="options"></div>
      <button class="quiz-next" id="quiz-next" onclick="nextQ()">التالي ←</button>
    </div>

    <div class="result-wrap" id="result-wrap">
      <div class="result-emoji" id="result-emoji">🎉</div>
      <div class="result-score" id="result-score" style="color:var(--primary)">-</div>
      <div class="result-label">درجتك في هذا القسم</div>
      <div class="result-xp" id="result-xp">+0 XP</div>
      <button class="result-close" onclick="closeQuiz()">✅ إغلاق وحفظ النتيجة</button>
    </div>
  </div>
</div>

<!-- ══ GATE MODAL ══ -->
<div class="modal-overlay" id="gate-overlay">
  <div class="gate-modal">
    <div class="gate-icon" id="gate-emoji">🚪</div>
    <div class="gate-title" id="gate-title">بوابة القسم</div>
    <div class="gate-desc" id="gate-desc">ستبدأ اختبار القسم الآن. لديك مؤقت 30 ثانية لكل سؤال.</div>
    <button class="gate-start-btn" id="gate-start-btn" onclick="startGateExam()">🚀 ابدأ الاختبار</button>
    <button class="gate-cancel" onclick="closeGate()">إلغاء</button>
  </div>
</div>

<!-- ══ TOAST ══ -->
<div class="toast" id="toast"></div>

<script>
// ══════════════════════════════════════════════
//  State
// ══════════════════════════════════════════════
let STATE = {
  uid: null,
  student: null,
  questions: {},   // skill -> []
  quiz: {
    skill: null, qs: [], idx: 0,
    correct: 0, answered: false,
    timer: null, timerVal: 30
  },
  gateSkill: null
};

const SKILLS = {
  reading:   {name:'Reading',   emoji:'📖', color:'var(--primary)'},
  writing:   {name:'Writing',   emoji:'✍️', color:'var(--success)'},
  listening: {name:'Listening', emoji:'🎧', color:'var(--warning)'},
  speaking:  {name:'Speaking',  emoji:'🎤', color:'#a855f7'},
};

// ══════════════════════════════════════════════
//  Boot — check URL token
// ══════════════════════════════════════════════
window.onload = () => {
  const params = new URLSearchParams(location.search);
  const uid = params.get('uid') || params.get('token');
  if(uid){ doLogin(uid); return; }
  const saved = localStorage.getItem('yamen_uid');
  if(saved){ doLogin(saved); return; }
};

// ══════════════════════════════════════════════
//  Login
// ══════════════════════════════════════════════
async function doLogin(uid_override){
  const uid = uid_override || document.getElementById('tid-input').value.trim();
  if(!uid){ showErr('أدخل معرف تلغرام'); return; }
  try{
    const r = await fetch(`/api/admin/students/${uid}`);
    if(!r.ok){ showErr('لم يتم العثور على حسابك — تأكد من المعرف أو تواصل مع الأدمن'); return; }
    const s = await r.json();
    STATE.uid = parseInt(uid);
    STATE.student = s;
    localStorage.setItem('yamen_uid', uid);
    if(!s.is_paid){
      document.getElementById('login-screen').style.display='none';
      document.getElementById('wait-screen').style.display='flex';
      setTimeout(()=>doLogin(uid), 15000);
      return;
    }
    showApp(s);
  } catch(e){
    showErr('خطأ في الاتصال — تأكد من اتصال الإنترنت');
  }
}

function showErr(msg){
  const el = document.getElementById('err-msg');
  el.textContent = msg;
  el.style.display = 'block';
}

// ══════════════════════════════════════════════
//  Show App
// ══════════════════════════════════════════════
async function showApp(s){
  document.getElementById('login-screen').style.display='none';
  document.getElementById('wait-screen').style.display='none';
  document.getElementById('app').style.display='block';

  // Hero
  document.getElementById('hero-name').textContent = s.full_name || s.username || 'الطالب';
  document.getElementById('top-name').textContent   = s.full_name || s.username || '-';
  document.getElementById('top-level').textContent  = 'المستوى: ' + (s.level || 'مبتدئ');
  document.getElementById('top-avatar').textContent = (s.full_name||'؟')[0];
  document.getElementById('h-xp').textContent       = s.xp || 0;
  document.getElementById('h-streak').textContent   = s.streak || 0;
  document.getElementById('h-tasks').textContent    = s.tasks_completed || 0;

  // XP bar
  const minXP = 500;
  const pct = Math.min(100, Math.round(((s.xp||0)/minXP)*100));
  document.getElementById('xp-fill').style.width   = pct+'%';
  document.getElementById('xp-pct').textContent    = pct+'%';
  document.getElementById('grad-target').textContent= `${s.xp||0} / ${minXP} XP للتخرج`;

  // Skills progress
  await loadSkillsProgress(s);

  // Missions
  await loadMissions();

  // Graduation
  await loadGradStatus();
}

// ══════════════════════════════════════════════
//  Skills Progress (from questions answered)
// ══════════════════════════════════════════════
async function loadSkillsProgress(s){
  // جلب الأسئلة لكل قسم
  for(const skill of Object.keys(SKILLS)){
    try{
      const r = await fetch(`/api/admin/questions?skill=${skill}`);
      const qs = await r.json();
      STATE.questions[skill] = qs;
      const total = qs.length || 10;
      // نقدر التقدم بناءً على XP بشكل تقريبي
      const prog = Math.min(total, Math.floor((s.xp||0) / 10));
      const pct  = Math.round((prog/total)*100);
      document.getElementById('fill-'+skill).style.width = pct+'%';
      document.getElementById('prog-'+skill).textContent = prog+'/'+total+' سؤال';
      document.getElementById('pct-'+skill).textContent  = pct+'%';

      // Gate state
      const gate = document.getElementById('gate-'+skill);
      if(pct >= 100){
        gate.className = 'skill-gate gate-passed';
        gate.textContent = '✅ أجتزت هذا القسم!';
        document.getElementById('badge-'+skill).className = 'skill-badge badge-done';
        document.getElementById('badge-'+skill).textContent = 'مكتمل';
      }
    } catch(e){ console.log('skill err',skill,e); }
  }
}

// ══════════════════════════════════════════════
//  Missions
// ══════════════════════════════════════════════
async function loadMissions(){
  const wrap = document.getElementById('missions-wrap');
  try{
    const r = await fetch('/api/admin/missions');
    const missions = await r.json();
    if(!missions.length){
      wrap.innerHTML='<div style="text-align:center;color:var(--gray-400);padding:20px">لا توجد مهام اليوم</div>';
      return;
    }
    const icons = {quiz:'📝', lesson:'📚', writing:'✍️', speaking:'🎤', default:'⚡'};
    wrap.innerHTML = missions.slice(0,5).map((m,i)=>`
      <div class="mission-item">
        <div class="mission-icon">${icons[m.mission_type]||icons.default}</div>
        <div class="mission-info">
          <div class="mission-name">${m.title}</div>
          <div class="mission-prog">${m.description||'أكمل المهمة للحصول على XP'}</div>
        </div>
        <div class="mission-xp">+${m.xp_reward} XP</div>
        <div class="mission-check ${i<2?'check-done':'check-todo'}">${i<2?'✓':'○'}</div>
      </div>
    `).join('');
  } catch(e){
    wrap.innerHTML='<div style="text-align:center;color:var(--danger);padding:20px">خطأ في تحميل المهام</div>';
  }
}

// ══════════════════════════════════════════════
//  Graduation Status
// ══════════════════════════════════════════════
async function loadGradStatus(){
  try{
    const r = await fetch(`/api/user/graduation-status?user_id=${STATE.uid}`);
    const d = await r.json();
    if(!d.checks) return;
    const {xp, tasks, streak, mock} = d.checks;
    set_gc('xp',    xp.current,    xp.required,    xp.ok,    'XP');
    set_gc('tasks', tasks.current, tasks.required,  tasks.ok, 'مهمة');
    set_gc('streak',streak.current,streak.required, streak.ok,'يوم');
    set_gc('mock',  mock.current,  mock.required,   mock.ok,  'درجة');
    if(d.ready){
      document.getElementById('grad-ready-msg').style.display='block';
    }
  } catch(e){ console.log('grad err',e); }
}

function set_gc(id, cur, req, ok, unit){
  const el = document.getElementById('gc-'+id);
  el.textContent  = cur+' / '+req+' '+unit;
  el.className    = 'grad-check-val '+(ok?'val-ok':'val-no');
}

// ══════════════════════════════════════════════
//  Open Skill (info click)
// ══════════════════════════════════════════════
function openSkill(skill){
  // فتح كويز سريع للقسم
  openGate(skill);
}

// ══════════════════════════════════════════════
//  Gate Modal
// ══════════════════════════════════════════════
function openGate(skill){
  STATE.gateSkill = skill;
  const sk = SKILLS[skill];
  document.getElementById('gate-emoji').textContent = sk.emoji;
  document.getElementById('gate-title').textContent = `بوابة قسم ${sk.name}`;
  const total = (STATE.questions[skill]||[]).length;
  document.getElementById('gate-desc').textContent =
    `ستبدأ اختبار ${sk.name} الآن.\n${total ? 'عدد الأسئلة: '+total : 'سيتم تحميل الأسئلة'}\nلديك 30 ثانية لكل سؤال — الوقت يُضغط عليك!`;
  document.getElementById('gate-overlay').classList.add('open');
}

function closeGate(){
  document.getElementById('gate-overlay').classList.remove('open');
}

async function startGateExam(){
  closeGate();
  const skill = STATE.gateSkill;
  let qs = STATE.questions[skill] || [];
  if(!qs.length){
    // جلب الأسئلة إذا لم تكن محملة
    try{
      const r = await fetch(`/api/admin/questions?skill=${skill}`);
      qs = await r.json();
      STATE.questions[skill] = qs;
    } catch(e){ showToast('خطأ في تحميل الأسئلة','error'); return; }
  }
  if(!qs.length){ showToast('لا توجد أسئلة في هذا القسم حتى الآن','error'); return; }
  startQuiz(skill, qs);
}

// ══════════════════════════════════════════════
//  Quiz Engine
// ══════════════════════════════════════════════
function startQuiz(skill, qs){
  // خلط الأسئلة
  const shuffled = [...qs].sort(()=>Math.random()-.5).slice(0,10);
  STATE.quiz = { skill, qs: shuffled, idx:0, correct:0, answered:false, timer:null, timerVal:30 };

  document.getElementById('quiz-skill-tag').textContent = SKILLS[skill].name;
  document.getElementById('quiz-body').style.display    = 'block';
  document.getElementById('result-wrap').style.display  = 'none';
  document.getElementById('quiz-overlay').classList.add('open');

  renderQ();
}

function renderQ(){
  const {qs, idx} = STATE.quiz;
  if(idx >= qs.length){ showResult(); return; }
  const q = qs[idx];
  STATE.quiz.answered = false;

  document.getElementById('quiz-progress').textContent = `السؤال ${idx+1} من ${qs.length}`;
  document.getElementById('quiz-q').textContent        = q.question_text;
  document.getElementById('quiz-next').style.display   = 'none';

  const opts = ['a','b','c','d'];
  const labels = {a:'أ', b:'ب', c:'ج', d:'د'};
  document.getElementById('options').innerHTML = opts.map(o => {
    const txt = q['option_'+o];
    if(!txt) return '';
    return `<button class="option-btn" id="opt-${o}" onclick="pickAns('${o}','${q.correct_option}')">${labels[o]}) ${txt}</button>`;
  }).join('');

  startTimer(parseInt(q.timer_seconds)||30);
}

function startTimer(sec){
  clearInterval(STATE.quiz.timer);
  STATE.quiz.timerVal = sec;
  updateTimerUI(sec);
  STATE.quiz.timer = setInterval(()=>{
    STATE.quiz.timerVal--;
    updateTimerUI(STATE.quiz.timerVal);
    if(STATE.quiz.timerVal <= 0){
      clearInterval(STATE.quiz.timer);
      if(!STATE.quiz.answered) timeOut();
    }
  }, 1000);
}

function updateTimerUI(val){
  const el = document.getElementById('timer-circle');
  document.getElementById('timer-val').textContent = val;
  el.className = 'timer-circle' + (val<=5?' danger': val<=10?' warning':'');
}

function timeOut(){
  if(STATE.quiz.answered) return;
  STATE.quiz.answered = true;
  // أظهر الإجابة الصحيحة
  const q = STATE.quiz.qs[STATE.quiz.idx];
  const correct_btn = document.getElementById('opt-'+q.correct_option);
  if(correct_btn) correct_btn.classList.add('correct');
  document.querySelectorAll('.option-btn').forEach(b=>b.disabled=true);
  document.getElementById('quiz-next').style.display='block';
  showToast('⏰ انتهى الوقت!','error');
}

function pickAns(chosen, correct){
  if(STATE.quiz.answered) return;
  STATE.quiz.answered = true;
  clearInterval(STATE.quiz.timer);

  const isCorrect = chosen === correct;
  if(isCorrect) STATE.quiz.correct++;

  document.querySelectorAll('.option-btn').forEach(b=>{
    b.disabled = true;
    const id = b.id.split('-')[1];
    if(id === correct) b.classList.add('correct');
    else if(id === chosen && !isCorrect) b.classList.add('wrong');
  });

  setTimeout(()=>{
    document.getElementById('quiz-next').style.display='block';
  }, 600);
}

function nextQ(){
  STATE.quiz.idx++;
  renderQ();
}

function showResult(){
  document.getElementById('quiz-body').style.display   = 'none';
  document.getElementById('result-wrap').style.display = 'block';

  const {correct, qs} = STATE.quiz;
  const total   = qs.length;
  const pct     = Math.round((correct/total)*100);
  const xpEarned= correct * 5;

  const emoji = pct>=80?'🏆':pct>=60?'🎉':pct>=40?'😊':'💪';
  document.getElementById('result-emoji').textContent = emoji;
  document.getElementById('result-score').textContent = pct+'%';
  document.getElementById('result-xp').textContent    = '+'+xpEarned+' XP';

  // إرسال النتيجة للـ API
  fetch('/api/student/quiz-result', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      user_id: STATE.uid,
      skill: STATE.quiz.skill,
      score: pct,
      xp_earned: xpEarned
    })
  }).catch(()=>{});
}

function closeQuiz(){
  clearInterval(STATE.quiz.timer);
  document.getElementById('quiz-overlay').classList.remove('open');
  // أعد تحميل بيانات الطالب
  if(STATE.uid) doLogin(STATE.uid.toString());
}

// ══════════════════════════════════════════════
//  Send Message
// ══════════════════════════════════════════════
async function sendMsg(){
  const txt = document.getElementById('msg-text').value.trim();
  if(!txt){ showToast('اكتب رسالة أولاً','error'); return; }
  if(!STATE.student) return;
  try{
    const r = await fetch('/api/student/message',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        user_id:   STATE.uid,
        username:  STATE.student.username || '',
        full_name: STATE.student.full_name || '',
        message:   txt
      })
    });
    if(r.ok){
      document.getElementById('msg-text').value='';
      showToast('✅ تم إرسال رسالتك للأدمن','success');
    }
  } catch(e){ showToast('خطأ في الإرسال','error'); }
}

// ══════════════════════════════════════════════
//  Toast
// ══════════════════════════════════════════════
function showToast(msg, type=''){
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className   = 'toast '+(type||'');
  t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'), 3000);
}
</script>
</body>
</html>"""

with open("templates/student_portal.html","w",encoding="utf-8") as f:
    f.write(html)
print("DONE - size:", len(html), "chars")
