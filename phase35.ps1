# ============================================================
# Phase 3.5: Email Coach - 6-Step Learning System
# ============================================================
cd C:\Users\nelt2\yamen_academy

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = "_backups\phase35_$ts"
New-Item -ItemType Directory -Force -Path $backup | Out-Null
Copy-Item "routes\writing_toefl.py" "$backup\"
Copy-Item "academy.db" "$backup\"
Copy-Item -Recurse "templates\toefl_writing" "$backup\" -ErrorAction SilentlyContinue
Write-Host "[OK] Backup: $backup" -ForegroundColor Green

# ============================================================
# 1) جداول DB جديدة + بذر المحتوى التعليمي
# ============================================================
@'
# -*- coding: utf-8 -*-
import sqlite3, json, os

DB = "academy.db"
con = sqlite3.connect(DB)
cur = con.cursor()

# جدول المحتوى التعليمي لكل سيناريو
cur.execute("""
CREATE TABLE IF NOT EXISTS email_coach_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id INTEGER NOT NULL,
    target_tier TEXT NOT NULL,
    step1_situation_ar TEXT,
    step1_situation_en TEXT,
    step1_recipient_ar TEXT,
    step1_tone_ar TEXT,
    step1_goals_json TEXT,
    step2_structure_json TEXT,
    step3_phrases_json TEXT,
    step4_model_email TEXT,
    step4_annotations_json TEXT,
    step5_fill_template TEXT,
    step5_blanks_hints_json TEXT,
    step6_checklist_json TEXT,
    common_mistakes_json TEXT,
    video_url TEXT,
    UNIQUE(scenario_id, target_tier)
)
""")

# جدول تقدم الطالب في خطوات التعلم
cur.execute("""
CREATE TABLE IF NOT EXISTS email_coach_progress (
    telegram_id TEXT,
    scenario_id INTEGER,
    step_completed INTEGER DEFAULT 0,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (telegram_id, scenario_id)
)
""")

cur.execute("DELETE FROM email_coach_content")

# ============================================================
# المحتوى التعليمي لكل سيناريو + لكل tier
# ============================================================

content = []

# ====== SCENARIO 1: غياب عن المحاضرة (tier59) ======
content.append({
    "scenario_id": 1,
    "target_tier": "tier59",
    "step1_situation_ar": "تخيّل أنك طالب جامعي في كورس مهم، ومرضت يوم أمس ولم تستطع حضور المحاضرة. الآن أستاذك أرسل لك إيميل يسأل: لماذا غبت؟ ويذكّرك بواجب يجب تسليمه يوم الجمعة. مهمتك: ترد عليه بإيميل مهذّب يحقق 3 أهداف.",
    "step1_situation_en": "You are a university student who missed an important class because you were sick. Your professor emailed you asking why, and reminded you about a Friday assignment. Reply politely.",
    "step1_recipient_ar": "👨‍🏫 الأستاذ الجامعي (Professor) — شخص رسمي وأكبر منك مقاماً. تكتب له بنبرة محترمة ومهذّبة جداً.",
    "step1_tone_ar": "🎩 رسمية ومحترمة (Formal & Respectful). تجنّب الاختصارات (don't → do not). استخدم Could you / Would you بدلاً من Can you.",
    "step1_goals_json": json.dumps([
        {"num": 1, "ar": "اعتذر عن الغياب", "en": "Apologize for being absent"},
        {"num": 2, "ar": "اشرح سبب غيابك (المرض)", "en": "Explain the reason (illness)"},
        {"num": 3, "ar": "اسأل عن الدرس والواجب", "en": "Ask about the lesson and assignment"}
    ], ensure_ascii=False),

    "step2_structure_json": json.dumps([
        {"part": "1️⃣ Greeting (التحية)", "purpose_ar": "نبدأ باحترام", "example_en": "Dear Professor [Last Name],", "tip_ar": "استخدم 'Dear' للأكاديميين، وليس 'Hi'"},
        {"part": "2️⃣ Opening (الافتتاحية)", "purpose_ar": "نقول سبب الإيميل في جملة واحدة", "example_en": "I am writing to apologize for missing your class yesterday.", "tip_ar": "ابدأ بـ 'I am writing to...' - افتتاحية احترافية"},
        {"part": "3️⃣ Body (الجسم)", "purpose_ar": "نشرح السبب ونطلب المعلومات", "example_en": "I was sick and had to visit the doctor. Could you please tell me what we studied?", "tip_ar": "اذكر السبب بإيجاز ثم اسأل بأدب"},
        {"part": "4️⃣ Closing (الختام)", "purpose_ar": "نشكر ونعتذر", "example_en": "Thank you for your understanding.", "tip_ar": "اختم دائماً بـ Thank you"},
        {"part": "5️⃣ Sign-off (التوقيع)", "purpose_ar": "ننهي بشكل رسمي", "example_en": "Best regards,\\nAhmad", "tip_ar": "'Best regards' أكثر شيوعاً واحتراماً"}
    ], ensure_ascii=False),

    "step3_phrases_json": json.dumps({
        "greetings": [
            {"en": "Dear Professor Smith,", "ar": "عزيزي البروفيسور سميث،"},
            {"en": "Dear Dr. Johnson,", "ar": "عزيزي الدكتور جونسون،"}
        ],
        "openings": [
            {"en": "I am writing to apologize for missing your class.", "ar": "أكتب لأعتذر عن غيابي."},
            {"en": "I am sorry I could not attend the lecture yesterday.", "ar": "آسف لأنني لم أستطع الحضور أمس."}
        ],
        "explanations": [
            {"en": "I was sick and had to stay home.", "ar": "كنت مريضاً واضطررت للبقاء في البيت."},
            {"en": "I had a high fever yesterday.", "ar": "كانت لدي حرارة عالية أمس."},
            {"en": "The doctor told me to rest.", "ar": "نصحني الطبيب بالراحة."}
        ],
        "requests": [
            {"en": "Could you please tell me what we studied?", "ar": "هل يمكنك إخباري بما درسنا؟"},
            {"en": "Can you give me the homework details?", "ar": "هل تعطيني تفاصيل الواجب؟"}
        ],
        "closings": [
            {"en": "Thank you for your understanding.", "ar": "شكراً لتفهّمك."},
            {"en": "I appreciate your help.", "ar": "أقدّر مساعدتك."}
        ],
        "signoffs": [
            {"en": "Best regards,", "ar": "أطيب التحيات،"},
            {"en": "Sincerely,", "ar": "بإخلاص،"}
        ]
    }, ensure_ascii=False),

    "step4_model_email": """Dear Professor Smith,

I am writing to apologize for missing your class yesterday. I was very sick with a high fever, so I had to stay home and rest. The doctor told me not to go out for one day.

I am sorry I missed the lesson. Could you please tell me what we studied? I also want to know about the homework. When is it due, and what should I do?

Thank you for your understanding. I will work hard to catch up.

Best regards,
Ahmad""",

    "step4_annotations_json": json.dumps([
        {"line": "Dear Professor Smith,", "comment_ar": "✅ تحية رسمية بكلمة Dear + اللقب الأكاديمي. ممنوع 'Hi' للأستاذ."},
        {"line": "I am writing to apologize for missing your class yesterday.", "comment_ar": "✅ افتتاحية ذهبية: 'I am writing to...' تخبر الأستاذ مباشرة بالهدف."},
        {"line": "I was very sick with a high fever, so I had to stay home and rest.", "comment_ar": "✅ سبب واضح ومختصر. لاحظ 'had to' = اضطررت (أقوى من 'wanted to')."},
        {"line": "Could you please tell me what we studied?", "comment_ar": "✅ سؤال بأدب: 'Could you please' أهم 3 كلمات في الإيميل الرسمي."},
        {"line": "When is it due, and what should I do?", "comment_ar": "✅ سؤالان واضحان عن الواجب."},
        {"line": "Thank you for your understanding.", "comment_ar": "✅ ختام مهذّب. هذه الجملة سحرية في كل إيميل."},
        {"line": "Best regards,\\nAhmad", "comment_ar": "✅ توقيع رسمي + الاسم الأول فقط."}
    ], ensure_ascii=False),

    "step5_fill_template": """Dear Professor _______________,

I am writing to apologize for _______________. I was _______________, so I had to _______________.

I am sorry I missed the lesson. Could you please _______________? I also want to know about _______________. When _______________?

Thank you for _______________.

Best regards,
_______________""",

    "step5_blanks_hints_json": json.dumps([
        {"blank": 1, "hint_ar": "لقب الأستاذ (Smith, Johnson, ...)", "example": "Smith"},
        {"blank": 2, "hint_ar": "ما الذي تعتذر عنه؟", "example": "missing your class yesterday"},
        {"blank": 3, "hint_ar": "حالتك الصحية", "example": "very sick with a high fever"},
        {"blank": 4, "hint_ar": "ما الذي اضطررت لفعله؟", "example": "stay home and rest"},
        {"blank": 5, "hint_ar": "اطلب شرح الدرس بأدب", "example": "tell me what we studied"},
        {"blank": 6, "hint_ar": "ماذا تريد أن تعرف؟", "example": "the homework"},
        {"blank": 7, "hint_ar": "متى موعد التسليم؟", "example": "is the homework due"},
        {"blank": 8, "hint_ar": "علام تشكره؟", "example": "your understanding"},
        {"blank": 9, "hint_ar": "اسمك", "example": "Ahmad"}
    ], ensure_ascii=False),

    "step6_checklist_json": json.dumps([
        "بدأت بـ Dear Professor (وليس Hi)",
        "ذكرت سبب الإيميل في الجملة الأولى",
        "اعتذرت عن الغياب",
        "شرحت سبب الغياب",
        "سألت عن الدرس والواجب",
        "استخدمت Could you please (وليس Can you)",
        "شكرت في النهاية",
        "ختمت بـ Best regards + اسمي",
        "عدد الكلمات ≥ 100"
    ], ensure_ascii=False),

    "common_mistakes_json": json.dumps([
        {"wrong": "Hi teacher,", "right": "Dear Professor Smith,", "why_ar": "Hi غير رسمي و'teacher' لا تُستخدم للأستاذ الجامعي."},
        {"wrong": "I want know homework", "right": "Could you please tell me about the homework?", "why_ar": "ينقصها 'to' بعد want، والصياغة غير مهذبة."},
        {"wrong": "Thanks. Bye.", "right": "Thank you for your understanding. Best regards,", "why_ar": "Thanks وBye غير رسميين."},
        {"wrong": "I dont came because im sick", "right": "I could not attend because I was sick.", "why_ar": "اختصار dont خاطئ، والفعل في الزمن الخطأ."}
    ], ensure_ascii=False)
})

