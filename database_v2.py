# -*- coding: utf-8 -*-
import sqlite3
import os
from datetime import datetime
from loguru import logger

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db_v2():
    conn = get_db()
    conn.executescript("""
    -- ══ جدول الطلاب الموحد ══
    CREATE TABLE IF NOT EXISTS students (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id         TEXT UNIQUE NOT NULL,
        name                TEXT DEFAULT 'طالب',
        username            TEXT,
        phone               TEXT,
        path_type           TEXT DEFAULT 'toefl',
        level               TEXT DEFAULT 'beginner',
        target_score        REAL DEFAULT 80,
        required_score      REAL DEFAULT 69,
        current_stage       INTEGER DEFAULT 1,
        placement_done      INTEGER DEFAULT 0,
        placement_score     REAL DEFAULT 0,
        is_active           INTEGER DEFAULT 1,
        is_paid             INTEGER DEFAULT 0,
        subscription_type   TEXT DEFAULT 'free',
        package_end         DATE,
        xp                  INTEGER DEFAULT 0,
        streak_days         INTEGER DEFAULT 0,
        last_active         DATE,
        tasks_completed     INTEGER DEFAULT 0,
        mock_exam_score     REAL DEFAULT 0,
        actual_exam_date    DATE,
        free_week           INTEGER DEFAULT 1,
        review_submitted    INTEGER DEFAULT 0,
        post_submitted      INTEGER DEFAULT 0,
        book_activated      INTEGER DEFAULT 0,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ══ تقدم المهارات ══
    CREATE TABLE IF NOT EXISTS user_skills_progress (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id     TEXT UNIQUE NOT NULL,
        reading_xp      INTEGER DEFAULT 0,
        listening_xp    INTEGER DEFAULT 0,
        speaking_xp     INTEGER DEFAULT 0,
        writing_xp      INTEGER DEFAULT 0,
        reading_pct     REAL DEFAULT 0,
        listening_pct   REAL DEFAULT 0,
        speaking_pct    REAL DEFAULT 0,
        writing_pct     REAL DEFAULT 0,
        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ══ الدروس ══
    CREATE TABLE IF NOT EXISTS lessons (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        stage           INTEGER DEFAULT 1,
        order_num       INTEGER DEFAULT 1,
        title           TEXT NOT NULL,
        skill_type      TEXT DEFAULT 'reading',
        content         TEXT,
        vocabulary      TEXT,
        grammar_rule    TEXT,
        audio_url       TEXT,
        is_active       INTEGER DEFAULT 1,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ══ الأسئلة ══
    CREATE TABLE IF NOT EXISTS questions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id       INTEGER,
        stage           INTEGER DEFAULT 1,
        question_type   TEXT DEFAULT 'mcq',
        skill_type      TEXT DEFAULT 'reading',
        question_text   TEXT NOT NULL,
        option_a        TEXT,
        option_b        TEXT,
        option_c        TEXT,
        option_d        TEXT,
        correct_answer  TEXT,
        explanation     TEXT,
        xp_reward       INTEGER DEFAULT 10,
        is_placement    INTEGER DEFAULT 0,
        is_active       INTEGER DEFAULT 1,
        FOREIGN KEY (lesson_id) REFERENCES lessons(id)
    );

    -- ══ امتحان تحديد المستوى ══
    CREATE TABLE IF NOT EXISTS placement_results (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id     TEXT NOT NULL,
        score           REAL DEFAULT 0,
        total_questions INTEGER DEFAULT 20,
        correct_answers INTEGER DEFAULT 0,
        level_assigned  TEXT,
        taken_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ══ بنك أخطاء الطالب ══
    CREATE TABLE IF NOT EXISTS student_error_bank (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id     TEXT NOT NULL,
        question_id     INTEGER NOT NULL,
        error_count     INTEGER DEFAULT 1,
        last_attempted  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(telegram_id, question_id)
    );

    -- ══ المهام اليومية ══
    CREATE TABLE IF NOT EXISTS daily_missions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        title           TEXT NOT NULL,
        description     TEXT,
        skill_type      TEXT DEFAULT 'reading',
        xp_reward       INTEGER DEFAULT 20,
        mission_date    DATE,
        is_active       INTEGER DEFAULT 1,
        created_by      TEXT DEFAULT 'admin',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ══ إنجازات الطالب في المهام ══
    CREATE TABLE IF NOT EXISTS student_missions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id     TEXT NOT NULL,
        mission_id      INTEGER NOT NULL,
        completed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(telegram_id, mission_id)
    );

    -- ══ الاشتراكات ══
    CREATE TABLE IF NOT EXISTS subscriptions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id     TEXT NOT NULL,
        plan_key        TEXT,
        plan_name       TEXT,
        start_date      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_date        TIMESTAMP,
        is_active       INTEGER DEFAULT 1
    );

    -- ══ الدفعات ══
    CREATE TABLE IF NOT EXISTS payments (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id     TEXT NOT NULL,
        plan_key        TEXT,
        plan_name       TEXT,
        amount          REAL DEFAULT 0,
        status          TEXT DEFAULT 'pending',
        receipt_photo_id TEXT,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ══ معايير التصحيح ══
    CREATE TABLE IF NOT EXISTS essay_grading_rules (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_name      TEXT NOT NULL,
        skill_type      TEXT DEFAULT 'writing',
        target_vocab    TEXT,
        academic_connectors TEXT,
        forbidden_words TEXT,
        vocab_points    INTEGER DEFAULT 2,
        connector_points INTEGER DEFAULT 3,
        penalty_points  INTEGER DEFAULT 1,
        is_active       INTEGER DEFAULT 1,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ══ تقديمات الكتابة ══
    CREATE TABLE IF NOT EXISTS writing_submissions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id     TEXT NOT NULL,
        topic_id        INTEGER,
        essay_text      TEXT,
        score           REAL DEFAULT 0,
        feedback        TEXT,
        vocab_matches   TEXT,
        connector_matches TEXT,
        forbidden_found TEXT,
        submitted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ══ كودات الكتاب ══
    CREATE TABLE IF NOT EXISTS book_codes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        code            TEXT UNIQUE NOT NULL,
        duration_days   INTEGER DEFAULT 90,
        is_used         INTEGER DEFAULT 0,
        used_by         TEXT,
        used_at         TIMESTAMP
    );

    -- ══ سجل XP ══
    CREATE TABLE IF NOT EXISTS xp_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id     TEXT NOT NULL,
        amount          INTEGER,
        skill_type      TEXT,
        reason          TEXT,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ══ إعدادات النظام ══
    CREATE TABLE IF NOT EXISTS system_settings (
        key             TEXT PRIMARY KEY,
        value           TEXT,
        description     TEXT,
        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ══ إعدادات افتراضية ══
    INSERT OR IGNORE INTO system_settings (key, value, description) VALUES
        ('min_quiz_pass', '70', 'الحد الأدنى لاجتياز الكويز'),
        ('min_stage_pass', '75', 'الحد الأدنى لاجتياز مرحلة'),
        ('xp_lesson_open', '20', 'XP عند فتح درس'),
        ('xp_quiz_correct', '15', 'XP عند إجابة صحيحة'),
        ('xp_streak_7days', '50', 'XP عند 7 أيام متتالية'),
        ('xp_popup_correct', '10', 'XP عند إجابة صحيحة مفاجئة'),
        ('xp_penalty_48h', '15', 'خصم XP بعد 48 ساعة غياب'),
        ('graduation_xp', '500', 'XP المطلوب للتخرج'),
        ('graduation_tasks', '10', 'مهام مطلوبة للتخرج'),
        ('graduation_streak', '3', 'أيام streak مطلوبة للتخرج'),
        ('force_sub_channel', '', 'معرف قناة الاشتراك الإجباري'),
        ('morning_msg_time', '09:00', 'وقت الرسالة الصباحية'),
        ('toefl_active', '1', 'مسار TOEFL مفعّل'),
        ('ielts_active', '0', 'مسار IELTS مفعّل');
    """)
    conn.commit()
    conn.close()
    logger.info("database_v2 initialized")

