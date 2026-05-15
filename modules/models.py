"""
models.py v17.0 — جميع جداول الأكاديمية
- courses (دورات)  - placement_questions (أسئلة الامتحان)
- placement_results (نتائج)  - subscriptions (باقات)
- billing_plans (خطط الأسعار)  - daily_skills (مهارات يومية)
"""
import os, sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "data", "yamen_academy.db")

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript('''
        -- ═══ ① المستخدمون ═══
        CREATE TABLE IF NOT EXISTS students (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT, first_name TEXT, last_name TEXT,
            email TEXT, phone TEXT,
            xp INTEGER DEFAULT 0, level INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1,
            course_id INTEGER DEFAULT 0,
            placement_done INTEGER DEFAULT 0,
            placement_level TEXT,
            last_active DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ ② الدورات ═══
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT,
            icon TEXT DEFAULT '📚',
            is_active INTEGER DEFAULT 1,
            is_default INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ ③ أسئلة امتحان المستوى ═══
        CREATE TABLE IF NOT EXISTS placement_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL,
            difficulty TEXT DEFAULT 'medium',
            skill_area TEXT DEFAULT 'general',
            time_limit_seconds INTEGER DEFAULT 60,
            points INTEGER DEFAULT 10,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ ④ نتائج الامتحان ═══
        CREATE TABLE IF NOT EXISTS placement_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_questions INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            score_percent REAL DEFAULT 0,
            level TEXT,
            skill_breakdown TEXT,
            completed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ ⑤ خطط الباقات ═══
        CREATE TABLE IF NOT EXISTS billing_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT,
            price_monthly REAL DEFAULT 0,
            price_yearly REAL DEFAULT 0,
            features TEXT,
            icon TEXT DEFAULT '💎',
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ ⑥ اشتراكات الطلاب ═══
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER REFERENCES billing_plans(id),
            plan_name TEXT,
            status TEXT DEFAULT 'pending',
            start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_date DATETIME,
            payment_method TEXT,
            payment_ref TEXT,
            amount_paid REAL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ ⑦ المهارات اليومية ═══
        CREATE TABLE IF NOT EXISTS daily_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            skill_type TEXT NOT NULL,
            task_type TEXT DEFAULT 'text',
            icon TEXT DEFAULT '📝',
            time_limit INTEGER DEFAULT 45,
            is_active INTEGER DEFAULT 1,
            subscription_required INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            telegram_link TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ ⑧ مواد المكتبة ═══
        CREATE TABLE IF NOT EXISTS library_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            item_type TEXT DEFAULT 'pdf',
            url TEXT, telegram_link TEXT,
            icon TEXT DEFAULT '📄',
            category TEXT DEFAULT 'general',
            course_id INTEGER DEFAULT 1,
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ ⑨ الأسئلة العادية ═══
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id INTEGER, question_text TEXT NOT NULL,
            skill_type TEXT NOT NULL,
            option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
            correct_option TEXT,
            points INTEGER DEFAULT 10,
            time_limit INTEGER DEFAULT 45,
            audio_url TEXT,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- ═══ ⑩ بنك الأخطاء + نشاط + صوتيات + كتابة + AI ═══
        CREATE TABLE IF NOT EXISTS error_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, question_id INTEGER, skill_type TEXT,
            correct_count INTEGER DEFAULT 0,
            UNIQUE(user_id, question_id)
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, action TEXT, details TEXT,
            xp_change INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS audio_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, skill_id INTEGER,
            filename TEXT, transcription TEXT,
            ai_score REAL, ai_feedback TEXT,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS writing_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, skill_id INTEGER,
            essay_text TEXT, ai_score REAL, ai_feedback TEXT,
            word_count INTEGER DEFAULT 0,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ai_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE, config_value TEXT,
            description TEXT
        );
    ''')

    # ═══ إدراج البيانات الافتراضية ═══
    # الدورة الافتراضية
    c.execute("INSERT OR IGNORE INTO courses (title, slug, description, icon, is_active, is_default) VALUES (?,?,?,?,?,?)",
              ("دورة التوفل الدولي TOEFL iBT", "toefl-ibt",
               "دورة متكاملة لاجتياز امتحان التوفل الدولي بجميع أقسامه: القراءة، الاستماع، المحادثة، الكتابة",
               "🌍", 1, 1))

    # أسئلة امتحان المستوى الافتراضية
    placement_defaults = [
        ("What is the synonym of 'rapid'?","Slow","Fast","Heavy","Bright","B","easy","vocabulary",45,5),
        ("Choose the correct sentence:","He go to school","He goes to school","He going school","He gone school","B","easy","grammar",45,5),
        ("The lecture mainly discusses...","History","Science","Art","Music","B","medium","listening",60,5),
        ("In paragraph 2, the author suggests that...","True","False","Not Given","Partly True","A","medium","reading",60,5),
        ("If x + 3 = 10, then x = ?","5","6","7","8","C","easy","logic",45,5),
        ("'To kill two birds with one stone' means:","To be cruel","To achieve two things at once","To fail","To hunt","B","medium","idioms",45,5),
        ("Which word is spelled correctly?","Accomodate","Accommodate","Acommodate","Accommodate","B","easy","spelling",30,5),
        ("The word 'ubiquitous' means:","Rare","Everywhere","Underground","Unique","B","hard","vocabulary",60,5),
        ("Rearrange: 'the / on / book / table / the / is'","Book the on table the is","The book is on the table","Table the book is on","On the table book is","B","easy","ordering",45,5),
        ("What is the main purpose of the TOEFL exam?","Math skills","English proficiency","Science knowledge","History","B","easy","general",30,5),
    ]
    for q in placement_defaults:
        c.execute("INSERT OR IGNORE INTO placement_questions (question_text,option_a,option_b,option_c,option_d,correct_option,difficulty,skill_area,time_limit_seconds,points) VALUES (?,?,?,?,?,?,?,?,?,?)", q)

    # باقات الأسعار
    plans = [
        ("الباقة المجانية","free","وصول محدود للمهارات الأساسية وامتحان المستوى",0,0,"امتحان مستوى ✅ | 3 مهارات يومية | المكتبة الأساسية","🆓",1,1),
        ("الباقة الفضية","silver","وصول لجميع المهارات + تمارين إضافية",9.99,89,"كل المجاني + جميع المهارات | تمارين غير محدودة | تقييم AI أسبوعي","🥈",1,2),
        ("الباقة الذهبية","gold","وصول كامل + تقييم AI يومي + جلسات مباشرة",19.99,179,"كل الفضي + AI يومي | جلسات مباشرة | شهادة إتمام","🥇",1,3),
        ("الباقة الماسية","diamond","كل شيء + متابعة شخصية من المدرب",49.99,449,"كل الذهبي + متابعة شخصية | أولوية الدعم | هدايا حصرية","💎",1,4),
    ]
    for p in plans:
        c.execute("INSERT OR IGNORE INTO billing_plans (name,slug,description,price_monthly,price_yearly,features,icon,is_active,sort_order) VALUES (?,?,?,?,?,?,?,?,?)", p)

    conn.commit()
    conn.close()
    print("✅ models.py v17.0 — 14 جدول + بيانات افتراضية")

# ═══ دوال مساعدة ═══
def query_db(query, args=(), one=False):
    conn = get_db()
    try:
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        conn.commit()
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(f"❌ query_db: {e}")
        return None
    finally:
        conn.close()

def execute_db(query, args=()):
    conn = get_db()
    try:
        conn.execute(query, args)
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ execute_db: {e}")
        return False
    finally:
        conn.close()
