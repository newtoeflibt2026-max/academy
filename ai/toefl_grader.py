# -*- coding: utf-8 -*-
"""
TOEFL Writing Grader (sync) - for Flask
Grades: Email (Task 2) + Academic Discussion (Task 3)
Uses Gemini 2.0 Flash with key rotation + fallback.
"""
import os, json, logging, requests, time

logger = logging.getLogger(__name__)

# Load keys from env
_KEYS_RAW = os.environ.get("GEMINI_WRITING_KEYS", "") or os.environ.get("GEMINI_API_KEY", "")
_KEYS = [k.strip() for k in _KEYS_RAW.split(",") if k.strip()]
_counter = 0
_fail_count = 0
_MAX_FAILS = 5
_API_DOWN = False

def _next_key():
    global _counter
    if not _KEYS:
        return ""
    k = _KEYS[_counter % len(_KEYS)]
    _counter += 1
    return k

def _call_gemini(prompt, max_tokens=1200):
    """Sync call to Gemini 2.0 Flash. Returns text or None on failure."""
    global _fail_count, _API_DOWN
    if _API_DOWN:
        return None
    key = _next_key()
    if not key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": max_tokens}
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 429:
            _fail_count += 1
            if _fail_count >= _MAX_FAILS:
                _API_DOWN = True
            return None
        if r.status_code != 200:
            _fail_count += 1
            return None
        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        _fail_count = 0
        return text
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        _fail_count += 1
        return None

# ═══════════════════════════════════════════════════════════
# Email Grader (Task 2 - 7 minutes)
# ═══════════════════════════════════════════════════════════
EMAIL_PROMPT = """انت مصحح TOEFL iBT 2026 معتمد لقسم Writing - Task 2 (Email).
قيم البريد الإلكتروني حسب معايير TOEFL الرسمية (1-6):
- التنظيم والوضوح
- استخدام النبرة المناسبة (Formal/Semi-Formal/Informal)
- تغطية كل النقاط المطلوبة
- دقة القواعد والمفردات

السيناريو المطلوب:
{scenario}

النقاط الواجب تغطيتها:
{requirements}

أجب بـ JSON فقط (بدون أي نص آخر):
{{
  "score": <رقم من 1 إلى 6>,
  "band_label": "<ممتاز/جيد جداً/جيد/مقبول/ضعيف>",
  "word_count": <عدد كلمات البريد>,
  "tone_match": <true/false>,
  "covered_points": [<قائمة النقاط المغطاة>],
  "missing_points": [<قائمة النقاط الناقصة>],
  "errors": [
    {{"type":"grammar/vocab/tone/structure", "text":"الخطأ", "correction":"التصحيح"}}
  ],
  "strengths": ["<نقطة قوة 1>", "<نقطة قوة 2>"],
  "improvements": ["<نصيحة 1>", "<نصيحة 2>", "<نصيحة 3>"],
  "feedback_ar": "<تعليق شامل بالعربية 2-3 جمل>"
}}
"""

DISCUSSION_PROMPT = """انت مصحح TOEFL iBT 2026 معتمد لقسم Writing - Task 3 (Academic Discussion).
قيم المنشور حسب معايير TOEFL الرسمية (1-6):
- وضوح الموقف وقوة الحجة
- التفاعل مع آراء الطلاب الآخرين
- استخدام الأمثلة المحددة والأدلة
- اللغة الأكاديمية والعبارات الانتقالية
- دقة القواعد والمفردات

سؤال الأستاذ:
{professor_question}

رأي الطالب الأول:
{student1}

رأي الطالب الثاني:
{student2}

أجب بـ JSON فقط (بدون أي نص آخر):
{{
  "score": <رقم من 1 إلى 6>,
  "band_label": "<ممتاز/جيد جداً/جيد/مقبول/ضعيف>",
  "word_count": <عدد الكلمات>,
  "position_clear": <true/false>,
  "engages_with_students": <true/false>,
  "has_specific_examples": <true/false>,
  "errors": [
    {{"type":"grammar/vocab/structure/coherence", "text":"الخطأ", "correction":"التصحيح"}}
  ],
  "strengths": ["<نقطة قوة 1>", "<نقطة قوة 2>"],
  "improvements": ["<نصيحة 1>", "<نصيحة 2>", "<نصيحة 3>"],
  "feedback_ar": "<تعليق شامل بالعربية 3-4 جمل>"
}}
"""

def _extract_json(text):
    """Extract JSON from Gemini response (may be wrapped in ```json...```)."""
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.lstrip("`").lstrip("json").strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    try:
        return json.loads(text)
    except Exception:
        # Try to find first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end+1])
            except:
                pass
    return None

