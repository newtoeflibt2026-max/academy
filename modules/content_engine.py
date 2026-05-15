"""
YAMEN ACADEMY — EXTERNAL CONTENT ENGINE
=========================================
This module is the heart of the Content/Code separation architecture.

RULE: This file is written ONCE and NEVER modified.
      Adding a new lesson = adding a new JSON file in /content/lessons/
      The engine auto-discovers it.

Architecture:
  /content/
  ├── lessons/       ← One JSON file per lesson  (e.g. L001_reading.json)
  ├── questions/     ← One JSON file per question bank
  ├── index.json     ← Auto-generated index (regenerated on scan)
  └── schema/        ← JSON schema documentation (for admins)

Functions:
  scan_content()       → Scans /content/ folders, regenerates index.json
  get_lesson(id)       → Returns full lesson JSON by lesson_id
  list_lessons(cat)    → Lists all lessons, optionally filtered by category
  get_question(qid)    → Returns a single question
  search(query)        → Full-text search across all lessons
"""

import json, os, glob
from datetime import datetime
from typing import Optional, List, Dict, Any

# === CONFIGURATION (change ONLY these paths, never the logic) ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE_DIR, "content")
LESSONS_DIR = os.path.join(CONTENT_DIR, "lessons")
QUESTIONS_DIR = os.path.join(CONTENT_DIR, "questions")
INDEX_PATH = os.path.join(CONTENT_DIR, "index.json")

