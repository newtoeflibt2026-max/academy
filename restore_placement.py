# -*- coding: utf-8 -*-
"""Restore placement.html with correct UTF-8 encoding."""

html = u"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yamen Academy - اختبار تحديد المستوى</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: linear-gradient(135deg, #1a237e 0%, #283593 100%); min-height: 100vh; }
        .container { max-width: 800px; margin: 0 auto; padding: 1rem; }
        
        .header { background: white; border-radius: 16px; padding: 1.5rem; margin-top: 1rem; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.15); }
        .header h1 { color: #1a237e; font-size: 1.8rem; margin-bottom: 0.3rem; }
        .header .meta { color: #666; font-size: 0.9rem; }
        .header .badge-row { display: flex; justify-content: center; gap: 0.5rem; margin-top: 0.8rem; flex-wrap: wrap; }
        .badge { padding: 0.3rem 1rem; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
        .badge-questions { background: #e8eaf6; color: #1a237e; }
        .badge-time { background: #fff3e0; color: #e65100; }
        .badge-level { background: #e8f5e9; color: #2e7d32; }
        
        .progress-bar { background: white; border-radius: 12px; padding: 0.8rem 1rem; margin-top: 1rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); display: flex; align-items: center; gap: 1rem; }
        .progress-bar .progress { flex: 1; height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; }
        .progress-bar .progress-fill { height: 100%; background: #1a237e; border-radius: 4px; transition: width 0.3s; }
        .progress-bar .counter { font-size: 0.9rem; font-weight: bold; color: #1a237e; white-space: nowrap; }
        .progress-bar .timer { font-size: 0.9rem; font-weight: bold; color: #e65100; white-space: nowrap; }
        
        .card { background: white; border-radius: 16px; padding: 2rem; margin-top: 1rem; box-shadow: 0 4px 20px rgba(0,0,0,0.15); }
        .card .q-num { display: inline-block; background: #1a237e; color: white; padding: 0.3rem 1rem; border-radius: 12px; font-size: 0.85rem; margin-bottom: 1rem; }
        .card .q-skill { display: inline-block; padding: 0.25rem 0.8rem; border-radius: 12px; font-size: 0.75rem; font-weight: bold; margin-right: 0.5rem; }
        .card h2 { color: #1a237e; font-size: 1.2rem; margin: 1rem 0; line-height: 1.6; }
        
        .options { display: flex; flex-direction: column; gap: 0.7rem; margin-top: 1.5rem; }
        .option { display: flex; align-items: center; gap: 0.8rem; padding: 1rem 1.2rem; border: 2px solid #e0e0e0; border-radius: 12px; cursor: pointer; transition: all 0.2s; font-size: 1rem; }
        .option:hover { border-color: #1a237e; background: #f5f5ff; }
        .option.selected { border-color: #1a237e; background: #e8eaf6; font-weight: bold; }
        .option .letter { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 0.9rem; background: #e8eaf6; color: #1a237e; flex-shrink: 0; }
        .option.selected .letter { background: #1a237e; color: white; }
        
        .nav-btns { display: flex; justify-content: space-between; margin-top: 1.5rem; gap: 1rem; }
        .btn { padding: 0.7rem 2rem; border-radius: 10px; font-size: 1rem; font-weight: bold; cursor: pointer; border: none; transition: all 0.2s; }
        .btn-prev { background: #e0e0e0; color: #333; }
        .btn-prev:hover { background: #bdbdbd; }
        .btn-next { background: #1a237e; color: white; }
        .btn-next:hover { background: #283593; }
        .btn-submit { background: #2e7d32; color: white; }
        .btn-submit:hover { background: #1b5e20; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        
        .result-card { text-align: center; }
        .result-card .big-score { font-size: 4rem; font-weight: bold; color: #1a237e; }
        .result-card .level-badge { display: inline-block; margin-top: 1rem; padding: 0.5rem 2rem; border-radius: 25px; font-size: 1.2rem; font-weight: bold; color: white; }
        .result-card .stats { display: flex; justify-content: center; gap: 2rem; margin: 1.5rem 0; }
        .result-card .stat { text-align: center; }
        .result-card .stat .value { font-size: 1.5rem; font-weight: bold; color: #1a237e; }
        .result-card .stat .label { font-size: 0.8rem; color: #888; }
        
        .skill-reading { background: #ffcdd2; color: #c62828; }
        .skill-listening { background: #bbdefb; color: #1565c0; }
        .skill-writing { background: #c8e6c9; color: #2e7d32; }
        .skill-speaking { background: #ffe0b2; color: #e65100; }
        .skill-grammar { background: #e1bee7; color: #6a1b9a; }
        .skill-vocabulary { background: #b2ebf2; color: #00838f; }
        
        .loading { text-align: center; padding: 3rem; color: white; }
        .loading .spinner { width: 50px; height: 50px; border: 4px solid rgba(255,255,255,0.3); border-top-color: white; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 1rem; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>📝 اختبار تحديد المستوى</h1>
            <p class="meta">10 أسئلة اختيارية • 6 دقائق • مستوى TOEFL</p>
            <div class="badge-row">
                <span class="badge badge-questions">✅ التصنيف: ضعيف (0-3) / متوسط (4-7) / متقدم (8-10)</span>
                <span class="badge badge-time">✅ لا يمكن تخطي الاختبار</span>
                <span class="badge badge-level">✅ الإكمال إجباري للدخول إلى الداشبورد</span>
            </div>
        </div>

        <!-- Progress Bar -->
        <div class="progress-bar" id="progress-bar">
            <div class="progress"><div class="progress-fill" id="progress-fill" style="width:0%"></div></div>
            <span class="counter" id="q-counter">0/10</span>
            <span class="timer" id="timer">06:00</span>
        </div>

        <!-- Question Card -->
        <div class="card" id="question-card">
            <div id="question-content"></div>
        </div>

        <!-- Result Card (hidden initially) -->
        <div class="card result-card" id="result-card" style="display:none;">
            <h2 style="color:#1a237e;">🎉 اكتمل الاختبار!</h2>
            <div class="big-score" id="result-score">0%</div>
            <div class="level-badge" id="result-level">---</div>
            <div class="stats">
                <div class="stat"><div class="value" id="result-correct">0</div><div class="label">صحيح</div></div>
                <div class="stat"><div class="value" id="result-total">0</div><div class="label">الأسئلة</div></div>
                <div class="stat"><div class="value" id="result-band">---</div><div class="label">المستوى</div></div>
            </div>
            <p id="result-message" style="color:#666; margin:1rem 0;"></p>
            <button class="btn btn-submit" onclick="goToDashboard()">📊 انتقل إلى الداشبورد</button>
        </div>

        <!-- Loading -->
        <div class="loading" id="loading" style="display:none;">
            <div class="spinner"></div>
            <p>جاري تحميل الأسئلة...</p>
        </div>
    </div>

    <script>
        const USER_ID = new URLSearchParams(location.search).get("user_id") || "5602495831";
        let questions = [], currentIndex = 0, answers = {}, timer = null;
        let timeLeft = 360; // 6 minutes

        async function loadQuestions() {
            document.getElementById("loading").style.display = "block";
            document.getElementById("question-card").style.display = "none";
            try {
                const res = await fetch("/api/placement/questions");
                const all = await res.json();
                questions = all.slice(0, 10);
                if (questions.length === 0) {
                    document.getElementById("loading").innerHTML = "<p style='color:white;'>لا توجد أسئلة متاحة حالياً</p>";
                    return;
                }
                document.getElementById("loading").style.display = "none";
                document.getElementById("question-card").style.display = "block";
                currentIndex = 0;
                renderQuestion();
                startTimer();
            } catch (e) {
                document.getElementById("loading").innerHTML = "<p style='color:white;'>خطأ في تحميل الأسئلة: " + e.message + "</p>";
            }
        }

        function startTimer() {
            updateTimerDisplay();
            timer = setInterval(function() {
                timeLeft--;
                updateTimerDisplay();
                if (timeLeft <= 0) {
                    clearInterval(timer);
                    submitTest();
                }
            }, 1000);
        }

        function updateTimerDisplay() {
            var mins = Math.floor(timeLeft / 60);
            var secs = timeLeft % 60;
            document.getElementById("timer").textContent = (mins < 10 ? "0" : "") + mins + ":" + (secs < 10 ? "0" : "") + secs;
            if (timeLeft <= 60) {
                document.getElementById("timer").style.color = "#c62828";
            }
        }

        function renderQuestion() {
            if (currentIndex >= questions.length) {
                submitTest();
                return;
            }
            var q = questions[currentIndex];
            var progressPct = ((currentIndex + 1) / questions.length) * 100;
            document.getElementById("progress-fill").style.width = progressPct + "%";
            document.getElementById("q-counter").textContent = (currentIndex + 1) + "/" + questions.length;

            var skillClass = "skill-" + (q.skill || "reading");
            var skillName = q.skill || "reading";
            var letters = ["A", "B", "C", "D"];
            var options = [q.option_a, q.option_b, q.option_c, q.option_d];

            var html = '<span class="q-num">سؤال ' + (currentIndex + 1) + '</span>';
            html += '<span class="q-skill ' + skillClass + '">' + skillName + '</span>';
            html += '<h2>' + q.question + '</h2>';
            html += '<div class="options">';

            for (var i = 0; i < options.length; i++) {
                var selected = answers[q.id] === letters[i] ? ' selected' : '';
                html += '<div class="option' + selected + '" onclick="selectAnswer(' + q.id + ', \'' + letters[i] + '\')">';
                html += '<div class="letter">' + letters[i] + '</div>';
                html += '<span>' + options[i] + '</span>';
                html += '</div>';
            }

            html += '</div>';
            html += '<div class="nav-btns">';
            html += '<button class="btn btn-prev" onclick="prevQuestion()" ' + (currentIndex === 0 ? 'disabled' : '') + '>← السابق</button>';
            if (currentIndex === questions.length - 1) {
                html += '<button class="btn btn-submit" onclick="submitTest()">✅ إنهاء الاختبار</button>';
            } else {
                html += '<button class="btn btn-next" onclick="nextQuestion()">التالي →</button>';
            }
            html += '</div>';

            document.getElementById("question-content").innerHTML = html;
        }

        function selectAnswer(qid, letter) {
            answers[qid] = letter;
            renderQuestion();
        }

        function nextQuestion() {
            if (currentIndex < questions.length - 1) {
                currentIndex++;
                renderQuestion();
            }
        }

        function prevQuestion() {
            if (currentIndex > 0) {
                currentIndex--;
                renderQuestion();
            }
        }

        async function submitTest() {
            if (timer) { clearInterval(timer); }

            var answerList = [];
            for (var qid in answers) {
                if (answers.hasOwnProperty(qid)) {
                    answerList.push({ question_id: parseInt(qid), answer: answers[qid] });
                }
            }

            document.getElementById("question-card").style.display = "none";
            document.getElementById("result-card").style.display = "block";
            document.getElementById("result-score").textContent = "...";
            document.getElementById("result-level").textContent = "جاري التصحيح...";

            try {
                var res = await fetch("/api/placement/submit", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ student_id: USER_ID, answers: answerList })
                });

                var data = await res.json();

                if (data.status === "ok") {
                    var levelColors = { beginner: "#e65100", intermediate: "#1565c0", advanced: "#2e7d32" };
                    document.getElementById("result-score").textContent = data.score + "%";
                    document.getElementById("result-level").textContent = data.label + " (" + data.band + ")";
                    document.getElementById("result-level").style.background = levelColors[data.level] || "#1a237e";
                    document.getElementById("result-correct").textContent = data.correct;
                    document.getElementById("result-total").textContent = data.total;
                    document.getElementById("result-band").textContent = data.band;
                    document.getElementById("result-message").textContent = data.message;
                } else {
                    document.getElementById("result-score").textContent = "خطأ";
                    document.getElementById("result-level").textContent = "فشل";
                    document.getElementById("result-message").textContent = data.message || "حدث خطأ غير معروف";
                }
            } catch (e) {
                document.getElementById("result-score").textContent = "خطأ";
                document.getElementById("result-level").textContent = "فشل";
                document.getElementById("result-message").textContent = "خطأ في حفظ النتيجة: " + e.message;
            }
        }

        function goToDashboard() {
            window.location.href = "/dashboard/" + USER_ID;
        }

        // Start
        loadQuestions();
    </script>
</body>
</html>"""

with open("templates/placement.html", "w", encoding="utf-8") as f:
    f.write(html)

print("[OK] placement.html restored!")
print("- UTF-8 encoding (no BOM)")
print("- Correct URL: /api/placement/submit")
print("- All Arabic text intact")
print("- File size: {} bytes".format(len(html.encode("utf-8"))))
