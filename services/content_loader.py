# -*- coding: utf-8 -*-
"""
content_loader.py - محرك تحميل المحتوى من ملفات JSON
==================================================
يقرأ كل ملفات content/reading/*/*.json تلقائياً
يتحقق من الـ schema (الحقول الإلزامية)
يحفظها في cache (لا قراءة قرص متكررة)
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

# المسار الجذري للمحتوى
CONTENT_ROOT = Path(__file__).resolve().parent.parent / "content" / "reading"

# الحقول الإلزامية في كل ملف
# Phase 5.6: per-type required fields (flexible validation)
COMMON_REQUIRED = ["id", "type", "title_ar", "title_en", "tier", "duration_seconds"]
REQUIRED_BY_TYPE = {
    "academic_reading": COMMON_REQUIRED + ["passage", "questions"],
    "daily_reading":    COMMON_REQUIRED + ["passage", "questions"],
    "complete_words":   COMMON_REQUIRED + ["segments"],
}
# legacy alias (some code may still reference REQUIRED_FIELDS)
REQUIRED_FIELDS = COMMON_REQUIRED

# الأنواع المسموحة
ALLOWED_TYPES = ["academic_reading", "daily_reading", "complete_words"]
ALLOWED_TIERS = ["tier59", "tier69", "tier90", "easy", "medium", "hard"]

# Cache في الذاكرة
_cache: Dict[str, dict] = {}
_cache_loaded = False


def _validate(data: dict, filepath: str) -> List[str]:
    """يرجع قائمة أخطاء (فارغة = صحيح). Phase 5.6: validation per type."""
    errors = []
    # الحقول المطلوبة تختلف حسب type
    ctype = data.get("type")
    required = REQUIRED_BY_TYPE.get(ctype, COMMON_REQUIRED)
    for field in required:
        if field not in data:
            errors.append(f"حقل مفقود: {field}")
    if "type" in data and data["type"] not in ALLOWED_TYPES:
        errors.append(f"type غير مسموح: {data['type']}")
    if "tier" in data and data["tier"] not in ALLOWED_TIERS:
        errors.append(f"tier غير مسموح: {data['tier']}")
    # MCQ-based content
    if ctype in ("academic_reading", "daily_reading"):
        if "questions" in data:
            if not isinstance(data["questions"], list) or len(data["questions"]) == 0:
                errors.append("questions يجب أن تكون قائمة غير فارغة")
        if "passage" in data:
            if not isinstance(data["passage"], dict) or "text_en" not in data["passage"]:
                errors.append("passage يجب أن يحتوي text_en")
    # Complete-words content (Phase 5.6)
    if ctype == "complete_words":
        segs = data.get("segments")
        if not isinstance(segs, list) or len(segs) == 0:
            errors.append("segments يجب أن تكون قائمة غير فارغة")
        else:
            blanks = [s for s in segs if isinstance(s, dict) and "blank" in s]
            if len(blanks) == 0:
                errors.append("segments يجب أن تحتوي على blank واحد على الأقل")
            for i, b in enumerate(blanks):
                bl = b.get("blank", {})
                if not all(k in bl for k in ("prefix", "missing", "full_word")):
                    errors.append(f"blank #{i} ناقص أحد الحقول prefix/missing/full_word")
    return errors



def load_all(force_reload: bool = False) -> Dict[str, dict]:
    """يحمّل كل المحتوى من content/reading/. يستخدم cache افتراضياً."""
    global _cache, _cache_loaded
    if _cache_loaded and not force_reload:
        return _cache

    _cache = {}
    if not CONTENT_ROOT.exists():
        print(f"[content_loader] WARNING: {CONTENT_ROOT} غير موجود")
        _cache_loaded = True
        return _cache

    loaded_count = 0
    error_count = 0
    for subdir in ["academic_reading", "daily_reading", "daily_life", "academic", "daily", "complete_words"]:
        folder = CONTENT_ROOT / subdir
        if not folder.exists():
            continue
        for jf in sorted(folder.glob("*.json")):
            try:
                with open(jf, encoding="utf-8-sig") as f:
                    data = json.load(f)
                errors = _validate(data, str(jf))
                if errors:
                    print(f"[content_loader] SKIP {jf.name}: {errors}")
                    error_count += 1
                    continue
                # تأكيد الـ id فريد
                content_id = data["id"]
                if content_id in _cache:
                    print(f"[content_loader] WARNING: id مكرر {content_id}")
                _cache[content_id] = data
                loaded_count += 1
            except json.JSONDecodeError as e:
                print(f"[content_loader] JSON error {jf.name}: {e}")
                error_count += 1
            except Exception as e:
                print(f"[content_loader] ERROR {jf.name}: {e}")
                error_count += 1

    _cache_loaded = True
    print(f"[content_loader] تم تحميل {loaded_count} ملف "
          f"({error_count} خطأ) من {CONTENT_ROOT}")
    return _cache


def get_by_id(content_id: str) -> Optional[dict]:
    """يرجع محتوى واحد بـ id"""
    return load_all().get(content_id)


def list_by_type(content_type: str, tier: Optional[str] = None) -> List[dict]:
    """يرجع قائمة المحتوى حسب النوع (وtier اختياري)"""
    items = []
    for item in load_all().values():
        if item.get("type") != content_type:
            continue
        if tier and item.get("tier") != tier:
            continue
        # نرجع نسخة خفيفة للقوائم (بدون نص + بدون أسئلة)
        items.append({
            "id": item["id"],
            "type": item["type"],
            "title_ar": item["title_ar"],
            "title_en": item["title_en"],
            "tier": item["tier"],
            "duration_seconds": item["duration_seconds"],
            "questions_count": len(item.get("questions", [])),
            "word_count": item.get("passage", {}).get("word_count", 0),
            "topic": item.get("passage", {}).get("topic", "")
        })
    return items


def list_all_types() -> Dict[str, int]:
    """إحصائية: كم محتوى لكل نوع"""
    stats = {t: 0 for t in ALLOWED_TYPES}
    for item in load_all().values():
        t = item.get("type")
        if t in stats:
            stats[t] += 1
    return stats


def reload():
    """إعادة تحميل من القرص (للتطوير)"""
    global _cache_loaded
    _cache_loaded = False
    return load_all(force_reload=True)


if __name__ == "__main__":
    # اختبار سريع عند تشغيل الملف مباشرة
    print("=" * 60)
    print("content_loader - اختبار")
    print("=" * 60)
    all_content = load_all()
    print(f"\nإجمالي المحتوى: {len(all_content)}")
    print(f"\nالإحصائيات حسب النوع:")
    for t, n in list_all_types().items():
        print(f"   {t}: {n}")
    print(f"\nقائمة academic_reading:")
    for item in list_by_type("academic_reading"):
        print(f"   - [{item['tier']}] {item['title_ar']} "
              f"({item['questions_count']} أسئلة، {item['word_count']} كلمة)")
    print(f"\nاختبار get_by_id('academic_biology_cells_01'):")
    item = get_by_id("academic_biology_cells_01")
    if item:
        print(f"   ✓ وُجد: {item['title_ar']}")
        print(f"   ✓ عدد الأسئلة: {len(item['questions'])}")
        print(f"   ✓ السؤال الأول: {item['questions'][0]['prompt_en']}")
    else:
        print("   ✗ لم يُوجد")