# ====== SCENARIO 2: مشروع جماعي (tier69) ======
content.append({
    "scenario_id": 2,
    "target_tier": "tier69",
    "step1_situation_ar": "أنت ضمن مجموعة من 4 طلاب تعملون على مشروع جامعي. أحد أعضاء المجموعة اختفى لمدة أسبوعين (لم يرد على رسائل، ولم يحضر اجتماعات). الموعد النهائي بعد أسبوع. قائد المجموعة (زميلك) أرسل لك إيميل يسأل رأيك. مهمتك: ترد بإيميل ودي لكنه احترافي يحقق 3 أهداف.",
    "step1_situation_en": "You are part of a 4-student group project. One member has been missing for 2 weeks. The deadline is next week. The group leader asks for your opinion.",
    "step1_recipient_ar": "👥 زميل في الدراسة (قائد مجموعة). شخص في نفس مستواك لكن في موقع مسؤولية، لذا النبرة ودّية لكن جدّية.",
    "step1_tone_ar": "🤝 ودّية احترافية (Friendly Professional). أقل رسمية من الأستاذ، لكن واضحة ومنظّمة.",
    "step1_goals_json": json.dumps([
        {"num": 1, "ar": "شارك رأيك في الموقف", "en": "Share your opinion about the situation"},
        {"num": 2, "ar": "اقترح خطوة عملية واحدة على الأقل", "en": "Suggest at least one specific action"},
        {"num": 3, "ar": "اعرض المساعدة بعمل إضافي", "en": "Offer to help with extra work"}
    ], ensure_ascii=False),

    "step2_structure_json": json.dumps([
        {"part": "1️⃣ Greeting", "purpose_ar": "تحية ودية لزميل", "example_en": "Hi Sarah, / Dear Sarah,", "tip_ar": "للزملاء يمكن استخدام Hi، لكن Dear أكثر احترافية."},
        {"part": "2️⃣ Opening", "purpose_ar": "اشكره على الإيميل وأظهر اهتمامك", "example_en": "Thank you for reaching out about the group situation.", "tip_ar": "ابدأ بشكر يخفّف الجو ويُظهر التعاون."},
        {"part": "3️⃣ Body 1 - Opinion", "purpose_ar": "اطرح رأيك بوضوح", "example_en": "I think we should contact him one more time...", "tip_ar": "استخدم 'I think' أو 'In my opinion' لإبداء الرأي."},
        {"part": "4️⃣ Body 2 - Suggestion", "purpose_ar": "اقترح حلاً عملياً", "example_en": "I suggest that we redistribute his tasks among the remaining members.", "tip_ar": "'I suggest that we...' صياغة قوية للاقتراحات."},
        {"part": "5️⃣ Body 3 - Offer help", "purpose_ar": "اعرض مساعدتك", "example_en": "I am willing to take on additional work to make sure we meet the deadline.", "tip_ar": "'I am willing to' = مستعد لـ، نبرة كريمة."},
        {"part": "6️⃣ Closing + Sign-off", "purpose_ar": "اختم بإيجابية", "example_en": "Let me know what you think. Best,\\nAhmad", "tip_ar": "'Let me know' دعوة للحوار."}
    ], ensure_ascii=False),

    "step3_phrases_json": json.dumps({
        "greetings": [
            {"en": "Hi Sarah,", "ar": "مرحباً سارة،"},
            {"en": "Dear Sarah,", "ar": "عزيزتي سارة،"}
        ],
        "openings": [
            {"en": "Thank you for reaching out about the group situation.", "ar": "شكراً لتواصلك بشأن وضع المجموعة."},
            {"en": "I appreciate you asking for my opinion.", "ar": "أقدّر سؤالك عن رأيي."}
        ],
        "opinions": [
            {"en": "In my opinion, we need to act quickly.", "ar": "في رأيي، يجب أن نتصرف بسرعة."},
            {"en": "I think the best approach is to...", "ar": "أعتقد أن أفضل طريقة هي..."},
            {"en": "I believe we should...", "ar": "أؤمن أنه يجب علينا..."}
        ],
        "suggestions": [
            {"en": "I suggest that we redistribute his tasks.", "ar": "أقترح إعادة توزيع مهامه."},
            {"en": "Perhaps we could send him a final message.", "ar": "ربما نرسل له رسالة أخيرة."},
            {"en": "We should inform the professor as soon as possible.", "ar": "يجب إبلاغ الأستاذ بأسرع وقت."}
        ],
        "offers": [
            {"en": "I am willing to take on additional work.", "ar": "أنا مستعد لأخذ عمل إضافي."},
            {"en": "I would be happy to help with the extra tasks.", "ar": "يسعدني المساعدة بالمهام الإضافية."}
        ],
        "closings": [
            {"en": "Let me know what you think.", "ar": "أخبرني برأيك."},
            {"en": "Looking forward to your reply.", "ar": "أتطلع لردك."}
        ],
        "signoffs": [
            {"en": "Best,", "ar": "تحياتي،"},
            {"en": "Best regards,", "ar": "أطيب التحيات،"}
        ]
    }, ensure_ascii=False),

    "step4_model_email": """Hi Sarah,

Thank you for reaching out about the group situation. I have been thinking about this issue as well, and I am glad we can discuss it together before the deadline.

In my opinion, we should give him one final chance by sending a clear message explaining the urgency of the deadline. If he does not respond within 24 hours, I suggest that we redistribute his tasks among the remaining three members and inform Professor Anderson about what happened.

I am willing to take on additional work to make sure we submit a high-quality project on time. Specifically, I can handle the data analysis section that he was responsible for.

Please let me know what you think, and I am ready to start as soon as we agree on a plan.

Best,
Ahmad""",

    "step4_annotations_json": json.dumps([
        {"line": "Hi Sarah,", "comment_ar": "✅ تحية ودية مناسبة للزميل."},
        {"line": "Thank you for reaching out about the group situation.", "comment_ar": "✅ افتتاحية تُظهر الاحترام والتعاون."},
        {"line": "In my opinion, we should give him one final chance...", "comment_ar": "✅ رأي واضح مع تبرير منطقي (الهدف الأول)."},
        {"line": "I suggest that we redistribute his tasks...", "comment_ar": "✅ اقتراح عملي محدد بصياغة قوية (الهدف الثاني)."},
        {"line": "I am willing to take on additional work...", "comment_ar": "✅ عرض ملموس وليس مجرد كلام عام (الهدف الثالث)."},
        {"line": "Specifically, I can handle the data analysis section...", "comment_ar": "🌟 لمسة احترافية: ذكر مهمة محددة يُظهر الجدية."},
        {"line": "Best,\\nAhmad", "comment_ar": "✅ توقيع ودي مناسب للزميل."}
    ], ensure_ascii=False),

    "step5_fill_template": """Hi _______________,

Thank you for reaching out about _______________. I have been thinking about this issue as well.

In my opinion, _______________. If that does not work, I suggest that we _______________.

I am willing to _______________. Specifically, I can _______________.

Please let me know what you think.

Best,
_______________""",

    "step5_blanks_hints_json": json.dumps([
        {"blank": 1, "hint_ar": "اسم قائد المجموعة", "example": "Sarah"},
        {"blank": 2, "hint_ar": "موضوع الإيميل", "example": "the group situation"},
        {"blank": 3, "hint_ar": "رأيك في الموقف (1-2 جملة)", "example": "we should give him one final chance"},
        {"blank": 4, "hint_ar": "خطتك البديلة", "example": "redistribute his tasks and inform the professor"},
        {"blank": 5, "hint_ar": "ما المساعدة التي تعرضها؟", "example": "take on additional work"},
        {"blank": 6, "hint_ar": "مهمة محددة يمكنك القيام بها", "example": "handle the data analysis part"},
        {"blank": 7, "hint_ar": "اسمك", "example": "Ahmad"}
    ], ensure_ascii=False),

    "step6_checklist_json": json.dumps([
        "بدأت بتحية مناسبة للزميل (Hi/Dear)",
        "شكرته على التواصل",
        "أبديت رأيي بوضوح بـ 'In my opinion' أو 'I think'",
        "اقترحت خطوة عملية محددة",
        "عرضت مساعدة ملموسة (مهمة محددة)",
        "استخدمت أكثر من 120 كلمة",
        "تجنّبت الاختصارات (don't → do not)",
        "ختمت بـ Best + اسمي"
    ], ensure_ascii=False),

    "common_mistakes_json": json.dumps([
        {"wrong": "I dont know what to do", "right": "I think the best approach is to...", "why_ar": "لا تُظهر ضعفاً، اطرح رأياً واضحاً."},
        {"wrong": "Maybe we do something", "right": "I suggest that we redistribute his tasks.", "why_ar": "Maybe ضعيف. استخدم 'I suggest that we' صياغة قوية."},
        {"wrong": "I can help if you want", "right": "I am willing to take on the data analysis section.", "why_ar": "كن محدداً في عرض المساعدة."}
    ], ensure_ascii=False)
})

