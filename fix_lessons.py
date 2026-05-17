import json, os, sys

sys.path.insert(0, '.')
lessons_dir = r'content\lessons'
os.makedirs(lessons_dir, exist_ok=True)

# Delete old incomplete files
for f in os.listdir(lessons_dir):
    if any(f.startswith(p) for p in ['reading_','listening_','writing_','speaking_','grammar_','vocab_']):
        os.remove(os.path.join(lessons_dir, f))
        print(f'  Deleted: {f}')

lessons = [
    ('L003', 'اساسيات القراءة - الفكرة الرئيسية', 'reading', 'beginner', 1),
    ('L004', 'استيعاب التفاصيل الداعمة', 'reading', 'intermediate', 2),
    ('L005', 'المفردات في السياق', 'reading', 'intermediate', 3),
    ('L006', 'الاستدلال والاستنتاج', 'reading', 'advanced', 4),
    ('L007', 'تنظيم النص وبنية الفقرات', 'reading', 'advanced', 5),
    ('L008', 'ملخص النص واعادة الصياغة', 'reading', 'advanced', 6),
    ('L009', 'اساسيات الاستماع - المحادثات القصيرة', 'listening', 'beginner', 1),
    ('L010', 'المحاضرات الاكاديمية', 'listening', 'intermediate', 2),
    ('L011', 'تحديد موقف المتحدث', 'listening', 'intermediate', 3),
    ('L012', 'الربط بين الافكار', 'listening', 'advanced', 4),
    ('L013', 'تدوين الملاحظات الفعال', 'listening', 'advanced', 5),
    ('L014', 'تمارين استماع شاملة', 'listening', 'advanced', 6),
    ('L015', 'اساسيات الكتابة - بنية المقال', 'writing', 'beginner', 1),
    ('L016', 'الكتابة المتكاملة - المهمة الاولى', 'writing', 'intermediate', 2),
    ('L017', 'الكتابة المستقلة - المهمة الثانية', 'writing', 'intermediate', 3),
    ('L018', 'تطوير الافكار والامثلة', 'writing', 'advanced', 4),
    ('L019', 'القواعد المتقدمة في الكتابة', 'writing', 'advanced', 5),
    ('L020', 'مراجعة وتحرير النصوص', 'writing', 'advanced', 6),
    ('L021', 'اساسيات المحادثة - التعريف بالنفس', 'speaking', 'beginner', 1),
    ('L022', 'المهمة الاولى - الراي الشخصي', 'speaking', 'intermediate', 2),
    ('L023', 'المهمة المتكاملة - القراءة والاستماع', 'speaking', 'intermediate', 3),
    ('L024', 'المهمة المتكاملة - المحاضرة', 'speaking', 'advanced', 4),
    ('L025', 'الطلاقة والنطق', 'speaking', 'advanced', 5),
    ('L026', 'محاكاة اختبار المحادثة الكامل', 'speaking', 'advanced', 6),
    ('L027', 'الازمنة الاساسية', 'grammar', 'beginner', 1),
    ('L028', 'الازمنة التامة والمستمرة', 'grammar', 'intermediate', 2),
    ('L029', 'الجمل الشرطية', 'grammar', 'intermediate', 3),
    ('L030', 'المبني للمجهول', 'grammar', 'advanced', 4),
    ('L031', 'ادوات الربط والروابط', 'grammar', 'advanced', 5),
    ('L032', 'الاخطاء الشائعة وتصحيحها', 'grammar', 'advanced', 6),
    ('L033', 'كلمات اكاديمية اساسية', 'vocabulary', 'beginner', 1),
    ('L034', 'مفردات العلوم والتكنولوجيا', 'vocabulary', 'intermediate', 2),
    ('L035', 'مفردات العلوم الانسانية', 'vocabulary', 'intermediate', 3),
    ('L036', 'التعابير الاصطلاحية', 'vocabulary', 'advanced', 4),
    ('L037', 'عائلات الكلمات والاشتقاقات', 'vocabulary', 'advanced', 5),
    ('L038', 'استراتيجيات حفظ المفردات', 'vocabulary', 'advanced', 6),
]

for lesson_id, title, category, difficulty, order in lessons:
    lesson = {
        'lesson_id': lesson_id,
        'title': title,
        'title_en': title,
        'category': category,
        'skill_type': category,
        'difficulty': difficulty,
        'duration_minutes': 45,
        'description': title + ' - دورة تحضيرية شاملة لاختبار TOEFL',
        'prerequisites': [],
        'objectives': ['اتقان ' + title, 'تطبيق استراتيجيات الاختبار'],
        'sections': [
            {
                'title': 'مقدمة',
                'content': '<h2>' + title + '</h2><p>مرحبا بك في هذا الدرس. ستتعلم المهارات الاساسية لهذا القسم من اختبار TOEFL.</p>'
            },
            {
                'title': 'شرح المفاهيم',
                'content': '<h3>المفاهيم الاساسية</h3><p>شرح المفاهيم الرئيسية بطريقة مبسطة وسهلة الفهم.</p>'
            },
            {
                'title': 'تمارين تطبيقية',
                'content': '<h3>تدريبات عملية</h3><p>اختبر فهمك من خلال التمارين التالية.</p>'
            }
        ],
        'quiz': {'questions': []},
        'metadata': {'version': 1, 'updated_at': '2026-05-16'}
    }

    filename = lesson_id + '_' + title[:40].replace(' ', '_').replace('-','') + '.json'
    filepath = os.path.join(lessons_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(lesson, f, indent=2, ensure_ascii=False)

print(f'[OK] {len(lessons)} lessons created!')

# Re-scan
from modules.content_engine import scan_content
r = scan_content()
print(f'[DONE] {r["total_lessons"]} lessons in index!')