# ============================================================
# INTERNAL GRADER v3 - مصحح داخلي محسن (ETS 2026 - تقديري)
# rubric للمهمة 0-5، يحول 1-6 + معادلة 120، يكشف التكرار والحشو
# + يبني برومبت تدريب Gemini احترافي
# ============================================================
import re as _r
_GEMINI_URL = "https://gemini.google.com/app"
_CONNECTORS = ["because","however","therefore","although","moreover","furthermore",
 "in addition","for example","for instance","on the other hand","as a result",
 "first","second","finally","in conclusion","while","whereas","since","thus","also"]
_FILLER = ["very","really","just","actually","basically","thing","things","stuff"]

def _ets_scales(task5):
    """يحول درجة المهمة (0-5) إلى مقياس ETS الجديد 1-6 (نصف نقطة) + معادلة 0-120."""
    sec30 = round((task5 / 5.0) * 30)
    raw6 = 1.0 + (sec30 / 30.0) * 5.0
    band6 = round(raw6 * 2) / 2.0
    band6 = max(1.0, min(6.0, band6))
    eq120 = round((band6 - 1.0) / 5.0 * 120)
    disp = f"{band6:g} / 6 (\u2248 {eq120} / 120)"
    return band6, eq120, sec30, disp

def _build_gemini_prompt(task_label, question, context, student_text):
    if isinstance(context, list):
        ctx = (chr(10)).join('- ' + str(c) for c in context if c).strip()
    else:
        ctx = str(context or '').strip()
    NL = chr(10)
    parts = []
    parts.append('دورك: أنت مدرب خبير ودقيق لمهارة TOEFL iBT Writing (صيغة 2026)، تساعدني على تطوير كتابتي وتتابع معي في نفس المحادثة.')
    parts.append('')
    parts.append('== نوع المهمة ==')
    parts.append(task_label)
    parts.append('')
    parts.append('== السؤال/الموضوع ==')
    parts.append(question)
    parts.append('')
    if ctx:
        parts.append('== متطلبات المهمة ==')
        parts.append(ctx)
        parts.append('')
    parts.append('== إجابتي ==')
    parts.append(student_text)
    parts.append('')
    parts.append('== المطلوب منك بالضبط (أجب بالعربية بشكل منظم وواضح) ==')
    parts.append('1) صحح إجابتي وفق معايير ETS الرسمية: تطور الفكرة وتنظيمها، الاستخدام اللغوي والمفردات، القواعد والإملاء، مدى تلبية المهمة.')
    parts.append('2) أعطني درجة المهمة من 0 إلى 5، ثم حولها لمقياس 1-6 (نصف نقطة) ومعادلة 120، بالصيغة: X / 6 (\u2248 Y / 120).')
    parts.append('3) حدد أهم 3-5 أخطاء فعلية/نقاط ضعف عندي مع أمثلة من نصي.')
    parts.append('4) أعطني أقوى نقطة عندي (لأبني عليها).')
    parts.append('5) صمم لي مهمة تدريبية صغيرة تعالج أهم نقطة ضعف، ثم اطلب مني أن أكتب محاولتي وألصقها هنا لتتابع تطوري.')
    parts.append('6) قدم فقرة نموذجية قصيرة كمثال على المستوى الأعلى.')
    parts.append('')
    parts.append('ملاحظة مهمة جدا: المهمة التدريبية الجديدة (السؤال والمطلوب من الطالب) اكتبها بالانجليزية فقط لانها تحاكي امتحان TOEFL الحقيقي. اما الشرح والتصحيح والملاحظات والتقييم فبالعربية.')
    parts.append('في نهاية ردك اطلب مني أن ألصق محاولتي القادمة في نفس المحادثة لتستمر بمتابعتي وتقييم تقدمي خطوة بخطوة.')
    return NL.join(parts)