# ====== SCENARIO 3: استفسار عن منحة (tier69) ======
content.append({
    "scenario_id": 3,
    "target_tier": "tier69",
    "step1_situation_ar": "رأيت إعلاناً عن منحة جديدة في جامعتك مخصصة للطلاب الدوليين. أنت مهتم بالتقديم لكن تحتاج معلومات أكثر. مهمتك: ترسل إيميلاً رسمياً لمكتب المنح الدراسية يحقق 3 أهداف.",
    "step1_situation_en": "You saw a scholarship announcement and need more info. Write to the Financial Aid Office.",
    "step1_recipient_ar": "🏛️ مكتب رسمي في الجامعة (Financial Aid Office). موظفون لا تعرفهم شخصياً، لذا النبرة رسمية جداً.",
    "step1_tone_ar": "📋 رسمية جداً (Highly Formal). كأنك تكتب لمؤسسة. ابدأ بـ Dear Sir/Madam أو To Whom It May Concern.",
    "step1_goals_json": json.dumps([
        {"num": 1, "ar": "عرّف عن نفسك بإيجاز (السنة، التخصص)", "en": "Introduce yourself briefly"},
        {"num": 2, "ar": "اسأل عن شروط الأهلية", "en": "Ask about eligibility requirements"},
        {"num": 3, "ar": "اسأل عن الموعد النهائي والمستندات المطلوبة", "en": "Ask about deadline and required documents"}
    ], ensure_ascii=False),

    "step2_structure_json": json.dumps([
        {"part": "1️⃣ Greeting", "purpose_ar": "تحية مؤسسية رسمية", "example_en": "Dear Sir or Madam,", "tip_ar": "للمكاتب الرسمية بدون اسم شخصي."},
        {"part": "2️⃣ Opening + Introduction", "purpose_ar": "عرّف عن نفسك وموضوع الإيميل", "example_en": "My name is Ahmad. I am a second-year student majoring in Engineering, and I am writing to inquire about...", "tip_ar": "اربط تعريفك بالهدف مباشرة."},
        {"part": "3️⃣ Body 1 - Question 1", "purpose_ar": "اسأل عن الأهلية", "example_en": "Could you please clarify the eligibility requirements for international students?", "tip_ar": "'Could you please clarify' صياغة مهنية."},
        {"part": "4️⃣ Body 2 - Question 2", "purpose_ar": "اسأل عن الموعد والمستندات", "example_en": "I would also like to know the application deadline and which documents I should submit.", "tip_ar": "اجمع سؤالين مرتبطين في جملة واحدة."},
        {"part": "5️⃣ Closing", "purpose_ar": "شكر مهني وتوقّع رد", "example_en": "I would greatly appreciate your guidance. I look forward to your response.", "tip_ar": "نبرة 'looking forward' احترافية."},
        {"part": "6️⃣ Sign-off", "purpose_ar": "توقيع رسمي", "example_en": "Sincerely,\\nAhmad [Last Name]", "tip_ar": "'Sincerely' أكثر رسمية من 'Best regards' للمكاتب."}
    ], ensure_ascii=False),

    "step3_phrases_json": json.dumps({
        "greetings": [
            {"en": "Dear Sir or Madam,", "ar": "سيدي/سيدتي الكريم،"},
            {"en": "To Whom It May Concern,", "ar": "إلى من يهمه الأمر،"}
        ],
        "intros": [
            {"en": "My name is Ahmad and I am a second-year Engineering student.", "ar": "اسمي أحمد، طالب سنة ثانية هندسة."},
            {"en": "I am writing to inquire about the new scholarship for international students.", "ar": "أكتب للاستفسار عن المنحة الجديدة."}
        ],
        "questions": [
            {"en": "Could you please clarify the eligibility requirements?", "ar": "هل يمكنكم توضيح شروط الأهلية؟"},
            {"en": "I would like to know the application deadline.", "ar": "أود معرفة الموعد النهائي للتقديم."},
            {"en": "What documents are required for the application?", "ar": "ما المستندات المطلوبة؟"},
            {"en": "Is there a minimum GPA requirement?", "ar": "هل هناك حد أدنى للمعدل؟"}
        ],
        "closings": [
            {"en": "I would greatly appreciate your guidance.", "ar": "سأقدّر إرشادكم كثيراً."},
            {"en": "I look forward to your response.", "ar": "أتطلع لردكم."},
            {"en": "Thank you for your time and assistance.", "ar": "شكراً لوقتكم ومساعدتكم."}
        ],
        "signoffs": [
            {"en": "Sincerely,", "ar": "بإخلاص،"},
            {"en": "Yours faithfully,", "ar": "بكل وفاء،"}
        ]
    }, ensure_ascii=False),

    "step4_model_email": """Dear Sir or Madam,

My name is Ahmad Al-Yamani, and I am a second-year student majoring in Computer Engineering at your university. I recently saw the announcement about the new scholarship program for international students, and I am very interested in applying. However, I have a few questions before I submit my application.

First, could you please clarify the eligibility requirements? Specifically, I would like to know if there is a minimum GPA, and whether students from all faculties can apply.

Second, I would greatly appreciate it if you could tell me the application deadline and provide a complete list of the documents I need to prepare, such as transcripts, recommendation letters, or a personal statement.

Thank you very much for your time and assistance. I look forward to hearing from you soon.

Sincerely,
Ahmad Al-Yamani""",

    "step4_annotations_json": json.dumps([
        {"line": "Dear Sir or Madam,", "comment_ar": "✅ تحية رسمية مثالية للمكاتب الإدارية."},
        {"line": "My name is Ahmad Al-Yamani, and I am a second-year student...", "comment_ar": "✅ تعريف شخصي مهني (الهدف الأول): اسم + سنة + تخصص."},
        {"line": "I recently saw the announcement... I am very interested in applying.", "comment_ar": "✅ سبب الإيميل واضح من البداية."},
        {"line": "could you please clarify the eligibility requirements?", "comment_ar": "✅ سؤال الأهلية بصياغة رسمية (الهدف الثاني)."},
        {"line": "Specifically, I would like to know if there is a minimum GPA...", "comment_ar": "🌟 لمسة احترافية: تفصيل السؤال يُظهر اهتمامك."},
        {"line": "I would greatly appreciate it if you could tell me the application deadline...", "comment_ar": "✅ السؤال الثاني عن الموعد والمستندات (الهدف الثالث)."},
        {"line": "Sincerely,\\nAhmad Al-Yamani", "comment_ar": "✅ توقيع رسمي بالاسم الكامل."}
    ], ensure_ascii=False),

    "step5_fill_template": """Dear Sir or Madam,

My name is _______________, and I am a _______________ student majoring in _______________. I recently saw the announcement about _______________, and I am very interested in applying.

First, could you please clarify _______________?

Second, I would appreciate it if you could tell me _______________ and provide a list of _______________.

Thank you for your time. I look forward to _______________.

Sincerely,
_______________""",

    "step5_blanks_hints_json": json.dumps([
        {"blank": 1, "hint_ar": "اسمك الكامل", "example": "Ahmad Al-Yamani"},
        {"blank": 2, "hint_ar": "سنتك الدراسية", "example": "second-year"},
        {"blank": 3, "hint_ar": "تخصصك", "example": "Computer Engineering"},
        {"blank": 4, "hint_ar": "اسم المنحة", "example": "the new international student scholarship"},
        {"blank": 5, "hint_ar": "السؤال عن الأهلية", "example": "the eligibility requirements"},
        {"blank": 6, "hint_ar": "ما تريد معرفته (موعد)", "example": "the application deadline"},
        {"blank": 7, "hint_ar": "ما تريد قائمة به", "example": "the required documents"},
        {"blank": 8, "hint_ar": "ماذا تنتظر؟", "example": "hearing from you soon"},
        {"blank": 9, "hint_ar": "توقيعك الكامل", "example": "Ahmad Al-Yamani"}
    ], ensure_ascii=False),

    "step6_checklist_json": json.dumps([
        "بدأت بـ Dear Sir or Madam (للمكتب الرسمي)",
        "عرّفت عن نفسي (اسم + سنة + تخصص)",
        "ذكرت سبب الإيميل (المنحة)",
        "سألت بوضوح عن شروط الأهلية",
        "سألت عن الموعد النهائي والمستندات",
        "استخدمت 'Could you please clarify' و 'I would appreciate'",
        "تجنّبت الاختصارات والكلمات العامية",
        "عدد الكلمات ≥ 120",
        "ختمت بـ Sincerely + اسمي الكامل"
    ], ensure_ascii=False),

    "common_mistakes_json": json.dumps([
        {"wrong": "Hi, I want scholarship info", "right": "Dear Sir or Madam, I am writing to inquire about the scholarship.", "why_ar": "مكتب رسمي = تحية رسمية ومقدمة كاملة."},
        {"wrong": "Send me the documents list", "right": "Could you please send me the list of required documents?", "why_ar": "الأمر المباشر فظ. استخدم سؤالاً مهذباً."},
        {"wrong": "Reply fast please", "right": "I look forward to your response.", "why_ar": "'Reply fast' غير لائق. 'Look forward to' أكثر احترافية."}
    ], ensure_ascii=False)
})

