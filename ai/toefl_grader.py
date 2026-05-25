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
    text = _call_gemini(prompt, max_tokens=1500)
    result = _extract_json(text)
    if not result:
        return _fallback_grade(student_email, "email")
    result["ai_available"] = True
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
    text = _call_gemini(prompt, max_tokens=1500)
    result = _extract_json(text)
    if not result:
        return _fallback_grade(student_response, "discussion")
    result["ai_available"] = True
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