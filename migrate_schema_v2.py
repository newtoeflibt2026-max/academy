"""
Migration Script v2 - Yamen Academy
يُضيف نظام المراحل (Stages) والمسارات (Tracks) إلى قاعدة البيانات.
آمن: ينشئ نسخة احتياطية ويتحقق قبل وبعد التطبيق.
"""
import sqlite3
import shutil
import os
import json
from datetime import datetime

DB_PATH = r"C:\Users\nelt2\yamen_academy\academy.db"
BACKUP_ROOT = r"C:\Users\nelt2\yamen_academy\_backups"

def log(msg, color="white"):
    colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
              "cyan": "\033[96m", "white": "\033[0m"}
    print(f"{colors.get(color, '')}{msg}\033[0m")

# ============= 1) النسخ الاحتياطي =============
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.join(BACKUP_ROOT, f"schema_v2_{ts}")
os.makedirs(backup_dir, exist_ok=True)
shutil.copy2(DB_PATH, os.path.join(backup_dir, "academy.db.bak"))
log(f"✅ نسخة احتياطية: {backup_dir}", "green")

# ============= 2) فتح الاتصال =============
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# فحص الحالة قبل التعديل
cur.execute("SELECT COUNT(*) FROM lessons")
lessons_before = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM students")
students_before = cur.fetchone()[0]
log(f"\n📊 قبل التعديل: lessons={lessons_before}, students={students_before}", "cyan")