# ====== SCENARIO 4: طلب رسالة توصية (tier90) ======
content.append({
    "scenario_id": 4,
    "target_tier": "tier90",
    "step1_situation_ar": "تتقدّم لبرنامج ماجستير وتحتاج رسالة توصية من بروفيسورة سابقة درّستك مادتين بتقديرات ممتازة. الموعد النهائي بعد 3 أسابيع. مهمتك: تكتب لها إيميلاً راقياً ومتقناً يُظهر مستوى Tier 90 (90+ نقطة). 3 أهداف يجب تحقيقها.",
    "step1_situation_en": "Request a recommendation letter from a former professor for graduate school. Deadline in 3 weeks.",
    "step1_recipient_ar": "👩‍🏫 بروفيسورة سابقة درّستك. تعرفك لكن مرّ وقت، لذا تذكّرها بنفسك. النبرة: رسمية + شخصية معاً (يُظهر علاقة سابقة جيدة).",
    "step1_tone_ar": "🎓 رفيعة المستوى (Polished Formal). جمل أكاديمية معقدة، مفردات قوية (sincerely grateful, esteemed, invaluable). تجنّب البساطة.",
    "step1_goals_json": json.dumps([
        {"num": 1, "ar": "ذكّرها بمن أنت وأي مواد درّستك", "en": "Remind her who you are and which courses"},
        {"num": 2, "ar": "اطلب الرسالة بأدب راقٍ مع شرح الغرض", "en": "Request the letter politely with purpose"},
        {"num": 3, "ar": "اذكر الموعد وعرض إرسال المستندات المساعدة", "en": "Provide deadline and offer supporting docs"}
    ], ensure_ascii=False),

    "step2_structure_json": json.dumps([
        {"part": "1️⃣ Greeting", "purpose_ar": "تحية أكاديمية رفيعة", "example_en": "Dear Professor Anderson,", "tip_ar": "استخدم اسمها الأكاديمي الكامل."},
        {"part": "2️⃣ Reconnect + Remind", "purpose_ar": "ذكّرها بك بشكل لبق", "example_en": "I hope this email finds you well. You may remember me as a student in your Advanced Linguistics and Discourse Analysis courses last year.", "tip_ar": "'I hope this email finds you well' = افتتاحية أكاديمية كلاسيكية."},
        {"part": "3️⃣ State Purpose", "purpose_ar": "اطلب الرسالة بصياغة راقية", "example_en": "I am writing to respectfully request your support in the form of a letter of recommendation for my application to...", "tip_ar": "'respectfully request' = أعلى مستويات الأدب."},
        {"part": "4️⃣ Justify Choice", "purpose_ar": "اشرح لماذا اخترتها هي تحديداً", "example_en": "Given the depth of feedback you provided on my research papers, I believe your recommendation would carry significant weight.", "tip_ar": "هذه فقرة Tier 90 - تربط المدح بسبب موضوعي."},
        {"part": "5️⃣ Practical Details", "purpose_ar": "الموعد والمستندات", "example_en": "The deadline is March 15th. I would be happy to provide my updated CV, statement of purpose, or any other materials you may find helpful.", "tip_ar": "عرض مساعدتها = احتراف."},
        {"part": "6️⃣ Closing + Sign-off", "purpose_ar": "ختام شاكر متواضع", "example_en": "I am sincerely grateful for your continued mentorship. Yours sincerely,\\nAhmad Al-Yamani", "tip_ar": "'sincerely grateful' + 'Yours sincerely' = مستوى أكاديمي عالٍ."}
    ], ensure_ascii=False),

    "step3_phrases_json": json.dumps({
        "greetings": [
            {"en": "Dear Professor Anderson,", "ar": "عزيزتي البروفيسورة أندرسون،"}
        ],
        "openings": [
            {"en": "I hope this email finds you well.", "ar": "أرجو أن يصلك هذا الإيميل وأنت بأفضل حال."},
            {"en": "I trust you are doing well since we last met.", "ar": "آمل أنك بخير منذ آخر لقاء."}
        ],
        "reminders": [
            {"en": "You may remember me as a student in your Advanced Linguistics course.", "ar": "ربما تذكرينني كطالب في مادة اللسانيات المتقدمة."},
            {"en": "I had the privilege of being your student in two courses last year.", "ar": "حظيت بشرف كوني طالبك في مادتين السنة الماضية."}
        ],
        "requests": [
            {"en": "I am writing to respectfully request a letter of recommendation.", "ar": "أكتب لأطلب باحترام رسالة توصية."},
            {"en": "I would be sincerely grateful if you could provide a recommendation letter.", "ar": "سأكون ممتناً بصدق لو قدمتِ لي رسالة توصية."}
        ],
        "justifications": [
            {"en": "Your insights have profoundly shaped my academic interests.", "ar": "رؤاكِ شكّلت اهتماماتي الأكاديمية بعمق."},
            {"en": "Given your expertise in the field, your recommendation would be invaluable.", "ar": "نظراً لخبرتك، ستكون توصيتكِ ذات قيمة بالغة."}
        ],
        "offers": [
            {"en": "I would be happy to provide my CV and statement of purpose.", "ar": "يسرني تزويدك بسيرتي الذاتية وبيان الأهداف."},
            {"en": "Please let me know if you need any additional materials.", "ar": "أخبريني إن احتجتِ أي مواد إضافية."}
        ],
        "closings": [
            {"en": "I am sincerely grateful for your continued support.", "ar": "أنا ممتن بصدق لدعمكِ المستمر."},
            {"en": "Thank you for considering my request.", "ar": "شكراً لتقبّلك طلبي."}
        ],
        "signoffs": [
            {"en": "Yours sincerely,", "ar": "بإخلاص،"},
            {"en": "With sincere appreciation,", "ar": "مع خالص التقدير،"}
        ]
    }, ensure_ascii=False),

    "step4_model_email": """Dear Professor Anderson,

I hope this email finds you well. You may remember me as a student in your Advanced Linguistics and Discourse Analysis courses during the 2024-2025 academic year, in which I had the privilege of earning high distinctions under your guidance.

I am writing to respectfully request your support in the form of a letter of recommendation for my application to the Master's program in Applied Linguistics at the University of Cambridge. Given the depth and thoughtfulness of the feedback you provided on my research papers, particularly my final thesis on sociolinguistic variation, I believe your recommendation would carry significant weight with the admissions committee.

The application deadline is March 15th, which gives us approximately three weeks. To make the process as convenient as possible, I would be happy to provide my updated CV, statement of purpose, transcripts, and a brief summary of the key projects I completed in your courses. Please do not hesitate to let me know if there is any additional information that would be helpful.

I am sincerely grateful for your continued mentorship, which has profoundly shaped my academic trajectory. Thank you in advance for considering my request.

Yours sincerely,
Ahmad Al-Yamani""",

    "step4_annotations_json": json.dumps([
        {"line": "I hope this email finds you well.", "comment_ar": "🌟 افتتاحية أكاديمية كلاسيكية - تُظهر الاحترام دون مبالغة."},
        {"line": "You may remember me as a student in your Advanced Linguistics...", "comment_ar": "🌟 تذكير لبق + إضافة سنة دراسية ومادتين محددتين (الهدف الأول)."},
        {"line": "in which I had the privilege of earning high distinctions under your guidance.", "comment_ar": "🌟 إنجاز محدد + اعتراف بفضلها = توازن مثالي بين الثقة والتواضع."},
        {"line": "I am writing to respectfully request your support in the form of a letter of recommendation...", "comment_ar": "🌟 صياغة Tier 90: 'respectfully request' + 'in the form of' بدلاً من 'for a letter'."},
        {"line": "Given the depth and thoughtfulness of the feedback you provided...", "comment_ar": "🌟 تبرير اختيارها = يُظهر أن الطلب مدروس، ليس عشوائياً."},
        {"line": "particularly my final thesis on sociolinguistic variation", "comment_ar": "🌟 ذكر مشروع محدد يساعدها على تذكّرك."},
        {"line": "I would be happy to provide my updated CV, statement of purpose, transcripts, and a brief summary...", "comment_ar": "🌟 عرض شامل ومنظم = احترام لوقتها."},
        {"line": "I am sincerely grateful for your continued mentorship, which has profoundly shaped my academic trajectory.", "comment_ar": "🌟 ختام Tier 90: 'profoundly shaped my academic trajectory' = مفردات راقية."},
        {"line": "Yours sincerely,", "comment_ar": "🌟 توقيع أكاديمي رسمي."}
    ], ensure_ascii=False),

    "step5_fill_template": """Dear Professor _______________,

I hope this email finds you well. You may remember me as a student in your _______________ course(s) during _______________, in which I _______________.

I am writing to respectfully request your support in the form of a letter of recommendation for my application to _______________. Given _______________, I believe your recommendation would carry significant weight.

The deadline is _______________. I would be happy to provide _______________. Please let me know if _______________.

I am sincerely grateful for _______________. Thank you for considering my request.

Yours sincerely,
_______________""",

    "step5_blanks_hints_json": json.dumps([
        {"blank": 1, "hint_ar": "لقب البروفيسورة", "example": "Anderson"},
        {"blank": 2, "hint_ar": "اسم/أسماء المواد", "example": "Advanced Linguistics"},
        {"blank": 3, "hint_ar": "الفترة الزمنية", "example": "the 2024-2025 academic year"},
        {"blank": 4, "hint_ar": "إنجازك في الكورس", "example": "earned the highest grade in class"},
        {"blank": 5, "hint_ar": "البرنامج الذي تتقدم له", "example": "the MA program at Cambridge"},
        {"blank": 6, "hint_ar": "تبرير اختيارها", "example": "your expertise in this field"},
        {"blank": 7, "hint_ar": "الموعد النهائي", "example": "March 15th"},
        {"blank": 8, "hint_ar": "المستندات التي ستوفرها", "example": "my CV, statement of purpose, and transcripts"},
        {"blank": 9, "hint_ar": "ما الذي يحتاج توضيحاً", "example": "you need any additional information"},
        {"blank": 10, "hint_ar": "علام تشكرها بعمق", "example": "your continued mentorship"},
        {"blank": 11, "hint_ar": "اسمك الكامل", "example": "Ahmad Al-Yamani"}
    ], ensure_ascii=False),

    "step6_checklist_json": json.dumps([
        "بدأت بـ Dear Professor + اللقب الكامل",
        "افتتحت بـ 'I hope this email finds you well'",
        "ذكّرتها بنفسي (مادة + سنة + إنجاز)",
        "استخدمت 'respectfully request' أو 'sincerely grateful'",
        "بررت اختيارها (لماذا هي تحديداً)",
        "ذكرت مشروعاً أو موضوعاً محدداً",
        "أعطيت الموعد بوضوح",
        "عرضت قائمة شاملة من المستندات (CV + SOP + transcripts)",
        "ختمت بفقرة شكر عميق",
        "استخدمت Yours sincerely + الاسم الكامل",
        "عدد الكلمات ≥ 150",
        "تنوّعت في طول الجمل (قصيرة + متوسطة + طويلة)",
        "تجنّبت تماماً الاختصارات (don't, won't, can't)"
    ], ensure_ascii=False),

    "common_mistakes_json": json.dumps([
        {"wrong": "I need a recommendation letter from you", "right": "I am writing to respectfully request your support in the form of a letter of recommendation.", "why_ar": "'I need' في Tier 90 ضعيفة جداً. Tier 90 يستخدم 'respectfully request' و 'in the form of'."},
        {"wrong": "You taught me last year", "right": "You may remember me as a student in your Advanced Linguistics course during 2024-2025.", "why_ar": "كن محدداً: اسم المادة + السنة الدراسية + ذكر شيء يُميّزك."},
        {"wrong": "Please send it before March 15", "right": "The deadline is March 15th. I would be happy to provide any supporting materials you may need.", "why_ar": "ابتعد عن صيغة الأمر. اذكر الموعد كمعلومة، ثم اعرض المساعدة."},
        {"wrong": "Thanks a lot", "right": "I am sincerely grateful for your continued mentorship.", "why_ar": "Tier 90 يتطلب مفردات أكاديمية: sincerely grateful, continued mentorship, profoundly shaped."}
    ], ensure_ascii=False)
})