# ══ SETTINGS ══════════════════════════════════════════════════════════════

def get_setting(key, default=""):
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT value FROM system_settings WHERE key=?", (key,)
        ).fetchone()
        conn.close()
        return row["value"] if row else default
    except Exception as e:
        logger.error(f"get_setting {key}: {e}")
        return default

def set_setting(key, value, description=""):
    try:
        conn = get_db()
        conn.execute(
            """INSERT INTO system_settings (key, value, description, updated_at)
               VALUES (?,?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value,
               updated_at=CURRENT_TIMESTAMP""",
            (key, str(value), description)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"set_setting {key}: {e}")

# ══ STUDENTS ══════════════════════════════════════════════════════════════

def get_student(telegram_id):
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM students WHERE telegram_id=? LIMIT 1",
            (str(telegram_id),)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"get_student: {e}")
        return None

def create_student(telegram_id, name, username=None, path_type="toefl",
                   target_score=80, required_score=69):
    try:
        conn = get_db()
        conn.execute(
            """INSERT OR IGNORE INTO students
               (telegram_id, name, username, path_type, target_score,
                required_score, last_active)
               VALUES (?,?,?,?,?,?,date('now'))""",
            (str(telegram_id), name, username, path_type,
             target_score, required_score)
        )
        conn.execute(
            """INSERT OR IGNORE INTO user_skills_progress (telegram_id)
               VALUES (?)""", (str(telegram_id),)
        )
        conn.commit()
        conn.close()
        return get_student(telegram_id)
    except Exception as e:
        logger.error(f"create_student: {e}")
        return None