# ============= 3) جدول stages =============
log("\n--- إنشاء جدول stages ---", "cyan")
cur.execute("""
CREATE TABLE IF NOT EXISTS stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    name_ar TEXT NOT NULL,
    name_en TEXT NOT NULL,
    description TEXT,
    section_name TEXT,
    order_num REAL NOT NULL DEFAULT 0,
    gatekeeper_threshold INTEGER DEFAULT 70,
    is_active INTEGER DEFAULT 1,
    is_locked_future INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")
log("✅ stages جاهز", "green")

# ============= 4) جدول stage_progress =============
log("\n--- إنشاء جدول stage_progress ---", "cyan")
cur.execute("""
CREATE TABLE IF NOT EXISTS stage_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    stage_id INTEGER NOT NULL,
    status TEXT DEFAULT 'locked',
    lessons_completed INTEGER DEFAULT 0,
    gatekeeper_attempts INTEGER DEFAULT 0,
    gatekeeper_best_score REAL DEFAULT 0,
    gatekeeper_passed INTEGER DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    UNIQUE(student_id, stage_id)
)""")
log("✅ stage_progress جاهز", "green")

# ============= 5) جدول weekly_reviews =============
log("\n--- إنشاء جدول weekly_reviews ---", "cyan")
cur.execute("""
CREATE TABLE IF NOT EXISTS weekly_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    week_number INTEGER NOT NULL,
    review_type TEXT NOT NULL,
    screenshot_file_id TEXT,
    text_content TEXT,
    submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
    approved_by_admin INTEGER DEFAULT 0,
    approved_at TEXT,
    rejected_reason TEXT
)""")
log("✅ weekly_reviews جاهز", "green")

# ============= 6) إضافة أعمدة لـ students =============
log("\n--- توسيع جدول students ---", "cyan")
new_student_cols = [
    ("track", "TEXT DEFAULT 'toefl'"),
    ("target_score", "INTEGER DEFAULT 0"),
    ("current_stage_id", "INTEGER"),
    ("placement_path", "TEXT"),
    ("placement_score", "REAL DEFAULT 0"),
    ("signup_date", "TEXT"),
    ("free_week_number", "INTEGER DEFAULT 1"),
    ("last_review_approved_at", "TEXT"),
    ("subscription_locked_until", "TEXT"),
]
cur.execute("PRAGMA table_info(students)")
existing_cols = {row[1] for row in cur.fetchall()}
for col, definition in new_student_cols:
    if col not in existing_cols:
        try:
            cur.execute(f"ALTER TABLE students ADD COLUMN {col} {definition}")
            log(f"  + {col}", "green")
        except sqlite3.OperationalError as e:
            log(f"  ⚠ {col}: {e}", "yellow")
    else:
        log(f"  = {col} موجود", "yellow")

# ============= 7) إضافة أعمدة لـ lessons =============
log("\n--- توسيع جدول lessons ---", "cyan")
new_lesson_cols = [
    ("stage_id", "INTEGER"),
    ("section_name", "TEXT"),
    ("order_index", "REAL DEFAULT 0"),
]
cur.execute("PRAGMA table_info(lessons)")
existing_cols = {row[1] for row in cur.fetchall()}
for col, definition in new_lesson_cols:
    if col not in existing_cols:
        try:
            cur.execute(f"ALTER TABLE lessons ADD COLUMN {col} {definition}")
            log(f"  + {col}", "green")
        except sqlite3.OperationalError as e:
            log(f"  ⚠ {col}: {e}", "yellow")
    else:
        log(f"  = {col} موجود", "yellow")

# ============= 8) إدراج المراحل الافتراضية =============
log("\n--- إدراج المراحل الافتراضية ---", "cyan")

STAGES_DATA = [
    # Foundation Track (إجباري لمن نتيجته < 50%)
    ("foundation", "F1", "التأسيس - أساسيات القواعد", "Foundation - Basic Grammar",
     "أزمنة، أفعال مساعدة، تركيب الجمل البسيطة", "grammar", 1.0, 70, 1, 0),
    ("foundation", "F2", "التأسيس - مفردات أساسية", "Foundation - Core Vocabulary",
     "500 كلمة الأكثر شيوعاً في TOEFL", "vocabulary", 2.0, 70, 1, 0),
    ("foundation", "F3", "التأسيس - قواعد متقدمة", "Foundation - Advanced Grammar",
     "Conditionals, Passive, Reported Speech", "grammar", 3.0, 70, 1, 0),
    ("foundation", "F4", "التأسيس - قراءة وفهم تمهيدي", "Foundation - Pre-Reading",
     "جمل قصيرة وفقرات تمهيدية", "reading", 4.0, 70, 1, 0),

    # TOEFL Reading
    ("toefl", "TR1", "القراءة - المبتدئ", "Reading - Beginner",
     "المرحلة الأولى للقراءة", "reading", 10.0, 70, 1, 0),
    ("toefl", "TR2", "القراءة - المتوسط", "Reading - Intermediate",
     "المرحلة الثانية للقراءة", "reading", 11.0, 70, 1, 0),
    ("toefl", "TR3", "القراءة - المتقدم", "Reading - Advanced",
     "المرحلة الثالثة للقراءة", "reading", 12.0, 70, 1, 0),
    ("toefl", "TR4", "القراءة - الإتقان", "Reading - Mastery",
     "المرحلة الرابعة للقراءة", "reading", 13.0, 75, 1, 0),

    # TOEFL Listening
    ("toefl", "TL1", "الاستماع - المبتدئ", "Listening - Beginner",
     "محادثات قصيرة وأكاديميات تمهيدية", "listening", 20.0, 70, 1, 0),
    ("toefl", "TL2", "الاستماع - المتوسط", "Listening - Intermediate",
     "محاضرات أكاديمية متوسطة", "listening", 21.0, 70, 1, 0),
    ("toefl", "TL3", "الاستماع - المتقدم", "Listening - Advanced",
     "محاضرات معقدة وأخذ ملاحظات", "listening", 22.0, 70, 1, 0),
    ("toefl", "TL4", "الاستماع - الإتقان", "Listening - Mastery",
     "محاكاة كاملة للامتحان", "listening", 23.0, 75, 1, 0),

    # TOEFL Speaking
    ("toefl", "TS1", "المحادثة - المبتدئ", "Speaking - Beginner",
     "Independent Task 1", "speaking", 30.0, 70, 1, 0),
    ("toefl", "TS2", "المحادثة - المتوسط", "Speaking - Intermediate",
     "Integrated Tasks 2-3", "speaking", 31.0, 70, 1, 0),
    ("toefl", "TS3", "المحادثة - المتقدم", "Speaking - Advanced",
     "Integrated Task 4 + Templates", "speaking", 32.0, 70, 1, 0),
    ("toefl", "TS4", "المحادثة - الإتقان", "Speaking - Mastery",
     "محاكاة كاملة 4 مهام", "speaking", 33.0, 75, 1, 0),

    # TOEFL Writing
    ("toefl", "TW1", "الكتابة - المبتدئ", "Writing - Beginner",
     "بنية الفقرة والمقال", "writing", 40.0, 70, 1, 0),
    ("toefl", "TW2", "الكتابة - المتوسط", "Writing - Intermediate",
     "Integrated Writing Task", "writing", 41.0, 70, 1, 0),
    ("toefl", "TW3", "الكتابة - المتقدم", "Writing - Advanced",
     "Academic Discussion Task", "writing", 42.0, 70, 1, 0),
    ("toefl", "TW4", "الكتابة - الإتقان", "Writing - Mastery",
     "محاكاة كاملة مع تقييم", "writing", 43.0, 75, 1, 0),

    # IELTS (مغلق للمستقبل)
    ("ielts", "IR1", "IELTS Reading 1", "IELTS Reading 1",
     "قريباً", "reading", 100.0, 70, 0, 1),
    ("ielts", "IL1", "IELTS Listening 1", "IELTS Listening 1",
     "قريباً", "listening", 110.0, 70, 0, 1),
]

inserted, skipped = 0, 0
for row in STAGES_DATA:
    track, code, name_ar, name_en, desc, section, order_num, threshold, is_active, is_locked = row
    try:
        cur.execute("""INSERT INTO stages
            (track, code, name_ar, name_en, description, section_name,
             order_num, gatekeeper_threshold, is_active, is_locked_future)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (track, code, name_ar, name_en, desc, section, order_num, threshold, is_active, is_locked))
        inserted += 1
    except sqlite3.IntegrityError:
        skipped += 1

