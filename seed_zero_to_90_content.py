# -*- coding: utf-8 -*-
"""
Seed / enrich reading content for Yamen Academy mini app.
Goal: help weak students progress from zero to 90 in TOEFL iBT 2026 reading.

What this script does:
1) enriches lessons 19..30 with real teaching content, focus points, vocabulary,
   and grammar/rule hints where missing or too short.
2) seeds daily_missions table if empty.

Usage:
    set DB_PATH=C:\path\to\academy.db
    py seed_zero_to_90_content.py
"""
import os, sqlite3, json, datetime


def resolve_db_path():
    env = os.environ.get("DB_PATH", "").strip()
    if env:
        return env
    if os.path.isdir("/app/data"):
        return "/app/data/academy.db"
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")

DB_PATH = resolve_db_path()
TODAY = datetime.date.today().isoformat()

LESSONS = {
    19: {
        "focus_point": "فهم بنية قسم Reading الجديد في TOEFL iBT 2026: ما الذي ستراه؟ وكيف تُوزَّع المهام؟",
        "vocabulary": "module, passage, academic text, factual question, inference, vocabulary in context, timing",
        "grammar_rule": "هنا لا نركز على قاعدة نحوية واحدة؛ نركز على قراءة السؤال أولاً ثم تحديد نوع المهمة قبل البدء بالإجابة.",
        "content": """
<h2>📘 بنية قسم القراءة الجديد — TOEFL iBT 2026</h2>
<p>في التوفل الجديد لا يكفي أن تكون لغتك جيدة فقط؛ يجب أن <b>تفهم شكل الامتحان</b> حتى لا تضيع الوقت. الطالب الضعيف عادة يخسر درجات سهلة لأنه يدخل السؤال بلا خطة.</p>
<h3>ما الذي ستتعلمه في هذا الدرس؟</h3>
<ul>
  <li>كيف يبدو قسم القراءة من الداخل.</li>
  <li>ما الفرق بين نصوص الحياة اليومية والنصوص الأكاديمية.</li>
  <li>ما أنواع الأسئلة التي تتكرر كثيراً.</li>
  <li>كيف تفرّق بين سؤال Fact وVocabulary وInference خلال ثوانٍ.</li>
</ul>
<h3>الفكرة الذهبية</h3>
<p>قبل أن تقرأ النص كله، اسأل نفسك: <b>ما نوع المهمة؟</b> لأن نوع المهمة يحدد طريقة القراءة. أحياناً تحتاج البحث عن حقيقة مباشرة، وأحياناً تحتاج فهم معنى كلمة من السياق، وأحياناً تحتاج استنتاجاً غير مكتوب حرفياً.</p>
<h3>خطة الطالب من الصفر إلى 90</h3>
<ol>
  <li>ابدأ بالنصوص القصيرة واليومية حتى يثبت الأساس.</li>
  <li>انتقل إلى النصوص الأكاديمية السهلة ثم المتوسطة.</li>
  <li>تعلّم أنماط الأسئلة، وليس الكلمات فقط.</li>
  <li>درّب نفسك على السرعة الهادئة: فهم + قرار سريع.</li>
</ol>
<h3>مؤشر النجاح في هذا الدرس</h3>
<p>إذا استطعت بعد الدرس أن تشرح باختصار ما هو الفرق بين <b>Factual</b> و <b>Inference</b> و <b>Vocabulary in Context</b> فأنت بدأت الطريق الصحيح.</p>
"""
    },
    20: {
        "focus_point": "إتقان تقنية SCAN → READ → ANSWER بدل القراءة العشوائية.",
        "vocabulary": "scan, keyword, clue, anchor word, skim, locate, eliminate",
        "grammar_rule": "الاستراتيجية هنا مهارية لا نحوية: نبدأ بالكلمة المفتاحية ثم نعود للسطر الداعم قبل اختيار الإجابة.",
        "content": """
<h2>🔎 تقنية SCAN-READ-ANSWER الذهبية</h2>
<p>معظم الطلاب الضعفاء يقرأون النص من أوله إلى آخره ثم يبدأون في السؤال. هذه طريقة بطيئة ومتعبة. الطريقة الأفضل في القراءة الموجّهة هي:</p>
<ol>
  <li><b>SCAN</b>: امسح السؤال وابحث عن الكلمات المفتاحية.</li>
  <li><b>READ</b>: اقرأ فقط الجزء القريب من الكلمة المفتاحية.</li>
  <li><b>ANSWER</b>: جاوب بعد إلغاء الخيارات الخاطئة.</li>
</ol>
<h3>كيف نختار الكلمة المفتاحية؟</h3>
<ul>
  <li>اسم شخص أو مكان أو تاريخ.</li>
  <li>مصطلح أكاديمي واضح.</li>
  <li>عبارة مميزة لا تتكرر كثيراً.</li>
</ul>
<h3>خطأ شائع</h3>
<p>الطالب يرى الكلمة المفتاحية في النص فيختار أول خيار يشبهها. الصحيح هو أن <b>تقرأ الجملة قبلها وبعدها</b> لأن الجواب غالباً يكون في الشرح لا في الكلمة نفسها.</p>
<h3>قاعدة إلغاء الخيارات</h3>
<p>إذا وجدت خياراً <b>أقوى من النص</b> أو <b>أوسع من النص</b> أو <b>يعكس النص</b> فهو غالباً خطأ. تعلّم حذف الخطأ قبل البحث عن الصحيح.</p>
<h3>تدريب منزلي</h3>
<p>عند كل سؤال، دوّن 3 أشياء: الكلمة المفتاحية، السطر الداعم، والسبب الذي جعلك تحذف خيارين على الأقل.</p>
"""
    },
    21: {
        "focus_point": "Task 1 Complete the Words: كيف تكمل الكلمة الناقصة باستخدام المعنى وبنية الكلمة؟",
        "vocabulary": "prefix, suffix, root, noun form, verb form, adjective form, context clue",
        "grammar_rule": "لاحظ نوع الكلمة المطلوبة: اسم؟ فعل؟ صفة؟ ثم استخدم الجذر + النهاية المناسبة.",
        "content": """
<h2>✍️ Task 1 — إكمال الكلمات</h2>
<p>هذا النوع لا يقيس الحفظ فقط، بل يقيس <b>الوعي ببنية الكلمة</b> ومعنى الجملة. الطالب القوي لا يخمّن الحروف؛ بل يسأل:</p>
<ul>
  <li>ما نوع الكلمة المطلوبة هنا؟</li>
  <li>هل تحتاج صيغة اسم أم فعل أم صفة؟</li>
  <li>ما الإشارة في السياق التي تقودني للإجابة؟</li>
</ul>
<h3>مفاتيح الحل</h3>
<ol>
  <li>اقرأ الجملة كاملة أولاً.</li>
  <li>حدّد معنى الفراغ.</li>
  <li>استفد من أول الحروف أو الجذر.</li>
  <li>راجع هل الكلمة تناسب القاعدة والمعنى معاً.</li>
</ol>
<h3>مثال</h3>
<p>If technology has revo_____ education, then online learning has become essential.</p>
<p>هنا الكلمة المطلوبة فعل ماضٍ/اسم معنى؟ السياق يشير إلى <b>revolutionized</b> لأن الجملة تتحدث عن أثر كبير غيّر التعليم.</p>
<h3>الهدف من هذا الدرس</h3>
<p>أن تتوقف عن التخمين الأعمى وتبدأ بالنظر إلى <b>المعنى + الصيغة</b> في وقت واحد.</p>
"""
    },
    22: {
        "focus_point": "Task 2 النصوص اليومية: الإعلانات، الرسائل، الجداول، التنبيهات.",
        "vocabulary": "notice, schedule, opening hours, policy, fee, appointment, deadline",
        "grammar_rule": "في نصوص الحياة اليومية، المعلومة المهمة غالباً تأتي في كلمات عملية: time, fee, date, rule, requirement.",
        "content": """
<h2>🧾 Task 2 — القراءة في الحياة اليومية</h2>
<p>هذا النوع ممتاز للطلاب الضعفاء لأنه يبني الثقة بسرعة. النصوص هنا تشبه ما قد تراه في الحياة: إعلان، بريد، جدول، منشور، تعليمات.</p>
<h3>ما الذي يجب أن تبحث عنه؟</h3>
<ul>
  <li>من؟ لمن؟</li>
  <li>متى؟</li>
  <li>كم؟</li>
  <li>ما القاعدة أو الشرط؟</li>
</ul>
<h3>استراتيجية سريعة</h3>
<p>في هذا النوع لا تبدأ من كل كلمة. ابدأ من البيانات العملية: <b>الأوقات، التواريخ، الأسعار، الشروط، أماكن الحدث</b>. هذه غالباً تحمل الإجابة.</p>
<h3>الفخ الشائع</h3>
<p>خلط بين التفاصيل القديمة والجديدة، مثل ساعات عمل قديمة وساعات معدلة، أو شرط عام واستثناء خاص.</p>
<h3>لماذا هذا الدرس مهم للطريق إلى 90؟</h3>
<p>لأن الطالب الذي يتقن النصوص اليومية يتعلّم مهارة أساسية: <b>التقاط المعلومة الدقيقة بسرعة</b>. وهذه المهارة نفسها تنتقل لاحقاً إلى النصوص الأكاديمية.</p>
"""
    },
    23: {
        "focus_point": "أسئلة Fact وNegative Fact: أين الدليل؟ وكيف نكتشف الخيار غير المذكور؟",
        "vocabulary": "according to, states, mentions, NOT mentioned, directly stated, detail",
        "grammar_rule": "عندما ترى according to the passage أو states that فاعلم أن الجواب في النص بشكل مباشر غالباً.",
        "content": """
<h2>📚 Task 3 Part 1 — Factual & Negative Factual</h2>
<p>هذا هو أول باب حقيقي لدخول القراءة الأكاديمية. الفكرة البسيطة: بعض الأسئلة تريد معلومة مذكورة مباشرة، وبعضها يريد الخيار الذي <b>لم يُذكر</b>.</p>
<h3>أسئلة Fact</h3>
<p>إذا رأيت كلمات مثل <b>According to the passage</b> أو <b>The passage states</b>، فأنت تبحث عن دليل مباشر.</p>
<h3>أسئلة Negative Fact</h3>
<p>إذا رأيت <b>NOT</b> أو <b>EXCEPT</b>، غيّر عقلك فوراً. هنا لا نبحث عما هو صحيح، بل عما <b>ليس مدعوماً بالنص</b>.</p>
<h3>طريقة الحل</h3>
<ol>
  <li>حدد السؤال: Fact أم Negative Fact؟</li>
  <li>ابحث عن السطر الداعم.</li>
  <li>في Negative Fact: استبعد 3 خيارات مدعومة، والباقي هو الجواب.</li>
</ol>
<h3>تنبيه مهم</h3>
<p>لا تعتمد على معرفتك العامة. التوفل لا يسألك: ماذا تعرف؟ بل يسألك: <b>ماذا قال النص؟</b></p>
"""
    },
    24: {
        "focus_point": "Vocabulary in Context: معنى الكلمة من السياق وليس من القاموس.",
        "vocabulary": "context, substitute, closest meaning, nuance, infer from surrounding sentence",
        "grammar_rule": "اختبر كل خيار داخل الجملة: أي كلمة يمكن أن تُستبدل دون أن ينهار المعنى؟",
        "content": """
<h2>🧠 Task 3 Part 2 — Vocabulary in Context</h2>
<p>ليس المطلوب أن تعرف كل كلمة في النص. المطلوب أن تعرف كيف تستخرج <b>المعنى الأقرب</b> من السياق.</p>
<h3>خطوات ذكية</h3>
<ol>
  <li>اقرأ الجملة التي فيها الكلمة.</li>
  <li>اقرأ الجملة قبلها وبعدها.</li>
  <li>اسأل: هل المعنى هنا إيجابي أم سلبي؟ عام أم دقيق؟</li>
  <li>جرّب خيارات الإجابة داخل الجملة.</li>
</ol>
<h3>الفخ الشائع</h3>
<p>اختيار معنى معجمي مشهور للكلمة رغم أنه لا يناسب الجملة. في التوفل، <b>السياق هو القاضي</b>.</p>
<h3>مثال تدريبي</h3>
<p>If a theory was <b>challenged</b>, هل المقصود attacked أم explained أم repeated؟ انظر إلى الجمل المحيطة لترى هل السياق يتحدث عن نقد أم دعم.</p>
"""
    },
    25: {
        "focus_point": "Inference & Rhetorical Purpose: ماذا يُفهَم من النص؟ ولماذا ذكر الكاتب هذه المعلومة؟",
        "vocabulary": "infer, imply, suggest, purpose, rhetorical function, likely, probably",
        "grammar_rule": "إذا جاء السؤال بصيغة suggests / implies / likely means، فالإجابة ليست اقتباساً حرفياً بل نتيجة منطقية مدعومة بالنص.",
        "content": """
<h2>🎯 Task 3 Part 3 — Inference & Rhetorical Purpose</h2>
<p>هنا يبدأ الفرق الحقيقي بين الطالب المتوسط والطالب الذي يسير نحو 90. السؤال لا يقول لك: أين المعلومة؟ بل يقول: <b>ماذا نفهم من المعلومة؟</b></p>
<h3>Inference</h3>
<p>الاستنتاج يعني أن الجواب <b>ليس مكتوباً حرفياً</b> لكنه نتيجة منطقية إذا جمعت الأدلة.</p>
<h3>Rhetorical Purpose</h3>
<p>لماذا ذكر الكاتب هذا المثال أو هذه الجملة؟ هل ليدعم فكرة؟ ليعطي مثالاً؟ ليقارن؟ ليحذّر؟</p>
<h3>قانون مهم</h3>
<p>الإجابة الصحيحة في Inference تكون <b>أقل من النص بدرجة</b>، لا أكثر. إذا كان الخيار يبالغ أو يعمم فهو غالباً خطأ.</p>
<h3>طريقة سريعة</h3>
<ol>
  <li>حدد الفقرة أو الجملة الهدف.</li>
  <li>اسأل: ما الرسالة التي أراد الكاتب إيصالها؟</li>
  <li>اختر خياراً يمكن الدفاع عنه من النص، لا من التخمين.</li>
</ol>
"""
    },
    26: {
        "focus_point": "Insert a Sentence & Paragraph Relations: أين تذهب الجملة؟ وما علاقتها بالفقرة؟",
        "vocabulary": "reference, transition, pronoun clue, contrast, cause, result, example, continuation",
        "grammar_rule": "ابحث عن أدوات الربط والضمائر: this, these, however, therefore, for example. هي مفاتيح مكان الجملة.",
        "content": """
<h2>🧩 Task 3 Part 4 — Insert a Sentence & Paragraph Relations</h2>
<p>هذا النوع يقيس فهمك لتماسك النص، لا فهم الجملة وحدها.</p>
<h3>متى توضع الجملة في مكان معين؟</h3>
<ul>
  <li>إذا بدأت بـ however فهي غالباً بعد فكرة معاكسة.</li>
  <li>إذا احتوت this/these/it فهي تحتاج مرجعاً قبلها.</li>
  <li>إذا بدأت بـ for example فهي تأتي بعد فكرة عامة.</li>
  <li>إذا شرحت نتيجة فابحث عن سبب قبلها.</li>
</ul>
<h3>العلاقة داخل الفقرة</h3>
<p>كل فقرة جيدة فيها تدفق: فكرة → شرح → مثال → نتيجة. إذا فهمت هذا التدفق، صار مكان الجملة أوضح بكثير.</p>
<h3>سر الطلاب الأقوياء</h3>
<p>هم لا يقرأون الجملة وحدها فقط؛ بل يختبرون اتصالها بما قبلها وما بعدها.</p>
"""
    },
    27: {
        "focus_point": "بناء المفردات الأكاديمية بتقنية CRIS: Collect, Review, Infer, Speak/Use.",
        "vocabulary": "collect, review, infer, usage, collocation, synonym, academic family",
        "grammar_rule": "لا تحفظ الكلمة منفصلة؛ احفظ معناها، نوعها، مرادفها، وجملة استخدام حقيقية.",
        "content": """
<h2>📖 بناء المفردات الأكاديمية — تقنية CRIS</h2>
<p>الطالب الذي يطمح إلى 90 لا يعتمد على الحفظ العشوائي. هو يبني مفرداته بطريقة منظمة.</p>
<h3>تقنية CRIS</h3>
<ol>
  <li><b>Collect</b>: اجمع الكلمات المهمة من الدروس والنصوص.</li>
  <li><b>Review</b>: راجعها مراجعة متقطعة على أيام.</li>
  <li><b>Infer</b>: استخرج معناها من السياق قبل رؤية الترجمة.</li>
  <li><b>Speak / Use</b>: استخدمها في جملة قصيرة من عندك.</li>
</ol>
<h3>كيف تحفظ بذكاء؟</h3>
<ul>
  <li>احفظ الكلمة مع نوعها: noun / verb / adjective.</li>
  <li>احفظ معها مرادفاً بسيطاً.</li>
  <li>احفظ معها مثالاً قصيراً.</li>
</ul>
<h3>هدف هذا الدرس</h3>
<p>أن تتحول المفردات من "قائمة صعبة" إلى "أدوات قراءة" تساعدك على الفهم السريع.</p>
"""
    },
    28: {
        "focus_point": "تطبيق شامل متوسط: دمج مهارات fact + vocab + inference في نص أكاديمي واحد.",
        "vocabulary": "ecosystem, evidence, adaptation, process, response, effect, theory",
        "grammar_rule": "راجع نوع السؤال أولاً، ثم طبّق الاستراتيجية المناسبة بدل استخدام نفس الأسلوب لكل الأسئلة.",
        "content": """
<h2>🧪 تطبيق شامل — النصوص الأكاديمية (المستوى المتوسط)</h2>
<p>في هذا الدرس لن تتعلم مهارة جديدة فقط، بل ستدمج ما تعلمته سابقاً في نص أكاديمي حقيقي.</p>
<h3>ماذا تتدرّب عليه هنا؟</h3>
<ul>
  <li>التقاط المعلومة المباشرة.</li>
  <li>فهم كلمة من السياق.</li>
  <li>استخراج استنتاج منطقي.</li>
  <li>إدارة الوقت بين الأسئلة.</li>
</ul>
<h3>قاعدة الدمج</h3>
<p>ليس كل سؤال يُحل بالطريقة نفسها. النجاح في هذا الدرس يعني أن <b>تتعرف أولاً على نوع السؤال</b> ثم تطبق التقنية المناسبة بسرعة.</p>
<h3>بعد هذا الدرس</h3>
<p>إذا نجحت هنا، فأنت جاهز للانتقال من "التأسيس" إلى "التحكم" الحقيقي في القراءة الأكاديمية.</p>
"""
    },
    29: {
        "focus_point": "تطبيق شامل صعب: التعامل مع نصوص عالية الكثافة ومفاهيم علمية معقدة.",
        "vocabulary": "quantum, evolution, mechanism, hypothesis, distinguish, transform, evidence-based",
        "grammar_rule": "لا تتوقف عند كل كلمة صعبة. ابحث عن الفكرة العامة أولاً ثم عد للتفاصيل المطلوبة فقط.",
        "content": """
<h2>🚀 تطبيق شامل — النصوص الأكاديمية الصعبة</h2>
<p>هذا الدرس يبني قدرة الطالب على مواجهة نصوص تشبه المستوى الحقيقي للدرجات العالية.</p>
<h3>كيف نتعامل مع نص صعب؟</h3>
<ol>
  <li>لا تحاول ترجمة كل شيء.</li>
  <li>حدّد الفكرة العامة لكل فقرة.</li>
  <li>ضع دائرة ذهنية حول الكلمات العلمية المتكررة.</li>
  <li>ارجع فقط إلى الجزء الذي يحتاجه السؤال.</li>
</ol>
<h3>الفخ الأخطر</h3>
<p>الهلع من أول فقرة. النص الصعب لا يعني أنه مستحيل. في كثير من الأحيان، الأسئلة نفسها يمكن حلها إذا فهمت <b>العلاقات الأساسية</b> داخل النص.</p>
"""
    },
    30: {
        "focus_point": "10 قواعد ذهبية للعلامة العالية في Reading.",
        "vocabulary": "discipline, elimination, precision, consistency, pacing, evidence, review",
        "grammar_rule": "هذه ليست قواعد نحوية، بل قواعد أداء في الامتحان: كيف تفكر، كيف تحذف، وكيف تحافظ على الوقت.",
        "content": """
<h2>🏆 أسرار العلامة الكاملة — 10 قواعد ذهبية</h2>
<ol>
  <li>اقرأ السؤال قبل أن تتورط في النص.</li>
  <li>حدّد نوع السؤال أولاً.</li>
  <li>لا تثق في الخيار الذي يبدو مألوفاً فقط.</li>
  <li>ابحث عن الدليل، لا عن الإحساس.</li>
  <li>في Inference: اختر الأقل مبالغة.</li>
  <li>في Negative Fact: استبعد ما هو مذكور.</li>
  <li>في Vocabulary: اختبر البديل داخل الجملة.</li>
  <li>في Sentence Insertion: راقب الضمائر والروابط.</li>
  <li>إذا احترت بين خيارين، اسأل: أيهما مدعوم أكثر؟</li>
  <li>الثبات أهم من السرعة العشوائية.</li>
</ol>
<p>إذا التزمت بهذه القواعد مع التدريب التدريجي، فطريق 90 يصبح واقعياً جداً حتى للطالب الذي بدأ من مستوى ضعيف.</p>
"""
    }
}

