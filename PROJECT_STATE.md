# Yamen Academy - Project State
Last updated: 2026-06-17

## Mission
TOEFL iBT prep for Arabic-speaking students.

## CANONICAL ARCHITECTURE
- Student dashboard: /student?student_id=<id>
- Lesson with questions: /miniapp/quiz/<id>
- Theory-only lesson: /miniapp/lesson/<id>
- Main API: /api/student/dashboard

## CONTENT (current)
- Foundation: 50 lessons (F1, F2, F3) - has questions
- Reading: 32 lessons (R-01 to R-32) - mixed theory + practice
- Listening / Speaking: NOT BUILT (hidden from UI)
- Writing: BUILT (5 stages, 30 lessons, 70 questions) - routes/writing_toefl.py

## F1-EXAM
Placement test. 20 Q. >=70% skips Foundation, goes to Reading.

## DATABASE
- students PK: user_id (INTEGER). Lookup: telegram_id (TEXT).
- lessons: lesson_code is human key (F1-L01, R-01).
- student_lesson_progress: tracks completion.
- lesson_questions: practice questions per lesson.

## DO NOT
- Create new dashboard pages (/home, /welcome2, etc.)
- Display empty skills - hide them
- Hardcode lesson IDs

## FOR AI ASSISTANTS
Read this file + CHANGELOG.md before any change.


## DAY 2 - Focused Journey (added 2026-06-14)
- New API: /api/student/journey - phase-aware focused view
- Dashboard now shows ONLY: current lesson (big card) + 3 upcoming + phase progress
- 4 phases: F1, F2, F3, reading
- Celebration message when student completes a phase
- Old long lesson list is hidden by default (still accessible via /student lessons tab)


═══════════════════════════════════════════════════
## 📌 خطة Writing المعتمدة (محدّث: 2026-06-17 10:00)
## القرارات المعمارية (لا تُنسى بين الجلسات)
═══════════════════════════════════════════════════

### القرار 1 — الربط بالـ TIER لا بالمستوى الذاتي
- المحتوى والتمارين تُربط بهدف الدرجة المدفوع: 59 / 69 / 90.
- الطالب يرى مساره فقط: من دفع 59 لا يُربك بمحتوى 90.
- مسار 59 = القالب الجاهز + الجمل الأساسية (يضمن درجة 3).
- مسار 69 = ربط الأفكار + تطوير التفاصيل (درجة 4).
- مسار 90 = الدقة اللغوية + النبرة الراقية (درجة 5).
- كل مسار أعلى يتضمّن ما تحته (تراكمي).

### القرار 2 — كل درس متكامل = 3 أجزاء
1) صندوق توجيه (حدّد هدفك، تدرّب ضمن مسارك، لا تقفز).
2) شرح متدرّج بالـ tier (59 ثم 69 ثم 90).
3) تمارين MCQ مربوطة بالدرس + بالـ tier، تُصحّح تلقائيًا.

### القرار 3 — التصحيح عبر Gemini (نسخ/لصق فقط)
- أُلغي التصحيح التلقائي عبر API (مشكلة quota وهمية).
- المسار: انسخ السؤال+إجابتك+برومبت ETS → الصق في gemini.google → خذ الدرجة.
- لا درجة وهمية ميكانيكية، لا رسالة مدرس 24 ساعة.

### القرار 4 — Rating/الترتيب (متفق عليه - للتنفيذ)
- نظام تقييم تقدّم الطالب يُبنى حسب منظومة الـ tier والمواضيع المعتمدة.
- [يُستكمل التفصيل بعد توضيح المستخدم للمنظومة بالضبط]

### الحالة الحالية للبيانات (من audit)
- writing_lessons: 30 درس، كلها tier=all (يجب تصنيفها).
- writing_questions: 63 tier=all + 4 tier59 + 3 tier69 + 3 tier90.
- اشتراك المستخدم 5572314718: plan_name=foundation_full (ربط الخطة بالـtier غير محسوم).
- ثغرة: نظام tier مبني جزئيًا ثم تُرك → سبب الفوضى.

### المنجز في جلسة 2026-06-17 10:00
- إصلاح 500 في تسليم الدروس (sentence_building_exercises بلا lesson_id).
- إصلاح تصحيح MCQ (فك JSON) في الدروس + امتحان المراحل → المراحل تُفتح.
- استعادة بطاقة الكتابة في student_dashboard.
- إعادة كتابة درس 14 (أنواع الإيميلات الخمسة، ETS-aligned).
- إعادة كتابة درس 15 (التشريح الكامل) + 3 تمارين mcq.

### الخطوة التالية المحددة
1) حسم ربط plan_name بالـ tier (foundation_full = أي tier؟).
2) تصنيف الدروس الـ30 حسب الـ tier.
3) تطبيق صندوق التوجيه + البنية الثلاثية على دروس البريد.
4) بناء نظام Rating حسب المنظومة المعتمدة.
═══════════════════════════════════════════════════
