# استيراد gemini_client اختياري - لا ينهار إذا كانت مكتبة google غير مثبتة
try:
    from .gemini_client import correct_essay, evaluate_speaking
except Exception as _e:
    correct_essay = None
    evaluate_speaking = None
    import sys as _sys
    print("[ai] gemini_client غير متاح (تجاهل):", _e, file=_sys.stderr)

