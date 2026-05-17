# -*- coding: utf-8 -*-
"""Build placement.html from scratch with strict UTF-8 encoding."""
import os

HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yamen Academy – اختبار تحديد المستوى</title>
    <style>
        /* ======== RESET & BASE ======== */
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: "Segoe UI", "Cairo", Arial, sans-serif;
            background: linear-gradient(135deg, #0d1b3e 0%, #1a237e 40%, #283593 70%, #1a237e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            direction: rtl;
        }

        /* ======== QUIZ CARD ======== */
        .quiz-card {
            width: 100%;
            max-width: 720px;
            background: #ffffff;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.35), 0 0 0 1px rgba(255,255,255,0.08);
            overflow: hidden;
            transition: opacity 0.4s ease, transform 0.4s ease;
        }
        .quiz-card.hidden { display: none; }

        /* ======== HEADER ======== */
        .quiz-header {
            background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
            padding: 28px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
        }
        .quiz-header h1 {
            color: #ffffff;
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.3px;
            line-height: 1.3;
        }
        .quiz-header .subtitle {
            color: rgba(255,255,255,0.75);
            font-size: 0.85rem;
            font-weight: 400;
            margin-top: 2px;
        }
        .quiz-header .badge {
            background: rgba(255,255,255,0.15);
            color: #ffffff;
            padding: 4px 14px;
            border-radius: 30px;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.3px;
            backdrop-filter: blur(4px);
            border: 1px solid rgba(255,255,255,0.12);
            white-space: nowrap;
        }

        /* ======== TIMER ======== */
        .timer-box {
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(255,255,255,0.12);
            padding: 10px 20px;
            border-radius: 50px;
            border: 1px solid rgba(255,255,255,0.18);
            backdrop-filter: blur(6px);
        }
        .timer-box .timer-icon { font-size: 1.25rem; }
        .timer-box .timer-display {
            font-family: "Consolas", "Courier New", monospace;
            font-size: 1.5rem;
            font-weight: 700;
            color: #ffd54f;
            letter-spacing: 2px;
            min-width: 58px;
            text-align: center;
        }
        .timer-box.warning .timer-display {
            color: #ff7043;
            animation: pulse 0.7s ease-in-out infinite;
        }
        .timer-box.danger .timer-display {
            color: #ef5350;
            animation: pulse 0.4s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* ======== PROGRESS BAR ======== */
        .progress-wrap {
            padding: 16px 32px 0;
            background: #ffffff;
        }
        .progress-info {
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            color: #5c6bc0;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e8eaf6;
            border-radius: 8px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #5c6bc0, #7c4dff);
            border-radius: 8px;
            transition: width 0.35s ease;
        }

        /* ======== QUESTION CONTAINER ======== */
        .question-area {
            padding: 28px 32px 12px;
            background: #ffffff;
            min-height: 320px;
        }
        .question-number {
            display: inline-block;
            background: #e8eaf6;
            color: #3949ab;
            font-size: 0.8rem;
            font-weight: 700;
            padding: 5px 14px;
            border-radius: 20px;
            margin-bottom: 16px;
        }
        .question-text {
            font-size: 1.18rem;
            font-weight: 600;
            color: #1a237e;
            line-height: 1.8;
            margin-bottom: 22px;
            min-height: 60px;
        }
        .skill-tag {
            display: inline-block;
            background: #fff3e0;
            color: #e65100;
            font-size: 0.7rem;
            font-weight: 700;
            padding: 3px 12px;
            border-radius: 12px;
            margin-right: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* ======== OPTIONS ======== */
        .options-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .option-item {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 14px 18px;
            border: 2px solid #e0e0e0;
            border-radius: 14px;
            cursor: pointer;
            transition: all 0.2s ease;
            background: #fafafa;
            font-size: 0.98rem;
            color: #333;
            font-weight: 500;
            user-select: none;
        }
        .option-item:hover {
            border-color: #7986cb;
            background: #f5f6ff;
            transform: translateX(-4px);
        }
        .option-item.selected {
            border-color: #3949ab;
            background: #e8eaf6;
            box-shadow: 0 0 0 3px rgba(57,73,171,0.15);
        }
        .option-letter {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background: #e8eaf6;
            color: #3949ab;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 0.95rem;
            flex-shrink: 0;
            transition: all 0.2s ease;
        }
        .option-item.selected .option-letter {
            background: #3949ab;
            color: #ffffff;
        }

        /* ======== NAVIGATION ======== */
        .nav-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 32px 28px;
            gap: 12px;
            background: #ffffff;
            border-radius: 0 0 20px 20px;
        }
        .btn {
            padding: 12px 28px;
            border-radius: 12px;
            font-size: 0.95rem;
            font-weight: 700;
            cursor: pointer;
            border: none;
            transition: all 0.25s ease;
            font-family: inherit;
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }
        .btn-prev {
            background: #f5f5f5;
            color: #546e7a;
        }
        .btn-prev:hover:not(:disabled) {
            background: #e0e0e0;
            color: #263238;
        }
        .btn-prev:disabled {
            opacity: 0.35;
            cursor: not-allowed;
        }
        .btn-next {
            background: linear-gradient(135deg, #3949ab, #5c6bc0);
            color: #ffffff;
        }
        .btn-next:hover:not(:disabled) {
            background: linear-gradient(135deg, #283593, #3949ab);
            transform: translateX(-2px);
            box-shadow: 0 6px 20px rgba(57,73,171,0.35);
        }
        .btn-submit {
            background: linear-gradient(135deg, #43a047, #66bb6a);
            color: #ffffff;
            font-size: 1rem;
            padding: 14px 36px;
        }
        .btn-submit:hover:not(:disabled) {
            background: linear-gradient(135deg, #2e7d32, #43a047);
            transform: translateX(-2px);
            box-shadow: 0 6px 20px rgba(46,125,50,0.4);
        }
        .question-dots {
            display: flex;
            gap: 6px;
        }
        .question-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #e0e0e0;
            transition: background 0.25s ease;
        }
        .question-dot.answered { background: #5c6bc0; }
        .question-dot.current { background: #3949ab; transform: scale(1.3); }

        /* ======== RESULTS SCREEN ======== */
        .results-card {
            width: 100%;
            max-width: 600px;
            background: #ffffff;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
            padding: 40px 32px;
            text-align: center;
            display: none;
        }
        .results-card.visible { display: block; }
        .results-card .icon-check {
            font-size: 4rem;
            margin-bottom: 16px;
        }
        .results-card h2 {
            font-size: 1.8rem;
            color: #1a237e;
            font-weight: 800;
            margin-bottom: 8px;
        }
        .results-card .score-big {
            font-size: 4rem;
            font-weight: 900;
            background: linear-gradient(135deg, #3949ab, #7c4dff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 16px 0 8px;
        }
        .results-card .level-badge {
            display: inline-block;
            padding: 8px 24px;
            border-radius: 30px;
            font-weight: 700;
            font-size: 1rem;
            margin: 8px 0 20px;
        }
        .results-card .level-badge.beginner { background: #fff3e0; color: #e65100; }
        .results-card .level-badge.intermediate { background: #e8f5e9; color: #2e7d32; }
        .results-card .level-badge.advanced { background: #e8eaf6; color: #3949ab; }
        .results-card .stats-row {
            display: flex;
            justify-content: center;
            gap: 32px;
            margin: 20px 0 28px;
        }
        .results-card .stat-item {
            text-align: center;
        }
        .results-card .stat-value {
            font-size: 1.5rem;
            font-weight: 800;
            color: #1a237e;
        }
        .results-card .stat-label {
            font-size: 0.8rem;
            color: #78909c;
            margin-top: 2px;
        }
        .btn-dashboard {
            display: inline-block;
            padding: 14px 40px;
            border-radius: 14px;
            background: linear-gradient(135deg, #1a237e, #3949ab);
            color: #ffffff;
            font-size: 1rem;
            font-weight: 700;
            text-decoration: none;
            transition: all 0.25s ease;
            border: none;
            cursor: pointer;
            font-family: inherit;
        }
        .btn-dashboard:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(26,35,126,0.4);
        }

        /* ======== LOADING & ERROR ======== */
        .loading-spinner {
            text-align: center;
            padding: 60px 20px;
            color: #5c6bc0;
            font-size: 1.05rem;
        }
        .error-msg {
            text-align: center;
            padding: 40px 20px;
            color: #e53935;
            font-weight: 600;
        }

        /* ======== RESPONSIVE ======== */
        @media (max-width: 600px) {
            .quiz-card { border-radius: 16px; }
            .quiz-header { padding: 20px 18px; }
            .quiz-header h1 { font-size: 1.2rem; }
            .question-area { padding: 20px 18px 8px; }
            .nav-row { padding: 8px 18px 20px; flex-wrap: wrap; }
            .btn { padding: 10px 18px; font-size: 0.85rem; }
            .timer-display { font-size: 1.2rem; min-width: 46px; }
            .results-card { padding: 28px 18px; }
            .results-card .score-big { font-size: 3rem; }
            .results-card .stats-row { gap: 18px; }
        }
    </style>
</head>
<body>

    <!-- ======== QUIZ CARD ======== -->
    <div class="quiz-card" id="quizCard">
        <!-- Header -->
        <div class="quiz-header">
            <div>
                <h1>📝 اختبار تحديد المستوى</h1>
                <div class="subtitle">Yamen Academy · TOEFL Diagnostic</div>
            </div>
            <div class="timer-box" id="timerBox">
                <span class="timer-icon">⏱️</span>
                <span class="timer-display" id="timerDisplay">06:00</span>
            </div>
        </div>

        <!-- Progress -->
        <div class="progress-wrap">
            <div class="progress-info">
                <span id="progressLabel">السؤال 1 من 10</span>
                <span id="answeredLabel">تمت الإجابة: 0</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill" style="width: 0%;"></div>
            </div>
        </div>

        <!-- Question Area -->
        <div class="question-area" id="questionContainer">
            <div class="loading-spinner">⏳ جاري تحميل الأسئلة...</div>
        </div>

        <!-- Navigation -->
        <div class="nav-row" id="navRow" style="display:none;">
            <button class="btn btn-prev" id="btnPrev" onclick="prevQuestion()" disabled>⬅️ السابق</button>
            <div class="question-dots" id="questionDots"></div>
            <button class="btn btn-next" id="btnNext" onclick="nextQuestion()">التالي ➡️</button>
            <button class="btn btn-submit" id="btnSubmit" onclick="submitTest()" style="display:none;">✅ إنهاء الاختبار</button>
        </div>
    </div>

    <!-- ======== RESULTS CARD ======== -->
    <div class="results-card" id="resultsCard">
        <div class="icon-check">🎉</div>
        <h2>اكتمل الاختبار!</h2>
        <div class="score-big" id="scoreBig">--%</div>
        <div class="level-badge" id="levelBadge">--</div>
        <div class="stats-row">
            <div class="stat-item">
                <div class="stat-value" id="correctCount">--</div>
                <div class="stat-label">إجابات صحيحة</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="totalCount">--</div>
                <div class="stat-label">مجموع الأسئلة</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="bandLabel">--</div>
                <div class="stat-label">المستوى</div>
            </div>
        </div>
        <p style="color:#546e7a; font-size:0.92rem; margin-bottom: 20px;" id="resultMsg"></p>
        <a class="btn-dashboard" id="dashboardLink" href="/dashboard">🏠 انتقل إلى لوحة التحكم</a>
    </div>

    <script>
        /* ======== GLOBALS ======== */
        let questions = [];
        let answers = {};
        let currentIndex = 0;
        let timeLeft = 360; // 6 minutes
        let timerInterval = null;
        let submitted = false;

        /* Generate a browser-fingerprint-based user ID */
        const USER_ID = (function() {
            let stored = localStorage.getItem('yamen_user_id');
            if (stored) return stored;
            let id = 'web_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('yamen_user_id', id);
            return id;
        })();

        /* ======== DOM REFS ======== */
        const quizCard        = document.getElementById('quizCard');
        const resultsCard     = document.getElementById('resultsCard');
        const questionContainer = document.getElementById('questionContainer');
        const navRow          = document.getElementById('navRow');
        const timerDisplay    = document.getElementById('timerDisplay');
        const timerBox        = document.getElementById('timerBox');
        const progressFill    = document.getElementById('progressFill');
        const progressLabel   = document.getElementById('progressLabel');
        const answeredLabel   = document.getElementById('answeredLabel');
        const questionDots    = document.getElementById('questionDots');
        const btnPrev         = document.getElementById('btnPrev');
        const btnNext         = document.getElementById('btnNext');
        const btnSubmit       = document.getElementById('btnSubmit');

        /* ======== TIMER ======== */
        function updateTimerDisplay() {
            let mins = Math.floor(timeLeft / 60);
            let secs = timeLeft % 60;
            timerDisplay.textContent = String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
            timerBox.classList.remove('warning', 'danger');
            if (timeLeft <= 60) timerBox.classList.add('danger');
            else if (timeLeft <= 120) timerBox.classList.add('warning');
        }

        function startTimer() {
            updateTimerDisplay();
            timerInterval = setInterval(() => {
                timeLeft--;
                updateTimerDisplay();
                if (timeLeft <= 0) {
                    clearInterval(timerInterval);
                    submitTest();
                }
            }, 1000);
        }

        /* ======== RENDER ======== */
        function renderDots() {
            questionDots.innerHTML = questions.map((_, i) => {
                let cls = 'question-dot';
                if (i === currentIndex) cls += ' current';
                if (answers[i] !== undefined) cls += ' answered';
                return '<span class="' + cls + '"></span>';
            }).join('');
        }

        function renderQuestion(index) {
            if (!questions.length) {
                questionContainer.innerHTML = '<div class="error-msg">⚠️ لا توجد أسئلة متاحة.</div>';
                return;
            }
            if (index < 0 || index >= questions.length) return;
            currentIndex = index;
            let q = questions[index];
            let skillLabels = {
                reading: '📖 قراءة', listening: '🎧 استماع', writing: '✍️ كتابة',
                speaking: '🗣️ تحدث', grammar: '📝 قواعد', vocabulary: '📚 مفردات'
            };
            let skill = (q.skill || '').toLowerCase();
            let skillTag = skillLabels[skill] ? '<span class="skill-tag">' + skillLabels[skill] + '</span>' : '';

            let html = '';
            html += '<div class="question-number">' + skillTag + 'السؤال ' + (index + 1) + ' من ' + questions.length + '</div>';
            html += '<div class="question-text">' + escapeHtml(q.question) + '</div>';
            html += '<ul class="options-list">';
            let letters = ['A', 'B', 'C', 'D'];
            let options = [
                { letter: 'A', text: q.option_a },
                { letter: 'B', text: q.option_b },
                { letter: 'C', text: q.option_c },
                { letter: 'D', text: q.option_d }
            ];
            for (let opt of options) {
                let selectedCls = (answers[index] === opt.letter) ? ' selected' : '';
                html += '<li class="option-item' + selectedCls + '" onclick="selectAnswer(' + index + ', \'' + opt.letter + '\')">';
                html += '<span class="option-letter">' + opt.letter + '</span>';
                html += '<span>' + escapeHtml(opt.text || '') + '</span>';
                html += '</li>';
            }
            html += '</ul>';
            questionContainer.innerHTML = html;

            updateNavigation();
            renderDots();
            updateProgress();
        }

        function updateNavigation() {
            btnPrev.disabled = (currentIndex === 0);
            if (currentIndex >= questions.length - 1) {
                btnNext.style.display = 'none';
                btnSubmit.style.display = 'inline-flex';
            } else {
                btnNext.style.display = 'inline-flex';
                btnSubmit.style.display = 'none';
            }
        }

        function updateProgress() {
            let answeredCount = Object.keys(answers).length;
            let pct = questions.length ? Math.round((answeredCount / questions.length) * 100) : 0;
            progressFill.style.width = pct + '%';
            progressLabel.textContent = 'السؤال ' + (currentIndex + 1) + ' من ' + questions.length;
            answeredLabel.textContent = 'تمت الإجابة: ' + answeredCount;
        }

        function selectAnswer(questionIndex, letter) {
            if (submitted) return;
            answers[questionIndex] = letter;
            renderQuestion(questionIndex);
        }

        function nextQuestion() {
            if (currentIndex < questions.length - 1) renderQuestion(currentIndex + 1);
        }

        function prevQuestion() {
            if (currentIndex > 0) renderQuestion(currentIndex - 1);
        }

        function escapeHtml(str) {
            if (!str) return '';
            let div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        /* ======== SUBMIT ======== */
        async function submitTest() {
            if (submitted) return;
            submitted = true;
            clearInterval(timerInterval);

            // Build answers array: { question_id, answer }
            let answersList = questions.map((q, i) => ({
                question_id: q.id,
                answer: answers[i] || ''
            }));

            try {
                let res = await fetch('/api/placement/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: USER_ID, answers: answersList })
                });

                if (!res.ok) {
                    let errText = await res.text();
                    showError('خطأ في الخادم: ' + res.status + ' - ' + errText);
                    submitted = false;
                    startTimer();
                    return;
                }

                let data = await res.json();

                if (data.status === 'error' || data.error) {
                    showError(data.message || data.error || 'حدث خطأ غير معروف.');
                    submitted = false;
                    startTimer();
                    return;
                }

                showResults(data);
            } catch (err) {
                showError('خطأ في حفظ النتيجة: ' + err.message);
                submitted = false;
                startTimer();
            }
        }

        function showResults(data) {
            quizCard.classList.add('hidden');
            resultsCard.classList.add('visible');
            resultsCard.style.display = 'block';

            document.getElementById('scoreBig').textContent = (data.score || 0) + '%';
            document.getElementById('correctCount').textContent = data.correct || 0;
            document.getElementById('totalCount').textContent = data.total || questions.length;
            document.getElementById('bandLabel').textContent = (data.band || '--').toUpperCase();

            let badge = document.getElementById('levelBadge');
            let level = (data.level || 'beginner').toLowerCase();
            badge.textContent = data.label || data.level || '--';
            badge.className = 'level-badge ' + level;

            document.getElementById('resultMsg').textContent = data.message || '';

            let dashLink = document.getElementById('dashboardLink');
            if (data.redirect) {
                dashLink.href = data.redirect;
            }
        }

        function showError(msg) {
            questionContainer.innerHTML = '<div class="error-msg">❌ ' + escapeHtml(msg) + '</div>';
            alert(msg);
        }

        /* ======== LOAD QUESTIONS ======== */
        async function loadQuestions() {
            try {
                let res = await fetch('/api/placement/questions');
                if (!res.ok) throw new Error('فشل تحميل الأسئلة (HTTP ' + res.status + ')');
                questions = await res.json();
                if (!questions || !questions.length) {
                    questionContainer.innerHTML = '<div class="error-msg">⚠️ لا توجد أسئلة متاحة حالياً. الرجاء التواصل مع المسؤول.</div>';
                    return;
                }
                // Limit to 10 questions
                if (questions.length > 10) questions = questions.slice(0, 10);
                navRow.style.display = 'flex';
                renderQuestion(0);
                startTimer();
            } catch (err) {
                questionContainer.innerHTML = '<div class="error-msg">❌ فشل الاتصال بالخادم: ' + escapeHtml(err.message) + '<br><br><small>تأكد من أن السيرفر يعمل على <code>localhost:8080</code></small></div>';
            }
        }

        /* ======== INIT ======== */
        document.addEventListener('DOMContentLoaded', loadQuestions);
    </script>
</body>
</html>"""

TARGET = os.path.join(os.getcwd(), "templates", "placement.html")

# Write with strict UTF-8 (no BOM)
with open(TARGET, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"[OK] placement.html written — {len(HTML.encode('utf-8')):,} bytes (UTF-8)")
print(f"[OK] Path: {TARGET}")

# Verify encoding
with open(TARGET, "r", encoding="utf-8") as f:
    content = f.read()

checks = [
    ("اكتمل الاختبار", "Arabic result text"),
    ("النتيجة", "Arabic score label"),
    ("انتقل إلى لوحة التحكم", "Arabic dashboard link"),
    ("اختبار تحديد المستوى", "Arabic title"),
    ("/api/placement/submit", "Correct submit URL"),
    ("/api/placement/questions", "Questions fetch URL"),
    ("user_id", "Payload uses user_id"),
    ("USER_ID", "Browser-fingerprint ID generation"),
    ("06:00", "Timer initial value"),
    ("startTimer", "Timer function exists"),
    ("submitTest", "Submit function exists"),
    ("renderQuestion", "Render function exists"),
    ("selectAnswer", "Answer selection exists"),
]

all_ok = True
for keyword, label in checks:
    if keyword in content:
        print(f"  ✅ {label}: '{keyword}' — FOUND")
    else:
        print(f"  ❌ {label}: '{keyword}' — MISSING!")
        all_ok = False

if all_ok:
    print("\n🎉 ALL CHECKS PASSED — placement.html is ready!")
else:
    print("\n⚠️  SOME CHECKS FAILED — review the output above.")