# ====== SCENARIO 5: فرصة بحثية (tier90) ======
content.append({
    "scenario_id": 5,
    "target_tier": "tier90",
    "step1_situation_ar": "أعلن قسمك عن فرصة 'مساعد باحث' مع البروفيسور جونسون في علوم البيئة (مجال تحبه). الوظيفة تتطلب مهارات تحليلية وخبرة بحثية. مهمتك: تكتب إيميلاً يُقدّمك كأفضل مرشح ويفتح باب لقاء. مستوى Tier 90 (90+). 3 أهداف.",
    "step1_situation_en": "Apply for a research assistant position with Prof. Johnson in environmental science.",
    "step1_recipient_ar": "👨‍🔬 بروفيسور لم تعمل معه قبلاً (مشرف محتمل). يقرأ كثير من الإيميلات يومياً، لذا يجب أن يكون إيميلك متميزاً ومركّزاً.",
    "step1_tone_ar": "🎯 احترافي + استراتيجي. كل جملة لها هدف. اربط شغفك بأبحاثه، خبرتك بمتطلبات الوظيفة، طلبك بقيمة محددة.",
    "step1_goals_json": json.dumps([
        {"num": 1, "ar": "أظهر اهتماماً عميقاً بمجاله البحثي تحديداً", "en": "Show deep interest in his specific research"},
        {"num": 2, "ar": "اعرض خلفيتك بأمثلة محددة", "en": "Present background with specific examples"},
        {"num": 3, "ar": "اقترح موعد لقاء لمناقشة الفرصة", "en": "Propose a meeting to discuss further"}
    ], ensure_ascii=False),

    "step2_structure_json": json.dumps([
        {"part": "1️⃣ Greeting", "purpose_ar": "تحية رسمية + اللقب الأكاديمي", "example_en": "Dear Professor Johnson,", "tip_ar": "اللقب يُظهر احتراماً للمكانة الأكاديمية."},
        {"part": "2️⃣ Hook (الجذب)", "purpose_ar": "افتتاحية تلفت انتباهه فوراً", "example_en": "I was excited to see the announcement about the research assistant position in your environmental sustainability lab, as your recent work on coastal ecosystem resilience aligns directly with my own academic interests.", "tip_ar": "اذكر ورقة محددة أو موضوع له = يُظهر أنك قرأت أبحاثه."},
        {"part": "3️⃣ Background", "purpose_ar": "عرض الخبرة بأمثلة محددة", "example_en": "Over the past two years, I have developed strong analytical skills through coursework in statistical methods and hands-on experience analyzing biodiversity datasets...", "tip_ar": "كن محدداً: ما المهارات + من أين اكتسبتها."},
        {"part": "4️⃣ Value Proposition", "purpose_ar": "ماذا ستضيف لمختبره", "example_en": "I believe my background in data visualization and field sampling techniques would allow me to contribute meaningfully from the outset.", "tip_ar": "ركّز على ما تُقدّمه، ليس فقط ما تريده."},
        {"part": "5️⃣ Call to Action", "purpose_ar": "اقترح خطوة محددة", "example_en": "Would it be possible to schedule a brief meeting at your convenience to discuss the position in more detail?", "tip_ar": "'at your convenience' = احترام لوقته."},
        {"part": "6️⃣ Closing + Sign-off", "purpose_ar": "ختام مع توقع رد", "example_en": "I have attached my CV for your review. Thank you for your time and consideration.\\nYours sincerely,\\nAhmad", "tip_ar": "ذكر مرفق + شكر + توقيع رسمي."}
    ], ensure_ascii=False),

    "step3_phrases_json": json.dumps({
        "greetings": [
            {"en": "Dear Professor Johnson,", "ar": "عزيزي البروفيسور جونسون،"}
        ],
        "hooks": [
            {"en": "I was excited to see the announcement about the research assistant position in your lab.", "ar": "سررت برؤية الإعلان عن وظيفة مساعد باحث في مختبرك."},
            {"en": "Your recent work on [topic] aligns directly with my academic interests.", "ar": "عملك الأخير في [الموضوع] يتماشى مع اهتماماتي."},
            {"en": "I have been following your research on [topic] with great interest.", "ar": "أتابع أبحاثك في [الموضوع] باهتمام كبير."}
        ],
        "experience": [
            {"en": "Over the past two years, I have developed strong analytical skills...", "ar": "خلال العامين الماضيين، طوّرت مهارات تحليلية قوية..."},
            {"en": "I have hands-on experience with [skill/tool].", "ar": "لديّ خبرة عملية في [المهارة]."},
            {"en": "My coursework in [subject] has prepared me to contribute to...", "ar": "دراستي في [المادة] أعدّتني للمساهمة في..."}
        ],
        "value": [
            {"en": "I believe my background would allow me to contribute meaningfully from the outset.", "ar": "أعتقد أن خلفيتي ستمكّنني من المساهمة بفعالية من البداية."},
            {"en": "I am eager to apply my skills in [area] to support your ongoing research.", "ar": "أتطلع لتطبيق مهاراتي في [المجال] لدعم أبحاثك."}
        ],
        "requests": [
            {"en": "Would it be possible to schedule a brief meeting at your convenience?", "ar": "هل يمكن ترتيب لقاء قصير حسب وقتك المناسب؟"},
            {"en": "I would welcome the opportunity to discuss how I might contribute.", "ar": "سيشرفني فرصة مناقشة كيف يمكنني المساهمة."}
        ],
        "closings": [
            {"en": "Thank you for your time and consideration.", "ar": "شكراً لوقتك واعتبارك."},
            {"en": "I look forward to the possibility of working with you.", "ar": "أتطلع لإمكانية العمل معك."}
        ],
        "signoffs": [
            {"en": "Yours sincerely,", "ar": "بإخلاص،"},
            {"en": "With sincere appreciation,", "ar": "مع خالص التقدير،"}
        ]
    }, ensure_ascii=False),

    "step4_model_email": """Dear Professor Johnson,

I was excited to see the announcement about the research assistant position in your environmental sustainability lab. Your recent work on coastal ecosystem resilience, particularly the 2025 publication in the Journal of Environmental Science, aligns directly with my own academic interests, and I am writing to formally express my interest in this opportunity.

Over the past two years, I have developed strong analytical skills through coursework in statistical methods, GIS mapping, and ecological modeling. As part of my undergraduate thesis, I independently analyzed a dataset of over 10,000 biodiversity records from Mediterranean coastal regions and presented my findings at the university's annual research symposium. Additionally, I gained hands-on experience with R and Python during a summer internship at the National Marine Institute, where I contributed to a project assessing the impacts of microplastic pollution on intertidal species.

I believe my background in data analysis, combined with my genuine passion for environmental science, would allow me to contribute meaningfully to your ongoing research from the outset. I am particularly interested in expanding my expertise in remote sensing applications, an area in which your lab is widely recognized.

Would it be possible to schedule a brief meeting at your convenience to discuss the position in greater detail? I have attached my CV and a writing sample for your review, and I would be happy to provide any additional information you may require.

Thank you very much for your time and consideration. I look forward to the possibility of working with you.

Yours sincerely,
Ahmad Al-Yamani""",

    "step4_annotations_json": json.dumps([
        {"line": "I was excited to see the announcement about the research assistant position in your environmental sustainability lab.", "comment_ar": "🌟 افتتاحية حماسية لكن مهنية - 'excited' أفضل من 'interested' الباهت."},
        {"line": "Your recent work on coastal ecosystem resilience, particularly the 2025 publication in the Journal of Environmental Science", "comment_ar": "🌟 ذكر نشر محدد = دليل قاطع على أنك قرأت أبحاثه (الهدف الأول)."},
        {"line": "Over the past two years, I have developed strong analytical skills...", "comment_ar": "🌟 تأطير الخبرة بإطار زمني = ينظّم المعلومات."},
        {"line": "I independently analyzed a dataset of over 10,000 biodiversity records...", "comment_ar": "🌟 رقم محدد (10,000) = مصداقية + حجم العمل."},
        {"line": "presented my findings at the university's annual research symposium", "comment_ar": "🌟 إنجاز ملموس + خبرة عرض = جاهز للبيئة الأكاديمية."},
        {"line": "I gained hands-on experience with R and Python during a summer internship", "comment_ar": "🌟 أدوات محددة + خبرة عمل (الهدف الثاني)."},
        {"line": "I believe my background... would allow me to contribute meaningfully to your ongoing research from the outset.", "comment_ar": "🌟 قيمة مضافة - ليس فقط 'أريد أن أتعلم' بل 'أستطيع أن أساهم'."},
        {"line": "I am particularly interested in expanding my expertise in remote sensing applications, an area in which your lab is widely recognized.", "comment_ar": "🌟 إطراء ذكي مبني على معرفة + رغبة في التعلم منه."},
        {"line": "Would it be possible to schedule a brief meeting at your convenience...", "comment_ar": "🌟 طلب لقاء بأدب راقٍ (الهدف الثالث)."},
        {"line": "I have attached my CV and a writing sample for your review", "comment_ar": "🌟 استباق طلباته - يُظهر تنظيماً واحترافية."},
        {"line": "Yours sincerely,\\nAhmad Al-Yamani", "comment_ar": "🌟 توقيع أكاديمي رسمي."}
    ], ensure_ascii=False),

    "step5_fill_template": """Dear Professor _______________,

I was excited to see the announcement about _______________. Your recent work on _______________ aligns directly with my own academic interests.

Over the past _______________, I have developed _______________ through _______________. As part of _______________, I _______________. Additionally, I gained hands-on experience with _______________ during _______________.

I believe my background in _______________ would allow me to contribute meaningfully to _______________. I am particularly interested in _______________.

Would it be possible to _______________ at your convenience to discuss the position in greater detail? I have attached _______________ for your review.

Thank you very much for your time and consideration.

Yours sincerely,
_______________""",

    "step5_blanks_hints_json": json.dumps([
        {"blank": 1, "hint_ar": "لقب البروفيسور", "example": "Johnson"},
        {"blank": 2, "hint_ar": "الوظيفة المعلنة", "example": "the research assistant position in your lab"},
        {"blank": 3, "hint_ar": "موضوع بحثي محدد له", "example": "coastal ecosystem resilience"},
        {"blank": 4, "hint_ar": "الفترة الزمنية لخبرتك", "example": "two years"},
        {"blank": 5, "hint_ar": "المهارات التي طوّرتها", "example": "strong analytical skills"},
        {"blank": 6, "hint_ar": "كيف اكتسبتها؟", "example": "coursework in statistics and GIS"},
        {"blank": 7, "hint_ar": "مشروع رئيسي قمت به", "example": "my undergraduate thesis"},
        {"blank": 8, "hint_ar": "ما أنجزته في المشروع", "example": "analyzed 10,000 biodiversity records and presented findings"},
        {"blank": 9, "hint_ar": "أدوات تقنية تتقنها", "example": "R and Python"},
        {"blank": 10, "hint_ar": "أين اكتسبت الخبرة العملية", "example": "a summer internship at a marine institute"},
        {"blank": 11, "hint_ar": "خلفيتك الرئيسية", "example": "data analysis and environmental science"},
        {"blank": 12, "hint_ar": "ما الذي ستساهم به", "example": "your ongoing research from the outset"},
        {"blank": 13, "hint_ar": "مجال محدد في مختبره", "example": "remote sensing applications"},
        {"blank": 14, "hint_ar": "اقتراحك للقاء", "example": "schedule a brief meeting"},
        {"blank": 15, "hint_ar": "ما المستندات المرفقة", "example": "my CV and a writing sample"},
        {"blank": 16, "hint_ar": "اسمك الكامل", "example": "Ahmad Al-Yamani"}
    ], ensure_ascii=False),

    "step6_checklist_json": json.dumps([
        "بدأت بـ Dear Professor + اللقب",
        "ذكرت ورقة أو موضوعاً محدداً من أبحاثه",
        "أظهرت شغفاً صادقاً ومحدداً (ليس عاماً)",
        "ذكرت إنجازاً قابلاً للقياس (رقم/نسبة/عرض)",
        "ذكرت أدوات/مهارات محددة (R, Python, GIS, ...)",
        "ربطت خبرتك بمتطلبات الوظيفة",
        "اقترحت قيمة محددة ستضيفها",
        "اقترحت لقاء بأدب ('at your convenience')",
        "ذكرت مرفقات (CV, writing sample)",
        "ختمت بـ Yours sincerely + الاسم الكامل",
        "عدد الكلمات ≥ 150 (يفضل 180-220)",
        "تنوّعت الجمل بين قصيرة ومركّبة",
        "استخدمت مفردات أكاديمية (meaningfully, particularly, widely recognized)",
        "لا اختصارات أبداً (do not, would not, etc.)"
    ], ensure_ascii=False),

    "common_mistakes_json": json.dumps([
        {"wrong": "I saw your job and I want to apply", "right": "I was excited to see the announcement about the research assistant position in your environmental sustainability lab.", "why_ar": "Tier 90 يتطلب افتتاحية محددة ومحفّزة. اذكر اسم المختبر/المجال."},
        {"wrong": "I like environmental science", "right": "Your recent work on coastal ecosystem resilience aligns directly with my academic interests.", "why_ar": "'I like' في Tier 90 سطحية. اربط شغفك بعمله المحدد."},
        {"wrong": "I have good skills in data", "right": "I have developed strong analytical skills through coursework in statistical methods, GIS mapping, and ecological modeling.", "why_ar": "كن محدداً: أي مهارات + من أين اكتسبتها."},
        {"wrong": "Hope to work with you", "right": "I look forward to the possibility of working with you, and I would welcome the opportunity to discuss how I might contribute.", "why_ar": "Tier 90: جمل مركّبة تُظهر التفكير العميق."},
        {"wrong": "Reply to me soon", "right": "Thank you very much for your time and consideration.", "why_ar": "أبداً لا تطلب رداً سريعاً. اشكر وانتظر."}
    ], ensure_ascii=False)
})

