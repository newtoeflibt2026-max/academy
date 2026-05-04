import logging
from google import genai
from config import settings

logger = logging.getLogger(__name__)

# ── Keys pool ──
_WRITING_KEYS = []
_SPEAKING_KEYS = []
_MAIN_KEY = settings.GEMINI_API_KEY

if settings.GEMINI_WRITING_KEYS:
    _WRITING_KEYS = [k.strip() for k in settings.GEMINI_WRITING_KEYS.split(',') if k.strip()]
if settings.GEMINI_SPEAKING_KEYS:
    _SPEAKING_KEYS = [k.strip() for k in settings.GEMINI_SPEAKING_KEYS.split(',') if k.strip()]

_w_counter = 0
_s_counter = 0

# ── API Status tracker ──
_API_DOWN_WRITING = False
_API_DOWN_SPEAKING = False
_API_FAIL_COUNT_W = 0
_API_FAIL_COUNT_S = 0
_MAX_FAILS = 3  # بعد 3 فشل متتالية، اعتبر الـAPI معطل

def _next_writing_key():
    global _w_counter
    if _WRITING_KEYS:
        k = _WRITING_KEYS[_w_counter % len(_WRITING_KEYS)]
        _w_counter += 1
        return k
    return _MAIN_KEY

def _next_speaking_key():
    global _s_counter
    if _SPEAKING_KEYS:
        k = _SPEAKING_KEYS[_s_counter % len(_SPEAKING_KEYS)]
        _s_counter += 1
        return k
    return _MAIN_KEY

# ── IELTS 2026 EXAMINER PROMPTS ──
WRITING_PROMPT = """انت مصحح IELTS معتمد حسب معايير 2026 الرسمية.
قيم المقال حسب 4 معايير:
1. Task Response (هل غطى كل جوانب السؤال؟)
2. Coherence & Cohesion (ترابط الأفكار وادوات الربط)
3. Lexical Resource (تنوع المفردات والمتلازمات Collocations)
4. Grammatical Range & Accuracy (دقة القواعد وتنوع الازمنة)

لا تستخدم اي عبارات تحفيزية. لا تمدح الطالب.
التزم بالتنسيق التالي بالضبط:

الدرجة التقديرية (Band Score): [X.X]

الاخطاء المرصودة:
• [خطأ محدد مع ذكر نوعه: قواعدي/مفردات/ترابط/استجابة]
• [خطأ...]

التصحيح المقترح:
[الجملة المعدلة بشكل احترافي]

نصيحة ذهبية:
[نصيحة عملية واحدة لتجنب هذا الخطأ مستقبلا]

رد بالعربية فقط. كن مباشرا وعمليا."""

SPEAKING_PROMPT = """انت فاحص IELTS Speaking معتمد حسب معايير 2026 الرسمية.
قيم التسجيل الصوتي حسب 4 معايير:
1. Fluency (الطلاقة - سرعة الكلام بدون تردد)
2. Pronunciation (النطق - وضوح المخارج والتنغيم)
3. Lexical Resource (المفردات - تنوع وعمق)
4. Grammatical Range (القواعد - دقة وتنوع التراكيب)

لا تستخدم عبارات تحفيزية. لا تمدح الطالب.
التزم بالتنسيق التالي بالضبط:

الدرجة التقديرية (Band Score): [X.X]

الاخطاء المرصودة:
• [خطأ محدد - نطق/طلاقة/مفردات/قواعد]
• [خطأ...]

التصحيح المقترح:
[النطق الصحيح او الصياغة الصحيحة]

نصيحة ذهبية:
[نصيحة عملية واحدة لتجنب هذا الخطأ مستقبلا]

رد بالعربية فقط. كن مباشرا وعمليا."""

# ── Health check ──
def _is_api_available(feature: str) -> bool:
    global _API_DOWN_WRITING, _API_DOWN_SPEAKING
    if feature == "writing":
        return not _API_DOWN_WRITING
    return not _API_DOWN_SPEAKING

