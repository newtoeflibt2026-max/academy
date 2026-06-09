# 🎓 Yamen Academy — منصة تعليم IELTS

منصّة تعليمية شاملة لتأهيل طلاب IELTS عبر بوت تيليجرام + Mini App + لوحة إدارة.

## 🌐 الإنتاج
- التطبيق: https://yamenacademyapp.up.railway.app
- البوت: عبر Telegram Webhook
- قاعدة البيانات: SQLite على Railway (`/app/data/academy.db`)

## 🧩 الأقسام التعليمية
1. **التأسيس الشامل (Foundation)** — 22 مرحلة، 29+ درس، نحوي + مفردات + قواعد.
2. **Reading** — قراءة وتمارين يومية.
3. **Listening** — استماع ومحاكاة الامتحان.
4. **Writing** — مهمات Task 1 / Task 2 مع تصحيح بشري.
5. **Speaking** — تدريب على المقابلات.
6. **Mock Exams** — امتحانات تجريبية شاملة.

## 🛠️ المعمارية
- **Backend:** Flask + Gunicorn (`app.py` ~6098 سطر) + Blueprints في `routes/`.
- **Bot:** aiogram (`handlers/`, `bot_webhook.py`).
- **Frontend:** HTML + Tailwind-like CSS + Vanilla JS (`templates/`).
- **DB:** SQLite (`DB_PATH = /app/data/academy.db`).

## ✅ الميزات المُنجزة
- نظام دفع الباقات (8 باقات) مع موافقة الأدمن عبر التيليجرام.
- موافقة الأدمن تُحدّث `students.is_paid=1` وتُسجّل في `subscriptions`.
- دفتر الأخطاء يعرض فقط الأسئلة الموجودة (يُخفي اليتيمة).
- لوحة إدارة كاملة (طلاب، باقات، أسئلة، مدفوعات، إحصاءات).
- إضافة طالب يدوياً عبر `/api/admin/students/add`.

## 🚧 قيد العمل
- إكمال محتوى التأسيس (أسئلة كافية لكل درس F1–F22).
- **شرح موجّه لكل خيار** (correct + wrong reasons).
- بنك اختبارات نهاية المرحلة بأسئلة منفصلة عن الدروس.
- إعادة تفعيل `has_access` بعد اكتمال الباقات.

## 📂 ملفات مرجعية
- `INSTRUCTIONS.md` — إرشادات التطوير الدائمة.
- `.env` — أسرار البيئة (BOT_TOKEN، DB_PATH، ...).
- `Procfile` — أوامر تشغيل Railway.

## 🔐 المتغيرات البيئية المطلوبة على Railway
- `BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET=yamen-webhook-secret-2026`
- `DATABASE_URL` (اختياري)

## 📜 سجل آخر التعديلات
- `6f006d9` fix(mistakes): count only visible (non-orphaned) errors
- `ffe805c` fix(mistakes): join lesson_questions and questions tables
- `27c9058` fix(payments): repair mojibake emojis in admin payment notification
- `5ed6684` fix(payments): use admin_approve/admin_reject callbacks

## 👤 المطوّر
Yamen Academy © 2026