def _grade_internal(student_text, context_terms=None, task_type="email",
                    min_words=100, question="", task_label=""):
    """مصحح داخلي تقديري (غير رسمي للتدريب). الدرجة النهائية للطالب."""
    context_terms = context_terms or []
    text = (student_text or "").strip()
    words = [w for w in _r.split(r"\s+", text) if w]
    wc = len(words)
    lower = text.lower()
    norm = [w.lower().strip('.,!?;:"\'()') for w in words if w.strip('.,!?;:"\'()')]

    label = task_label or ("TOEFL Writing - Write an Email" if task_type=="email"
                           else "TOEFL Writing - Academic Discussion")
    gp = _build_gemini_prompt(label, question or "(لا يوجد سؤال في القاعدة)",
                              context_terms, text)
    base = {"gemini_prompt": gp, "gemini_url": _GEMINI_URL, "is_estimate": True}

    if wc < 20:
        b6,eq,_,disp = _ets_scales(0)
        return {**base,"score":0,"score6":b6,"score120":eq,"display":disp,
            "band_label":"ضعيف","word_count":wc,"errors":[],"strengths":[],
            "improvements":["النص قصير جدا. اكتب 100 كلمة على الأقل."],
            "feedback_ar":f"النص قصير جدا ({wc} كلمة) للتقييم.","ai_available":True}

    pts = 0.0; strengths=[]; improvements=[]

    ratio = wc/max(min_words,1)
    if ratio>=1.0: pts+=20; strengths.append("طول مناسب للمهمة")
    elif ratio>=0.7: pts+=14; improvements.append(f"قريب من الحد ({min_words}+ كلمة). زد قليلا.")
    else: pts+=10*ratio; improvements.append(f"النص أقصر من المطلوب ({min_words}+ كلمة وليس {wc}).")

    terms=[t.lower() for t in context_terms if t and len(str(t))>3]
    if terms:
        kws=set()
        for t in terms:
            for w in _r.split(r"\s+", t):
                w=w.strip('.,!?;:"\'()').lower()
                if len(w)>4: kws.add(w)
        hit=sum(1 for k in kws if k in lower)
        cov=hit/max(len(kws),1)
        pts+=25*min(cov*1.5,1.0)
        if cov>=0.4: strengths.append("تناول عناصر المهمة المطلوبة")
        else: improvements.append("تأكد من تغطية كل نقاط/متطلبات المهمة.")
    else: pts+=18

    sents=[s for s in _r.split(r"[.!?]+", text) if s.strip()]
    ns=len(sents)
    if ns>=5: pts+=10; strengths.append("تنظيم جيد للجمل والأفكار")
    elif ns>=3: pts+=7
    else: pts+=3; improvements.append("قسم أفكارك إلى جمل أكثر.")
    if task_type=="email":
        if any(g in lower for g in ["dear","hello","hi ","greetings"]): pts+=5
        else: improvements.append("ابدأ بتحية رسمية (Dear ...).")
        if any(c in lower for c in ["regards","sincerely","thank you","best ","yours"]): pts+=5
        else: improvements.append("اختم بخاتمة رسمية (Best regards ...).")
    else:
        pts += 10 if (ns>=6 or "\n" in text) else 5

    uniq=len(set(norm)); total=max(len(norm),1)
    diversity=uniq/total
    from collections import Counter
    cnt=Counter(w for w in norm if len(w)>3 and w not in _FILLER and w not in _CONNECTORS)
    over=sum(v-3 for v in cnt.values() if v>3)
    rep_penalty=min(over*1.5, 12)
    pts += 12*min(diversity/0.55,1.0)
    if diversity>=0.55 and over==0: strengths.append("تنوع جيد في المفردات بلا تكرار")
    elif over>0: improvements.append("قلل تكرار الكلمات وتنويع المفردات مطلوب.")
    conn=sum(1 for c in _CONNECTORS if c in lower)
    if conn>=3: pts+=8; strengths.append("استخدام جيد لأدوات الربط")
    elif conn>=1: pts+=5
    else: improvements.append("استخدم أدوات ربط (however, because, therefore).")

    filler_ratio=sum(1 for w in norm if w in _FILLER)/total
    if filler_ratio>0.12:
        pts-=8; improvements.append("قلل كلمات الحشو (very, really, just, things).")
    clean_sents=[_r.sub(r"\s+"," ",s.strip().lower()) for s in sents if len(s.strip())>10]
    if len(clean_sents)!=len(set(clean_sents)):
        pts-=8; improvements.append("هناك جمل مكررة حرفيا في نصك.")
    pts -= rep_penalty

    score100=max(0,min(100,round(pts)))
    task5=round(score100/100*5*2)/2.0

    if task5>=4.5: band="ممتاز"
    elif task5>=3.5: band="جيد جدا"
    elif task5>=2.5: band="جيد"
    elif task5>=1.5: band="مقبول"
    else: band="ضعيف"

    b6,eq120,sec30,disp=_ets_scales(task5)
    if not strengths: strengths.append("محاولة جادة في الكتابة")
    if not improvements: improvements.append("راجع نصك مع Gemini لرفع المستوى.")

    return {**base,
        "score": task5, "score6": b6, "score120": eq120, "section30": sec30,
        "display": disp, "band_label": band, "word_count": wc, "errors": [],
        "strengths": strengths[:4], "improvements": improvements[:4],
        "feedback_ar": (f"تقدير تدريبي تقريبي: {disp} \u2014 {band}. عدد الكلمات {wc}. "
                        "هذا تقدير داخلي للتدريب وليس درجة الامتحان. انسخ البرومبت "
                        "أدناه وصححه على Gemini للحصول على تصحيح احترافي وخطة تدريب."),
        "ai_available": True}

