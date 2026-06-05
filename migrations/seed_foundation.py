# -*- coding: utf-8 -*-
"""
Foundation Seed - يُشغَّل تلقائياً عند بدء التطبيق.
آمن (idempotent): لا يُكرّر شيئاً موجوداً، لا يلمس بيانات الطلاب.
"""
import sqlite3, json, os

def _db_path():
    return os.environ.get("DB_PATH") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "academy.db")

def _safe_alter(cur, table, col, ddl):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if col not in cols:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
            print(f"  [+] {table}.{col}")
        except Exception as e:
            print(f"  [skip] {table}.{col}: {e}")

def run():
    DB = _db_path()
    if not os.path.exists(DB):
        print(f"[seed_foundation] DB not found: {DB} - skipping")
        return
    print(f"[seed_foundation] DB: {DB}")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ===== 1) ALTER TABLES =====
    print("[seed_foundation] altering tables...")
    _safe_alter(cur, "lesson_questions", "set_number",     "set_number INTEGER DEFAULT 1")
    _safe_alter(cur, "lesson_questions", "explanation_ar", "explanation_ar TEXT")
    _safe_alter(cur, "lesson_questions", "translation_ar", "translation_ar TEXT")
    _safe_alter(cur, "lesson_attempts",  "set_number",     "set_number INTEGER DEFAULT 1")
    _safe_alter(cur, "error_bank", "lesson_id",            "lesson_id INTEGER")
    _safe_alter(cur, "error_bank", "times_retried",        "times_retried INTEGER DEFAULT 0")
    _safe_alter(cur, "error_bank", "times_correct_after",  "times_correct_after INTEGER DEFAULT 0")
    _safe_alter(cur, "error_bank", "is_mastered",          "is_mastered INTEGER DEFAULT 0")
    _safe_alter(cur, "error_bank", "explanation_ar",       "explanation_ar TEXT")
    _safe_alter(cur, "error_bank", "concept_ar",           "concept_ar TEXT")

    # ===== 2) إنشاء F1 stage إذا غير موجود =====
    cur.execute("SELECT id FROM stages WHERE code='F1'")
    row = cur.fetchone()
    if row:
        F1_ID = row["id"]
        print(f"[seed_foundation] F1 stage exists id={F1_ID}")
    else:
        cur.execute("""INSERT INTO stages (code, name_ar, track, path, order_num, is_active)
                       VALUES ('F1', 'التأسيس - أساسيات القواعد', 'foundation', 'foundation', 1, 1)""")
        F1_ID = cur.lastrowid
        print(f"[seed_foundation] F1 stage created id={F1_ID}")

    # ===== 3) F1-L01 و F1-L02 =====
    cur.execute("SELECT lesson_code FROM lessons WHERE stage_id=? AND lesson_code IN ('F1-L01','F1-L02')", (F1_ID,))
    existing = {r["lesson_code"] for r in cur.fetchall()}

    LESSONS = _foundation_lessons_data()
    for L in LESSONS:
        if L["code"] in existing:
            print(f"  [skip] {L['code']} already exists")
            continue
        ej = json.dumps({"examples": L["examples"], "content_html": L["content_html"]}, ensure_ascii=False)
        cur.execute("""INSERT INTO lessons
            (stage_id, title, title_ar, content, skill, xp_reward, timer_minutes,
             order_index, is_active, pass_score, lesson_code, explanation_json)
            VALUES (?, ?, ?, ?, 'grammar', ?, ?, ?, 1, 70, ?, ?)""",
            (F1_ID, L["title_ar"], L["title_ar"], L["content_html"],
             L["xp"], L["timer"], L["order"], L["code"], ej))
        lid = cur.lastrowid
        for i, q in enumerate(L["questions"], 1):
            opts_json = json.dumps(q["options"], ensure_ascii=False)
            cur.execute("""INSERT INTO lesson_questions
                (lesson_id, q_id, q_type, question, options_json, correct_answer,
                 explanation, explanation_ar, translation_ar, set_number, order_num, concept)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (lid, f"{L['code']}-Q{i}", q["q_type"], q["question"], opts_json,
                 q["correct"], q["exp"], q["exp"], q.get("trans",""), q["set"], i, L["concept"]))
        print(f"  [+] {L['code']} id={lid} with {len(L['questions'])} questions")

    conn.commit()
    conn.close()
    print("[seed_foundation] done")


def _foundation_lessons_data():
    L01_HTML = """<h3>الهدف</h3><p>تعلّم الضمائر الإنجليزية الأساسية وكيفية استخدام فعل to be.</p>
<h3>1) الضمائر الشخصية</h3>
<table><tr><th>الضمير</th><th>المعنى</th><th>مثال</th></tr>
<tr><td>I</td><td>أنا</td><td>I am a student.</td></tr>
<tr><td>You</td><td>أنت/أنتم</td><td>You are kind.</td></tr>
<tr><td>He</td><td>هو</td><td>He is a doctor.</td></tr>
<tr><td>She</td><td>هي</td><td>She is happy.</td></tr>
<tr><td>It</td><td>هو/هي (غير عاقل)</td><td>It is a book.</td></tr>
<tr><td>We</td><td>نحن</td><td>We are friends.</td></tr>
<tr><td>They</td><td>هم</td><td>They are teachers.</td></tr></table>
<h3>2) to be (am/is/are)</h3>
<table><tr><th>الضمير</th><th>الفعل</th><th>الاختصار</th></tr>
<tr><td>I</td><td>am</td><td>I'm</td></tr>
<tr><td>He/She/It</td><td>is</td><td>He's / She's / It's</td></tr>
<tr><td>You/We/They</td><td>are</td><td>You're / We're / They're</td></tr></table>
<h3>3) النفي والسؤال</h3>
<ul><li>I am not = I'm not</li><li>He is not = He isn't</li><li>They are not = They aren't</li>
<li>Are you tired? / Is she a doctor?</li></ul>
<div class="warn">خطأ شائع: لا تقل "I are" أو "He are".</div>"""

    L01_EX = [
        {"en":"I am a student.","ar":"أنا طالب."},
        {"en":"She is my sister.","ar":"هي أختي."},
        {"en":"We are from Jordan.","ar":"نحن من الأردن."},
        {"en":"They are not at home.","ar":"هم ليسوا في البيت."},
        {"en":"Is he your teacher?","ar":"هل هو معلمك؟"},
    ]
    L01_Q = [
        {"set":1,"q_type":"mcq","question":"___ am a doctor.","options":["He","I","She","They"],"correct":"B","exp":"الضمير I يأخذ am.","trans":"___ أنا طبيب."},
        {"set":1,"q_type":"mcq","question":"She ___ my friend.","options":["am","is","are","be"],"correct":"B","exp":"He/She/It تأخذ is.","trans":"هي ___ صديقتي."},
        {"set":1,"q_type":"mcq","question":"We ___ happy today.","options":["am","is","are","were"],"correct":"C","exp":"We/You/They تأخذ are.","trans":"نحن ___ سعداء."},
        {"set":1,"q_type":"mcq","question":"اختر الجملة الصحيحة:","options":["He am a teacher.","He is a teacher.","He are a teacher.","He be a teacher."],"correct":"B","exp":"He تأخذ is.","trans":""},
        {"set":1,"q_type":"mcq","question":"___ they your brothers?","options":["Am","Is","Are","Be"],"correct":"C","exp":"They تأخذ are.","trans":"___ هم إخوتك؟"},
        {"set":1,"q_type":"mcq","question":"اختر النفي لـ 'She is here':","options":["She not is here.","She is no here.","She isn't here.","She don't is here."],"correct":"C","exp":"is + not = isn't.","trans":""},
        {"set":1,"q_type":"mcq","question":"It ___ a beautiful day.","options":["am","is","are","do"],"correct":"B","exp":"It تأخذ is.","trans":"إنه يوم جميل."},
        {"set":1,"q_type":"mcq","question":"اختصار 'You are':","options":["You's","You're","Youre","You'r"],"correct":"B","exp":"You're.","trans":""},
        {"set":2,"q_type":"mcq","question":"My parents ___ very kind.","options":["am","is","are","be"],"correct":"C","exp":"parents جمع = They → are.","trans":"والداي ___ لطيفان."},
        {"set":2,"q_type":"mcq","question":"___ I late?","options":["Am","Is","Are","Be"],"correct":"A","exp":"I → Am.","trans":"هل ___ متأخر؟"},
        {"set":2,"q_type":"mcq","question":"The cat ___ on the chair.","options":["am","is","are","do"],"correct":"B","exp":"The cat = It → is.","trans":"القطة ___ على الكرسي."},
        {"set":2,"q_type":"mcq","question":"اختر الجملة الخاطئة:","options":["I am tired.","We are ready.","He are smart.","They are here."],"correct":"C","exp":"He تأخذ is.","trans":""},
        {"set":2,"q_type":"mcq","question":"You ___ my best friend.","options":["am","is","are","be"],"correct":"C","exp":"You دائماً are.","trans":"أنت ___ صديقي."},
        {"set":2,"q_type":"mcq","question":"النفي لـ 'They are angry':","options":["They aren't angry.","They isn't angry.","They not are angry.","They no are angry."],"correct":"A","exp":"are+not=aren't.","trans":""},
        {"set":2,"q_type":"mcq","question":"Ahmed and Sara ___ in class.","options":["am","is","are","be"],"correct":"C","exp":"شخصان = جمع → are.","trans":"أحمد وسارة ___ في الصف."},
        {"set":2,"q_type":"mcq","question":"اختصار 'She is not':","options":["She'snt","She isn't","She not's","Shen't"],"correct":"B","exp":"isn't.","trans":""},
        {"set":3,"q_type":"mcq","question":"___ your father a doctor?","options":["Am","Is","Are","Be"],"correct":"B","exp":"father = He → Is.","trans":"هل ___ والدك طبيباً؟"},
        {"set":3,"q_type":"mcq","question":"The students ___ from different countries.","options":["am","is","are","does"],"correct":"C","exp":"students جمع → are.","trans":"الطلاب ___ من بلاد مختلفة."},
        {"set":3,"q_type":"mcq","question":"ترجمة 'نحن لسنا متعبين':","options":["We not tired.","We aren't tired.","We no tired.","We don't tired."],"correct":"B","exp":"We aren't.","trans":""},
        {"set":3,"q_type":"mcq","question":"My sister and I ___ best friends.","options":["am","is","are","be"],"correct":"C","exp":"sister and I = We → are.","trans":"أختي وأنا ___ أصدقاء."},
        {"set":3,"q_type":"mcq","question":"___ it cold outside?","options":["Am","Is","Are","Does"],"correct":"B","exp":"it → Is.","trans":"هل ___ بارد بالخارج؟"},
        {"set":3,"q_type":"mcq","question":"اختر الصحيحة:","options":["I'm not hungry.","I amn't hungry.","I not am hungry.","I no hungry."],"correct":"A","exp":"I'm not (لا يوجد amn't).","trans":""},
        {"set":3,"q_type":"mcq","question":"This book ___ very interesting.","options":["am","is","are","do"],"correct":"B","exp":"This book = It → is.","trans":"هذا الكتاب ___ ممتع."},
        {"set":3,"q_type":"mcq","question":"السؤال لـ 'You are a teacher':","options":["You are a teacher?","Are you a teacher?","Is you a teacher?","Do you a teacher?"],"correct":"B","exp":"Are you...?","trans":""},
    ]

    L02_HTML = """<h3>الهدف</h3><p>تعلّم زمن المضارع البسيط للعادات والحقائق العامة.</p>
