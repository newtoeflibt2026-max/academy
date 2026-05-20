# fix_engine.py - يصلح content_engine.py ليقرأ الملفات مباشرة
import re

with open('modules/content_engine.py', 'r', encoding='utf-8') as f:
    code = f.read()

# اصلاح get_index: احذف index.json القديم دائماً وأعد البناء
old_get_index = '''def get_index() -> Dict[str, Any]:
    """Returns the current index. Rebuilds if index.json is missing."""
    if not os.path.exists(INDEX_PATH):
        return scan_content()
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)'''

new_get_index = '''def get_index() -> Dict[str, Any]:
    """Returns the current index. Always rebuilds from files to ensure freshness."""
    # Always scan from files to avoid stale cache
    return scan_content()'''

code = code.replace(old_get_index, new_get_index)

with open('modules/content_engine.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('[OK] content_engine.py patched - get_index() now always rebuilds from files')