MISSIONS = [
    ("مهمة اليوم: قراءة موجهة", "ابدأ بأقرب درس Reading غير مكتمل وركّز على نوع السؤال قبل اختيار الإجابة.", "reading", 20, "lesson", 1),
    ("مهمة اليوم: مفردات أكاديمية", "استخرج 5 كلمات أكاديمية من الدرس الحالي واكتب معنى كل كلمة وجملة قصيرة.", "reading", 15, "vocabulary", 5),
    ("مهمة اليوم: سرعة ودقة", "أجب عن 5 أسئلة مع تدوين سبب حذف خيارين في كل سؤال.", "reading", 20, "quiz", 5),
]

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

for lid, payload in LESSONS.items():
    cur.execute("SELECT id, LENGTH(COALESCE(content,'')) FROM lessons WHERE id=?", (lid,))
    row = cur.fetchone()
    if not row:
        continue
    cur.execute("""
        UPDATE lessons
        SET content=?, focus_point=?, vocabulary=?, grammar_rule=?, title_ar=COALESCE(title_ar, title)
        WHERE id=?
    """, (payload["content"], payload["focus_point"], payload["vocabulary"], payload["grammar_rule"], lid))

cur.execute("SELECT COUNT(*) FROM daily_missions")
mission_count = cur.fetchone()[0]
if mission_count == 0:
    for i, (title, desc, skill, xp, mtype, target_count) in enumerate(MISSIONS):
        cur.execute("""
            INSERT INTO daily_missions
            (title, description, skill_type, xp_reward, mission_date, morning_message, is_active, mission_type, target_count)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (title, desc, skill, xp, TODAY, f"صباح الخير 🌟 {title}", mtype, target_count))

con.commit()
con.close()
print(f"[OK] Seeded/enriched reading content in {DB_PATH}")
