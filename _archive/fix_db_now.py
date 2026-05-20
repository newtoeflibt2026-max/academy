import sqlite3
conn = sqlite3.connect('academy.db')
c = conn.cursor()

# system_settings
for col, typ in [('description','TEXT'), ('updated_at','TEXT')]:
    try:
        c.execute('ALTER TABLE system_settings ADD COLUMN ' + col + ' ' + typ)
        print('system_settings: added ' + col)
    except Exception as e:
        print('system_settings.' + col + ': ' + str(e))

# phase_settings
for col, typ in [
    ('phase_number','INTEGER'),
    ('phase_name','TEXT'),
    ('min_xp','INTEGER DEFAULT 0'),
    ('min_streak','INTEGER DEFAULT 0'),
    ('min_quiz_score','REAL DEFAULT 0'),
    ('min_attendance_days','INTEGER DEFAULT 0'),
    ('description','TEXT'),
    ('updated_at','TEXT'),
]:
    try:
        c.execute('ALTER TABLE phase_settings ADD COLUMN ' + col + ' ' + typ)
        print('phase_settings: added ' + col)
    except Exception as e:
        print('phase_settings.' + col + ': ' + str(e))

# students
for col, typ in [
    ('phone','TEXT'),
    ('is_paid','INTEGER DEFAULT 0'),
    ('tasks_completed','INTEGER DEFAULT 0'),
    ('completed_lessons','TEXT'),
    ('mock_score','REAL DEFAULT 0'),
    ('current_phase','INTEGER DEFAULT 1'),
    ('streak','INTEGER DEFAULT 0'),
]:
    try:
        c.execute('ALTER TABLE students ADD COLUMN ' + col + ' ' + typ)
        print('students: added ' + col)
    except Exception as e:
        print('students.' + col + ': ' + str(e))

conn.commit()

# phase_settings seed
c.execute('SELECT COUNT(*) FROM phase_settings')
count = c.fetchone()[0]
print('phase_settings rows: ' + str(count))
if count == 0:
    phases = [
        (1, 'المبتدئ', 0, 0, 0, 0, 'المرحلة الأولى'),
        (2, 'المتوسط', 200, 2, 60, 7, 'المرحلة الثانية'),
        (3, 'المتقدم', 500, 5, 75, 14, 'المرحلة الثالثة'),
    ]
    for p in phases:
        c.execute('INSERT INTO phase_settings (phase_number,phase_name,min_xp,min_streak,min_quiz_score,min_attendance_days,description) VALUES (?,?,?,?,?,?,?)', p)
    print('phase_settings seeded')

# system_settings defaults
defaults = [
    ('graduation_min_xp', '500', 'الحد الادنى من XP للتخرج'),
    ('graduation_min_tasks', '10', 'عدد المهام اليومية المطلوبة'),
    ('graduation_min_streak', '3', 'الحد الادنى للـ streak'),
    ('graduation_min_mock_score', '69', 'الحد الادنى لنتيجة Mock Exam'),
    ('graduation_mock_bonus', '10', 'نقاط اضافية فوق required_score'),
    ('subscription_price', '25000', 'سعر الاشتراك بالدينار'),
    ('subscription_currency', 'IQD', 'العملة'),
    ('bot_welcome_message', 'مرحبا بك في اكاديمية يامن للتوفل', 'رسالة الترحيب'),
    ('paid_required_message', 'هذه الميزة للمشتركين فقط تواصل مع الادمن', 'رسالة المدفوع'),
]
for key, value, desc in defaults:
    try:
        c.execute('INSERT OR IGNORE INTO system_settings (key,value,description) VALUES (?,?,?)', (key, value, desc))
    except Exception as e:
        print('setting ' + key + ': ' + str(e))

conn.commit()
conn.close()
print('ALL DONE')