# إدراج الكل
for c_item in content:
    cur.execute("""
        INSERT INTO email_coach_content
        (scenario_id, target_tier, step1_situation_ar, step1_situation_en,
         step1_recipient_ar, step1_tone_ar, step1_goals_json,
         step2_structure_json, step3_phrases_json,
         step4_model_email, step4_annotations_json,
         step5_fill_template, step5_blanks_hints_json,
         step6_checklist_json, common_mistakes_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        c_item["scenario_id"], c_item["target_tier"],
        c_item["step1_situation_ar"], c_item["step1_situation_en"],
        c_item["step1_recipient_ar"], c_item["step1_tone_ar"],
        c_item["step1_goals_json"],
        c_item["step2_structure_json"], c_item["step3_phrases_json"],
        c_item["step4_model_email"], c_item["step4_annotations_json"],
        c_item["step5_fill_template"], c_item["step5_blanks_hints_json"],
        c_item["step6_checklist_json"], c_item["common_mistakes_json"]
    ))

con.commit()

n = cur.execute("SELECT COUNT(*) FROM email_coach_content").fetchone()[0]
print(f"[OK] {n} coach contents inserted")
for r in cur.execute("SELECT scenario_id, target_tier FROM email_coach_content ORDER BY scenario_id").fetchall():
    print(f"   Scenario #{r[0]} - {r[1]}")
con.close()
'@ | Out-File -FilePath "_p35_seed.py" -Encoding utf8
py _p35_seed.py
Remove-Item _p35_seed.py
Write-Host ""

# ============================================================
# 2) إضافة Route للـ Coach في writing_toefl.py
# ============================================================
@'
# -*- coding: utf-8 -*-
import io

p = "routes/writing_toefl.py"
with io.open(p, "r", encoding="utf-8") as f:
    code = f.read()

if "view_email_coach" in code:
    print("[SKIP] Coach routes already exist")
else:
    new_route = '''

# ============================================================
# Phase 3.5: Email Coach (6-step learning)
# ============================================================
@writing_bp.route("/writing/email/<int:scenario_id>/coach", methods=["GET"])
@writing_bp.route("/writing/email/<int:scenario_id>/coach/<int:step>", methods=["GET"])
def view_email_coach(scenario_id, step=1):
    """صفحة التعلم خطوة بخطوة قبل كتابة الإيميل."""
    import json as _json
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()
    # السيناريو الأساسي
    s_row = c.execute("""
        SELECT id, code, title_ar, title_en, scenario_text, recipient_role,
               requirements_json, min_words, target_tier
        FROM writing_email_scenarios WHERE id=?
    """, (scenario_id,)).fetchone()
    if not s_row:
        return "Scenario not found", 404
    scenario = {
        "id": s_row[0], "code": s_row[1], "title_ar": s_row[2], "title_en": s_row[3],
        "scenario_text": s_row[4], "recipient_role": s_row[5],
        "requirements": _json.loads(s_row[6]) if s_row[6] else [],
        "min_words": s_row[7], "target_tier": s_row[8]
    }
    # المحتوى التعليمي
    cc_row = c.execute("""
        SELECT step1_situation_ar, step1_situation_en, step1_recipient_ar,
               step1_tone_ar, step1_goals_json,
               step2_structure_json, step3_phrases_json,
               step4_model_email, step4_annotations_json,
               step5_fill_template, step5_blanks_hints_json,
               step6_checklist_json, common_mistakes_json
        FROM email_coach_content WHERE scenario_id=?
    """, (scenario_id,)).fetchone()
    if not cc_row:
        return f"No coach content for scenario {scenario_id}", 404
    coach = {
        "step1_situation_ar": cc_row[0], "step1_situation_en": cc_row[1],
        "step1_recipient_ar": cc_row[2], "step1_tone_ar": cc_row[3],
        "step1_goals": _json.loads(cc_row[4]) if cc_row[4] else [],
        "step2_structure": _json.loads(cc_row[5]) if cc_row[5] else [],
        "step3_phrases": _json.loads(cc_row[6]) if cc_row[6] else {},
        "step4_model_email": cc_row[7],
        "step4_annotations": _json.loads(cc_row[8]) if cc_row[8] else [],
        "step5_fill_template": cc_row[9],
        "step5_blanks_hints": _json.loads(cc_row[10]) if cc_row[10] else [],
        "step6_checklist": _json.loads(cc_row[11]) if cc_row[11] else [],
        "common_mistakes": _json.loads(cc_row[12]) if cc_row[12] else []
    }
    # تحديث التقدم
    c.execute("""
        INSERT OR REPLACE INTO email_coach_progress
        (telegram_id, scenario_id, step_completed, last_seen_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (tg_id, scenario_id, step))
    conn.commit()
    step = max(1, min(6, int(step)))
    return render_template("toefl_writing/email_coach.html",
                           scenario=scenario, coach=coach,
                           current_step=step, user_id=tg_id)
'''
    code = code.rstrip() + "\n" + new_route + "\n"
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(code)
    print("[OK] Coach route added")
'@ | Out-File -FilePath "_p35_route.py" -Encoding utf8
py _p35_route.py
Remove-Item _p35_route.py
Write-Host ""

# ============================================================
# 3) تحديث email_list.html - إضافة زر "تعلّم أولاً"
# ============================================================
@'
import io, re
p = "templates/toefl_writing/email_list.html"
with io.open(p, "r", encoding="utf-8") as f:
    html = f.read()

# استبدل زر "ابدأ الكتابة" بزرّين
old = '<a class="btn" href="/writing/email/{{ s.id }}?user_id={{ user_id }}">ابدأ الكتابة ←</a>'
new = '''<a class="btn" style="background:#10b981;" href="/writing/email/{{ s.id }}/coach?user_id={{ user_id }}">📚 تعلّم أولاً</a>
      <a class="btn" style="margin-right:8px;" href="/writing/email/{{ s.id }}?user_id={{ user_id }}">✍️ ابدأ الكتابة ←</a>'''

if old in html:
    html = html.replace(old, new)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print("[OK] email_list.html updated with coach button")
else:
    print("[SKIP] already updated or pattern not found")
'@ | Out-File -FilePath "_p35_list.py" -Encoding utf8
py _p35_list.py
Remove-Item _p35_list.py

# ============================================================
# 4) إنشاء قالب email_coach.html
# ============================================================
@'
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>📚 Coach - {{ scenario.title_ar }}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background:#f5f7fb; margin:0; padding:0; color:#1e293b; line-height:1.7; }
  .container { max-width:900px; margin:0 auto; padding:15px; }
  .header { background:linear-gradient(135deg,#10b981,#059669); color:#fff; padding:20px; border-radius:14px; margin:15px 0; }
  .header h1 { margin:0 0 5px 0; font-size:22px; }
  .header p { margin:0; opacity:0.95; font-size:14px; }
  .progress-bar { background:#fff; border-radius:14px; padding:15px; margin-bottom:15px; box-shadow:0 2px 8px rgba(0,0,0,0.05); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; }
  .step-circle { width:38px; height:38px; border-radius:50%; background:#e2e8f0; color:#64748b; display:flex; align-items:center; justify-content:center; font-weight:bold; cursor:pointer; text-decoration:none; transition:0.2s; }
  .step-circle.done { background:#10b981; color:#fff; }
  .step-circle.current { background:#4f46e5; color:#fff; transform:scale(1.15); box-shadow:0 4px 12px rgba(79,70,229,0.4); }
  .step-circle:hover { transform:scale(1.1); }
  .step-line { flex:1; height:2px; background:#e2e8f0; margin:0 -5px; min-width:10px; }
  .step-line.done { background:#10b981; }
  .card { background:#fff; border-radius:14px; padding:25px; margin-bottom:15px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }
  .card h2 { margin:0 0 15px 0; color:#1e293b; font-size:22px; border-bottom:3px solid #10b981; padding-bottom:10px; display:inline-block; }
  .info-box { background:#f0fdf4; border-right:4px solid #10b981; padding:15px; border-radius:8px; margin:12px 0; }
  .info-box.blue { background:#eff6ff; border-right-color:#3b82f6; }
  .info-box.yellow { background:#fef9c3; border-right-color:#eab308; }
  .info-box.red { background:#fee2e2; border-right-color:#dc2626; }
  .info-box.purple { background:#f3e8ff; border-right-color:#a855f7; }
  .goal-card { background:#fff; border:2px solid #10b981; padding:12px 15px; border-radius:10px; margin:8px 0; display:flex; gap:12px; align-items:center; }
  .goal-num { background:#10b981; color:#fff; width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold; flex-shrink:0; }
  .structure-row { background:#f8fafc; padding:15px; border-radius:10px; margin:10px 0; border-right:4px solid #4f46e5; }
  .structure-row .part-title { font-weight:bold; color:#4f46e5; margin-bottom:5px; }
  .structure-row .example { background:#1e293b; color:#a7f3d0; padding:8px 12px; border-radius:6px; font-family:'Courier New', monospace; direction:ltr; text-align:left; margin:8px 0; }
  .structure-row .tip { font-size:13px; color:#64748b; font-style:italic; }
  .phrase-group { background:#fff; border:1px solid #e2e8f0; border-radius:10px; padding:12px; margin:10px 0; }
  .phrase-group h4 { margin:0 0 10px 0; color:#4f46e5; }
  .phrase-item { background:#f8fafc; padding:10px; border-radius:6px; margin:5px 0; cursor:pointer; transition:0.2s; }
  .phrase-item:hover { background:#e0e7ff; }
  .phrase-item .en { font-weight:bold; direction:ltr; text-align:left; display:block; }
  .phrase-item .ar { font-size:13px; color:#64748b; }
  .phrase-item .copy-hint { font-size:11px; color:#10b981; }
  .model-email { background:#1e293b; color:#e2e8f0; padding:20px; border-radius:10px; direction:ltr; text-align:left; white-space:pre-wrap; font-family:'Georgia', serif; line-height:1.8; margin:15px 0; font-size:15px; }
  .annotation-item { background:#fef9c3; padding:12px; border-radius:8px; margin:8px 0; }
  .annotation-item .line { background:#1e293b; color:#fbbf24; padding:6px 10px; border-radius:5px; direction:ltr; text-align:left; font-family:'Courier New', monospace; font-size:13px; margin-bottom:6px; }
  .annotation-item .comment { color:#92400e; }
  .fill-area { background:#fff; border:2px dashed #4f46e5; padding:20px; border-radius:10px; direction:ltr; text-align:left; font-family:'Georgia', serif; line-height:2.2; font-size:15px; white-space:pre-wrap; }
  .fill-area input { border:none; border-bottom:2px solid #4f46e5; padding:4px 8px; min-width:150px; font-size:14px; background:transparent; text-align:left; direction:ltr; font-family:inherit; }
  .fill-area input:focus { outline:none; border-bottom-color:#10b981; background:#f0fdf4; }
  .hints-panel { background:#eff6ff; padding:15px; border-radius:10px; margin:15px 0; }
  .hints-panel h4 { margin:0 0 10px 0; color:#1d4ed8; }
  .hint-item { padding:6px 0; font-size:14px; }
  .checklist-item { background:#fff; padding:12px 15px; border-radius:8px; margin:6px 0; display:flex; align-items:center; gap:10px; border:1px solid #e2e8f0; }
  .checklist-item input[type="checkbox"] { width:20px; height:20px; cursor:pointer; }
  .mistake-card { background:#fee2e2; padding:15px; border-radius:10px; margin:10px 0; }
  .mistake-card .wrong { color:#dc2626; text-decoration:line-through; font-family:'Courier New', monospace; direction:ltr; text-align:left; display:block; padding:6px 10px; background:#fff; border-radius:5px; margin:5px 0; }
  .mistake-card .right { color:#16a34a; font-family:'Courier New', monospace; direction:ltr; text-align:left; display:block; padding:6px 10px; background:#fff; border-radius:5px; margin:5px 0; }
  .nav-buttons { display:flex; justify-content:space-between; gap:10px; margin:20px 0; flex-wrap:wrap; }
  .btn { padding:12px 24px; border:none; border-radius:8px; font-size:15px; font-weight:bold; cursor:pointer; text-decoration:none; display:inline-block; }
  .btn-primary { background:#4f46e5; color:#fff; }
  .btn-primary:hover { background:#4338ca; }
  .btn-success { background:#10b981; color:#fff; font-size:18px; padding:15px 30px; }
  .btn-success:hover { background:#059669; }
  .btn-secondary { background:#e2e8f0; color:#1e293b; }
  .recipient-tone { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:15px 0; }
  @media (max-width:600px) { .recipient-tone { grid-template-columns:1fr; } }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📚 مدرّب الإيميل - {{ scenario.title_ar }}</h1>
    <p>{{ scenario.title_en }} | المستوى: {{ scenario.target_tier }} | الحد الأدنى: {{ scenario.min_words }} كلمة</p>
  </div>

  <!-- شريط التقدم -->
  <div class="progress-bar">
    {% for i in range(1, 7) %}
      <a href="/writing/email/{{ scenario.id }}/coach/{{ i }}?user_id={{ user_id }}"
         class="step-circle {% if i < current_step %}done{% elif i == current_step %}current{% endif %}">
        {% if i < current_step %}✓{% else %}{{ i }}{% endif %}
      </a>
      {% if i < 6 %}<div class="step-line {% if i < current_step %}done{% endif %}"></div>{% endif %}
    {% endfor %}
  </div>

  <!-- ========================== الخطوة 1: فهم الموقف ========================== -->
  {% if current_step == 1 %}
  <div class="card">
    <h2>🎬 الخطوة 1: افهم الموقف</h2>

    <div class="info-box">
      <strong>📖 الموقف بالعربية:</strong><br>
      {{ coach.step1_situation_ar }}
    </div>

    <div class="info-box blue">
      <strong style="direction:ltr;display:block;text-align:left;">📖 The Situation (English):</strong>
      <div style="direction:ltr;text-align:left;margin-top:5px;">{{ coach.step1_situation_en }}</div>
    </div>

    <div class="recipient-tone">
      <div class="info-box yellow">
        <strong>👤 من المُرسَل إليه؟</strong><br>
        {{ coach.step1_recipient_ar }}
      </div>
      <div class="info-box purple">
        <strong>🎭 ما النبرة المطلوبة؟</strong><br>
        {{ coach.step1_tone_ar }}
      </div>
    </div>

    <h3 style="color:#10b981; margin-top:25px;">🎯 الأهداف الـ 3 التي يجب تحقيقها:</h3>
    {% for g in coach.step1_goals %}
    <div class="goal-card">
      <div class="goal-num">{{ g.num }}</div>
      <div>
        <strong>{{ g.ar }}</strong><br>
        <span style="color:#64748b; direction:ltr; display:block; text-align:left; font-size:13px;">{{ g.en }}</span>
      </div>
    </div>
    {% endfor %}

    <div class="info-box red" style="margin-top:20px;">
      ⚠️ <strong>قبل أن تنتقل للخطوة التالية، اسأل نفسك:</strong>
      <ul style="margin:8px 0 0 0;">
        <li>هل فهمت من المُرسَل إليه؟</li>
        <li>هل أعرف الأهداف الثلاثة بدقة؟</li>
        <li>هل أتذكر النبرة المطلوبة (رسمية/ودية)؟</li>
      </ul>
    </div>
  </div>
  {% endif %}

  <!-- ========================== الخطوة 2: البنية ========================== -->
  {% if current_step == 2 %}
  <div class="card">
    <h2>🏗️ الخطوة 2: بنية الإيميل (5-6 أجزاء)</h2>
    <div class="info-box blue">
      كل إيميل احترافي يتكوّن من <strong>5-6 أجزاء أساسية</strong>. تعلّم البنية ثم املأها بالمحتوى. هذه البنية تعمل في 99% من الإيميلات.
    </div>

    {% for s in coach.step2_structure %}
    <div class="structure-row">
      <div class="part-title">{{ s.part }}</div>
      <div style="margin:6px 0;">🎯 <strong>الغرض:</strong> {{ s.purpose_ar }}</div>
      <div class="example">{{ s.example_en }}</div>
      <div class="tip">💡 {{ s.tip_ar }}</div>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- ========================== الخطوة 3: بنك العبارات ========================== -->
  {% if current_step == 3 %}
  <div class="card">
    <h2>💎 الخطوة 3: بنك العبارات الذهبية</h2>
    <div class="info-box">
      هذه عبارات احترافية مخصصة لمستواك ({{ scenario.target_tier }}). <strong>احفظ 1-2 من كل قسم</strong> وستصبح كتابتك أقوى فوراً.
      <br><small>💡 اضغط على أي عبارة لنسخها.</small>
    </div>

    {% for category, items in coach.step3_phrases.items() %}
    <div class="phrase-group">
      <h4>📌 {{ category|title }}</h4>
      {% for p in items %}
      <div class="phrase-item" onclick="copyText('{{ p.en|e }}', this)">
        <span class="en">{{ p.en }}</span>
        <span class="ar">{{ p.ar }}</span>
        <span class="copy-hint">📋 اضغط للنسخ</span>
      </div>
      {% endfor %}
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- ========================== الخطوة 4: نموذج مُحلَّل ========================== -->
  {% if current_step == 4 %}
  <div class="card">
    <h2>📖 الخطوة 4: نموذج مثالي مُحلَّل</h2>
    <div class="info-box">
      هذا نموذج كامل لإيميل مستوى <strong>{{ scenario.target_tier }}</strong>. اقرأه أولاً، ثم اقرأ الشرح أسفله لتفهم لماذا كل سطر قوي.
    </div>

    <h3 style="color:#4f46e5;">📧 الإيميل الكامل:</h3>
    <div class="model-email">{{ coach.step4_model_email }}</div>

    <h3 style="color:#4f46e5; margin-top:25px;">🔍 تحليل سطر بسطر:</h3>
    {% for a in coach.step4_annotations %}
    <div class="annotation-item">
      <div class="line">{{ a.line }}</div>
      <div class="comment">{{ a.comment_ar }}</div>
    </div>
    {% endfor %}

    <h3 style="color:#dc2626; margin-top:25px;">❌ أخطاء شائعة لتتجنّبها:</h3>
    {% for m in coach.common_mistakes %}
    <div class="mistake-card">
      <span class="wrong">❌ {{ m.wrong }}</span>
      <span class="right">✅ {{ m.right }}</span>
      <div style="margin-top:8px; font-size:14px;"><strong>لماذا؟</strong> {{ m.why_ar }}</div>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- ========================== الخطوة 5: قالب فراغات ========================== -->
  {% if current_step == 5 %}
  <div class="card">
    <h2>✏️ الخطوة 5: تدرّب بملء الفراغات</h2>
    <div class="info-box yellow">
      الآن ستجرّب بنفسك! هذا قالب الإيميل مع فراغات. املأ كل فراغ بمحتواك الخاص (استخدم الإرشادات يمين الصفحة).
    </div>

    <div class="fill-area" id="fill-area">
      {{ coach.step5_fill_template|safe }}
    </div>

    <div class="hints-panel">
      <h4>💡 إرشادات لكل فراغ:</h4>
      {% for h in coach.step5_blanks_hints %}
      <div class="hint-item">
        <strong>الفراغ {{ h.blank }}:</strong> {{ h.hint_ar }}
        <span style="color:#10b981; direction:ltr; display:inline-block; font-family:Courier New, monospace; font-size:13px;">مثال: "{{ h.example }}"</span>
      </div>
      {% endfor %}
    </div>

    <div class="info-box">
      💪 <strong>تحدّي:</strong> اقرأ القالب أعلاه واملأه ذهنياً قبل الانتقال للخطوة التالية. لا حاجة للحفظ، فقط افهم كيف تتدفق الجمل.
    </div>
  </div>
  {% endif %}

  <!-- ========================== الخطوة 6: Checklist ========================== -->
  {% if current_step == 6 %}
  <div class="card">
    <h2>✅ الخطوة 6: قائمة التحقق النهائية</h2>
    <div class="info-box">
      أنت جاهز للكتابة! قبل أن تضغط "ابدأ الكتابة"، تأكد من أنك تعرف هذه الـ <strong>{{ coach.step6_checklist|length }} نقاط</strong>.
      ستحتاج للرجوع لها بعد كتابة إيميلك للمراجعة.
    </div>

    {% for item in coach.step6_checklist %}
    <label class="checklist-item">
      <input type="checkbox">
      <span>{{ item }}</span>
    </label>
    {% endfor %}

    <div style="text-align:center; margin:30px 0 10px 0;">
      <a href="/writing/email/{{ scenario.id }}?user_id={{ user_id }}" class="btn btn-success">
        🚀 أنا جاهز - ابدأ الكتابة الآن (7 دقائق)
      </a>
    </div>
    <div style="text-align:center; color:#64748b; font-size:13px;">
      ⏱️ التايمر سيبدأ بمجرد فتح صفحة الكتابة. أمامك 7 دقائق فقط - استغلّها بحكمة.
    </div>
  </div>
  {% endif %}

  <!-- أزرار التنقل بين الخطوات -->
  <div class="nav-buttons">
    {% if current_step > 1 %}
      <a href="/writing/email/{{ scenario.id }}/coach/{{ current_step - 1 }}?user_id={{ user_id }}" class="btn btn-secondary">→ الخطوة السابقة</a>
    {% else %}
      <a href="/writing/email?user_id={{ user_id }}" class="btn btn-secondary">→ رجوع للقائمة</a>
    {% endif %}

    {% if current_step < 6 %}
      <a href="/writing/email/{{ scenario.id }}/coach/{{ current_step + 1 }}?user_id={{ user_id }}" class="btn btn-primary">فهمت ✓ الخطوة التالية ←</a>
    {% endif %}
  </div>
</div>

<script>
function copyText(text, el) {
  navigator.clipboard.writeText(text).then(() => {
    const original = el.querySelector('.copy-hint').textContent;
    el.querySelector('.copy-hint').textContent = '✅ تم النسخ!';
    el.style.background = '#dcfce7';
    setTimeout(() => {
      el.querySelector('.copy-hint').textContent = original;
      el.style.background = '';
    }, 1500);
  });
}

// تحويل _______ إلى input عند الضغط في قسم الفراغات
document.addEventListener('DOMContentLoaded', () => {
  const fillArea = document.getElementById('fill-area');
  if (fillArea) {
    fillArea.innerHTML = fillArea.innerHTML.replace(/_{5,}/g, '<input type="text" placeholder="...">');
  }
});
</script>
</body>
</html>
'@ | Out-File -FilePath "templates\toefl_writing\email_coach.html" -Encoding utf8
Write-Host "[OK] email_coach.html created" -ForegroundColor Green

# ============================================================
# 5) فحص ونشر
# ============================================================
Write-Host ""
Write-Host "=== Syntax Check ===" -ForegroundColor Cyan
py -m py_compile routes/writing_toefl.py
if ($LASTEXITCODE -eq 0) { Write-Host "[OK] writing_toefl.py compiles" -ForegroundColor Green }

# قتل الخادم القديم
Write-Host ""
Write-Host "=== Restarting Server ===" -ForegroundColor Cyan
Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
Write-Host "[OK] Old server killed" -ForegroundColor Green

# تشغيل خادم جديد في نافذة منفصلة
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\Users\nelt2\yamen_academy; py app.py"
Start-Sleep -Seconds 5

# اختبار سريع
Write-Host ""
Write-Host "=== Testing Coach Page ===" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8080/writing/email/1/coach/1?user_id=TEST_TIER" -UseBasicParsing -TimeoutSec 10
    Write-Host "[OK] Coach page status: $($r.StatusCode), length: $($r.Content.Length)" -ForegroundColor Green
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Git commit
Write-Host ""
git add -A
git commit -m "feat(writing): Phase 3.5 - Email Coach 6-step learning system (tier-aware content)"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "🎉 Phase 3.5 Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "🧪 Test URLs:"
Write-Host "  Coach (Step 1): http://localhost:8080/writing/email/1/coach?user_id=TEST_TIER"
Write-Host "  Coach (Step 5): http://localhost:8080/writing/email/1/coach/5?user_id=TEST_TIER"
Write-Host "  After learning: http://localhost:8080/writing/email/1?user_id=TEST_TIER"
Write-Host "  Tier 90 Coach:  http://localhost:8080/writing/email/4/coach?user_id=TEST_TIER"
