import json, os

lessons_dir = os.path.join('content', 'lessons')
os.makedirs(lessons_dir, exist_ok=True)

lessons = [
    ('L003', 'اساسيات القراءة - الفكرة الرئيسية', 'reading', 'beginner', 3),
    ('L004', 'استيعاب التفاصيل الداعمة', 'reading', 'intermediate', 4),
    ('L005', 'المفردات في السياق', 'reading', 'intermediate', 5),
    ('L006', 'الاستدلال والاستنتاج', 'reading', 'advanced', 6),
    ('L007', 'تنظيم النص وبنية الفقرات', 'reading', 'advanced', 7),
    ('L008', 'ملخص النص واعادة الصياغة', 'reading', 'advanced', 8),
    ('L009', 'اساسيات الاستماع - المحادثات القصيرة', 'listening', 'beginner', 9),
    ('L010', 'المحاضرات الاكاديمية', 'listening', 'intermediate', 10),
    ('L011', 'تحديد موقف المتحدث', 'listening', 'intermediate', 11),
    ('L012', 'الربط بين الافكار', 'listening', 'advanced', 12),
    ('L013', 'تدوين الملاحظات الفعال', 'listening', 'advanced', 13),
    ('L014', 'تمارين استماع شاملة', 'listening', 'advanced', 14),
    ('L015', 'اساسيات الكتابة - بنية المقال', 'writing', 'beginner', 15),
    ('L016', 'الكتابة المتكاملة - المهمة الاولى', 'writing', 'intermediate', 16),
    ('L017', 'الكتابة المستقلة - المهمة الثانية', 'writing', 'intermediate', 17),
    ('L018', 'تطوير الافكار والامثلة', 'writing', 'advanced', 18),
    ('L019', 'القواعد المتقدمة في الكتابة', 'writing', 'advanced', 19),
    ('L020', 'مراجعة وتحرير النصوص', 'writing', 'advanced', 20),
    ('L021', 'اساسيات المحادثة - التعريف بالنفس', 'speaking', 'beginner', 21),
    ('L022', 'المهمة الاولى - الراي الشخصي', 'speaking', 'intermediate', 22),
    ('L023', 'المهمة المتكاملة - القراءة والاستماع', 'speaking', 'intermediate', 23),
    ('L024', 'المهمة المتكاملة - المحاضرة', 'speaking', 'advanced', 24),
    ('L025', 'الطلاقة والنطق', 'speaking', 'advanced', 25),
    ('L026', 'محاكاة اختبار المحادثة الكامل', 'speaking', 'advanced', 26),
    ('L027', 'الازمنة الاساسية', 'grammar', 'beginner', 27),
    ('L028', 'الازمنة التامة والمستمرة', 'grammar', 'intermediate', 28),
    ('L029', 'الجمل الشرطية', 'grammar', 'intermediate', 29),
    ('L030', 'المبني للمجهول', 'grammar', 'advanced', 30),
    ('L031', 'ادوات الربط والروابط', 'grammar', 'advanced', 31),
    ('L032', 'الاخطاء الشائعة وتصحيحها', 'grammar', 'advanced', 32),
    ('L033', 'كلمات اكاديمية اساسية', 'vocabulary', 'beginner', 33),
    ('L034', 'مفردات العلوم والتكنولوجيا', 'vocabulary', 'intermediate', 34),
    ('L035', 'مفردات العلوم الانسانية', 'vocabulary', 'intermediate', 35),
    ('L036', 'التعابير الاصطلاحية', 'vocabulary', 'advanced', 36),
    ('L037', 'عائلات الكلمات والاشتقاقات', 'vocabulary', 'advanced', 37),
    ('L038', 'استراتيجيات حفظ المفردات', 'vocabulary', 'advanced', 38),
]

count = 0
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

    filename = lesson_id + '_' + title[:30].replace(' ', '_').replace('-', '') + '.json'
    filepath = os.path.join(lessons_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(lesson, f, indent=2, ensure_ascii=False)
    count += 1
    print('Created: ' + filename)

print('\n[DONE] ' + str(count) + ' lessons created in content/lessons/')

# Re-scan
import sys
sys.path.insert(0, '.')
from modules.content_engine import scan_content
r = scan_content()
print('[DONE] Index rebuilt: ' + str(r['total_lessons']) + ' lessons total')