def _fallback_grade(student_text, task_type="email"):
    """Simple offline grader when Gemini fails."""
    words = student_text.split()
    wc = len(words)
    # Heuristic scoring
    if wc < 30:
        score = 1
        label = "ضعيف"
    elif wc < 60:
        score = 2
        label = "ضعيف"
    elif wc < 90:
        score = 3
        label = "مقبول"
    elif wc < 120:
        score = 4
        label = "جيد"
    elif wc < 160:
        score = 5
        label = "جيد جداً"
    else:
        score = 5
        label = "جيد جداً"
    return {
        "score": score,
        "band_label": label,
        "word_count": wc,
        "errors": [],
        "strengths": ["تم استلام إجابتك"],
        "improvements": ["خدمة التصحيح التلقائي غير متاحة حالياً. سيقوم المدرس بمراجعتها قريباً."],
        "feedback_ar": f"تم استلام إجابتك ({wc} كلمة). التقييم الأولي مبني على الطول فقط. سيقوم المدرس بمراجعة شاملة قريباً.",
        "ai_available": False
    }


def _call_gemini_safe(prompt, max_retries=2):
    """يعيد (response_text, ai_available). إذا quota مستنفذة أو خطأ، يعيد (None, False)."""
    import urllib.request, json as _json, urllib.error
    for attempt in range(max_retries):
        key = _next_key()
        if not key:
            return (None, False)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
        payload = _json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024}
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read().decode("utf-8")
                data = _json.loads(body)
                text = data.get("candidates",[{}])[0].get("content",{}).get("parts",[{}])[0].get("text","")
                if text.strip():
                    return (text, True)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                continue  # جرب مفتاحاً آخر
            if e.code in (400, 403):
                continue
        except Exception:
            continue
    return (None, False)


def grade_email(scenario, requirements, student_email):
    """Grade a TOEFL Writing Task 2 (Email). Returns dict."""
    if not student_email or len(student_email.strip()) < 20:
        return {
            "score": 0,
            "band_label": "ضعيف",
            "word_count": len(student_email.split()),
            "errors": [],
            "strengths": [],
            "improvements": ["البريد قصير جداً. يجب أن يكون 100-150 كلمة على الأقل."],
            "feedback_ar": "البريد قصير جداً للتقييم. حاول كتابة 100-150 كلمة.",
            "ai_available": True
        }
    req_str = "\n".join([f"- {r}" for r in requirements]) if isinstance(requirements, list) else str(requirements)
    prompt = EMAIL_PROMPT.format(scenario=scenario, requirements=req_str) + f"\n\nبريد الطالب:\n{student_email}"
    return _grade_internal(student_email, context_terms=requirements, task_type="email", min_words=100, question=scenario)
    return result

def grade_discussion(professor_question, student1, student2, student_response):
    """Grade a TOEFL Writing Task 3 (Academic Discussion). Returns dict."""
    if not student_response or len(student_response.strip()) < 30:
        return {
            "score": 0,
            "band_label": "ضعيف",
            "word_count": len(student_response.split()),
            "errors": [],
            "strengths": [],
            "improvements": ["الرد قصير جداً. يجب أن يكون 100+ كلمة."],
            "feedback_ar": "الرد قصير جداً للتقييم. حاول كتابة 100+ كلمة.",
            "ai_available": True
        }
    prompt = DISCUSSION_PROMPT.format(
        professor_question=professor_question,
        student1=student1,
        student2=student2
    ) + f"\n\nرد الطالب:\n{student_response}"
    return _grade_internal(student_response, context_terms=[student1, student2], task_type="discussion", min_words=100, question=professor_question)
    return result

# ═══════════════════════════════════════════════════════════
# Build a Sentence Grader (LOCAL - no AI needed!)
# ═══════════════════════════════════════════════════════════
def grade_sentence_order(correct_sentence, student_words):
    """Compare student-ordered words to the correct sentence.
    Returns dict with score 0/1 + diff info.
    """
    if not student_words:
        return {"correct": False, "score": 0, "feedback_ar": "لم تقم بترتيب أي كلمات."}
    student_sent = " ".join(student_words).strip()
    # Normalize: lowercase, remove punctuation for comparison
    import re
    def norm(s):
        return re.sub(r"[^\w\s']", "", s.lower()).strip()
    is_correct = norm(student_sent) == norm(correct_sentence)
    return {
        "correct": is_correct,
        "score": 1 if is_correct else 0,
        "student_sentence": student_sent,
        "correct_sentence": correct_sentence,
        "feedback_ar": "إجابة صحيحة! ✅" if is_correct else f"الإجابة الصحيحة: {correct_sentence}"
    }