def activate_paid(telegram_id):
    try:
        conn = get_db()
        conn.execute(
            "UPDATE students SET is_paid=1, is_active=1 WHERE telegram_id=?",
            (str(telegram_id),)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"activate_paid: {e}")
        return False

def get_all_students_admin():
    try:
        conn = get_db()
        rows = conn.execute(
            """SELECT s.*, sp.reading_xp, sp.listening_xp,
                      sp.speaking_xp, sp.writing_xp
               FROM students s
               LEFT JOIN user_skills_progress sp ON s.telegram_id=sp.telegram_id
               ORDER BY s.xp DESC"""
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"get_all_students_admin: {e}")
        return []

# ══ XP & SKILLS ══════════════════════════════════════════════════════════

def add_xp(telegram_id, amount, skill_type="general", reason=""):
    try:
        conn = get_db()
        conn.execute(
            "UPDATE students SET xp=MAX(0,xp+?) WHERE telegram_id=?",
            (amount, str(telegram_id))
        )
        skill_col = {
            "reading": "reading_xp",
            "listening": "listening_xp",
            "speaking": "speaking_xp",
            "writing": "writing_xp"
        }.get(skill_type)
        if skill_col:
            conn.execute(
                f"""INSERT INTO user_skills_progress (telegram_id, {skill_col})
                    VALUES (?, ?)
                    ON CONFLICT(telegram_id) DO UPDATE
                    SET {skill_col}={skill_col}+excluded.{skill_col},
                    updated_at=CURRENT_TIMESTAMP""",
                (str(telegram_id), max(0, amount))
            )
        conn.execute(
            """INSERT INTO xp_log (telegram_id, amount, skill_type, reason)
               VALUES (?,?,?,?)""",
            (str(telegram_id), amount, skill_type, reason)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"add_xp: {e}")

def get_skills_progress(telegram_id):
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM user_skills_progress WHERE telegram_id=?",
            (str(telegram_id),)
        ).fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception as e:
        logger.error(f"get_skills_progress: {e}")
        return {}

# ══ GRADUATION CHECK ══════════════════════════════════════════════════════

def check_graduation(telegram_id):
    student = get_student(telegram_id)
    if not student:
        return False, "الطالب غير موجود"

    required_score = student.get("required_score", 69)
    mock_pass_score = required_score + 10
    needed_xp = int(get_setting("graduation_xp", "500"))
    needed_tasks = int(get_setting("graduation_tasks", "10"))
    needed_streak = int(get_setting("graduation_streak", "3"))

    checks = [
        (student.get("is_paid", 0) == 1,
         "يجب تفعيل الاشتراك المدفوع"),
        (student.get("xp", 0) >= needed_xp,
         f"يجب تحقيق {needed_xp} XP (لديك {student.get('xp',0)})"),
        (student.get("tasks_completed", 0) >= needed_tasks,
         f"يجب إنهاء {needed_tasks} مهام (أنهيت {student.get('tasks_completed',0)})"),
        (student.get("streak_days", 0) >= needed_streak,
         f"يجب الالتزام {needed_streak} أيام متتالية"),
        (student.get("mock_exam_score", 0) >= mock_pass_score,
         f"يجب تجاوز {mock_pass_score}% في الامتحان التجريبي"),
    ]

    failed = [msg for ok, msg in checks if not ok]
    if failed:
        return False, "\n".join([f"❌ {m}" for m in failed])
    return True, "✅ مبروك! أنت مؤهل للتخرج"

