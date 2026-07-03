# قالب قطعة قراءة أكاديمية (Academic Reading)

ضع ملف JSON جديداً في هذا المجلد بهذه البنية، وسيظهر تلقائياً في الفهرس.

## الترتيب
- اسم الملف وحقل id: ar_<tier>_<NN>  مثل ar_easy_09 / ar_medium_12 / ar_hard_20
- tier: "easy" أو "medium" أو "hard"  (يحدد اللون والترتيب والفتح التتابعي)

## الحقول المطلوبة
- id, tier, title_en (يُعرض للطالب), title_ar, type="academic_reading"
- passage.text_en : النص ~200 كلمة، الفقرات مفصولة بـ \n\n
- questions: قائمة، كل سؤال فيه:
  - q (نص السؤال بالإنجليزي)
  - options: {"A":..,"B":..,"C":..,"D":..}
  - correct: "A".."D"
  - type: أحد: factual | negative_factual | vocabulary | rhetorical |
          inference | insert_sentence | paragraph_relationship | important_idea
  - explanation_ar: شرح الإجابة الصحيحة بالعربي (يظهر دائماً بعد التصحيح)

## الحقول الخيارية (ميزات الأستاذ الخصوصي)
- glossary: {"word":"الترجمة العربية", ...} كلمات صعبة تظهر بخط منقّط تُنقر للترجمة
- لكل سؤال:
  - q_translation_ar: ترجمة السؤال (زر اختياري)
  - avoid_tip_ar: "كيف تتجنّب هذا الخطأ" (يظهر فقط عند الإجابة الخاطئة)

## ملاحظات
- 5 أسئلة لكل قطعة (نمط التوفل المحدّث).
- نوّع الأنواع: السهل يركّز على factual/vocabulary، والصعب يضيف
  inference/insert_sentence/paragraph_relationship/important_idea.
- النص لا يخبر الطالب بأي فقرة يبحث (نمط التوفل المحدّث).