def _mark_fail(feature: str):
    global _API_FAIL_COUNT_W, _API_FAIL_COUNT_S, _API_DOWN_WRITING, _API_DOWN_SPEAKING
    if feature == "writing":
        _API_FAIL_COUNT_W += 1
        if _API_FAIL_COUNT_W >= _MAX_FAILS:
            _API_DOWN_WRITING = True
            logger.warning("Writing API marked DOWN after 3 consecutive failures")
    else:
        _API_FAIL_COUNT_S += 1
        if _API_FAIL_COUNT_S >= _MAX_FAILS:
            _API_DOWN_SPEAKING = True
            logger.warning("Speaking API marked DOWN after 3 consecutive failures")

def _mark_success(feature: str):
    global _API_FAIL_COUNT_W, _API_FAIL_COUNT_S, _API_DOWN_WRITING, _API_DOWN_SPEAKING
    if feature == "writing":
        _API_FAIL_COUNT_W = 0
        _API_DOWN_WRITING = False
    else:
        _API_FAIL_COUNT_S = 0
        _API_DOWN_SPEAKING = False

# ── Fallback messages ──
WRITING_DOWN_MSG = "خدمة تصحيح الكتابة غير متاحة حاليا. تم استنفاد الحد اليومي او انقطع الاتصال. جرب غدا."
SPEAKING_DOWN_MSG = "خدمة تقييم المحادثة غير متاحة حاليا. تم استنفاد الحد اليومي او انقطع الاتصال. جرب غدا."

# ── Main functions ──
async def correct_essay(text: str) -> str:
    if _API_DOWN_WRITING:
        return WRITING_DOWN_MSG
    
    api_key = _next_writing_key()
    if not api_key:
        _API_DOWN_WRITING = True
        return WRITING_DOWN_MSG
    
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=WRITING_PROMPT + "\n\nالمقال:\n" + text,
            config={"max_output_tokens": 800, "temperature": 0.3}
        )
        if resp.text:
            _mark_success("writing")
            return resp.text[:4000]
        _mark_fail("writing")
        return "لم يستجب المصحح. حاول مرة اخرى."
    except Exception as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            _API_DOWN_WRITING = True
            logger.warning(f"Writing quota exceeded: {e}")
            return WRITING_DOWN_MSG
        _mark_fail("writing")
        logger.error(f"Writing error: {e}")
        return WRITING_DOWN_MSG if _API_DOWN_WRITING else "خطا في التصحيح. حاول لاحقا."

async def evaluate_speaking(audio_path: str, topic: str = "general") -> str:
    if _API_DOWN_SPEAKING:
        return SPEAKING_DOWN_MSG
    
    api_key = _next_speaking_key()
    if not api_key:
        _API_DOWN_SPEAKING = True
        return SPEAKING_DOWN_MSG
    
    try:
        import base64, os
        if os.path.getsize(audio_path) > 4 * 1024 * 1024:
            return "الملف الصوتي كبير جدا. اقصى حد 4 ميجابايت."
        
        with open(audio_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                {"inline_data": {"mime_type": "audio/ogg", "data": b64}},
                SPEAKING_PROMPT + "\n\nالموضوع: " + topic
            ],
            config={"max_output_tokens": 500, "temperature": 0.3}
        )
        if resp.text:
            _mark_success("speaking")
            return resp.text[:4000]
        _mark_fail("speaking")
        return "لم يستجب المصحح."
    except Exception as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            _API_DOWN_SPEAKING = True
            logger.warning(f"Speaking quota exceeded: {e}")
            return SPEAKING_DOWN_MSG
        _mark_fail("speaking")
        logger.error(f"Speaking error: {e}")
        return SPEAKING_DOWN_MSG if _API_DOWN_SPEAKING else "خطا في التقييم. حاول لاحقا."