# ══ GRADING ENGINE ════════════════════════════════════════════════════════

def grade_essay(telegram_id, essay_text, topic_id=None):
    try:
        conn = get_db()
        if topic_id:
            rule = conn.execute(
                "SELECT * FROM essay_grading_rules WHERE id=? AND is_active=1",
                (topic_id,)
            ).fetchone()
        else:
            rule = conn.execute(
                "SELECT * FROM essay_grading_rules WHERE is_active=1 LIMIT 1"
            ).fetchone()
        conn.close()

        if not rule:
            return {
                "score": 0,
                "feedback": "لا توجد معايير تصحيح محددة لهذا الموضوع",
                "vocab_matches": [],
                "connector_matches": [],
                "forbidden_found": []
            }

        text_lower = essay_text.lower()
        score = 0
        vocab_matches = []
        connector_matches = []
        forbidden_found = []

        vocab_points = rule["vocab_points"] or 2
        connector_points = rule["connector_points"] or 3
        penalty_points = rule["penalty_points"] or 1

        if rule["target_vocab"]:
            for word in rule["target_vocab"].split(","):
                word = word.strip().lower()
                if word and word in text_lower:
                    vocab_matches.append(word)
                    score += vocab_points

        if rule["academic_connectors"]:
            for conn_word in rule["academic_connectors"].split(","):
                conn_word = conn_word.strip().lower()
                if conn_word and conn_word in text_lower:
                    connector_matches.append(conn_word)
                    score += connector_points

        if rule["forbidden_words"]:
            for bad in rule["forbidden_words"].split(","):
                bad = bad.strip().lower()
                if bad and bad in text_lower:
                    forbidden_found.append(bad)
                    score -= penalty_points

        score = max(0, min(100, score))
        words = len(essay_text.split())

        feedback = (
            f"📝 <b>تقييم كتابتك:</b>\n\n"
            f"📊 الدرجة: <b>{score}/100</b>\n"
            f"📏 عدد الكلمات: <b>{words}</b>\n\n"
        )
        if vocab_matches:
            feedback += f"✅ مفردات أكاديمية ممتازة: {', '.join(vocab_matches)}\n"
        if connector_matches:
            feedback += f"🔗 روابط متقدمة: {', '.join(connector_matches)}\n"
        if forbidden_found:
            feedback += f"⚠️ تجنب تكرار: {', '.join(forbidden_found)}\n"
        if score >= 80:
            feedback += "\n🌟 ممتاز! أسلوبك الأكاديمي قوي جداً"
        elif score >= 60:
            feedback += "\n👍 جيد! ركز على إضافة روابط أكاديمية أكثر"
        else:
            feedback += "\n💪 استمر في التدرب وأضف مفردات أكاديمية"

        db2 = get_db()
        db2.execute(
            """INSERT INTO writing_submissions
               (telegram_id, topic_id, essay_text, score, feedback,
                vocab_matches, connector_matches, forbidden_found)
               VALUES (?,?,?,?,?,?,?,?)""",
            (str(telegram_id), topic_id, essay_text, score, feedback,
             ",".join(vocab_matches), ",".join(connector_matches),
             ",".join(forbidden_found))
        )
        db2.commit()
        db2.close()

        add_xp(telegram_id, min(score // 10, 10), "writing", "essay grading")

        return {
            "score": score,
            "feedback": feedback,
            "vocab_matches": vocab_matches,
            "connector_matches": connector_matches,
            "forbidden_found": forbidden_found
        }
    except Exception as e:
        logger.error(f"grade_essay: {e}")
        return {"score": 0, "feedback": f"خطأ: {e}",
                "vocab_matches": [], "connector_matches": [],
                "forbidden_found": []}

# ══ PLACEMENT ════════════════════════════════════════════════════════════

def get_placement_questions():
    try:
        conn = get_db()
        rows = conn.execute(
            """SELECT * FROM questions
               WHERE is_placement=1 AND is_active=1
               ORDER BY RANDOM() LIMIT 20"""
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"get_placement_questions: {e}")
        return []

def save_placement_result(telegram_id, score, correct, total):
    try:
        level = "advanced" if score >= 70 else \
                "intermediate" if score >= 50 else "beginner"
        conn = get_db()
        conn.execute(
            """INSERT INTO placement_results
               (telegram_id, score, total_questions, correct_answers, level_assigned)
               VALUES (?,?,?,?,?)""",
            (str(telegram_id), score, total, correct, level)
        )
        conn.execute(
            """UPDATE students SET placement_done=1, placement_score=?,
               level=?, current_stage=?
               WHERE telegram_id=?""",
            (score, level, 1 if score < 50 else 2, str(telegram_id))
        )
        conn.commit()
        conn.close()
        return level
    except Exception as e:
        logger.error(f"save_placement_result: {e}")
        return "beginner"

# ══ DAILY MISSIONS ════════════════════════════════════════════════════════

def get_today_mission():
    try:
        conn = get_db()
        today = datetime.now().date().isoformat()
        row = conn.execute(
            """SELECT * FROM daily_missions
               WHERE (mission_date=? OR mission_date IS NULL)
               AND is_active=1 ORDER BY id DESC LIMIT 1""",
            (today,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"get_today_mission: {e}")
        return None

def complete_mission(telegram_id, mission_id):
    try:
        conn = get_db()
        conn.execute(
            """INSERT OR IGNORE INTO student_missions
               (telegram_id, mission_id) VALUES (?,?)""",
            (str(telegram_id), mission_id)
        )
        conn.execute(
            "UPDATE students SET tasks_completed=tasks_completed+1 WHERE telegram_id=?",
            (str(telegram_id),)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"complete_mission: {e}")
        return False

# ══ LEADERBOARD ══════════════════════════════════════════════════════════

def get_leaderboard_data(limit=10):
    try:
        conn = get_db()
        rows = conn.execute(
            """SELECT telegram_id, name, xp, streak_days, level
               FROM students ORDER BY xp DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"get_leaderboard_data: {e}")
        return []

def get_student_rank(telegram_id):
    try:
        conn = get_db()
        student = conn.execute(
            "SELECT xp FROM students WHERE telegram_id=?",
            (str(telegram_id),)
        ).fetchone()
        if not student:
            conn.close()
            return None, 0
        rank = conn.execute(
            "SELECT COUNT(*)+1 as r FROM students WHERE xp>?",
            (student["xp"],)
        ).fetchone()["r"]
        conn.close()
        return rank, student["xp"]
    except Exception as e:
        logger.error(f"get_student_rank: {e}")
        return None, 0

# ══ SUBSCRIPTIONS ════════════════════════════════════════════════════════

def get_subscription(telegram_id):
    try:
        conn = get_db()
        row = conn.execute(
            """SELECT * FROM subscriptions
               WHERE telegram_id=? AND is_active=1
               ORDER BY end_date DESC LIMIT 1""",
            (str(telegram_id),)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"get_subscription: {e}")
        return None

def activate_subscription(telegram_id, plan_key, plan_name, days):
    from datetime import timedelta
    try:
        conn = get_db()
        end_date = (datetime.now() + timedelta(days=days)).isoformat()
        conn.execute(
            "UPDATE subscriptions SET is_active=0 WHERE telegram_id=?",
            (str(telegram_id),)
        )
        conn.execute(
            """INSERT INTO subscriptions
               (telegram_id, plan_key, plan_name, end_date)
               VALUES (?,?,?,?)""",
            (str(telegram_id), plan_key, plan_name, end_date)
        )
        conn.execute(
            """UPDATE students SET is_active=1, is_paid=1,
               subscription_type=?, package_end=?
               WHERE telegram_id=?""",
            (plan_key, end_date, str(telegram_id))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"activate_subscription: {e}")

def create_payment(telegram_id, plan_key, plan_name, amount, receipt_photo_id):
    try:
        conn = get_db()
        conn.execute(
            """INSERT INTO payments
               (telegram_id, plan_key, plan_name, amount, receipt_photo_id)
               VALUES (?,?,?,'pending',?)""",
            (str(telegram_id), plan_key, plan_name, amount, receipt_photo_id)
        )
        pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()
        return pid
    except Exception as e:
        logger.error(f"create_payment: {e}")
        return None

def approve_payment(payment_id, plan_key, plan_name, telegram_id, days):
    try:
        conn = get_db()
        conn.execute(
            "UPDATE payments SET status='approved' WHERE id=?", (payment_id,)
        )
        conn.commit()
        conn.close()
        activate_subscription(telegram_id, plan_key, plan_name, days)
    except Exception as e:
        logger.error(f"approve_payment: {e}")