<h3>1) متى نستخدم Simple Present؟</h3>
<ul><li>العادات اليومية: I drink coffee every morning.</li>
<li>الحقائق العامة: The sun rises in the east.</li>
<li>الجدول الدائم: The train leaves at 7 AM.</li>
<li>المشاعر: I love my family.</li></ul>
<h3>2) قاعدة التصريف</h3>
<table><tr><th>الضمير</th><th>الفعل</th><th>مثال</th></tr>
<tr><td>I/You/We/They</td><td>بدون تغيير</td><td>I play</td></tr>
<tr><td>He/She/It</td><td>+s أو +es أو +ies</td><td>He plays</td></tr></table>
<h3>3) متى نضيف ماذا؟</h3>
<table><tr><th>القاعدة</th><th>مثال</th></tr>
<tr><td>أغلب الأفعال → +s</td><td>work→works</td></tr>
<tr><td>ينتهي بـ s,sh,ch,x,o → +es</td><td>watch→watches, go→goes</td></tr>
<tr><td>ساكن + y → ies</td><td>study→studies</td></tr>
<tr><td>متحرك + y → +s</td><td>play→plays</td></tr></table>
<h3>4) كلمات دلالية</h3>
<ul><li>every day, always, usually, often, sometimes, never</li></ul>
<div class="warn">خطأ شائع للعرب: نسيان s مع He/She. قل "He plays" وليس "He play".</div>"""

    L02_EX = [
        {"en":"I drink coffee every morning.","ar":"أشرب القهوة كل صباح."},
        {"en":"She studies English at university.","ar":"هي تدرس الإنجليزية في الجامعة."},
        {"en":"He watches TV after dinner.","ar":"هو يشاهد التلفاز بعد العشاء."},
        {"en":"We play football on Fridays.","ar":"نلعب كرة القدم أيام الجمعة."},
        {"en":"The sun rises in the east.","ar":"الشمس تشرق من الشرق."},
    ]
    L02_Q = [
        {"set":1,"q_type":"mcq","question":"She ___ English every day.","options":["study","studies","studys","studyies"],"correct":"B","exp":"ساكن+y → ies.","trans":"هي ___ الإنجليزية يومياً."},
        {"set":1,"q_type":"mcq","question":"I ___ football on weekends.","options":["play","plays","playes","playies"],"correct":"A","exp":"I بدون s.","trans":"أنا ___ كرة القدم."},
        {"set":1,"q_type":"mcq","question":"He ___ TV after work.","options":["watch","watchs","watches","watchies"],"correct":"C","exp":"watch ينتهي بـ ch → es.","trans":"هو ___ التلفاز."},
        {"set":1,"q_type":"mcq","question":"They ___ in a small house.","options":["live","lives","livees","living"],"correct":"A","exp":"They بدون s.","trans":"هم ___ في بيت صغير."},
        {"set":1,"q_type":"mcq","question":"My father ___ to work.","options":["go","goes","gos","going"],"correct":"B","exp":"go ينتهي بـ o → es.","trans":"والدي ___ إلى العمل."},
        {"set":1,"q_type":"mcq","question":"اختر الصحيحة:","options":["He play tennis.","He plays tennis.","He playes tennis.","He playing tennis."],"correct":"B","exp":"He → plays.","trans":""},
        {"set":1,"q_type":"mcq","question":"The baby ___ when hungry.","options":["cry","cries","crys","cryes"],"correct":"B","exp":"cry → cries.","trans":"الطفل ___ عندما يجوع."},
        {"set":1,"q_type":"mcq","question":"We ___ Arabic at home.","options":["speak","speaks","speakes","speaking"],"correct":"A","exp":"We بدون s.","trans":"نحن ___ العربية."},
        {"set":2,"q_type":"mcq","question":"My sister ___ to music.","options":["listen","listens","listenes","listening"],"correct":"B","exp":"sister=She → listens.","trans":"أختي ___ للموسيقى."},
        {"set":2,"q_type":"mcq","question":"The teacher ___ the lesson.","options":["explain","explains","explaines","explainies"],"correct":"B","exp":"teacher = He/She → s.","trans":"المعلم ___ الدرس."},
        {"set":2,"q_type":"mcq","question":"Children ___ to play.","options":["like","likes","likees","liking"],"correct":"A","exp":"Children جمع.","trans":"الأطفال ___ اللعب."},
        {"set":2,"q_type":"mcq","question":"He ___ his car every Sunday.","options":["wash","washs","washes","washies"],"correct":"C","exp":"wash → es.","trans":"هو ___ سيارته."},
        {"set":2,"q_type":"mcq","question":"اختر الخاطئة:","options":["I work hard.","She works hard.","They works hard.","He works hard."],"correct":"C","exp":"They بدون s.","trans":""},
        {"set":2,"q_type":"mcq","question":"The boy ___ his bicycle.","options":["ride","rides","ridees","riding"],"correct":"B","exp":"The boy=He → rides.","trans":"الولد ___ دراجته."},
        {"set":2,"q_type":"mcq","question":"My friend ___ to fix it.","options":["try","tries","trys","tryes"],"correct":"B","exp":"try → tries.","trans":"صديقي ___ أن يصلحها."},
        {"set":2,"q_type":"mcq","question":"Birds ___ in the sky.","options":["fly","flies","flys","flying"],"correct":"A","exp":"Birds جمع.","trans":"الطيور ___ في السماء."},
        {"set":3,"q_type":"mcq","question":"It ___ a lot in winter.","options":["rain","rains","raines","rainies"],"correct":"B","exp":"It → rains.","trans":"إنها ___ كثيراً شتاءً."},
        {"set":3,"q_type":"mcq","question":"My mother ___ delicious food.","options":["cook","cooks","cookes","cookies"],"correct":"B","exp":"mother=She → cooks.","trans":"أمي ___ طعاماً لذيذاً."},
        {"set":3,"q_type":"mcq","question":"You and I ___ good friends.","options":["am","is","are","be"],"correct":"C","exp":"You and I=We → are.","trans":"أنت وأنا ___ صديقان."},
        {"set":3,"q_type":"mcq","question":"The dog ___ at strangers.","options":["bark","barks","barkes","barkies"],"correct":"B","exp":"The dog=It → barks.","trans":"الكلب ___ على الغرباء."},
        {"set":3,"q_type":"mcq","question":"اختر الصحيحة عن العادة:","options":["I am drink water now.","I drinks water every day.","I drink water every day.","I drinking water every day."],"correct":"C","exp":"I drink (بدون s).","trans":""},
        {"set":3,"q_type":"mcq","question":"My brother ___ his homework.","options":["finish","finishs","finishes","finishies"],"correct":"C","exp":"finish → finishes.","trans":"أخي ___ واجبه."},
        {"set":3,"q_type":"mcq","question":"Students ___ hard before exams.","options":["study","studies","studys","studying"],"correct":"A","exp":"Students جمع.","trans":"الطلاب ___ قبل الامتحان."},
        {"set":3,"q_type":"mcq","question":"She ___ her grandmother weekly.","options":["visit","visits","visites","visiting"],"correct":"B","exp":"She → visits.","trans":"هي ___ جدتها."},
    ]

    return [
        {"code":"F1-L01","title_ar":"الضمائر الشخصية + فعل to be","content_html":L01_HTML,
         "examples":L01_EX,"questions":L01_Q,"xp":25,"timer":10,"order":1,"concept":"to_be"},
        {"code":"F1-L02","title_ar":"المضارع البسيط - المثبت","content_html":L02_HTML,
         "examples":L02_EX,"questions":L02_Q,"xp":25,"timer":10,"order":2,"concept":"simple_present"},
    ]


if __name__ == "__main__":
    run()