log(f"✅ مراحل مُدرجة: {inserted} | متخطاة (موجودة): {skipped}", "green")

# ============= 9) ربط الدروس الـ12 بمراحل القراءة =============
log("\n--- ربط الدروس بمراحل القراءة ---", "cyan")
cur.execute("SELECT id, lesson_code, phase, skill FROM lessons ORDER BY id")
lessons = cur.fetchall()

# الحصول على معرفات مراحل القراءة
cur.execute("SELECT id, code FROM stages WHERE track='toefl' AND section_name='reading'")
reading_stages = {row[1]: row[0] for row in cur.fetchall()}

linked = 0
for L in lessons:
    lid, code, phase, skill = L["id"], L["lesson_code"], L["phase"] or 1, L["skill"] or "reading"
    # phase 1 → TR1, phase 2 → TR2, phase 3 → TR3
    target_code = f"TR{min(max(int(phase), 1), 3)}"
    stage_id = reading_stages.get(target_code)
    if stage_id:
        cur.execute("""UPDATE lessons SET stage_id=?, section_name=?, order_index=?
                       WHERE id=?""", (stage_id, "reading", float(lid), lid))
        linked += 1

log(f"✅ تم ربط {linked} درس بمراحل القراءة", "green")

# ============= 10) إنشاء فهارس للأداء =============
log("\n--- إنشاء فهارس ---", "cyan")
cur.execute("CREATE INDEX IF NOT EXISTS idx_lessons_stage ON lessons(stage_id, order_index)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_progress_student ON stage_progress(student_id, stage_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_stages_track ON stages(track, order_num)")
log("✅ الفهارس جاهزة", "green")

# ============= 11) Commit =============
conn.commit()

# ============= 12) التحقق النهائي =============
log("\n📊 التحقق النهائي:", "cyan")
cur.execute("SELECT COUNT(*) FROM stages")
log(f"  stages: {cur.fetchone()[0]}", "yellow")
cur.execute("SELECT COUNT(*) FROM lessons WHERE stage_id IS NOT NULL")
log(f"  دروس مرتبطة بمراحل: {cur.fetchone()[0]}", "yellow")
cur.execute("""SELECT s.code, s.name_ar, COUNT(l.id) AS lesson_count
               FROM stages s LEFT JOIN lessons l ON l.stage_id=s.id
               WHERE s.track='toefl' AND s.section_name='reading'
               GROUP BY s.id ORDER BY s.order_num""")
log("\n  مراحل القراءة وعدد دروسها:", "cyan")
for r in cur.fetchall():
    log(f"    {r[0]} - {r[1]}: {r[2]} درس", "white")

# عرض جميع المراحل النشطة
cur.execute("""SELECT code, name_ar, section_name FROM stages
               WHERE is_active=1 AND is_locked_future=0
               ORDER BY order_num""")
log("\n  المراحل النشطة:", "cyan")
for r in cur.fetchall():
    log(f"    {r[0]:6} | {r[2]:12} | {r[1]}", "white")

conn.close()
log(f"\n✅✅ تمت الهجرة بنجاح! النسخة الاحتياطية في: {backup_dir}", "green")
log("الخطوة التالية: شغّل py main.py وأخبرني بالنتيجة للانتقال للحلقة 2 (/start)", "cyan")