# ================================================================
#  CORE ENGINE — SCAN & INDEX
#  ================================================================
def scan_content() -> Dict[str, Any]:
    """
    Scans /content/lessons/ and /content/questions/ folders.
    Reads all JSON files, builds a master index.
    Regenerates index.json automatically.
    
    Returns: the full index dict
    """
    index = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "total_lessons": 0,
        "total_questions": 0,
        "lessons": [],
        "questions": [],
        "categories": {
            "reading":    {"count": 0, "lesson_ids": []},
            "writing":    {"count": 0, "lesson_ids": []},
            "listening":  {"count": 0, "lesson_ids": []},
            "speaking":   {"count": 0, "lesson_ids": []},
            "grammar":    {"count": 0, "lesson_ids": []},
            "vocabulary": {"count": 0, "lesson_ids": []},
        }
    }

    # --- Scan lessons ---
    os.makedirs(LESSONS_DIR, exist_ok=True)
    lesson_files = sorted(glob.glob(os.path.join(LESSONS_DIR, "*.json")))
    
    for filepath in lesson_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lesson = json.load(f)
            
            lesson_id = lesson.get("lesson_id", os.path.basename(filepath).replace(".json", ""))
            category = lesson.get("category", "uncategorized")
            
            # Build lightweight index entry (don't store full content in index)
            entry = {
                "lesson_id": lesson_id,
                "title": lesson.get("title", ""),
                "title_en": lesson.get("title_en", ""),
                "category": category,
                "skill_type": lesson.get("skill_type", ""),
                "difficulty": lesson.get("difficulty", "medium"),
                "duration_minutes": lesson.get("duration_minutes", 0),
                "description": lesson.get("description", ""),
                "prerequisites": lesson.get("prerequisites", []),
                "objectives": lesson.get("objectives", []),
                "section_count": len(lesson.get("sections", [])),
                "quiz_question_count": len(lesson.get("quiz", {}).get("questions", [])),
                "file": os.path.basename(filepath),
                "metadata": lesson.get("metadata", {}),
            }
            
            index["lessons"].append(entry)
            index["total_lessons"] += 1
            
            # Update category
            if category in index["categories"]:
                index["categories"][category]["count"] += 1
                index["categories"][category]["lesson_ids"].append(lesson_id)
                
        except Exception as e:
            print(f"[ContentEngine] WARNING: Failed to read {filepath}: {e}")

    # --- Scan questions ---
    os.makedirs(QUESTIONS_DIR, exist_ok=True)
    question_files = sorted(glob.glob(os.path.join(QUESTIONS_DIR, "*.json")))
    
    for filepath in question_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                qbank = json.load(f)
            
            questions = qbank if isinstance(qbank, list) else qbank.get("questions", [])
            for q in questions:
                index["questions"].append({
                    "qid": q.get("qid", "?"),
                    "type": q.get("type", "multiple_choice"),
                    "question": q.get("question", "")[:80],
                    "category": q.get("category", ""),
                    "difficulty": q.get("difficulty", "medium"),
                    "file": os.path.basename(filepath),
                })
                index["total_questions"] += 1
                
        except Exception as e:
            print(f"[ContentEngine] WARNING: Failed to read {filepath}: {e}")

    # --- Write index ---
    os.makedirs(CONTENT_DIR, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    
    print(f"[ContentEngine] Scan complete: {index['total_lessons']} lessons, {index['total_questions']} questions")
    return index


# ================================================================
#  PUBLIC API — READ OPERATIONS (these are the only public methods)
# ================================================================

def get_index() -> Dict[str, Any]:
    """Returns the current index. Rebuilds if index.json is missing."""
    if not os.path.exists(INDEX_PATH):
        return scan_content()
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def list_lessons(category: Optional[str] = None, difficulty: Optional[str] = None,
                 skill_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Returns a list of lessons (lightweight, from index).
    
    Filters (all optional):
      - category:  reading, writing, listening, speaking, grammar, vocabulary
      - difficulty: easy, medium, hard
      - skill_type: reading, writing, listening, speaking, grammar
      - limit: max number of results
    """
    index = get_index()
    lessons = index.get("lessons", [])
    
    if category:
        lessons = [l for l in lessons if l.get("category") == category]
    if difficulty:
        lessons = [l for l in lessons if l.get("difficulty") == difficulty]
    if skill_type:
        lessons = [l for l in lessons if l.get("skill_type") == skill_type]
    
    return lessons[:limit]


def get_lesson(lesson_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns the FULL lesson content (including all sections, quiz, exercises).
    Reads directly from the JSON file.
    """
    # First, find which file this lesson is in
    index = get_index()
    lesson_file = None
    for entry in index.get("lessons", []):
        if entry["lesson_id"] == lesson_id:
            lesson_file = entry.get("file")
            break
    
    if not lesson_file:
        # Try direct file name
        lesson_file = f"{lesson_id}.json"
    
    filepath = os.path.join(LESSONS_DIR, lesson_file)
    if not os.path.exists(filepath):
        # Try scanning and looking again
        scan_content()
        index = get_index()
        for entry in index.get("lessons", []):
            if entry["lesson_id"] == lesson_id:
                filepath = os.path.join(LESSONS_DIR, entry["file"])
                break
    
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_next_lesson(current_lesson_id: str) -> Optional[Dict[str, Any]]:
    """Returns the next lesson in sequence (for linear learning paths)."""
    index = get_index()
    lessons = index.get("lessons", [])
    for i, l in enumerate(lessons):
        if l["lesson_id"] == current_lesson_id and i + 1 < len(lessons):
            return get_lesson(lessons[i + 1]["lesson_id"])
    return None


def search_lessons(query: str) -> List[Dict[str, Any]]:
    """
    Full-text search across all lessons.
    Searches: title, description, objectives, section content.
    Returns matching lessons (lightweight entries).
    """
    query_lower = query.lower()
    results = []
    index = get_index()
    
    # Search in index first (title, description)
    for entry in index.get("lessons", []):
        title = (entry.get("title", "") + " " + entry.get("title_en", "")).lower()
        desc = entry.get("description", "").lower()
        
        if query_lower in title or query_lower in desc:
            results.append(entry)
            continue
        
        # Deep search: load full lesson and search content
        lesson = get_lesson(entry["lesson_id"])
        if lesson:
            # Search objectives
            for obj in lesson.get("objectives", []):
                if query_lower in obj.lower():
                    results.append(entry)
                    break
            # Search section content
            for section in lesson.get("sections", []):
                if query_lower in section.get("content", "").lower():
                    if entry not in results:
                        results.append(entry)
                    break
    
    return results


def get_categories() -> Dict[str, Any]:
    """Returns category summary with counts."""
    index = get_index()
    return index.get("categories", {})


def create_lesson_from_admin(lesson_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a new lesson JSON file from admin input.
    This is the ONLY write operation — it writes to /content/, NEVER to code.
    
    Args:
        lesson_data: full lesson dict matching the schema
    
    Returns:
        {"ok": True, "lesson_id": "...", "file": "..."}
    """
    lesson_id = lesson_data.get("lesson_id", "")
    if not lesson_id:
        # Auto-generate ID
        index = get_index()
        existing_ids = {l["lesson_id"] for l in index.get("lessons", [])}
        counter = 1
        while f"L{counter:03d}" in existing_ids:
            counter += 1
        lesson_id = f"L{counter:03d}"
        lesson_data["lesson_id"] = lesson_id
    
    # Generate safe filename
    safe_title = lesson_data.get("title", "new_lesson").lower()
    safe_title = "".join(c if c.isalnum() or c in "_- " else "" for c in safe_title)
    safe_title = safe_title.replace(" ", "_")[:40]
    filename = f"{lesson_id}_{safe_title}.json"
    
    # Ensure metadata
    if "metadata" not in lesson_data:
        lesson_data["metadata"] = {}
    lesson_data["metadata"]["updated_at"] = datetime.now().isoformat()
    lesson_data["metadata"]["version"] = lesson_data["metadata"].get("version", 0) + 1
    
    # Write file
    os.makedirs(LESSONS_DIR, exist_ok=True)
    filepath = os.path.join(LESSONS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(lesson_data, f, indent=2, ensure_ascii=False)
    
    # Rebuild index
    scan_content()
    
    print(f"[ContentEngine] Created lesson: {lesson_id} → {filename}")
    return {"ok": True, "lesson_id": lesson_id, "file": filename}


def update_lesson_from_admin(lesson_id: str, lesson_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates an existing lesson JSON file from admin input.
    Writes ONLY to /content/lessons/, NEVER to code.
    """
    # Find existing file
    index = get_index()
    lesson_file = None
    for entry in index.get("lessons", []):
        if entry["lesson_id"] == lesson_id:
            lesson_file = entry.get("file")
            break
    
    if not lesson_file:
        return {"ok": False, "error": f"Lesson {lesson_id} not found"}
    
    filepath = os.path.join(LESSONS_DIR, lesson_file)
    if not os.path.exists(filepath):
        return {"ok": False, "error": f"File {lesson_file} not found on disk"}
    
    # Update metadata
    lesson_data["lesson_id"] = lesson_id  # Ensure ID remains
    if "metadata" not in lesson_data:
        lesson_data["metadata"] = {}
    lesson_data["metadata"]["updated_at"] = datetime.now().isoformat()
    lesson_data["metadata"]["version"] = lesson_data["metadata"].get("version", 0) + 1
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(lesson_data, f, indent=2, ensure_ascii=False)
    
    scan_content()
    print(f"[ContentEngine] Updated lesson: {lesson_id}")
    return {"ok": True, "lesson_id": lesson_id}


def delete_lesson_from_admin(lesson_id: str) -> Dict[str, Any]:
    """Deletes a lesson JSON file. Writes ONLY to /content/, NEVER to code."""
    index = get_index()
    lesson_file = None
    for entry in index.get("lessons", []):
        if entry["lesson_id"] == lesson_id:
            lesson_file = entry.get("file")
            break
    
    if not lesson_file:
        return {"ok": False, "error": f"Lesson {lesson_id} not found"}
    
    filepath = os.path.join(LESSONS_DIR, lesson_file)
    if os.path.exists(filepath):
        os.remove(filepath)
    
    scan_content()
    print(f"[ContentEngine] Deleted lesson: {lesson_id}")
    return {"ok": True, "lesson_id": lesson_id}


# ================================================================
#  INITIALIZATION — Scan on import
# ================================================================
print("[ContentEngine] Initializing external content engine...")
scan_content()
print(f"[ContentEngine] Ready. Content directory: {CONTENT_DIR}")
