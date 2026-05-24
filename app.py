# -*- coding: utf-8 -*-
from flask import Flask, jsonify, render_template, request

import os
DB_PATH = os.environ.get("DB_PATH", "academy.db")
import os, json
from datetime import datetime
from db import (get_db, get_all_students_db, get_student,
                activate_paid, deactivate_paid, update_student,
                get_setting, set_setting)

app = Flask(__name__)

# Phase 7: Placement test blueprint
try:
    from modules.placement_web import placement_bp
    app.register_blueprint(placement_bp)
    print('[OK] placement_bp registered')
except Exception as _e:
    print('[WARN] placement_bp not loaded:', _e)

app.secret_key = os.getenv("SECRET_KEY", "yamen-secret-2025")

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Pages Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

# ===== Phase 12G: Unified DB connection with WAL + busy_timeout =====
def _db_safe(path=None):
    """Open SQLite with WAL mode and 30s busy_timeout to prevent locks."""
    import sqlite3 as _sq
    p = path or os.environ.get("DB_PATH", "/app/data/academy.db")
    conn = _sq.connect(p, timeout=30.0, isolation_level=None, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    except Exception as _e:
        print(f"[_db_safe] PRAGMA warn: {_e}")
    return conn


# ===== Phase 13.2e HOTFIX: ensure ALL exam columns at module load =====
def _ensure_all_exam_columns():
    try:
        import sqlite3 as _sq3
        conn = _db_safe(); c = conn.cursor()
        c.execute("PRAGMA table_info(stage_exam_questions)")
        existing = {r[1] for r in c.fetchall()}
        needed = [
            ("difficulty", "TEXT"),
            ("set_id", "TEXT"),
            ("order_in_set", "INTEGER"),
            ("is_active", "INTEGER DEFAULT 1"),
            ("q_type", "TEXT"),
            ("passage_text", "TEXT"),
            ("audio_source", "TEXT"),
            ("blanks_json", "TEXT"),
            ("time_limit_seconds", "INTEGER"),
            ("word_count_min", "INTEGER"),
            ("word_count_max", "INTEGER"),
            ("rubric_json", "TEXT"),
            ("skill_section", "TEXT"),
            ("concept_ar", "TEXT"),
            ("explanation_ar", "TEXT"),
            ("trap_ar", "TEXT"),
            ("review_lesson_id", "INTEGER"),
            ("review_lesson_title", "TEXT"),
            ("strategy_ar", "TEXT"),
            ("elimination_ar", "TEXT"),
        ]
        added = []
        for col, typ in needed:
            if col not in existing:
                try:
                    c.execute(f"ALTER TABLE stage_exam_questions ADD COLUMN {col} {typ}")
                    added.append(col)
                except Exception as e:
                    print(f"[ALL-COLS] skip {col}: {e}")
        # ensure all rows have is_active=1
        try:
            c.execute("UPDATE stage_exam_questions SET is_active=1 WHERE is_active IS NULL")
        except Exception as e:
            print(f"[ALL-COLS] update is_active err: {e}")
        conn.commit(); conn.close()
        print(f"[ALL-COLS] Added: {added if added else 'none (all present)'}")
    except Exception as e:
        print(f"[ALL-COLS] ERROR: {e}")

# يُنفّذ فوراً عند load (Gunicorn/Flask/WSGI)
try:
    _ensure_all_exam_columns()
except Exception as _e:
    print(f"[ALL-COLS] startup error: {_e}")
# ===== End Phase 13.2e HOTFIX =====

def _ensure_wal_once():
    """Run once at startup to enable WAL persistently."""
    try:
        c = _db_safe()
        mode = c.execute("PRAGMA journal_mode;").fetchone()
        print(f"[Phase12G] journal_mode = {mode}")
        c.close()
    except Exception as e:
        print(f"[Phase12G] WAL init error: {e}")

# ===== Phase 12G: Fix stages.track NOT NULL =====

def _ensure_stages_track_default():
    """Ensure track column and default value - Final Fix"""
    try:
        conn = _db_safe()
        c = conn.cursor()
        try:
            c.execute("PRAGMA table_info(stages)")
            cols = [row[1] for row in c.fetchall()]
            if "track" not in cols:
                c.execute("""ALTER TABLE stages ADD COLUMN track TEXT DEFAULT 'foundation' NOT NULL""")
                print("[Phase12G] Added missing `track` column with DEFAULT")

            c.execute("UPDATE stages SET track = 'foundation' WHERE track IS NULL OR track = ''")
            conn.commit()
            print(f"[Phase12G] Normalized stages.track rows: {c.rowcount}")
        finally:
            conn.close()
    except Exception as e:
        if "duplicate column name" not in str(e).lower():
            print(f"[Phase12G] Ensure error: {e}")

try:
    _ensure_wal_once()
    _ensure_stages_track_default()
except Exception as _e:
    print(f"[Phase12G] startup hook error: {_e}")
# ===== End Phase 12G =====

# ===== Phase 13.1: TOEFL Question Type Engine =====
TOEFL_QUESTION_TYPES = {
    "mcq": {"section": "general", "label": "Multiple Choice (legacy)"},
    "complete_words": {"section": "reading", "label": "Complete the Words"},
    "read_daily_life": {"section": "reading", "label": "Read in Daily Life"},
    "read_academic": {"section": "reading", "label": "Read an Academic Passage"},
    "listen_response": {"section": "listening", "label": "Listen and Choose a Response"},
    "listen_conversation": {"section": "listening", "label": "Listen to a Conversation"},
    "listen_announcement": {"section": "listening", "label": "Listen to an Announcement"},
    "listen_academic": {"section": "listening", "label": "Listen to an Academic Talk"},
    "build_sentence": {"section": "writing", "label": "Build a Sentence"},
    "write_email": {"section": "writing", "label": "Write an Email (7 min)"},
    "write_discussion": {"section": "writing", "label": "Write for an Academic Discussion (10 min)"},
    "speak_repeat": {"section": "speaking", "label": "Listen and Repeat"},
    "speak_interview": {"section": "speaking", "label": "Take an Interview"},
}

def _ensure_toefl_v13_schema():
    """Add columns for TOEFL question types (idempotent)."""
    try:
        conn = _db_safe()
        c = conn.cursor()
        new_cols = [
            ("q_type", "TEXT DEFAULT 'mcq'"),
            ("skill_section", "TEXT"),
            ("passage_text", "TEXT"),
            ("audio_source", "TEXT"),
            ("audio_cached_url", "TEXT"),
            ("blanks_json", "TEXT"),
            ("time_limit_seconds", "INTEGER"),
            ("word_count_min", "INTEGER"),
            ("word_count_max", "INTEGER"),
            ("rubric_json", "TEXT"),
            ("order_in_set", "INTEGER DEFAULT 0"),
            ("set_id", "TEXT"),
        ]
        c.execute("PRAGMA table_info(stage_exam_questions)")
        existing = [r[1] for r in c.fetchall()]
        added = 0
        for col, typ in new_cols:
            if col not in existing:
                try:
                    c.execute(f"ALTER TABLE stage_exam_questions ADD COLUMN {col} {typ}")
                    added += 1
                except Exception as ce:
                    print(f"[Phase13.1] col {col} skip: {ce}")
        # Writing/Speaking responses table
        c.execute("""CREATE TABLE IF NOT EXISTS toefl_free_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT,
            question_id INTEGER,
            attempt_id INTEGER,
            response_text TEXT,
            response_audio_url TEXT,
            ai_score REAL,
            ai_band REAL,
            ai_feedback TEXT,
            teacher_score REAL,
            teacher_feedback TEXT,
            final_band REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()
        print(f"[Phase13.1] Added {added} columns + toefl_free_responses table")
        conn.close()
    except Exception as e:
        print(f"[Phase13.1] schema error: {e}")

# ===== CEFR / Band Score Mapper (ETS 2026 official) =====
def raw_to_band(raw, section):
    """Map raw section score to Band 1-6 per ETS 2026 concordance."""
    section = (section or "").lower()
    if section in ("reading", "listening"):
        table = [(29,6),(27,5.5),(24,5),(22,4.5),(18,4),(12,3.5),(6,3),(4,2.5),(3,2),(2,1.5),(0,1)] if section=="reading"             else [(28,6),(26,5.5),(22,5),(20,4.5),(17,4),(13,3.5),(9,3),(6,2.5),(4,2),(2,1.5),(0,1)]
    elif section == "writing":
        table = [(29,6),(27,5.5),(24,5),(21,4.5),(17,4),(15,3.5),(13,3),(10,2.5),(5,2),(3,1.5),(0,1)]
    elif section == "speaking":
        table = [(28,6),(27,5.5),(25,5),(23,4.5),(20,4),(18,3.5),(16,3),(13,2.5),(11,2),(5,1.5),(0,1)]
    else:
        # percentage 0-100 → band
        pct = float(raw)
        if pct >= 95: return 6
        if pct >= 88: return 5.5
        if pct >= 80: return 5
        if pct >= 72: return 4.5
        if pct >= 60: return 4
        if pct >= 48: return 3.5
        if pct >= 36: return 3
        if pct >= 24: return 2.5
        if pct >= 12: return 2
        if pct >= 5: return 1.5
        return 1
    r = float(raw)
    for threshold, band in table:
        if r >= threshold: return band
    return 1

def band_to_cefr(band):
    """Map Band 1-6 to CEFR level."""
    b = float(band)
    if b >= 6: return "C2"
    if b >= 5: return "C1"
    if b >= 4: return "B2"
    if b >= 3: return "B1"
    if b >= 2: return "A2"
    return "A1"

# ===== Telegram Audio Resolver =====
import urllib.request as _ureq, urllib.parse as _uparse, json as _json_mod
def resolve_telegram_audio(source):
    """Convert any audio source format to a playable URL.
    Supports:
      - "tg_file_id:BAACAg..." -> resolved via Bot API getFile
      - "https://t.me/..." -> returned as-is (opens Telegram)
      - any https:// URL -> returned as-is
    """
    if not source: return None
    source = str(source).strip()
    if source.startswith("tg_file_id:"):
        fid = source.replace("tg_file_id:", "").strip()
        token = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            return None
        try:
            url = f"https://api.telegram.org/bot{token}/getFile?file_id={_uparse.quote(fid)}"
            with _ureq.urlopen(url, timeout=10) as r:
                data = _json_mod.loads(r.read().decode("utf-8"))
            if data.get("ok") and data.get("result", {}).get("file_path"):
                fp = data["result"]["file_path"]
                return f"https://api.telegram.org/file/bot{token}/{fp}"
        except Exception as e:
            print(f"[resolve_telegram_audio] error: {e}")
            return None
    if source.startswith("http"):
        return source
    return None

@app.route("/api/audio/resolve")
def api_audio_resolve():
    """Resolve audio source to playable URL (for student exam pages)."""
    from flask import request, jsonify
    src = request.args.get("src", "")
    url = resolve_telegram_audio(src)
    if url:
        return jsonify({"ok": True, "url": url})
    return jsonify({"ok": False, "error": "could not resolve"}), 404

@app.route("/api/admin/question-types")
def api_question_types():
    from flask import jsonify
    return jsonify({"types": TOEFL_QUESTION_TYPES})

try:
    _ensure_toefl_v13_schema()
except Exception as _e:
    print(f"[Phase13.1] hook error: {_e}")
# ===== End Phase 13.1 =====

# ===== Phase 13.2: Content Importer Engine =====
import json as _json_imp, os as _os_imp
from flask import request as _req_imp, jsonify as _jsonify_imp

CONTENT_DIR = _os_imp.environ.get("CONTENT_DIR", "content/toefl_bank")

def _ensure_content_dir():
    try:
        _os_imp.makedirs(CONTENT_DIR, exist_ok=True)
    except Exception as e:
        print(f"[Content] mkdir err: {e}")

_ensure_content_dir()

@app.route("/api/admin/content/list")
def api_content_list():
    """List all available content JSON files."""
    _ensure_content_dir()
    try:
        files = []
        if _os_imp.path.isdir(CONTENT_DIR):
            for fn in sorted(_os_imp.listdir(CONTENT_DIR)):
                if fn.endswith(".json"):
                    fp = _os_imp.path.join(CONTENT_DIR, fn)
                    size = _os_imp.path.getsize(fp)
                    try:
                        with open(fp, "r", encoding="utf-8") as f:
                            meta = _json_imp.load(f)
                        files.append({
                            "filename": fn,
                            "size_bytes": size,
                            "title": meta.get("title", fn),
                            "stage_id": meta.get("stage_id"),
                            "q_type": meta.get("q_type"),
                            "skill_section": meta.get("skill_section"),
                            "questions_count": len(meta.get("questions", [])),
                            "description": meta.get("description", "")
                        })
                    except Exception as me:
                        files.append({"filename": fn, "size_bytes": size, "error": str(me)})
        return _jsonify_imp({"ok": True, "files": files, "dir": CONTENT_DIR})
    except Exception as e:
        return _jsonify_imp({"ok": False, "error": str(e)}), 500

@app.route("/api/admin/content/preview")
def api_content_preview():
    """Preview a content file before importing."""
    fn = _req_imp.args.get("file", "")
    if not fn or "/" in fn or ".." in fn:
        return _jsonify_imp({"ok": False, "error": "invalid filename"}), 400
    fp = _os_imp.path.join(CONTENT_DIR, fn)
    if not _os_imp.path.isfile(fp):
        return _jsonify_imp({"ok": False, "error": "not found"}), 404
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = _json_imp.load(f)
        # Return first 3 questions as preview
        preview = dict(data)
        preview["questions"] = data.get("questions", [])[:3]
        preview["total_questions"] = len(data.get("questions", []))
        return _jsonify_imp({"ok": True, "preview": preview})
    except Exception as e:
        return _jsonify_imp({"ok": False, "error": str(e)}), 500

@app.route("/api/admin/content/import", methods=["POST"])
def api_content_import():
    """Import a JSON content file into stage_exam_questions."""
    data = _req_imp.get_json() or {}
    fn = data.get("file", "") or _req_imp.args.get("file", "")
    replace_existing = bool(data.get("replace_existing", False))
    if not fn or "/" in fn or ".." in fn:
        return _jsonify_imp({"ok": False, "error": "invalid filename"}), 400
    fp = _os_imp.path.join(CONTENT_DIR, fn)
    if not _os_imp.path.isfile(fp):
        return _jsonify_imp({"ok": False, "error": "file not found"}), 404
    try:
        with open(fp, "r", encoding="utf-8") as f:
            bank = _json_imp.load(f)
        stage_id = bank.get("stage_id")
        if not stage_id:
            return _jsonify_imp({"ok": False, "error": "stage_id required in JSON"}), 400
        questions = bank.get("questions", [])
        if not questions:
            return _jsonify_imp({"ok": False, "error": "no questions"}), 400

        conn = _db_safe()
        c = conn.cursor()

        # Optional: delete existing for this stage+q_type
        deleted = 0
        if replace_existing:
            q_type_filter = bank.get("q_type")
            if q_type_filter:
                c.execute("DELETE FROM stage_exam_questions WHERE stage_id=? AND q_type=?", (stage_id, q_type_filter))
            else:
                c.execute("DELETE FROM stage_exam_questions WHERE stage_id=?", (stage_id,))
            deleted = c.rowcount

        inserted = 0
        errors = []
        set_id_default = bank.get("set_id") or fn.replace(".json", "")
        for idx, q in enumerate(questions, start=1):
            try:
                c.execute("""INSERT INTO stage_exam_questions
                    (stage_id, q_type, skill_section, question_text,
                     option_a, option_b, option_c, option_d, correct_answer,
                     explanation, concept_ar, explanation_ar, trap_ar,
                     review_lesson_id, review_lesson_title,
                     passage_text, audio_source, blanks_json,
                     time_limit_seconds, word_count_min, word_count_max,
                     rubric_json, set_id, order_in_set, difficulty,
                     strategy_ar, elimination_ar)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        stage_id,
                        q.get("q_type") or bank.get("q_type", "mcq"),
                        q.get("skill_section") or bank.get("skill_section"),
                        q.get("question_text", ""),
                        q.get("option_a"), q.get("option_b"),
                        q.get("option_c"), q.get("option_d"),
                        (q.get("correct_answer") or "").upper(),
                        q.get("explanation"),
                        q.get("concept_ar"), q.get("explanation_ar"),
                        q.get("trap_ar"),
                        q.get("review_lesson_id"),
                        q.get("review_lesson_title"),
                        q.get("passage_text") or bank.get("passage_text"),
                        q.get("audio_source") or bank.get("audio_source"),
                        _json_imp.dumps(q["blanks"]) if q.get("blanks") else None,
                        q.get("time_limit_seconds"),
                        q.get("word_count_min"), q.get("word_count_max"),
                        _json_imp.dumps(q["rubric"]) if q.get("rubric") else None,
                        q.get("set_id") or set_id_default,
                        q.get("order_in_set", idx),
                        q.get("difficulty", "medium"),
                        q.get("strategy_ar"),
                        q.get("elimination_ar")
                    ))
                inserted += 1
            except Exception as ie:
                errors.append(f"Q{idx}: {ie}")
        conn.commit()
        conn.close()
        return _jsonify_imp({
            "ok": True,
            "imported": inserted,
            "deleted": deleted,
            "errors": errors,
            "stage_id": stage_id,
            "file": fn
        })
    except Exception as e:
        return _jsonify_imp({"ok": False, "error": str(e)}), 500
# ===== End Phase 13.2 Importer =====

# ===== Phase 13.3: Performance Indexes + Cache + Share =====
def _ensure_performance_indexes():
    """Create critical indexes on hot tables (idempotent)."""
    indexes = [
        # students
        ("idx_students_paid", "students", "is_paid, is_active"),
        # lesson_questions (174+ rows, no index!)
        ("idx_lq_lesson", "lesson_questions", "lesson_id"),
        ("idx_lq_lesson_order", "lesson_questions", "lesson_id, order_num"),
        # error_bank
        ("idx_eb_user", "error_bank", "user_id"),
        ("idx_eb_user_q", "error_bank", "user_id, question_id"),
        # student_error_bank
        ("idx_seb_tg", "student_error_bank", "telegram_id"),
        # stage_exam_questions (hot table now)
        ("idx_seq_stage", "stage_exam_questions", "stage_id"),
        ("idx_seq_stage_type", "stage_exam_questions", "stage_id, q_type"),
        ("idx_seq_set", "stage_exam_questions", "set_id, order_in_set"),
        # stage_exam_attempts
        ("idx_sea_tg", "stage_exam_attempts", "telegram_id"),
        ("idx_sea_tg_stage", "stage_exam_attempts", "telegram_id, stage_id"),
        # lessons
        ("idx_lessons_stage", "lessons", "stage_id, order_index"),
        ("idx_lessons_active", "lessons", "is_active, stage_id"),
        # payments
        ("idx_pay_student", "payments", "user_id, status"),
        # student_progress (if exists)
        ("idx_sp_student", "student_progress", "student_id"),
    ]
    try:
        conn = _db_safe()
        c = conn.cursor()
        created = 0
        for name, table, cols in indexes:
            try:
                # Check if table exists
                exists = c.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone()
                if not exists:
                    continue
                c.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table}({cols})")
                created += 1
            except Exception as ie:
                print(f"[Phase13.3 idx] skip {name}: {ie}")
        conn.commit()
        # Run ANALYZE to update statistics
        try:
            c.execute("ANALYZE")
            conn.commit()
        except Exception:
            pass
        print(f"[Phase13.3] Indexes ensured: {created}")
        conn.close()
    except Exception as e:
        print(f"[Phase13.3] index error: {e}")

# ===== In-memory micro-cache (per-worker, TTL based) =====
import time as _time_cache
_CACHE_STORE = {}
_CACHE_TTL = 30  # seconds

def _cache_get(key):
    rec = _CACHE_STORE.get(key)
    if not rec: return None
    if _time_cache.time() - rec[0] > _CACHE_TTL:
        _CACHE_STORE.pop(key, None)
        return None
    return rec[1]

def _cache_set(key, value):
    _CACHE_STORE[key] = (_time_cache.time(), value)
    # Prevent unbounded growth
    if len(_CACHE_STORE) > 200:
        # Drop oldest 50
        oldest = sorted(_CACHE_STORE.items(), key=lambda x: x[1][0])[:50]
        for k, _ in oldest:
            _CACHE_STORE.pop(k, None)

def cached_response(key_prefix, ttl=30):
    """Decorator for caching JSON GET responses."""
    def deco(fn):
        from functools import wraps
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from flask import request as _rq
            if _rq.method != "GET":
                return fn(*args, **kwargs)
            key = f"{key_prefix}:{_rq.full_path}"
            hit = _cache_get(key)
            if hit is not None:
                return hit
            result = fn(*args, **kwargs)
            _cache_set(key, result)
            return result
        return wrapper
    return deco

# ===== Share-progress endpoint =====
@app.route("/api/student/share-text")
def api_share_text():
    """Generate a sharable text for a student's achievement."""
    from flask import request as _rq, jsonify as _jf
    user_id = _rq.args.get("user_id", "")
    xp = _rq.args.get("xp", "0")
    streak = _rq.args.get("streak", "0")
    score = _rq.args.get("score", "")
    stage = _rq.args.get("stage", "")
    lines = ["🎯 إنجازي اليوم في Yamen Academy:"]
    if score: lines.append(f"📊 درجتي: {score}%")
    if stage: lines.append(f"📚 المرحلة: {stage}")
    if xp and xp != "0": lines.append(f"⚡ XP المكتسبة: {xp}")
    if streak and streak != "0": lines.append(f"🔥 سلسلة متواصلة: {streak} يوم")
    lines.append("")
    lines.append("انضم لي وتعلّم TOEFL معاً! 🚀")
    lines.append("https://t.me/YamenAcademy_Bot")
    text = "\n".join(lines)
    return _jf({"ok": True, "text": text})

try:
    _ensure_performance_indexes()
except Exception as _e:
    print(f"[Phase13.3] hook error: {_e}")
# ===== End Phase 13.3 =====







# ===== Phase 12E-3 v2: Stage Exam enhancements =====
def _ensure_stage_exam_v2_columns():
    """Add concept_ar, explanation_ar, trap_ar, review_lesson_id, review_lesson_title columns."""
    try:
        conn = _db_safe()
        c = conn.cursor()
        # Ensure base tables exist first
        c.execute("""CREATE TABLE IF NOT EXISTS stage_exam_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stage_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
            correct_answer TEXT NOT NULL,
            explanation TEXT,
            difficulty TEXT DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS stage_exam_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT,
            stage_id INTEGER,
            score REAL,
            total_questions INTEGER,
            correct_count INTEGER,
            passed INTEGER DEFAULT 0,
            answers_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        # Add new columns (idempotent)
        new_cols = [
            ("concept_ar", "TEXT"),
            ("explanation_ar", "TEXT"),
            ("trap_ar", "TEXT"),
            ("review_lesson_id", "INTEGER"),
            ("review_lesson_title", "TEXT"),
        ]
        c.execute("PRAGMA table_info(stage_exam_questions)")
        existing = [row[1] for row in c.fetchall()]
        added = 0
        for col_name, col_type in new_cols:
            if col_name not in existing:
                try:
                    c.execute(f"ALTER TABLE stage_exam_questions ADD COLUMN {col_name} {col_type}")
                    added += 1
                except Exception as ce:
                    print(f"[Phase12E3v2] col {col_name} skip: {ce}")
        conn.commit()
        print(f"[Phase12E3v2] Added {added} new columns to stage_exam_questions")
        conn.close()
    except Exception as e:
        print(f"[Phase12E3v2] migration error: {e}")

try:
    _ensure_stage_exam_v2_columns()
except Exception as _e:
    print(f"[Phase12E3v2] startup hook error: {_e}")
# ===== End Phase 12E-3 v2 =====





@app.route("/")
def index():
    from flask import render_template
    return render_template("admin_dashboard.html")

@app.route("/student")
def student():
    from flask import render_template
    return render_template("student_dashboard.html")

@app.route("/api/admin/stats")
def api_stats():
    conn = get_db()
    try:
        total    = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        paid     = conn.execute("SELECT COUNT(*) FROM students WHERE is_paid=1").fetchone()[0]
        active   = conn.execute("SELECT COUNT(*) FROM students WHERE is_active=1").fetchone()[0]
        pending  = conn.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
        plans_c  = conn.execute("SELECT COUNT(*) FROM subscription_plans WHERE is_active=1").fetchone()[0]
        revenue  = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='verified'").fetchone()[0]
        return jsonify({"total_students":total,"paid_students":paid,"active_students":active,
                        "pending_payments":pending,"active_plans":plans_c,"total_revenue":revenue})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Students Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/students")
def api_students():
    q = request.args.get("q","").strip()
    conn = get_db()
    try:
        if q:
            rows = conn.execute(
                "SELECT * FROM students WHERE full_name LIKE ? OR username LIKE ? OR CAST(telegram_id AS TEXT) LIKE ? ORDER BY xp DESC",
                (f"%{q}%",f"%{q}%",f"%{q}%")).fetchall()
        else:
            rows = conn.execute("SELECT * FROM students ORDER BY xp DESC LIMIT 200").fetchall()
        return jsonify({"students":[dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/admin/students/<int:uid>")
def api_student_detail(uid):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM students WHERE telegram_id=?", (uid,)).fetchone()
        if not row: return jsonify({"error":"not found"}), 404
        return jsonify(dict(row))
    finally:
        conn.close()

@app.route("/api/admin/students/<int:uid>/activate-paid", methods=["POST"])
def api_activate_paid(uid):
    activate_paid(uid)
    return jsonify({"ok": True})

@app.route("/api/admin/students/<int:uid>/deactivate-paid", methods=["POST"])
def api_deactivate_paid(uid):
    deactivate_paid(uid)
    return jsonify({"ok": True})

@app.route("/api/admin/students/<int:uid>/toggle-active", methods=["POST"])
def api_toggle_active(uid):
    conn = get_db()
    try:
        row = conn.execute("SELECT is_active FROM students WHERE telegram_id=?", (uid,)).fetchone()
        if not row: return jsonify({"error":"not found"}), 404
        new_val = 0 if row[0] else 1
        conn.execute("UPDATE students SET is_active=? WHERE telegram_id=?", (new_val, uid))
        conn.commit()
        return jsonify({"ok": True, "is_active": new_val})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Questions Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/questions", methods=["GET"])
def api_get_questions():
    skill = request.args.get("skill","")
    conn = get_db()
    try:
        if skill:
            rows = conn.execute("SELECT * FROM questions WHERE skill=? ORDER BY id DESC", (skill,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM questions ORDER BY id DESC LIMIT 200").fetchall()
        return jsonify({"questions":[dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/admin/questions", methods=["POST"])
def api_add_question():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO questions
            (question_text,option_a,option_b,option_c,option_d,correct_option,skill,difficulty,explanation,timer_seconds)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (d.get("question_text",""), d.get("option_a",""), d.get("option_b",""),
             d.get("option_c",""), d.get("option_d",""), d.get("correct_option","a"),
             d.get("skill","grammar"), d.get("difficulty","medium"),
             d.get("explanation",""), int(d.get("timer_seconds",30))))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/questions/<int:qid>", methods=["DELETE"])
def api_delete_question(qid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM questions WHERE id=?", (qid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Lessons Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/lessons", methods=["GET"])
def api_get_lessons():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM lessons ORDER BY phase, order_num").fetchall()
        return jsonify({"lessons":[dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/admin/lessons", methods=["POST"])
def api_add_lesson():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO lessons
            (title,title_ar,description,skill,phase,order_num,content,xp_reward,timer_minutes,is_active)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (d.get("title",""), d.get("title_ar",""), d.get("description",""),
             d.get("skill","reading"), int(d.get("phase",1)), int(d.get("order_num",0)),
             d.get("content",""), int(d.get("xp_reward",10)),
             int(d.get("timer_minutes",0)), int(d.get("is_active",1))))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/lessons/<int:lid>", methods=["PUT"])
def api_update_lesson(lid):
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""UPDATE lessons SET title=?,title_ar=?,description=?,skill=?,
            phase=?,order_num=?,content=?,xp_reward=?,timer_minutes=?,is_active=?
            WHERE id=?""",
            (d.get("title",""), d.get("title_ar",""), d.get("description",""),
             d.get("skill","reading"), int(d.get("phase",1)), int(d.get("order_num",0)),
             d.get("content",""), int(d.get("xp_reward",10)),
             int(d.get("timer_minutes",0)), int(d.get("is_active",1)), lid))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/lessons/<int:lid>", methods=["DELETE"])
def api_delete_lesson(lid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM lessons WHERE id=?", (lid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Missions Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/missions", methods=["GET"])
def api_get_missions():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM daily_missions ORDER BY id DESC").fetchall()
        return jsonify({"missions":[dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/admin/missions", methods=["POST"])
def api_add_mission():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO daily_missions (title,description,mission_type,target_count,xp_reward)
            VALUES (?,?,?,?,?)""",
            (d.get("title",""), d.get("description",""), d.get("mission_type","quiz"),
             int(d.get("target_count",1)), int(d.get("xp_reward",20))))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/missions/<int:mid>", methods=["DELETE"])
def api_delete_mission(mid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM daily_missions WHERE id=?", (mid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Plans Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/plans", methods=["GET"])
def api_get_plans():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM subscription_plans ORDER BY price").fetchall()
        return jsonify({"plans":[dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/admin/plans", methods=["POST"])
def api_add_plan():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO subscription_plans
            (name,name_ar,price,currency,duration_days,description,features,is_active,is_featured)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (d.get("name",""), d.get("name_ar",""), float(d.get("price",25000)),
             d.get("currency","IQD"), int(d.get("duration_days",30)),
             d.get("description",""), json.dumps(d.get("features",[])),
             int(d.get("is_active",1)), int(d.get("is_featured",0))))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/plans/<int:pid>", methods=["PUT"])
def api_update_plan(pid):
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""UPDATE subscription_plans SET
            name=?,name_ar=?,price=?,currency=?,duration_days=?,
            description=?,features=?,is_active=?,is_featured=? WHERE id=?""",
            (d.get("name",""), d.get("name_ar",""), float(d.get("price",25000)),
             d.get("currency","IQD"), int(d.get("duration_days",30)),
             d.get("description",""), json.dumps(d.get("features",[])),
             int(d.get("is_active",1)), int(d.get("is_featured",0)), pid))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/plans/<int:pid>", methods=["DELETE"])
def api_delete_plan(pid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM subscription_plans WHERE id=?", (pid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/plans/<int:pid>/toggle", methods=["POST"])
def api_toggle_plan(pid):
    conn = get_db()
    try:
        row = conn.execute("SELECT is_active FROM subscription_plans WHERE id=?", (pid,)).fetchone()
        if not row: return jsonify({"error":"not found"}), 404
        new_val = 0 if row[0] else 1
        conn.execute("UPDATE subscription_plans SET is_active=? WHERE id=?", (new_val, pid))
        conn.commit()
        return jsonify({"ok": True, "is_active": new_val})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Payments Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/payments", methods=["GET"])
def api_get_payments():
    conn = get_db()
    try:
        rows = conn.execute("""SELECT p.*, s.full_name, s.username
            FROM payments p LEFT JOIN students s ON p.user_id=s.telegram_id
            ORDER BY p.created_at DESC LIMIT 100""").fetchall()
        return jsonify({"payments":[dict(r) for r in rows]})
    finally:
        conn.close()

@app.route("/api/admin/payments/<int:pid>/verify", methods=["POST"])
def api_verify_payment(pid):
    conn = get_db()
    try:
        row = conn.execute("SELECT user_id FROM payments WHERE id=?", (pid,)).fetchone()
        if not row: return jsonify({"error":"not found"}), 404
        conn.execute("UPDATE payments SET status='verified', verified_at=CURRENT_TIMESTAMP WHERE id=?", (pid,))
        conn.execute("UPDATE students SET is_paid=1 WHERE telegram_id=?", (row[0],))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Settings Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/settings", methods=["GET"])
def api_get_settings():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM system_settings").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/admin/settings", methods=["POST"])
def api_update_settings():
    d = request.json or {}
    for key, value in d.items():
        set_setting(key, str(value))
    return jsonify({"ok": True})

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Phase settings Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/phases", methods=["GET"])
def api_get_phases():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM phase_settings ORDER BY phase_number").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/admin/phases/<int:phase_num>", methods=["PUT"])
def api_update_phase(phase_num):
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""UPDATE phase_settings SET
            phase_name=?,min_xp=?,min_streak=?,min_quiz_score=?,min_attendance_days=?,description=?
            WHERE phase_number=?""",
            (d.get("phase_name",""), int(d.get("min_xp",0)), int(d.get("min_streak",0)),
             float(d.get("min_quiz_score",0)), int(d.get("min_attendance_days",0)),
             d.get("description",""), phase_num))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Broadcast Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/broadcast", methods=["POST"])
def api_broadcast():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO broadcasts (title,message,target,target_user_id)
            VALUES (?,?,?,?)""",
            (d.get("title",""), d.get("message",""),
             d.get("target","all"), int(d.get("target_user_id",0))))
        conn.commit()
        return jsonify({"ok": True, "note": "saved - bot will send on next cycle"})
    finally:
        conn.close()

@app.route("/api/admin/broadcast/history", methods=["GET"])
def api_broadcast_history():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM broadcasts ORDER BY created_at DESC LIMIT 50").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Student messages Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/messages", methods=["GET"])
def api_get_messages():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM student_messages ORDER BY created_at DESC LIMIT 100").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/admin/messages/<int:mid>/read", methods=["POST"])
def api_mark_read(mid):
    conn = get_db()
    try:
        conn.execute("UPDATE student_messages SET is_read=1 WHERE id=?", (mid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/student/message", methods=["POST"])
def api_student_message():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO student_messages (user_id,username,full_name,message)
            VALUES (?,?,?,?)""",
            (int(d.get("user_id",0)), d.get("username",""),
             d.get("full_name",""), d.get("message","")))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Public endpoints Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/public/plans", methods=["GET"])
def api_public_plans():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM subscription_plans WHERE is_active=1 ORDER BY price").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/user/graduation-status", methods=["GET"])
def api_grad_status():
    uid = request.args.get("user_id", 0, type=int)
    if not uid:
        return jsonify({"error": "user_id required"}), 400
    conn = get_db()
    try:
        student = conn.execute("SELECT * FROM students WHERE telegram_id=?", (uid,)).fetchone()
        if not student:
            return jsonify({"error": "not found"}), 404
        s = dict(student)
        min_xp    = int(get_setting("graduation_min_xp", "500"))
        min_tasks = int(get_setting("graduation_min_tasks", "50"))
        min_streak= int(get_setting("graduation_min_streak", "7"))
        min_mock  = float(get_setting("graduation_min_mock_score", "70"))
        checks = {
            "xp":     {"current": s.get("xp",0),             "required": min_xp,    "ok": s.get("xp",0) >= min_xp},
            "tasks":  {"current": s.get("tasks_completed",0), "required": min_tasks, "ok": s.get("tasks_completed",0) >= min_tasks},
            "streak": {"current": s.get("streak",0),          "required": min_streak,"ok": s.get("streak",0) >= min_streak},
            "mock":   {"current": s.get("mock_score",0),       "required": min_mock,  "ok": s.get("mock_score",0) >= min_mock},
        }
        ready = all(v["ok"] for v in checks.values())
        return jsonify({"ready": ready, "checks": checks, "student": s})
    finally:
        conn.close()


# Ã¢â€â‚¬Ã¢â€â‚¬ Phase Settings Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/phase-settings", methods=["GET"])
def api_phase_settings_get():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM phase_settings ORDER BY phase_number").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/admin/phase-settings/<int:pid>", methods=["PUT"])
def api_phase_settings_put(pid):
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("""UPDATE phase_settings SET phase_name=?,min_xp=?,min_streak=?,
            min_quiz_score=?,min_attendance_days=?,description=? WHERE phase_number=?""",
            (d.get("phase_name",""), int(d.get("min_xp",0)), int(d.get("min_streak",0)),
             float(d.get("min_quiz_score",0)), int(d.get("min_attendance_days",0)),
             d.get("description",""), pid))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬ Grading Rules Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/grading-rules", methods=["GET"])
def api_grading_rules_get():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM essay_grading_rules ORDER BY id").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route("/api/admin/grading-rules", methods=["POST"])
def api_grading_rules_post():
    d = request.json or {}
    conn = get_db()
    try:
        conn.execute("INSERT INTO essay_grading_rules (criteria,max_score,description) VALUES (?,?,?)",
            (d.get("criteria",""), int(d.get("max_score",10)), d.get("description","")))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/api/admin/grading-rules/<int:rid>", methods=["DELETE"])
def api_grading_rules_delete(rid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM essay_grading_rules WHERE id=?", (rid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


# Ã¢â€â‚¬Ã¢â€â‚¬ Quiz Result from Student Portal Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/student/quiz-result", methods=["POST"])
def api_quiz_result():
    d = request.json or {}
    uid      = int(d.get("user_id", 0))
    skill    = d.get("skill", "")
    xp_earned= int(d.get("xp_earned", 0))
    score    = float(d.get("score", 0))
    if uid and xp_earned > 0:
        conn = get_db()
        try:
            conn.execute("UPDATE students SET xp=xp+?, tasks_completed=tasks_completed+1 WHERE telegram_id=?",
                         (xp_earned, uid))
            conn.execute("INSERT INTO xp_log (user_id,amount,reason) VALUES (?,?,?)",
                         (uid, xp_earned, f"quiz_{skill}_{score:.0f}%"))
            conn.commit()
        finally:
            conn.close()
    return jsonify({"ok": True})


# Ã¢â€â‚¬Ã¢â€â‚¬ Add Student Manually Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/admin/students/add", methods=["POST"])
def api_add_student():
    d = request.json or {}
    tid  = int(d.get("telegram_id", 0))
    name = d.get("full_name", "").strip()
    user = d.get("username", "").strip()
    paid = int(d.get("is_paid", 0))
    if not tid:
        return jsonify({"error": "telegram_id Ã™â€¦Ã˜Â·Ã™â€žÃ™Ë†Ã˜Â¨"}), 400
    conn = get_db()
    try:
        conn.execute("""INSERT OR IGNORE INTO students
            (telegram_id, full_name, username, is_paid, is_active)
            VALUES (?,?,?,?,1)""", (tid, name, user, paid))
        if paid:
            conn.execute("UPDATE students SET is_paid=1 WHERE telegram_id=?", (tid,))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# Ã¢â€â‚¬Ã¢â€â‚¬ Phase Settings Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Entry point Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@app.route("/api/student/profile", methods=["GET"])
def api_student_profile():
    uid = request.args.get("user_id", "")
    if not uid:
        return jsonify({"error": "user_id required"}), 400
    conn = get_db()
    try:
        # Ã˜Â§Ã˜Â¨Ã˜Â­Ã˜Â« Ã˜Â¨Ã™Æ’Ã™â€žÃ˜Â§ Ã˜Â§Ã™â€žÃ˜Â¹Ã™â€¦Ã™Ë†Ã˜Â¯Ã™Å Ã™â€ 
        s = conn.execute(
            "SELECT * FROM students WHERE user_id=? OR telegram_id=?",
            (uid, uid)
        ).fetchone()
        if not s:
            return jsonify({"found": False})
        d = dict(s)
        return jsonify({
            "found": True,
            "is_paid": bool(d.get("is_paid", 0)),
            "is_active": bool(d.get("is_active", 0)),
            "full_name": d.get("full_name") or d.get("name", ""),
            "level": d.get("level", "beginner"),
            "xp": d.get("xp", 0) or d.get("total_xp", 0),
            "streak": d.get("streak", 0) or d.get("streak_days", 0),
            "placement_done": bool(d.get("placement_done", 0)),
            "current_phase": d.get("current_phase", 1) or d.get("stage", 1),
            "tasks_completed": d.get("tasks_completed", 0),
            "completed_lessons": d.get("completed_lessons", 0),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# Payment Approval / Rejection endpoints
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

@app.route("/api/admin/payments/<int:pid>/approve", methods=["POST"])
def api_approve_payment(pid):
    from datetime import datetime
    conn = get_db()
    try:
        pay = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
        if not pay:
            return jsonify({"error": "Payment not found"}), 404
        pay = dict(pay)
        uid = pay.get("user_id") or pay.get("telegram_id")
        plan_id = pay.get("plan_id", 1)

        # Ã˜ÂªÃ™ÂÃ˜Â¹Ã™Å Ã™â€ž Ã˜Â§Ã™â€žÃ˜Â·Ã˜Â§Ã™â€žÃ˜Â¨
        conn.execute("""
            UPDATE students SET is_paid=1, is_active=1,
            subscription_type='paid',
            last_activity=?
            WHERE user_id=? OR telegram_id=?
        """, (datetime.now().isoformat(), uid, str(uid)))

        # Ã˜ÂªÃ˜Â­Ã˜Â¯Ã™Å Ã˜Â« Ã˜Â­Ã˜Â§Ã™â€žÃ˜Â© Ã˜Â§Ã™â€žÃ˜Â¯Ã™ÂÃ˜Â¹
        conn.execute("""
            UPDATE payments SET status='approved', verified_at=?
            WHERE id=?
        """, (datetime.now().isoformat(), pid))

        conn.commit()

        # Ã˜Â¥Ã˜Â´Ã˜Â¹Ã˜Â§Ã˜Â± Ã˜Â§Ã™â€žÃ˜Â·Ã˜Â§Ã™â€žÃ˜Â¨ Ã˜Â¹Ã˜Â¨Ã˜Â± Ã˜Â§Ã™â€žÃ˜Â¨Ã™Ë†Ã˜Âª
        try:
            import asyncio, os
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            token = os.environ.get("BOT_TOKEN", "")
            if token and uid:
                async def notify():
                    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                    await bot.send_message(
                        chat_id=int(uid),
                        text="Ã¢Å“â€¦ <b>Ã˜ÂªÃ™â€¦ Ã˜ÂªÃ™ÂÃ˜Â¹Ã™Å Ã™â€ž Ã˜Â§Ã˜Â´Ã˜ÂªÃ˜Â±Ã˜Â§Ã™Æ’Ã™Æ’!</b>\n\nÃ™â€¦Ã˜Â±Ã˜Â­Ã˜Â¨Ã˜Â§Ã™â€¹ Ã˜Â¨Ã™Æ’ Ã™ÂÃ™Å  Ã˜Â£Ã™Æ’Ã˜Â§Ã˜Â¯Ã™Å Ã™â€¦Ã™Å Ã˜Â© Ã™Å Ã˜Â§Ã™â€¦Ã™â€  Ã™â€žÃ™â€žÃ˜ÂªÃ™Ë†Ã™ÂÃ™â€ž Ã°Å¸Å½â€œ\nÃ˜Â§Ã˜Â¨Ã˜Â¯Ã˜Â£ Ã˜Â±Ã˜Â­Ã™â€žÃ˜ÂªÃ™Æ’ Ã˜Â§Ã™â€žÃ˜ÂªÃ˜Â¹Ã™â€žÃ™Å Ã™â€¦Ã™Å Ã˜Â© Ã˜Â§Ã™â€žÃ˜Â¢Ã™â€ !"
                    )
                    await bot.session.close()
                asyncio.run(notify())
        except Exception as e:
            print(f"Bot notify error: {e}")

        return jsonify({"ok": True, "message": "Ã˜ÂªÃ™â€¦ Ã˜ÂªÃ™ÂÃ˜Â¹Ã™Å Ã™â€ž Ã˜Â§Ã™â€žÃ˜Â·Ã˜Â§Ã™â€žÃ˜Â¨"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/admin/payments/<int:pid>/reject", methods=["POST"])
def api_reject_payment(pid):
    conn = get_db()
    try:
        pay = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
        if not pay:
            return jsonify({"error": "Payment not found"}), 404
        pay = dict(pay)
        uid = pay.get("user_id") or pay.get("telegram_id")

        conn.execute("UPDATE payments SET status='rejected' WHERE id=?", (pid,))
        conn.commit()

        # Ã˜Â¥Ã˜Â´Ã˜Â¹Ã˜Â§Ã˜Â± Ã˜Â§Ã™â€žÃ˜Â·Ã˜Â§Ã™â€žÃ˜Â¨
        try:
            import asyncio, os
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            token = os.environ.get("BOT_TOKEN", "")
            if token and uid:
                async def notify():
                    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                    await bot.send_message(
                        chat_id=int(uid),
                        text="Ã¢ÂÅ’ <b>Ã˜ÂªÃ™â€¦ Ã˜Â±Ã™ÂÃ˜Â¶ Ã˜Â·Ã™â€žÃ˜Â¨ Ã˜Â§Ã™â€žÃ˜Â§Ã˜Â´Ã˜ÂªÃ˜Â±Ã˜Â§Ã™Æ’</b>\n\nÃ™Å Ã˜Â±Ã˜Â¬Ã™â€° Ã˜Â§Ã™â€žÃ˜ÂªÃ™Ë†Ã˜Â§Ã˜ÂµÃ™â€ž Ã™â€¦Ã˜Â¹ Ã˜Â§Ã™â€žÃ˜Â£Ã˜Â¯Ã™â€¦Ã™â€  Ã™â€žÃ™â€žÃ™â€¦Ã˜Â²Ã™Å Ã˜Â¯ Ã™â€¦Ã™â€  Ã˜Â§Ã™â€žÃ™â€¦Ã˜Â¹Ã™â€žÃ™Ë†Ã™â€¦Ã˜Â§Ã˜Âª."
                    )
                    await bot.session.close()
                asyncio.run(notify())
        except Exception as e:
            print(f"Bot notify error: {e}")

        return jsonify({"ok": True, "message": "Ã˜ÂªÃ™â€¦ Ã˜Â±Ã™ÂÃ˜Â¶ Ã˜Â§Ã™â€žÃ˜Â·Ã™â€žÃ˜Â¨"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/admin/students/<int:uid>/delete", methods=["DELETE"])
def api_delete_student(uid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM students WHERE user_id=? OR telegram_id=?", (uid, str(uid)))
        conn.execute("DELETE FROM payments WHERE user_id=? OR telegram_id=?", (uid, str(uid)))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/admin/students/<int:uid>/send-message", methods=["POST"])
def api_send_message_to_student(uid):
    d = request.json or {}
    text = d.get("text", "").strip()
    if not text:
        return jsonify({"error": "Ã˜Â§Ã™â€žÃ™â€ Ã˜Âµ Ã™â€¦Ã˜Â·Ã™â€žÃ™Ë†Ã˜Â¨"}), 400
    try:
        import asyncio, os
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        token = os.environ.get("BOT_TOKEN", "")
        if not token:
            return jsonify({"error": "BOT_TOKEN Ã˜ÂºÃ™Å Ã˜Â± Ã™â€¦Ã˜Â¶Ã˜Â¨Ã™Ë†Ã˜Â·"}), 500
        async def send():
            bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            await bot.send_message(chat_id=uid, text=text)
            await bot.session.close()
        asyncio.run(send())
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# Ã°Å¸â€œÅ¡ LESSON CONTENT MANAGEMENT Ã¢â‚¬â€ Phase 2A
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

ALLOWED_ITEM_TABLES = {
    "words":     "lesson_letter_fill",
    "texts":     "lesson_practice_texts",
    "questions": "lesson_questions",
    "dragdrop":  "lesson_drag_drop",
}

def _get_lesson_or_404(lid):
    conn = get_db()
    row = conn.execute("SELECT * FROM lessons WHERE id=?", (lid,)).fetchone()
    conn.close()
    return dict(row) if row else None


@app.route("/api/admin/lessons/<int:lid>/full", methods=["GET"])
def api_lesson_full(lid):
    """Return everything for one lesson."""
    try:
        lesson = _get_lesson_or_404(lid)
        if not lesson:
            return jsonify({"error": "Lesson not found"}), 404

        # parse explanation_json if exists
        try:
            lesson["explanation"] = json.loads(lesson.get("explanation_json") or "{}")
        except Exception:
            lesson["explanation"] = {}

        conn = get_db()
        words = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_letter_fill WHERE lesson_id=? ORDER BY order_num, id", (lid,)).fetchall()]
        for w in words:
            try:
                w["letter_array"] = json.loads(w.get("letter_array_json") or "[]")
            except Exception:
                w["letter_array"] = []

        texts = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_practice_texts WHERE lesson_id=? ORDER BY order_num, id", (lid,)).fetchall()]
        for t in texts:
            try:
                t["answers"] = json.loads(t.get("answers_json") or "{}")
            except Exception:
                t["answers"] = {}

        questions = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_questions WHERE lesson_id=? ORDER BY order_num, id", (lid,)).fetchall()]
        for q in questions:
            try:
                q["options"] = json.loads(q.get("options_json") or "{}")
            except Exception:
                q["options"] = {}

        dragdrops = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_drag_drop WHERE lesson_id=? ORDER BY order_num, id", (lid,)).fetchall()]
        for d in dragdrops:
            try:
                d["items"] = json.loads(d.get("items_json") or "[]")
                d["correct_order"] = json.loads(d.get("correct_order_json") or "[]")
            except Exception:
                d["items"] = []
                d["correct_order"] = []

        conn.close()
        return jsonify({
            "lesson": lesson,
            "words": words,
            "texts": texts,
            "questions": questions,
            "dragdrops": dragdrops,
            "counts": {
                "words": len(words),
                "texts": len(texts),
                "questions": len(questions),
                "dragdrops": len(dragdrops),
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/<int:lid>/words", methods=["POST"])
def api_add_word(lid):
    """Add a letter-fill word to a lesson."""
    try:
        if not _get_lesson_or_404(lid):
            return jsonify({"error": "Lesson not found"}), 404
        d = request.get_json(force=True) or {}
        word = (d.get("word") or "").strip().upper()
        if not word:
            return jsonify({"error": "word required"}), 400
        letter_array = d.get("letter_array") or list(word)

        conn = get_db()
        cur = conn.cursor()
        order_num = (cur.execute(
            "SELECT COALESCE(MAX(order_num),0)+1 FROM lesson_letter_fill WHERE lesson_id=?",
            (lid,)).fetchone()[0])
        cur.execute("""
            INSERT INTO lesson_letter_fill
            (lesson_id, word, translation, sentence, hint, letter_array_json, order_num)
            VALUES (?,?,?,?,?,?,?)
        """, (lid, word, d.get("translation",""), d.get("sentence",""),
              d.get("hint",""), json.dumps(letter_array, ensure_ascii=False), order_num))
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "id": new_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/<int:lid>/texts", methods=["POST"])
def api_add_text(lid):
    """Add a practice text."""
    try:
        if not _get_lesson_or_404(lid):
            return jsonify({"error": "Lesson not found"}), 404
        d = request.get_json(force=True) or {}
        content = (d.get("content") or "").strip()
        if not content:
            return jsonify({"error": "content required"}), 400

        conn = get_db()
        cur = conn.cursor()
        order_num = (cur.execute(
            "SELECT COALESCE(MAX(order_num),0)+1 FROM lesson_practice_texts WHERE lesson_id=?",
            (lid,)).fetchone()[0])
        cur.execute("""
            INSERT INTO lesson_practice_texts
            (lesson_id, text_id, level, text_type, content, answers_json, order_num)
            VALUES (?,?,?,?,?,?,?)
        """, (lid, d.get("text_id",""), d.get("level","easy"),
              d.get("text_type","complete_words"), content,
              json.dumps(d.get("answers", {}), ensure_ascii=False), order_num))
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "id": new_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/<int:lid>/questions", methods=["POST"])
def api_add_lesson_question(lid):
    """Add a question to a lesson (timer default 30s)."""
    try:
        if not _get_lesson_or_404(lid):
            return jsonify({"error": "Lesson not found"}), 404
        d = request.get_json(force=True) or {}
        question = (d.get("question") or "").strip()
        if not question:
            return jsonify({"error": "question required"}), 400

        conn = get_db()
        cur = conn.cursor()
        order_num = (cur.execute(
            "SELECT COALESCE(MAX(order_num),0)+1 FROM lesson_questions WHERE lesson_id=? AND order_num<999",
            (lid,)).fetchone()[0])
        cur.execute("""
            INSERT INTO lesson_questions
            (lesson_id, q_id, q_type, question, passage_ref,
             options_json, correct_answer, explanation, evidence,
             common_trap, tip, timer_seconds, order_num)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (lid, d.get("q_id",""), d.get("q_type","factual"),
              question, d.get("passage_ref",""),
              json.dumps(d.get("options", {}), ensure_ascii=False),
              d.get("correct_answer","A"),
              d.get("explanation",""), d.get("evidence",""),
              d.get("common_trap",""), d.get("tip",""),
              int(d.get("timer_seconds", 30)), order_num))
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "id": new_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/<int:lid>/dragdrop", methods=["POST"])
def api_add_dragdrop(lid):
    """Add a drag-and-drop exercise."""
    try:
        if not _get_lesson_or_404(lid):
            return jsonify({"error": "Lesson not found"}), 404
        d = request.get_json(force=True) or {}
        title = (d.get("title") or "").strip()
        items = d.get("items") or []
        correct_order = d.get("correct_order") or []
        if not items:
            return jsonify({"error": "items required"}), 400

        conn = get_db()
        cur = conn.cursor()
        order_num = (cur.execute(
            "SELECT COALESCE(MAX(order_num),0)+1 FROM lesson_drag_drop WHERE lesson_id=?",
            (lid,)).fetchone()[0])
        cur.execute("""
            INSERT INTO lesson_drag_drop
            (lesson_id, title, exercise_type, instructions,
             items_json, correct_order_json, order_num)
            VALUES (?,?,?,?,?,?,?)
        """, (lid, title, d.get("exercise_type","sentence_order"),
              d.get("instructions",""),
              json.dumps(items, ensure_ascii=False),
              json.dumps(correct_order, ensure_ascii=False), order_num))
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "id": new_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/import-json", methods=["POST"])
def api_import_lesson_json():
    """Import a full lesson from JSON (single lesson object or {'lessons': [...]})"""
    try:
        d = request.get_json(force=True) or {}
        # supports both: single lesson, or { "lessons": [...] }
        lessons_in = d.get("lessons") if "lessons" in d else [d]
        if not isinstance(lessons_in, list) or not lessons_in:
            return jsonify({"error": "no lessons in JSON"}), 400

        conn = get_db()
        cur = conn.cursor()
        added = []

        XP_DEFAULT = 40

        for L in lessons_in:
            code = (L.get("lesson_id") or L.get("code") or "").strip()
            title = (L.get("title") or "").strip() or "Untitled"
            focus = L.get("focus_point","")
            exp_json = json.dumps(L.get("explanation", {}), ensure_ascii=False)
            xp = int(L.get("xp_reward", XP_DEFAULT))
            skill = L.get("skill","reading")
            phase = int(L.get("phase", 1))
            timer_min = int(L.get("timer_minutes", 15))

            # next order_num
            order_num = (cur.execute(
                "SELECT COALESCE(MAX(order_num),0)+1 FROM lessons").fetchone()[0])

            cur.execute("""
                INSERT INTO lessons
                (title, title_ar, lesson_code, focus_point, explanation_json,
                 skill, phase, order_num, xp_reward, timer_minutes, is_active, content)
                VALUES (?,?,?,?,?,?,?,?,?,?,1,?)
            """, (title, title, code, focus, exp_json, skill, phase,
                  order_num, xp, timer_min, focus))
            lesson_pk = cur.lastrowid

            # words
            for i, w in enumerate(L.get("letter_fill_exercise",{}).get("target_words",[]), start=1):
                cur.execute("""
                    INSERT INTO lesson_letter_fill
                    (lesson_id, word, translation, sentence, hint, letter_array_json, order_num)
                    VALUES (?,?,?,?,?,?,?)
                """, (lesson_pk, w.get("word",""), w.get("translation",""),
                      w.get("sentence",""), w.get("hint",""),
                      json.dumps(w.get("letter_array",[]), ensure_ascii=False), i))

            # practice texts (all levels merged)
            order = 0
            for level_key in ("easy","medium","intermediate","difficult"):
                for t in L.get("practice_texts",{}).get(level_key, []):
                    order += 1
                    cur.execute("""
                        INSERT INTO lesson_practice_texts
                        (lesson_id, text_id, level, text_type, content, answers_json, order_num)
                        VALUES (?,?,?,?,?,?,?)
                    """, (lesson_pk, t.get("id",""), level_key, "complete_words",
                          t.get("text",""),
                          json.dumps(t.get("answers",{}), ensure_ascii=False), order))

            # generic questions list (multiple shapes)
            def _insert_question(q, qtype, passage=""):
                cur.execute("""
                    INSERT INTO lesson_questions
                    (lesson_id, q_id, q_type, question, passage_ref,
                     options_json, correct_answer, explanation, evidence,
                     common_trap, tip, timer_seconds, order_num)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,30,0)
                """, (lesson_pk, q.get("q_id",""), qtype,
                      q.get("question",""), q.get("passage", passage),
                      json.dumps(q.get("options",{}), ensure_ascii=False),
                      q.get("correct_answer",""),
                      q.get("explanation",""), q.get("evidence",""),
                      q.get("common_trap",""), q.get("tip","")))

            pq = L.get("practice_questions", {})
            type_map = {
                "factual_questions":"factual",
                "negative_factual_questions":"negative_factual",
                "vocabulary_questions":"vocabulary",
                "inference_questions":"inference",
                "rhetorical_purpose_questions":"rhetorical",
                "insert_sentence_questions":"insert_sentence",
                "paragraph_relationship_questions":"paragraph_relation",
            }
            if isinstance(pq, dict):
                for cat, qlist in pq.items():
                    if isinstance(qlist, list):
                        for q in qlist:
                            _insert_question(q, type_map.get(cat, cat))

            for sk in ("practice_set","practice_set_1","practice_set_2"):
                ps = L.get(sk, {})
                for q in ps.get("questions", []):
                    _insert_question(q, q.get("type","factual").lower().replace(" ","_"),
                                     ps.get("passage_title",""))

            fq = L.get("final_comprehensive_quiz", {})
            for q in fq.get("questions", []):
                _insert_question(q, q.get("type","factual").lower().replace(" ","_"))

            iq = L.get("inference_question", {})
            if iq:
                cur.execute("""
                    INSERT INTO lesson_questions
                    (lesson_id, q_id, q_type, question, options_json,
                     correct_answer, explanation, timer_seconds, order_num)
                    VALUES (?,?,'inference',?,?,?,?,30,999)
                """, (lesson_pk, f"{code}_final" if code else "final",
                      iq.get("question",""),
                      json.dumps(iq.get("options",{}), ensure_ascii=False),
                      iq.get("correct_answer",""),
                      iq.get("explanation","")))

            added.append({"id": lesson_pk, "code": code, "title": title})

        conn.commit()
        conn.close()
        return jsonify({"ok": True, "added": added, "count": len(added)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lesson-item/<table>/<int:item_id>", methods=["DELETE"])
def api_delete_lesson_item(table, item_id):
    """Delete a word/text/question/dragdrop item."""
    try:
        tbl = ALLOWED_ITEM_TABLES.get(table)
        if not tbl:
            return jsonify({"error": "invalid table"}), 400
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {tbl} WHERE id=?", (item_id,))
        conn.commit()
        affected = cur.rowcount
        conn.close()
        return jsonify({"ok": True, "deleted": affected})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lesson-item/<table>/<int:item_id>", methods=["PUT"])
def api_update_lesson_item(table, item_id):
    """Update a lesson item (partial update with whitelisted columns)."""
    try:
        tbl = ALLOWED_ITEM_TABLES.get(table)
        if not tbl:
            return jsonify({"error": "invalid table"}), 400
        d = request.get_json(force=True) or {}

        # whitelist columns per table
        allowed_cols = {
            "lesson_letter_fill":     ["word","translation","sentence","hint","letter_array_json","order_num"],
            "lesson_practice_texts":  ["text_id","level","text_type","content","answers_json","order_num"],
            "lesson_questions":       ["q_id","q_type","question","passage_ref","options_json",
                                       "correct_answer","explanation","evidence","common_trap",
                                       "tip","timer_seconds","order_num"],
            "lesson_drag_drop":       ["title","exercise_type","instructions","items_json",
                                       "correct_order_json","order_num"],
        }[tbl]

        # auto-convert dict/list fields to JSON string
        json_fields = {"options","letter_array","answers","items","correct_order"}
        body = {}
        for k, v in d.items():
            if k in json_fields:
                body[k + "_json"] = json.dumps(v, ensure_ascii=False)
            else:
                body[k] = v

        sets, vals = [], []
        for col in allowed_cols:
            if col in body:
                sets.append(f"{col}=?")
                vals.append(body[col])
        if not sets:
            return jsonify({"error": "no valid fields"}), 400
        vals.append(item_id)

        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"UPDATE {tbl} SET {', '.join(sets)} WHERE id=?", vals)
        conn.commit()
        affected = cur.rowcount
        conn.close()
        return jsonify({"ok": True, "updated": affected})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Student Lessons API Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/lessons", methods=["GET"])
def api_student_lessons():
    """Returns active lessons for students."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, lesson_code, title, title_ar, description,
                   COALESCE(skill_type, skill) AS skill_type,
                   COALESCE(skill, skill_type) AS skill,
                   COALESCE(stage, phase, 1) AS stage,
                   COALESCE(phase, stage, 1) AS phase,
                   COALESCE(xp_reward, 20) AS xp_reward,
                   COALESCE(order_num, id) AS order_num,
                   focus_point, is_active
            FROM lessons
            WHERE COALESCE(is_active, 1) = 1
            ORDER BY stage, phase, order_num, id
        """).fetchall()
        return jsonify({"lessons": [dict(r) for r in rows]})
    finally:
        conn.close()


@app.route("/api/lessons/<int:lid>", methods=["GET"])
def api_student_lesson_detail(lid):
    """Returns one full lesson with words/texts/questions for students."""
    conn = get_db()
    try:
        lesson_row = conn.execute(
            "SELECT * FROM lessons WHERE id=? AND COALESCE(is_active,1)=1",
            (lid,)
        ).fetchone()
        if not lesson_row:
            return jsonify({"error": "Lesson not found"}), 404
        lesson = dict(lesson_row)
        try:
            lesson["explanation"] = json.loads(lesson.get("explanation_json") or "{}")
        except Exception:
            lesson["explanation"] = {}

        words = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_letter_fill WHERE lesson_id=? ORDER BY order_num, id",
            (lid,)
        ).fetchall()]
        texts = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_practice_texts WHERE lesson_id=? ORDER BY order_num, id",
            (lid,)
        ).fetchall()]
        questions = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_questions WHERE lesson_id=? ORDER BY order_num, id",
            (lid,)
        ).fetchall()]
        dragdrops = [dict(r) for r in conn.execute(
            "SELECT * FROM lesson_drag_drop WHERE lesson_id=? ORDER BY order_num, id",
            (lid,)
        ).fetchall()]
        return jsonify({
            "lesson": lesson,
            "words": words,
            "texts": texts,
            "questions": questions,
            "dragdrops": dragdrops,
            "counts": {
                "words": len(words), "texts": len(texts),
                "questions": len(questions), "dragdrops": len(dragdrops)
            }
        })
    finally:
        conn.close()


@app.route("/api/lessons/<int:lid>/complete", methods=["POST"])
def api_student_complete_lesson(lid):
    """Marks a lesson as completed and awards XP."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or data.get("telegram_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    conn = get_db()
    try:
        lesson = conn.execute(
            "SELECT id, xp_reward, COALESCE(skill, skill_type, 'reading') AS skill FROM lessons WHERE id=?",
            (lid,)
        ).fetchone()
        if not lesson:
            return jsonify({"error": "Lesson not found"}), 404
        xp = int(lesson["xp_reward"] or 20)
        skill = lesson["skill"] or "reading"
        conn.execute(
            "UPDATE students SET xp = COALESCE(xp,0) + ?, total_xp = COALESCE(total_xp,0) + ? WHERE telegram_id=?",
            (xp, xp, user_id)
        )
        try:
            conn.execute(
                "INSERT INTO xp_log (user_id, amount, reason) VALUES (?,?,?)",
                (user_id, xp, "lesson_" + str(lid) + "_" + skill)
            )
        except Exception:
            pass
        conn.commit()
        return jsonify({"ok": True, "xp_awarded": xp, "skill": skill})
    finally:
        conn.close()



# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Student Profile by ID (for student_dashboard) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/api/student/<int:uid>", methods=["GET"])
def api_student_by_id(uid):
    """Returns full student profile by telegram_id for student dashboard."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM students WHERE telegram_id=?", (uid,)
        ).fetchone()
        if not row:
            return jsonify({"error": "student not found"}), 404
        d = dict(row)
        # Normalize fields the dashboard expects
        d.setdefault("level", "beginner")
        d.setdefault("xp", d.get("total_xp", 0) or 0)
        d.setdefault("streak", d.get("streak_days", 0) or 0)
        d.setdefault("missions_completed", d.get("missions_completed", 0) or 0)
        d.setdefault("placement_score", d.get("placement_score", 0) or 0)
        d.setdefault("full_name", d.get("name") or d.get("username") or "Ã˜Â·Ã˜Â§Ã™â€žÃ˜Â¨")
        return jsonify(d)
    finally:
        conn.close()


@app.route("/api/leaderboard", methods=["GET"])
def api_leaderboard():
    """Top students by XP for leaderboard tab."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT telegram_id, full_name, username,
                   COALESCE(xp, total_xp, 0) AS xp,
                   COALESCE(streak_days, streak, 0) AS streak,
                   level
            FROM students
            WHERE COALESCE(is_active, 1) = 1
            ORDER BY xp DESC
            LIMIT 50
        """).fetchall()
        return jsonify({"leaderboard": [dict(r) for r in rows]})
    finally:
        conn.close()


@app.route("/api/user/graduation-status", methods=["GET"])
def api_graduation_status():
    """Returns graduation eligibility for a student."""
    sid = request.args.get("student_id", type=int)
    if not sid:
        return jsonify({"error": "student_id required"}), 400
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM students WHERE telegram_id=?", (sid,)
        ).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        d = dict(row)
        return jsonify({
            "is_graduated": bool(d.get("is_graduated", 0)),
            "mock_score": d.get("mock_exam_score") or d.get("mock_score") or 0,
            "required_score": d.get("required_score") or 80,
            "tasks_completed": d.get("tasks_completed", 0) or 0,
            "completed_lessons": d.get("completed_lessons", 0) or 0,
            "xp": d.get("xp", 0) or 0,
        })
    finally:
        conn.close()



# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Lesson detail page Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
@app.route("/lesson/<int:lid>")
def lesson_page(lid):
    """Serves the full lesson page for students."""
    return render_template("lesson_view.html", lesson_id=lid)



# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# â”€â”€â”€ Mini App lesson page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route("/miniapp/plans")
def miniapp_plans_page():
    """Render pricing page (reads plans dynamically from /api/miniapp/plans)."""
    sid = _request.args.get("student_id", "")
    return render_template("pricing.html", student_id=sid)

@app.route("/miniapp/lesson/<int:lid>")
def miniapp_lesson_page(lid):
    from flask import render_template
    return render_template("miniapp_lesson.html", lesson_id=lid)

#  Mini App APIs â€” Phase 2 (added by automated script)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
import json as _json
import sqlite3 as _sqlite3
from datetime import datetime as _datetime, timedelta as _timedelta
from flask import jsonify as _jsonify, request as _request

def _miniapp_db():
    """Get DB connection via _db_safe (WAL+busy_timeout) + row_factory."""
    import sqlite3 as _sq
    conn = _db_safe()
    conn.row_factory = _sq.Row
    return conn




# ===================== Phase 11B: Auto-Migration =====================
def _ensure_phase11b_schema():
    """Ensure all Phase 11B columns/tables exist (idempotent, safe to call repeatedly)."""
    try:
        conn = _miniapp_db()
        cur = conn.cursor()
        # students table columns
        try:
            student_cols = [r[1] for r in cur.execute("PRAGMA table_info(students)").fetchall()]
        except Exception:
            student_cols = []
        for col, ddl in [
            ("free_plan_used", "ALTER TABLE students ADD COLUMN free_plan_used INTEGER DEFAULT 0"),
            ("free_plan_used_at", "ALTER TABLE students ADD COLUMN free_plan_used_at TEXT"),
            ("placement_score", "ALTER TABLE students ADD COLUMN placement_score INTEGER DEFAULT 0"),
            ("placement_path", "ALTER TABLE students ADD COLUMN placement_path TEXT"),
        ]:
            if col not in student_cols:
                try:
                    cur.execute(ddl)
                    print(f"[Phase11B] Added students.{col}")
                except Exception as ex:
                    print(f"[Phase11B] students.{col}: {ex}")
        # free_plan_weekly_tasks table
        cur.execute("""CREATE TABLE IF NOT EXISTS free_plan_weekly_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL, week_number INTEGER NOT NULL,
            task_type TEXT DEFAULT 'share', task_description TEXT,
            proof_image TEXT, status TEXT DEFAULT 'pending',
            submitted_at TEXT, reviewed_at TEXT, admin_note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, week_number)
        )""")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Phase11B] migration error: {e}")
        try: conn.close()
        except: pass

# Run migration on import
try:
    _ensure_phase11b_schema()
except Exception as _mig_e:
    print(f"[Phase11B] startup migration failed: {_mig_e}")
# ===================== End Phase 11B Auto-Migration =====================
@app.route("/api/miniapp/lessons")
def miniapp_lessons_list():
    """List lessons for student with status (locked/available/completed)."""
    try:
        sid = _request.args.get("student_id", type=int)
        if not sid:
            return _jsonify({"error": "student_id required"}), 400
        
        conn = _miniapp_db()
        cur = conn.cursor()
        
        # Get student
        cur.execute("SELECT user_id, current_phase, xp, track FROM students WHERE user_id=?", (sid,))
        student = cur.fetchone()
        if not student:
            conn.close()
            return _jsonify({"error": "student not found"}), 404
        
        current_phase = student["current_phase"] or 1
        
        # Get last attempt for cooldown
        cur.execute("""
            SELECT lesson_id, finished_at, passed 
            FROM lesson_attempts 
            WHERE telegram_id=? AND passed=1 
            ORDER BY finished_at DESC LIMIT 1
        """, (str(sid),))
        last_attempt = cur.fetchone()
        
        cooldown_lesson_id = None
        cooldown_until = None
        if last_attempt and last_attempt["finished_at"]:
            try:
                finished = _datetime.fromisoformat(last_attempt["finished_at"].replace(" ", "T"))
                unlock_at = finished + _timedelta(hours=24)
                if unlock_at > _datetime.utcnow():
                    cooldown_lesson_id = last_attempt["lesson_id"]
                    cooldown_until = unlock_at.isoformat()
            except Exception:
                pass
        
        # Get all completed lesson IDs for this student
        cur.execute("""
            SELECT DISTINCT lesson_id FROM lesson_attempts 
            WHERE telegram_id=? AND passed=1
        """, (str(sid),))
        completed_ids = {row["lesson_id"] for row in cur.fetchall()}
        
        # Get lessons grouped by stage
        cur.execute("""
            SELECT l.id, l.title, l.title_ar, l.skill, l.stage_id, l.order_index, 
                   l.xp_reward, l.section_name, l.content,
                   s.code as stage_code, s.name_ar as stage_name,
                   (SELECT COUNT(*) FROM lesson_questions WHERE lesson_id=l.id) as q_count
            FROM lessons l
            LEFT JOIN stages s ON s.id = l.stage_id
            WHERE l.is_active=1 AND l.stage_id <= ?
            ORDER BY l.stage_id, l.order_index
        """, (current_phase + 1,))  # show current + next stage
        
        lessons_by_stage = {}
        for row in cur.fetchall():
            lid = row["id"]
            stage_id = row["stage_id"]
            
            # Determine status
            if lid in completed_ids:
                status = "completed"
            elif cooldown_lesson_id and lid > cooldown_lesson_id and stage_id == current_phase:
                status = "locked_cooldown"
            elif stage_id > current_phase:
                status = "locked_stage"
            else:
                status = "available"
            
            if stage_id not in lessons_by_stage:
                lessons_by_stage[stage_id] = {
                    "stage_id": stage_id,
                    "stage_code": row["stage_code"],
                    "stage_name": row["stage_name"],
                    "lessons": []
                }
            
            title = row["title"] or row["title_ar"] or f"Lesson {lid}"
            lessons_by_stage[stage_id]["lessons"].append({
                "id": lid,
                "title": title,
                "skill": row["skill"] or "general",
                "section": row["section_name"] or "general",
                "xp_reward": row["xp_reward"] or 10,
                "questions_count": row["q_count"],
                "status": status,
                "order": row["order_index"]
            })
        
        conn.close()
        return _jsonify({
            "student_id": sid,
            "current_phase": current_phase,
            "cooldown_until": cooldown_until,
            "stages": list(lessons_by_stage.values())
        })
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/miniapp/lesson/<int:lid>")
def miniapp_lesson_detail(lid):
    """Get lesson content + questions (without correct answers)."""
    try:
        sid = _request.args.get("student_id", type=int)
        
        conn = _miniapp_db()
        cur = conn.cursor()
        
        # Get lesson
        cur.execute("""
            SELECT id, title, title_ar, content, skill, stage_id, xp_reward, 
                   vocabulary, grammar_rule, focus_point, section_name
            FROM lessons WHERE id=? AND is_active=1
        """, (lid,))
        lesson = cur.fetchone()
        if not lesson:
            conn.close()
            return _jsonify({"error": "lesson not found"}), 404
        
        # Get questions (without correct_answer, without explanation, without tip)
        cur.execute("""
            SELECT id, q_id, q_type, question, options_json, timer_seconds, order_num
            FROM lesson_questions 
            WHERE lesson_id=? 
            ORDER BY order_num, id
        """, (lid,))
        questions = []
        for row in cur.fetchall():
            opts = {}
            try:
                opts = _json.loads(row["options_json"] or "{}")
            except Exception:
                pass
            questions.append({
                "id": row["id"],
                "q_id": row["q_id"],
                "type": row["q_type"],
                "question": row["question"],
                "options": opts,
                "timer": row["timer_seconds"] or 30,
                "order": row["order_num"]
            })
        
        # Has the student completed this lesson?
        completed = False
        last_score = None
        if sid:
            cur.execute("""
                SELECT score_percent FROM lesson_attempts 
                WHERE telegram_id=? AND lesson_id=? AND passed=1 
                ORDER BY finished_at DESC LIMIT 1
            """, (str(sid), lid))
            r = cur.fetchone()
            if r:
                completed = True
                last_score = r["score_percent"]
        
        conn.close()
        title = lesson["title"] or lesson["title_ar"] or f"Lesson {lid}"
        return _jsonify({
            "id": lesson["id"],
            "title": title,
            "content": lesson["content"] or "",
            "skill": lesson["skill"] or "general",
            "stage_id": lesson["stage_id"],
            "xp_reward": lesson["xp_reward"] or 10,
            "vocabulary": lesson["vocabulary"],
            "grammar_rule": lesson["grammar_rule"],
            "focus_point": lesson["focus_point"],
            "section": lesson["section_name"],
            "questions": questions,
            "completed": completed,
            "last_score": last_score
        })
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/miniapp/quiz/check", methods=["POST"])
def miniapp_quiz_check():
    """Check single answer; return correctness + concept + explanation if wrong."""
    try:
        data = _request.get_json(force=True) or {}
        question_id = data.get("question_id")
        user_answer = (data.get("answer") or "").strip().upper()
        if not question_id:
            return _jsonify({"error": "question_id required"}), 400
        
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT correct_answer, concept, explanation, tip 
            FROM lesson_questions WHERE id=?
        """, (question_id,))
        q = cur.fetchone()
        conn.close()
        if not q:
            return _jsonify({"error": "question not found"}), 404
        
        correct = (q["correct_answer"] or "").strip().upper()
        is_correct = (user_answer == correct)
        
        resp = {
            "is_correct": is_correct,
            "correct_answer": correct,
        }
        # Show concept + explanation only on wrong answers
        if not is_correct:
            resp["concept"] = q["concept"] or ""
            resp["explanation"] = q["explanation"] or ""
            resp["tip"] = q["tip"] or ""
        return _jsonify(resp)
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/miniapp/quiz/submit", methods=["POST"])
def miniapp_quiz_submit():
    """Submit full quiz; save attempt; award XP; return result."""
    try:
        data = _request.get_json(force=True) or {}
        sid = data.get("student_id")
        lid = data.get("lesson_id")
        answers = data.get("answers") or []  # [{"q_id":..., "user":..., "correct":..., "is_correct":bool}, ...]
        
        if not sid or not lid:
            return _jsonify({"error": "student_id and lesson_id required"}), 400
        
        conn = _miniapp_db()
        cur = conn.cursor()
        
        # Compute score
        total = len(answers)
        correct = sum(1 for a in answers if a.get("is_correct"))
        score = (correct / total * 100) if total else 0
        passed = 1 if score >= 70 else 0
        
        now = _datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get lesson xp reward
        cur.execute("SELECT xp_reward FROM lessons WHERE id=?", (lid,))
        lrow = cur.fetchone()
        xp_reward = (lrow["xp_reward"] if lrow else 10) or 10
        xp_earned = xp_reward if passed else int(xp_reward * (score / 100))
        
        # Save attempt
        cur.execute("""
            INSERT INTO lesson_attempts 
              (telegram_id, lesson_id, started_at, finished_at, correct_count, total_questions, passed, score_percent, answers_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(sid), lid, now, now, correct, total, passed, score, _json.dumps(answers, ensure_ascii=False)))
        
        # Update student XP only if passed
        if passed:
            cur.execute("UPDATE students SET xp = COALESCE(xp,0) + ? WHERE user_id=?", (xp_earned, sid))
            # Log XP
            try:
                cur.execute("""
                    INSERT INTO xp_log (user_id, amount, reason, created_at)
                    VALUES (?, ?, ?, ?)
                """, (sid, xp_earned, f"lesson_{lid}_quiz", now))
            except Exception:
                pass  # xp_log may have different schema
        
        # Get updated XP
        cur.execute("SELECT xp FROM students WHERE user_id=?", (sid,))
        new_xp = cur.fetchone()
        new_xp_val = new_xp["xp"] if new_xp else 0
        
        conn.commit()
        conn.close()
        
        return _jsonify({
            "passed": bool(passed),
            "score": round(score, 1),
            "correct": correct,
            "total": total,
            "xp_earned": xp_earned if passed else 0,
            "total_xp": new_xp_val,
            "cooldown_hours": 24 if passed else 0
        })
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/miniapp/plans")
def miniapp_plans():
    """Get active subscription plans."""
    try:
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, name_ar, price, currency, duration_days, 
                   description, features, is_featured
            FROM subscription_plans 
            WHERE is_active=1 
            ORDER BY is_featured DESC, price ASC
        """)
        plans = []
        for row in cur.fetchall():
            features = []
            try:
                features = _json.loads(row["features"] or "[]")
            except Exception:
                features = [row["features"]] if row["features"] else []
            plans.append({
                "id": row["id"],
                "name": row["name_ar"] or row["name"],
                "price": row["price"],
                "currency": row["currency"],
                "duration_days": row["duration_days"],
                "description": row["description"],
                "features": features,
                "is_featured": bool(row["is_featured"])
            })
        conn.close()
        return _jsonify({"plans": plans})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  End of Mini App APIs
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•



# ============ PHASE 4B: QUIZ ROUTES + APIs ============
@app.route("/miniapp/quiz/<int:lid>")
def miniapp_quiz_page(lid):
    from flask import render_template
    return render_template("miniapp_quiz.html", lesson_id=lid)


@app.route("/api/miniapp/quiz/start", methods=["POST"])
def miniapp_quiz_start():
    """Start quiz: check cooldown, start attempt, return questions (no answers)."""
    try:
        import quiz_engine as qe
        data = _request.get_json(force=True) or {}
        sid = str(data.get("student_id") or "")
        lid = data.get("lesson_id")
        if not sid or not lid:
            return _jsonify({"error": "student_id and lesson_id required"}), 400

        # Cooldown check
        try:
            cd = qe.get_cooldown_status(sid, int(lid))
            if cd and cd.get("locked"):
                return _jsonify({"cooldown": cd})
        except Exception as _e:
            pass

        # Get questions (without correct answers)
        # Fetch questions directly from DB (bypass quiz_engine for accurate options_json reading)
        conn_q = _miniapp_db()
        cur_q = conn_q.cursor()
        cur_q.execute("""
            SELECT id, q_id, q_type, question, options_json, passage_ref,
                   timer_seconds, order_num
            FROM lesson_questions
            WHERE lesson_id=?
            ORDER BY order_num, id
        """, (int(lid),))
        rows = cur_q.fetchall()
        conn_q.close()

        # Shuffle order
        import random as _rnd
        rows_list = list(rows)
        _rnd.shuffle(rows_list)

        safe_questions = []
        for row in rows_list:
            try:
                opts = _json.loads(row["options_json"] or "{}")
            except Exception:
                opts = {}
            safe_questions.append({
                "id": row["id"],
                "q_id": row["q_id"],
                "q_type": row["q_type"] or "mcq",
                "question": row["question"] or "",
                "options": opts,
                "passage_ref": row["passage_ref"] or "",
                "timer_seconds": row["timer_seconds"] or 30,
                "order_num": row["order_num"] or 0,
            })

        # Start attempt
        attempt_id = None
        try:
            attempt_id = qe.start_quiz_attempt(sid, int(lid))
        except Exception as _e:
            pass

        # Get student target & required streak
        try:
            _target = qe.get_student_target(sid)
        except Exception:
            _target = 69
        try:
            _required = qe.get_required_streak(_target)
        except Exception:
            _required = 3

        return _jsonify({
            "attempt_id": attempt_id,
            "questions": safe_questions,
            "total": len(safe_questions),
            "target_score": _target,
            "required_streak": _required,
        })
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/miniapp/quiz/answer", methods=["POST"])
def miniapp_quiz_answer():
    """Check single answer; record mistake in error_bank if wrong."""
    try:
        import quiz_engine as qe
        data = _request.get_json(force=True) or {}
        sid = str(data.get("student_id") or "")
        qid = data.get("question_id")
        user_answer = (data.get("answer") or "").strip().upper()
        if not qid:
            return _jsonify({"error": "question_id required"}), 400

        # Use quiz_engine.check_answer
        is_correct, correct_ans, explanation = qe.check_answer(int(qid), user_answer)

        # Get concept, tip, evidence, common_trap from DB
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("SELECT concept, tip, evidence, common_trap, q_type, passage_ref FROM lesson_questions WHERE id=?", (int(qid),))
        row = cur.fetchone()
        conn.close()
        concept = row["concept"] if row else ""
        tip = row["tip"] if row else ""
        evidence = row["evidence"] if row else ""
        common_trap = row["common_trap"] if row else ""
        q_type_meta = row["q_type"] if row else ""
        passage_ref_meta = row["passage_ref"] if row else ""

        # Record mistake if wrong
        if not is_correct and sid:
            try:
                qe.record_mistake(sid, int(qid), user_answer, correct_ans or "")
            except Exception as _e:
                pass

        return _jsonify({
            "is_correct": is_correct,
            "correct_answer": correct_ans or "",
            "explanation": explanation or "",
            "concept": concept or "",
            "tip": tip or "",
            "evidence": evidence or "",
            "common_trap": common_trap or "",
            "q_type": q_type_meta or "",
            "passage_ref": passage_ref_meta or ""
        })
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/miniapp/quiz/finish", methods=["POST"])
def miniapp_quiz_finish():
    """Finish quiz using streak-based passing (get_required_streak)."""
    try:
        import quiz_engine as qe
        data = _request.get_json(force=True) or {}
        sid = str(data.get("student_id") or "")
        lid = data.get("lesson_id")
        attempt_id = data.get("attempt_id")
        answers = data.get("answers") or []

        if not sid or not lid:
            return _jsonify({"error": "student_id and lesson_id required"}), 400

        total = len(answers)
        correct = sum(1 for a in answers if a.get("is_correct"))

        # Compute best consecutive correct streak (in answer order)
        best_streak = 0
        cur_streak = 0
        for a in answers:
            if a.get("is_correct"):
                cur_streak += 1
                if cur_streak > best_streak:
                    best_streak = cur_streak
            else:
                cur_streak = 0

        # Get student target -> required streak
        try:
            target = qe.get_student_target(sid)
        except Exception:
            target = 69
        try:
            required = qe.get_required_streak(target)
        except Exception:
            required = 3

        passed = best_streak >= required
        score = (correct / total * 100) if total else 0

        # xp_reward from lessons
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("SELECT xp_reward FROM lessons WHERE id=?", (int(lid),))
        lrow = cur.fetchone()
        xp_reward = (lrow["xp_reward"] if lrow else 10) or 10
        conn.close()

        xp_earned = 0
        cooldown_seconds = 0
        cooldown_message = ""

        if passed:
            try:
                qe.finish_quiz_attempt(attempt_id, correct, total, answers)
            except Exception:
                pass
            xp_earned = xp_reward
            try:
                qe.clear_cooldown(sid, int(lid))
            except Exception:
                pass
        else:
            try:
                qe.finish_quiz_attempt(attempt_id, correct, total, answers)
            except Exception:
                pass
            try:
                fail_info = qe.register_failed_attempt(sid, int(lid))
                if isinstance(fail_info, dict):
                    cooldown_seconds = int(fail_info.get("wait_seconds", 0) or 0)
                    cooldown_message = fail_info.get("motivation", "") or ""
            except Exception:
                cooldown_seconds = 300

        return _jsonify({
            "passed": passed,
            "score": round(score, 1),
            "correct": correct,
            "wrong": total - correct,
            "total": total,
            "best_streak": best_streak,
            "required_streak": required,
            "target_score": target,
            "xp_earned": xp_earned,
            "cooldown_seconds": cooldown_seconds,
            "cooldown_message": cooldown_message,
        })
    except Exception as e:
        return _jsonify({"error": str(e)}), 500
# ============ END PHASE 4B ============

# ===================== Phase 10: Payment + Plans CRUD =====================
import os as _os10
from flask import send_from_directory as _send_from_directory

ZAIN_CASH_NUMBER = "0798919150"
UPLOAD_FOLDER = _os10.path.join(_os10.path.dirname(_os10.path.abspath(__file__)), "static", "uploads", "payments")
_os10.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/payment/<int:plan_id>")
def payment_page(plan_id):
    from flask import render_template
    sid = _request.args.get("student_id", "")
    return render_template("payment.html", plan_id=plan_id, student_id=sid, zain_cash=ZAIN_CASH_NUMBER)

@app.route("/api/payment/submit", methods=["POST"])
def api_payment_submit():
    import time
    try:
        sid = _request.form.get("student_id", "").strip()
        pid = _request.form.get("plan_id", "").strip()
        sender_name = _request.form.get("sender_name", "").strip()
        sender_phone = _request.form.get("sender_phone", "").strip()
        if not sid or not pid:
            return _jsonify({"error": "student_id and plan_id required"}), 400
        if "proof" not in _request.files:
            return _jsonify({"error": "proof image required"}), 400
        f = _request.files["proof"]
        if not f or f.filename == "":
            return _jsonify({"error": "empty file"}), 400
        ext = _os10.path.splitext(f.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            return _jsonify({"error": "only jpg/png/webp allowed"}), 400
        fname = "p_" + str(sid) + "_" + str(pid) + "_" + str(int(time.time())) + ext
        fpath = _os10.path.join(UPLOAD_FOLDER, fname)
        f.save(fpath)
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("SELECT name_ar, price, currency FROM subscription_plans WHERE id=?", (pid,))
        plan = cur.fetchone()
        if not plan:
            conn.close()
            return _jsonify({"error": "plan not found"}), 404
        cur.execute("INSERT INTO payments (user_id, telegram_id, plan_id, plan_name, amount, currency, status, proof_file, full_name, created_at, notes) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, datetime('now'), ?)",
            (sid, sid, pid, plan["name_ar"], plan["price"], plan["currency"], fname, sender_name, "phone:" + sender_phone))
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return _jsonify({"ok": True, "payment_id": new_id, "message": "تم استلام إثبات الدفع، سيتم مراجعته قريباً"})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/static/uploads/payments/<path:fname>")
def serve_payment_proof(fname):
    return _send_from_directory(UPLOAD_FOLDER, fname)

@app.route("/api/admin/payments/list")
def api_admin_payments_list():
    try:
        status = _request.args.get("status", "all")
        conn = _miniapp_db()
        cur = conn.cursor()
        if status == "all":
            cur.execute("SELECT p.*, sp.name_ar as plan_name_ar FROM payments p LEFT JOIN subscription_plans sp ON sp.id=p.plan_id ORDER BY p.id DESC LIMIT 200")
        else:
            cur.execute("SELECT p.*, sp.name_ar as plan_name_ar FROM payments p LEFT JOIN subscription_plans sp ON sp.id=p.plan_id WHERE p.status=? ORDER BY p.id DESC LIMIT 200", (status,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return _jsonify({"payments": rows})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/payments/<int:pid>/action", methods=["POST"])
def api_admin_payment_action(pid):
    try:
        data = _request.get_json(force=True, silent=True) or {}
        action = data.get("action", "")
        note = data.get("note", "")
        if action not in ("approve", "reject", "cancel"):
            return _jsonify({"error": "invalid action"}), 400
        status_map = {"approve": "approved", "reject": "rejected", "cancel": "cancelled"}
        new_status = status_map[action]
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("SELECT user_id, plan_id, status FROM payments WHERE id=?", (pid,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return _jsonify({"error": "payment not found"}), 404
        note_line = "\n[" + action + "] " + note
        cur.execute("UPDATE payments SET status=?, notes=COALESCE(notes,'')||?, verified_at=datetime('now') WHERE id=?", (new_status, note_line, pid))
        if action == "approve":
            cur.execute("SELECT name_ar, duration_days FROM subscription_plans WHERE id=?", (row["plan_id"],))
            plan = cur.fetchone()
            if plan:
                cur.execute("INSERT INTO subscriptions (user_id, telegram_id, plan_name, start_date, end_date, is_active) VALUES (?, ?, ?, datetime('now'), datetime('now', '+' || ? || ' days'), 1)",
                    (row["user_id"], row["user_id"], plan["name_ar"], plan["duration_days"]))
        if action == "cancel":
            cur.execute("UPDATE subscriptions SET is_active=0 WHERE user_id=? AND is_active=1", (row["user_id"],))
        conn.commit()
        conn.close()
        return _jsonify({"ok": True, "status": new_status})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/plans/list")
def api_admin_plans_list():
    try:
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM subscription_plans ORDER BY is_active DESC, is_featured DESC, price ASC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return _jsonify({"plans": rows})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/plans/create", methods=["POST"])
def api_admin_plan_create():
    try:
        d = _request.get_json(force=True, silent=True) or {}
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO subscription_plans (name, name_ar, price, currency, duration_days, description, features, is_active, is_featured, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (d.get("name", "custom"), d.get("name_ar", ""), float(d.get("price", 0)),
             d.get("currency", "JOD"), int(d.get("duration_days", 30)),
             d.get("description", ""), d.get("features", ""),
             int(d.get("is_active", 1)), int(d.get("is_featured", 0))))
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return _jsonify({"ok": True, "id": new_id})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/plans/<int:pid>/update", methods=["POST"])
def api_admin_plan_update(pid):
    try:
        d = _request.get_json(force=True, silent=True) or {}
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("UPDATE subscription_plans SET name=?, name_ar=?, price=?, currency=?, duration_days=?, description=?, features=?, is_active=?, is_featured=? WHERE id=?",
            (d.get("name", "custom"), d.get("name_ar", ""), float(d.get("price", 0)),
             d.get("currency", "JOD"), int(d.get("duration_days", 30)),
             d.get("description", ""), d.get("features", ""),
             int(d.get("is_active", 1)), int(d.get("is_featured", 0)), pid))
        conn.commit()
        conn.close()
        return _jsonify({"ok": True})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/plans/<int:pid>/delete", methods=["POST"])
def api_admin_plan_delete(pid):
    try:
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM payments WHERE plan_id=?", (pid,))
        if cur.fetchone()["c"] > 0:
            conn.close()
            return _jsonify({"error": "لا يمكن حذف باقة لها مدفوعات. عطّلها بدلاً من ذلك."}), 400
        cur.execute("DELETE FROM subscription_plans WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        return _jsonify({"ok": True})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/plans/<int:pid>/toggle", methods=["POST"])
def api_admin_plan_toggle(pid):
    try:
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("UPDATE subscription_plans SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?", (pid,))
        conn.commit()
        cur.execute("SELECT is_active FROM subscription_plans WHERE id=?", (pid,))
        row = cur.fetchone()
        conn.close()
        return _jsonify({"ok": True, "is_active": row["is_active"] if row else None})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500
# ===================== End of Phase 10 =====================

# ===================== Phase 11B: Free Plan Activation =====================
@app.route("/api/payment/free-activate", methods=["POST"])
def api_payment_free_activate():
    """Activate free plan for a student (one-time only, keeps progress)."""
    try:
        _ensure_phase11b_schema()
        data = _request.get_json(force=True, silent=True) or {}
        sid = str(data.get("student_id", "")).strip()
        pid = data.get("plan_id")
        if not sid or not pid:
            return _jsonify({"error": "student_id and plan_id required"}), 400

        conn = _miniapp_db()
        cur = conn.cursor()

        # Verify plan is actually free
        cur.execute("SELECT name_ar, price, duration_days FROM subscription_plans WHERE id=?", (pid,))
        plan = cur.fetchone()
        if not plan:
            conn.close()
            return _jsonify({"error": "الباقة غير موجودة"}), 404
        if float(plan["price"]) > 0:
            conn.close()
            return _jsonify({"error": "هذه الباقة ليست مجانية"}), 400

        # Check if student already used free plan
        cur.execute("SELECT free_plan_used FROM students WHERE user_id=?", (sid,))
        student = cur.fetchone()
        if student and student["free_plan_used"]:
            conn.close()
            return _jsonify({"error": "لقد استخدمت الباقة المجانية مسبقاً. يمكنك الاشتراك في إحدى الباقات المدفوعة."}), 400

        # Mark free plan as used (keeps all student progress intact)
        cur.execute("UPDATE students SET free_plan_used=1, free_plan_used_at=datetime('now') WHERE user_id=?", (sid,))

        # Create payment record (auto-approved)
        cur.execute("""INSERT INTO payments
            (user_id, telegram_id, plan_id, plan_name, amount, currency, status, full_name, created_at, verified_at, notes)
            VALUES (?, ?, ?, ?, 0, 'JOD', 'approved', '', datetime('now'), datetime('now'), 'تفعيل مجاني تلقائي')""",
            (sid, sid, pid, plan["name_ar"]))
        pay_id = cur.lastrowid

        # Create active subscription
        cur.execute("""INSERT INTO subscriptions
            (user_id, telegram_id, plan_name, start_date, end_date, is_active)
            VALUES (?, ?, ?, datetime('now'), datetime('now', '+' || ? || ' days'), 1)""",
            (sid, sid, plan["name_ar"], plan["duration_days"]))

        conn.commit()
        conn.close()
        return _jsonify({
            "ok": True,
            "payment_id": pay_id,
            "message": "🎉 تم تفعيل الباقة المجانية! استمتع برحلتك التعليمية."
        })
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/student/subscription-status")
def api_student_subscription_status():
    """Get current subscription status for a student (resilient to missing columns)."""
    try:
        sid = _request.args.get("student_id", "").strip()
        if not sid:
            return _jsonify({"error": "student_id required"}), 400
        conn = _miniapp_db()
        cur = conn.cursor()
        # Ensure new columns exist
        try:
            cur.execute("ALTER TABLE students ADD COLUMN free_plan_used INTEGER DEFAULT 0")
        except: pass
        try:
            cur.execute("ALTER TABLE students ADD COLUMN free_plan_used_at TEXT")
        except: pass
        try:
            cur.execute("ALTER TABLE students ADD COLUMN placement_score INTEGER DEFAULT 0")
        except: pass
        try:
            cur.execute("ALTER TABLE students ADD COLUMN placement_path TEXT")
        except: pass
        conn.commit()
        # Get available columns
        cols = [r[1] for r in cur.execute("PRAGMA table_info(students)").fetchall()]
        select_cols = []
        for c in ("free_plan_used","placement_done","placement_score","level","placement_path"):
            if c in cols:
                select_cols.append(c)
        if not select_cols:
            conn.close()
            return _jsonify({"error":"students table empty schema"}), 500
        q = "SELECT " + ",".join(select_cols) + " FROM students WHERE user_id=?"
        cur.execute(q, (sid,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return _jsonify({
                "free_plan_used": False, "placement_done": False,
                "placement_score": 0, "level": None, "placement_path": None,
                "has_active_subscription": False, "subscription": None,
                "student_exists": False
            })
        student = dict(row)
        # Active subscription
        cur.execute("""SELECT plan_name, start_date, end_date, is_active
            FROM subscriptions WHERE user_id=? AND is_active=1
            AND datetime(end_date) > datetime('now')
            ORDER BY id DESC LIMIT 1""", (sid,))
        sub = cur.fetchone()
        conn.close()
        return _jsonify({
            "student_exists": True,
            "free_plan_used": bool(student.get("free_plan_used", 0)),
            "placement_done": bool(student.get("placement_done", 0)),
            "placement_score": student.get("placement_score", 0),
            "level": student.get("level"),
            "placement_path": student.get("placement_path"),
            "has_active_subscription": sub is not None,
            "subscription": dict(sub) if sub else None
        })
    except Exception as e:
        import traceback
        return _jsonify({"error": str(e), "trace": traceback.format_exc()[:500]}), 500


# ===================== End Phase 11B Free Plan =====================

# ===================== Phase 11B: Free Plan Weekly Tasks =====================
WEEKLY_TASK_TYPES = {
    "share": "شارك الأكاديمية على وسائل التواصل (سناب/إنستا/فيسبوك)",
    "invite": "ادعُ صديقاً للتسجيل في الأكاديمية",
    "review": "اكتب تقييماً للأكاديمية على متجر التطبيقات أو جوجل",
    "story": "انشر قصة عن تجربتك مع الأكاديمية"
}

@app.route("/api/student/weekly-task/status")
def api_weekly_task_status():
    """Get current week's task status for a free plan student (fixed query)."""
    try:
        sid = _request.args.get("student_id", "").strip()
        if not sid:
            return _jsonify({"error": "student_id required"}), 400
        conn = _miniapp_db()
        cur = conn.cursor()
        # Fixed query with proper parentheses
        cur.execute("""SELECT start_date FROM subscriptions
            WHERE user_id=? AND is_active=1
            AND (plan_name LIKE ? OR plan_name LIKE ? OR plan_name LIKE ?)
            ORDER BY id DESC LIMIT 1""",
            (sid, "%مجاني%", "%تجريب%", "%free%"))
        sub = cur.fetchone()
        if not sub:
            conn.close()
            return _jsonify({"has_free_plan": False})
        import datetime as _dt
        try:
            start = _dt.datetime.strptime(sub["start_date"][:19], "%Y-%m-%d %H:%M:%S")
        except:
            start = _dt.datetime.now()
        days_passed = (_dt.datetime.now() - start).days
        current_week = (days_passed // 7) + 1
        if current_week > 4:
            conn.close()
            return _jsonify({"has_free_plan": True, "expired": True, "current_week": current_week})
        cur.execute("SELECT * FROM free_plan_weekly_tasks WHERE user_id=? AND week_number=?", (sid, current_week))
        task = cur.fetchone()
        cur.execute("SELECT week_number, status, submitted_at FROM free_plan_weekly_tasks WHERE user_id=? ORDER BY week_number", (sid,))
        history = [dict(r) for r in cur.fetchall()]
        conn.close()
        task_dict = dict(task) if task else None
        return _jsonify({
            "has_free_plan": True,
            "current_week": current_week,
            "days_passed": days_passed,
            "current_task": task_dict,
            "task_required": task_dict is None or task_dict.get("status") == "rejected",
            "is_blocked": task_dict is None and days_passed >= 7,
            "history": history,
            "task_types": WEEKLY_TASK_TYPES
        })
    except Exception as e:
        import traceback
        return _jsonify({"error": str(e), "trace": traceback.format_exc()[:500]}), 500


@app.route("/api/student/weekly-task/submit", methods=["POST"])
def api_weekly_task_submit():
    """Submit weekly task proof image."""
    try:
        sid = _request.form.get("student_id", "").strip()
        week = int(_request.form.get("week_number", 0))
        task_type = _request.form.get("task_type", "share")
        if not sid or not week:
            return _jsonify({"error": "student_id and week_number required"}), 400
        if "proof" not in _request.files:
            return _jsonify({"error": "proof image required"}), 400
        f = _request.files["proof"]
        if not f.filename:
            return _jsonify({"error": "empty file"}), 400
        ext = f.filename.rsplit(".", 1)[-1].lower()
        if ext not in ("jpg", "jpeg", "png", "webp"):
            return _jsonify({"error": "صيغة الصورة غير مدعومة"}), 400
        import os, time
        folder = os.path.join(app.root_path, "static", "uploads", "weekly_tasks")
        os.makedirs(folder, exist_ok=True)
        fname = f"week{week}_{sid}_{int(time.time())}.{ext}"
        f.save(os.path.join(folder, fname))
        rel = f"/static/uploads/weekly_tasks/{fname}"
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("""INSERT OR REPLACE INTO free_plan_weekly_tasks
            (user_id, week_number, task_type, task_description, proof_image, status, submitted_at)
            VALUES (?, ?, ?, ?, ?, 'pending', datetime('now'))""",
            (sid, week, task_type, WEEKLY_TASK_TYPES.get(task_type, ""), rel))
        conn.commit()
        conn.close()
        return _jsonify({"ok": True, "message": "✅ تم إرسال المهمة. سيراجعها الأدمن قريباً."})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/admin/weekly-tasks/list")
def api_admin_weekly_tasks_list():
    """Admin: list weekly tasks (resilient)."""
    try:
        status = _request.args.get("status", "pending")
        conn = _miniapp_db()
        cur = conn.cursor()
        # Ensure table exists
        cur.execute("""CREATE TABLE IF NOT EXISTS free_plan_weekly_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL, week_number INTEGER NOT NULL,
            task_type TEXT DEFAULT 'share', task_description TEXT,
            proof_image TEXT, status TEXT DEFAULT 'pending',
            submitted_at TEXT, reviewed_at TEXT, admin_note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, week_number)
        )""")
        conn.commit()
        if status == "all":
            cur.execute("SELECT * FROM free_plan_weekly_tasks ORDER BY submitted_at DESC LIMIT 100")
        else:
            cur.execute("SELECT * FROM free_plan_weekly_tasks WHERE status=? ORDER BY submitted_at DESC", (status,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return _jsonify({"tasks": rows, "count": len(rows)})
    except Exception as e:
        import traceback
        return _jsonify({"error": str(e), "trace": traceback.format_exc()[:500], "tasks": [], "count": 0}), 500


@app.route("/api/admin/weekly-tasks/<int:tid>/action", methods=["POST"])
def api_admin_weekly_task_action(tid):
    """Admin: approve/reject weekly task."""
    try:
        data = _request.get_json(force=True, silent=True) or {}
        action = data.get("action", "")
        note = data.get("note", "")
        if action not in ("approve", "reject"):
            return _jsonify({"error": "invalid action"}), 400
        new_status = "approved" if action == "approve" else "rejected"
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("UPDATE free_plan_weekly_tasks SET status=?, reviewed_at=datetime('now'), admin_note=? WHERE id=?",
            (new_status, note, tid))
        conn.commit()
        conn.close()
        return _jsonify({"ok": True, "status": new_status})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500
# ===================== End Weekly Tasks =====================



@app.route("/api/admin/stages/list")
def api_admin_stages_list_alias():
    """Alias: /api/admin/stages/list -> api_admin_stages (used by admin.html)."""
    return api_admin_stages()
@app.route("/api/admin/stages")
def api_admin_stages():
    """List all stages for admin panel."""
    try:
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM stages ORDER BY order_index, id")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return _jsonify({"stages": rows, "count": len(rows)})
    except Exception as e:
        import traceback
        return _jsonify({"error": str(e), "trace": traceback.format_exc()[:400], "stages": []}), 500

# ===================== Phase 11C: Weekly Task Templates =====================
def _ensure_weekly_templates_table():
    """Ensure weekly_task_templates table exists."""
    try:
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS weekly_task_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_number INTEGER UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            action_url TEXT,
            action_label TEXT DEFAULT 'اذهب للمهمة',
            icon TEXT DEFAULT '⭐',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )""")
        # Seed defaults if empty
        cur.execute("SELECT COUNT(*) FROM weekly_task_templates")
        if cur.fetchone()[0] == 0:
            defaults = [
                (1, "⭐ ريفيو على صفحة فيسبوك", "اكتب تقييماً 5 نجوم على صفحة الأكاديمية على فيسبوك. ارفع صورة الريفيو بعد النشر.",
                 "https://www.facebook.com/YamenToeflIelts/reviews", "🔗 افتح صفحة الريفيوات", "⭐"),
                (2, "👥 ادعُ صديقاً", "ادعُ صديقاً للتسجيل في الأكاديمية وأرسل صورة محادثة الدعوة معه.",
                 "https://t.me/YamenAcademyBot", "🔗 رابط البوت للدعوة", "👥"),
                (3, "📱 مشاركة قصة على إنستا/سناب", "انشر قصة عن تجربتك مع الأكاديمية على إنستغرام أو سناب شات وارفع صورة القصة.",
                 "", "📸 شارك الآن", "📱"),
                (4, "📝 تقييم على Google", "اكتب مراجعة على Google Maps أو متجر التطبيقات وارفع صورة المراجعة.",
                 "", "🔗 افتح صفحة التقييم", "📝")
            ]
            cur.executemany("""INSERT INTO weekly_task_templates
                (week_number, title, description, action_url, action_label, icon)
                VALUES (?, ?, ?, ?, ?, ?)""", defaults)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Phase11C] template table error: {e}")

try:
    _ensure_weekly_templates_table()
except Exception as _e:
    print(f"[Phase11C] init error: {_e}")


@app.route("/api/admin/weekly-templates")
def api_admin_weekly_templates_list():
    """List all weekly task templates."""
    try:
        _ensure_weekly_templates_table()
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM weekly_task_templates ORDER BY week_number")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return _jsonify({"templates": rows, "count": len(rows)})
    except Exception as e:
        import traceback
        return _jsonify({"error": str(e), "trace": traceback.format_exc()[:400]}), 500


@app.route("/api/admin/weekly-templates", methods=["POST"])
def api_admin_weekly_templates_create():
    """Create a new weekly task template."""
    try:
        _ensure_weekly_templates_table()
        data = _request.get_json(force=True, silent=True) or {}
        week = int(data.get("week_number", 0))
        if not week or week < 1:
            return _jsonify({"error": "week_number required (>=1)"}), 400
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("""INSERT INTO weekly_task_templates
            (week_number, title, description, action_url, action_label, icon, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (week, data.get("title",""), data.get("description",""),
             data.get("action_url",""), data.get("action_label","اذهب للمهمة"),
             data.get("icon","⭐"), int(data.get("is_active", 1))))
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return _jsonify({"ok": True, "id": new_id})
    except Exception as e:
        if "UNIQUE" in str(e):
            return _jsonify({"error": "أسبوع رقم {} موجود مسبقاً".format(week)}), 400
        import traceback
        return _jsonify({"error": str(e), "trace": traceback.format_exc()[:400]}), 500


@app.route("/api/admin/weekly-templates/<int:tid>", methods=["PUT","POST"])
def api_admin_weekly_templates_update(tid):
    """Update a weekly task template."""
    try:
        data = _request.get_json(force=True, silent=True) or {}
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("""UPDATE weekly_task_templates SET
            title=?, description=?, action_url=?, action_label=?, icon=?, is_active=?,
            updated_at=datetime('now') WHERE id=?""",
            (data.get("title",""), data.get("description",""), data.get("action_url",""),
             data.get("action_label","اذهب للمهمة"), data.get("icon","⭐"),
             int(data.get("is_active", 1)), tid))
        conn.commit()
        conn.close()
        return _jsonify({"ok": True})
    except Exception as e:
        import traceback
        return _jsonify({"error": str(e), "trace": traceback.format_exc()[:400]}), 500


@app.route("/api/admin/weekly-templates/<int:tid>", methods=["DELETE"])
def api_admin_weekly_templates_delete(tid):
    """Delete a weekly task template."""
    try:
        conn = _miniapp_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM weekly_task_templates WHERE id=?", (tid,))
        conn.commit()
        conn.close()
        return _jsonify({"ok": True})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500


@app.route("/api/student/weekly-task/current")
def api_student_weekly_task_current():
    """Get current week's task template for a free plan student."""
    try:
        _ensure_weekly_templates_table()
        sid = _request.args.get("student_id", "").strip()
        if not sid:
            return _jsonify({"error": "student_id required"}), 400
        conn = _miniapp_db()
        cur = conn.cursor()
        # Find active free subscription
        cur.execute("""SELECT start_date FROM subscriptions
            WHERE user_id=? AND is_active=1
            AND (plan_name LIKE ? OR plan_name LIKE ? OR plan_name LIKE ?)
            ORDER BY id DESC LIMIT 1""",
            (sid, "%مجاني%", "%تجريب%", "%free%"))
        sub = cur.fetchone()
        if not sub:
            conn.close()
            return _jsonify({"has_free_plan": False})
        import datetime as _dt
        try:
            start = _dt.datetime.strptime(sub["start_date"][:19], "%Y-%m-%d %H:%M:%S")
        except:
            start = _dt.datetime.now()
        days_passed = (_dt.datetime.now() - start).days
        current_week = (days_passed // 7) + 1
        if current_week > 4:
            conn.close()
            return _jsonify({"has_free_plan": True, "expired": True})
        # Get template for current week
        cur.execute("SELECT * FROM weekly_task_templates WHERE week_number=? AND is_active=1", (current_week,))
        tpl = cur.fetchone()
        # Get student's submission for current week
        cur.execute("SELECT * FROM free_plan_weekly_tasks WHERE user_id=? AND week_number=?", (sid, current_week))
        sub_task = cur.fetchone()
        conn.close()
        return _jsonify({
            "has_free_plan": True,
            "current_week": current_week,
            "days_passed": days_passed,
            "template": dict(tpl) if tpl else None,
            "submission": dict(sub_task) if sub_task else None,
            "can_submit": sub_task is None or (sub_task and sub_task["status"] == "rejected")
        })
    except Exception as e:
        import traceback
        return _jsonify({"error": str(e), "trace": traceback.format_exc()[:400]}), 500
# ===================== End Phase 11C =====================



@app.route('/weekly-task')
def page_weekly_task():
    """صفحة المهمة الأسبوعية للطالب"""
    return render_template('weekly-task.html')



# ============================================================
# ADMIN STAGES CRUD
# ============================================================


# [Phase12H] Old duplicate delete route removed - using v2 below


# ============================================================
# ADMIN LESSONS CRUD
# ============================================================
def _ensure_lessons_schema():
    try:
        conn = _miniapp_db(); cur = conn.cursor()
        cur.execute("PRAGMA table_info(lessons)")
        cols = [r[1] for r in cur.fetchall()]
        if "stage_id" not in cols:
            cur.execute("ALTER TABLE lessons ADD COLUMN stage_id INTEGER")
        if "order_index" not in cols:
            cur.execute("ALTER TABLE lessons ADD COLUMN order_index INTEGER DEFAULT 0")
        conn.commit(); conn.close()
    except Exception as e:
        print("[_ensure_lessons_schema]", e)


@app.route("/api/admin/lessons/by-stage/<int:stage_id>", methods=["GET"])
def api_admin_lessons_by_stage(stage_id):
    try:
        import sqlite3
        _ensure_lessons_schema()
        conn = _miniapp_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT l.*, (SELECT COUNT(*) FROM lesson_questions lq WHERE lq.lesson_id=l.id) AS q_count FROM lessons l WHERE l.stage_id=? ORDER BY COALESCE(l.order_index, l.id) ASC", (stage_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return jsonify({"lessons": rows, "count": len(rows)})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e), "lessons": []}), 500


@app.route("/api/admin/lessons/create", methods=["POST"])
def api_admin_lesson_create():
    try:
        _ensure_lessons_schema()
        data = request.get_json(force=True) or {}
        title = (data.get("title") or "").strip()
        stage_id = data.get("stage_id")
        content = data.get("content") or ""
        order_idx = data.get("order_index")
        if not title or not stage_id:
            return jsonify({"error": "title and stage_id required"}), 400
        conn = _miniapp_db(); cur = conn.cursor()
        if order_idx is None:
            cur.execute("SELECT COALESCE(MAX(order_index),0)+1 FROM lessons WHERE stage_id=?", (stage_id,))
            order_idx = cur.fetchone()[0]
        else:
            order_idx = int(order_idx)
            cur.execute("UPDATE lessons SET order_index = order_index + 1 WHERE stage_id=? AND order_index >= ?", (stage_id, order_idx))
        cur.execute("PRAGMA table_info(lessons)")
        cols = [r[1] for r in cur.fetchall()]
        ic = ["title", "stage_id", "order_index"]; iv = [title, stage_id, order_idx]
        if "content" in cols: ic.append("content"); iv.append(content)
        if "is_active" in cols: ic.append("is_active"); iv.append(1)
        ph = ",".join(["?"] * len(iv))
        cur.execute("INSERT INTO lessons (" + ",".join(ic) + ") VALUES (" + ph + ")", iv)
        lid = cur.lastrowid
        conn.commit(); conn.close()
        return jsonify({"ok": True, "id": lid, "order_index": order_idx})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/<int:lid>/update", methods=["POST", "PUT"])
def api_admin_lesson_update(lid):
    try:
        data = request.get_json(force=True) or {}
        conn = _miniapp_db(); cur = conn.cursor()
        cur.execute("PRAGMA table_info(lessons)")
        cols = [r[1] for r in cur.fetchall()]
        fields, vals = [], []
        for col in ["title", "stage_id", "order_index", "content", "is_active"]:
            if col in data and col in cols:
                fields.append(col + "=?"); vals.append(data[col])
        if not fields: return jsonify({"error": "no fields"}), 400
        vals.append(lid)
        cur.execute("UPDATE lessons SET " + ", ".join(fields) + " WHERE id=?", vals)
        conn.commit(); conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/<int:lid>/delete", methods=["POST", "DELETE"])
def api_admin_lesson_delete(lid):
    try:
        conn = _miniapp_db(); cur = conn.cursor()
        cur.execute("SELECT stage_id, order_index FROM lessons WHERE id=?", (lid,))
        row = cur.fetchone()
        if row:
            stage_id, order_idx = row
            try: cur.execute("DELETE FROM lesson_questions WHERE lesson_id=?", (lid,))
            except Exception: pass
            cur.execute("DELETE FROM lessons WHERE id=?", (lid,))
            if stage_id is not None and order_idx is not None:
                cur.execute("UPDATE lessons SET order_index = order_index - 1 WHERE stage_id=? AND order_index > ?", (stage_id, order_idx))
            conn.commit()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/<int:lid>/move", methods=["POST"])
def api_admin_lesson_move(lid):
    try:
        data = request.get_json(force=True) or {}
        new_stage_id = data.get("stage_id")
        new_order = data.get("order_index")
        if new_stage_id is None: return jsonify({"error": "stage_id required"}), 400
        conn = _miniapp_db(); cur = conn.cursor()
        cur.execute("SELECT stage_id, order_index FROM lessons WHERE id=?", (lid,))
        row = cur.fetchone()
        if not row: conn.close(); return jsonify({"error": "not found"}), 404
        old_stage, old_order = row
        if old_stage is not None and old_order is not None:
            cur.execute("UPDATE lessons SET order_index = order_index - 1 WHERE stage_id=? AND order_index > ?", (old_stage, old_order))
        if new_order is None:
            cur.execute("SELECT COALESCE(MAX(order_index),0)+1 FROM lessons WHERE stage_id=?", (new_stage_id,))
            new_order = cur.fetchone()[0]
        else:
            new_order = int(new_order)
            cur.execute("UPDATE lessons SET order_index = order_index + 1 WHERE stage_id=? AND order_index >= ? AND id<>?", (new_stage_id, new_order, lid))
        cur.execute("UPDATE lessons SET stage_id=?, order_index=? WHERE id=?", (new_stage_id, new_order, lid))
        conn.commit(); conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lessons/reorder", methods=["POST"])
def api_admin_lessons_reorder():
    try:
        data = request.get_json(force=True) or {}
        ordered_ids = data.get("ordered_ids") or []
        stage_id = data.get("stage_id")
        if not ordered_ids or stage_id is None: return jsonify({"error": "ordered_ids and stage_id required"}), 400
        conn = _miniapp_db(); cur = conn.cursor()
        for idx, lid in enumerate(ordered_ids, start=1):
            cur.execute("UPDATE lessons SET stage_id=?, order_index=? WHERE id=?", (stage_id, idx, lid))
        conn.commit(); conn.close()
        return jsonify({"ok": True, "count": len(ordered_ids)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# ADMIN LESSON QUESTIONS CRUD
# ============================================================
@app.route("/api/admin/lessons/<int:lid>/questions", methods=["GET"])
def api_admin_lesson_questions(lid):
    try:
        import sqlite3
        conn = _miniapp_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM lesson_questions WHERE lesson_id=? ORDER BY id ASC", (lid,))
            rows = [dict(r) for r in cur.fetchall()]
            # Map 'question' -> 'question_text' for JS compatibility
            for row in rows:
                if 'question' in row and 'question_text' not in row:
                    row['question_text'] = row['question']
                if 'options_json' in row and row.get('options_json'):
                    import json as _j
                    try:
                        opts = _j.loads(row['options_json'])
                        if 'option_a' not in row: row['option_a'] = opts.get('A','')
                        if 'option_b' not in row: row['option_b'] = opts.get('B','')
                        if 'option_c' not in row: row['option_c'] = opts.get('C','')
                        if 'option_d' not in row: row['option_d'] = opts.get('D','')
                    except: pass
        except Exception:
            rows = []
        conn.close()
        return jsonify({"questions": rows, "count": len(rows)})
    except Exception as e:
        return jsonify({"error": str(e), "questions": []}), 500


@app.route("/api/admin/lesson-questions/create", methods=["POST"])
def api_admin_lesson_question_create():
    try:
        data = request.get_json(force=True) or {}
        lid = data.get("lesson_id")
        q_text = (data.get("question_text") or "").strip()
        if not lid or not q_text:
            return jsonify({"error": "lesson_id and question_text required"}), 400

        import json as _json
        conn = _miniapp_db(); cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=OFF;")

        # Get actual columns
        cols_info = cur.execute("PRAGMA table_info(lesson_questions)").fetchall()
        existing_cols = [r[1] for r in cols_info]

        # Add missing columns if needed
        migrations = [
            ("question_text", "TEXT"), ("option_a", "TEXT"), ("option_b", "TEXT"),
            ("option_c", "TEXT"), ("option_d", "TEXT"), ("order_index", "INTEGER DEFAULT 0")
        ]
        for col, ctype in migrations:
            if col not in existing_cols:
                try:
                    cur.execute(f"ALTER TABLE lesson_questions ADD COLUMN {col} {ctype}")
                    existing_cols.append(col)
                except Exception:
                    pass

        # Build options_json
        opts = {"A": data.get("option_a",""), "B": data.get("option_b",""), "C": data.get("option_c",""), "D": data.get("option_d","")}

        # Get next order
        try:
            order_col = "order_num" if "order_num" in existing_cols else "order_index"
            row = cur.execute(f"SELECT COALESCE(MAX({order_col}),0) FROM lesson_questions WHERE lesson_id=?", (lid,)).fetchone()
            order = (row[0] or 0) + 1
        except Exception:
            order = 1

        # Build INSERT dynamically - only use columns that exist
        insert_map = {
            "lesson_id": lid,
            "question": q_text,
            "question_text": q_text,
            "options_json": _json.dumps(opts, ensure_ascii=False),
            "option_a": data.get("option_a", ""),
            "option_b": data.get("option_b", ""),
            "option_c": data.get("option_c", ""),
            "option_d": data.get("option_d", ""),
            "correct_answer": data.get("correct_answer", "A"),
            "explanation": data.get("explanation", ""),
            "q_type": "mcq",
        }
        # Add order column
        if "order_num" in existing_cols:
            insert_map["order_num"] = order
        if "order_index" in existing_cols:
            insert_map["order_index"] = order

        # Filter to only existing columns
        final_cols = []
        final_vals = []
        for col, val in insert_map.items():
            if col in existing_cols:
                final_cols.append(col)
                final_vals.append(val)

        placeholders = ",".join(["?"] * len(final_cols))
        sql = f"INSERT INTO lesson_questions ({','.join(final_cols)}) VALUES ({placeholders})"
        cur.execute(sql, final_vals)
        qid = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "id": qid})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/admin/lesson-questions/<int:qid>/update", methods=["POST", "PUT"])
def api_admin_lesson_question_update(qid):
    try:
        data = request.get_json(force=True) or {}
        conn = _miniapp_db(); cur = conn.cursor()
        fields, vals = [], []
        for col in ["question_text","option_a","option_b","option_c","option_d","correct_answer","explanation"]:
            if col in data:
                fields.append(col + "=?"); vals.append(data[col])
        if not fields: return jsonify({"error": "no fields"}), 400
        vals.append(qid)
        cur.execute("UPDATE lesson_questions SET " + ", ".join(fields) + " WHERE id=?", vals)
        conn.commit(); conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/lesson-questions/<int:qid>/delete", methods=["POST", "DELETE"])
def api_admin_lesson_question_delete(qid):
    try:
        conn = _miniapp_db(); cur = conn.cursor()
        cur.execute("DELETE FROM lesson_questions WHERE id=?", (qid,))
        conn.commit(); conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# ADMIN STUDENTS CRUD
# ============================================================
@app.route("/api/admin/students/list", methods=["GET"])
def api_admin_students_list():
    try:
        import sqlite3
        conn = _miniapp_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        q = (request.args.get("q") or "").strip()
        level = (request.args.get("level") or "").strip()
        page = int(request.args.get("page") or 1)
        per_page = int(request.args.get("per_page") or 50)
        offset = (page - 1) * per_page
        where, params = [], []
        if q:
            where.append("(CAST(user_id AS TEXT) LIKE ? OR full_name LIKE ?)")
            params.extend(["%" + q + "%", "%" + q + "%"])
        if level:
            where.append("level=?"); params.append(level)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        cur.execute("SELECT COUNT(*) FROM students " + where_sql, params)
        total = cur.fetchone()[0]
        cur.execute("PRAGMA table_info(students)")
        cols = [r[1] for r in cur.fetchall()]
        select_cols = "user_id"
        for c in ["full_name","level","placement_done","placement_score","placement_path","free_plan_used","free_plan_used_at","free_week_number","created_at"]:
            if c in cols: select_cols += ", " + c
        cur.execute("SELECT " + select_cols + " FROM students " + where_sql + " ORDER BY rowid DESC LIMIT ? OFFSET ?", params + [per_page, offset])
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            try:
                cur.execute("SELECT plan_name, end_date, is_active FROM subscriptions WHERE user_id=? AND is_active=1 ORDER BY id DESC LIMIT 1", (r["user_id"],))
                sub = cur.fetchone()
                r["subscription"] = dict(sub) if sub else None
            except Exception:
                r["subscription"] = None
        conn.close()
        return jsonify({"students": rows, "total": total, "page": page, "per_page": per_page})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e), "students": []}), 500


@app.route("/api/admin/students/<user_id>/update", methods=["POST", "PUT"])
def api_admin_student_update(user_id):
    try:
        data = request.get_json(force=True) or {}
        conn = _miniapp_db(); cur = conn.cursor()
        cur.execute("PRAGMA table_info(students)")
        cols = [r[1] for r in cur.fetchall()]
        fields, vals = [], []
        for c in ["full_name","level","placement_score","placement_path","free_plan_used"]:
            if c in data and c in cols:
                fields.append(c + "=?"); vals.append(data[c])
        if not fields: return jsonify({"error": "no fields"}), 400
        vals.append(user_id)
        cur.execute("UPDATE students SET " + ", ".join(fields) + " WHERE user_id=?", vals)
        conn.commit(); conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/students/<user_id>/delete", methods=["POST", "DELETE"])
def api_admin_student_delete(user_id):
    try:
        conn = _miniapp_db(); cur = conn.cursor()
        cur.execute("DELETE FROM students WHERE user_id=?", (user_id,))
        try: cur.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))
        except Exception: pass
        try: cur.execute("DELETE FROM free_plan_weekly_tasks WHERE user_id=?", (user_id,))
        except Exception: pass
        conn.commit(); conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/students/<user_id>/detail", methods=["GET"])
def api_admin_student_detail(user_id):
    try:
        import sqlite3
        conn = _miniapp_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM students WHERE user_id=?", (user_id,))
        s = cur.fetchone()
        if not s: return jsonify({"error": "not found"}), 404
        out = dict(s)
        try:
            cur.execute("SELECT * FROM subscriptions WHERE user_id=? ORDER BY id DESC", (user_id,))
            out["subscriptions"] = [dict(r) for r in cur.fetchall()]
        except Exception: out["subscriptions"] = []
        try:
            cur.execute("SELECT * FROM free_plan_weekly_tasks WHERE user_id=? ORDER BY week_number", (user_id,))
            out["weekly_tasks"] = [dict(r) for r in cur.fetchall()]
        except Exception: out["weekly_tasks"] = []
        conn.close()
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# ADMIN DASHBOARD STATS
# ============================================================
@app.route("/api/admin/dashboard/stats", methods=["GET"])
def api_admin_dashboard_stats():
    try:
        conn = _miniapp_db(); cur = conn.cursor()
        stats = {}
        try:
            cur.execute("SELECT COUNT(*) FROM students"); stats["total_students"] = cur.fetchone()[0]
        except Exception: stats["total_students"] = 0
        try:
            cur.execute("SELECT COUNT(*) FROM subscriptions WHERE is_active=1"); stats["active_subscriptions"] = cur.fetchone()[0]
        except Exception: stats["active_subscriptions"] = 0
        try:
            cur.execute("SELECT COUNT(*) FROM payments WHERE status='pending'"); stats["pending_payments"] = cur.fetchone()[0]
        except Exception: stats["pending_payments"] = 0
        try:
            cur.execute("SELECT COUNT(*) FROM free_plan_weekly_tasks WHERE status='pending'"); stats["pending_tasks"] = cur.fetchone()[0]
        except Exception: stats["pending_tasks"] = 0
        try:
            cur.execute("SELECT COUNT(*) FROM stages"); stats["total_stages"] = cur.fetchone()[0]
        except Exception: stats["total_stages"] = 0
        try:
            cur.execute("SELECT COUNT(*) FROM lessons"); stats["total_lessons"] = cur.fetchone()[0]
        except Exception: stats["total_lessons"] = 0
        try:
            cur.execute("SELECT COUNT(*) FROM lesson_questions"); stats["total_questions"] = cur.fetchone()[0]
        except Exception: stats["total_questions"] = 0
        try:
            cur.execute("SELECT COUNT(*) FROM students WHERE created_at >= datetime('now','-7 days')")
            stats["new_students_7d"] = cur.fetchone()[0]
        except Exception: stats["new_students_7d"] = 0
        conn.close()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500





# ============================================================
# PHASE 12B: PATHS, GRADUATION, MASTERY LEARNING
# ============================================================

def _ensure_phase12b_schema():
    import sqlite3
    conn = _miniapp_db()
    cur = conn.cursor()
    # students new columns
    cur.execute("PRAGMA table_info(students)")
    cols = [r[1] for r in cur.fetchall()]
    new_cols = {
        "current_path": "TEXT DEFAULT 'foundation'",
        "xp_total": "INTEGER DEFAULT 0",
        "streak_days": "INTEGER DEFAULT 0",
        "last_active_date": "TEXT",
        "graduation_unlocked": "INTEGER DEFAULT 0",
        "graduation_unlocked_by": "TEXT",
        "graduation_unlocked_at": "TEXT",
        "graduated": "INTEGER DEFAULT 0",
        "graduation_score": "REAL",
        "certificate_url": "TEXT",
    }
    for col, ddl in new_cols.items():
        if col not in cols:
            try:
                cur.execute("ALTER TABLE students ADD COLUMN " + col + " " + ddl)
            except Exception as e:
                print("[12B alter students]", col, e)
    # student_progress
    cur.execute("""CREATE TABLE IF NOT EXISTS student_progress (
        user_id TEXT, lesson_id INTEGER,
        status TEXT DEFAULT 'locked',
        score REAL DEFAULT 0, best_score REAL DEFAULT 0,
        attempts INTEGER DEFAULT 0, xp_earned INTEGER DEFAULT 0,
        started_at TEXT, completed_at TEXT,
        PRIMARY KEY (user_id, lesson_id)
    )""")
    # final exam questions
    cur.execute("""CREATE TABLE IF NOT EXISTS final_exam_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT, section TEXT, difficulty INTEGER DEFAULT 3,
        question_text TEXT,
        option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
        correct_answer TEXT, explanation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    # path config
    cur.execute("""CREATE TABLE IF NOT EXISTS path_config (
        path TEXT PRIMARY KEY,
        display_name TEXT, min_score REAL, max_score REAL,
        passing_threshold REAL DEFAULT 70,
        graduation_threshold REAL DEFAULT 70,
        exam_questions_count INTEGER DEFAULT 30,
        icon TEXT, color TEXT
    )""")
    # seed default paths if empty
    cur.execute("SELECT COUNT(*) FROM path_config")
    if cur.fetchone()[0] == 0:
        defaults = [
            ("foundation",   "Beginner - Foundation",  0,  30, 70, 70, 30, "S",  "#10b981"),
            ("intermediate", "Intermediate",          31, 50, 70, 70, 30, "M", "#3b82f6"),
            ("advanced",     "Advanced",              51, 70, 75, 75, 30, "L", "#8b5cf6"),
            ("master",       "Master",                71,100, 80, 80, 30, "G",  "#f59e0b"),
        ]
        for d in defaults:
            cur.execute("INSERT INTO path_config (path, display_name, min_score, max_score, passing_threshold, graduation_threshold, exam_questions_count, icon, color) VALUES (?,?,?,?,?,?,?,?,?)", d)
    # final exam answers/attempts
    cur.execute("""CREATE TABLE IF NOT EXISTS final_exam_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT, path TEXT,
        score REAL, passed INTEGER DEFAULT 0,
        answers_json TEXT,
        started_at TEXT, completed_at TEXT
    )""")
    conn.commit(); conn.close()


# auto-run schema on import
try:
    _ensure_phase12b_schema()
except Exception as e:
    print("[12B init]", e)


# ============================================================
# PATH CONFIG ADMIN
# ============================================================
@app.route("/api/admin/paths/list", methods=["GET"])
def api_admin_paths_list():
    try:
        import sqlite3
        _ensure_phase12b_schema()
        conn = _miniapp_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM path_config ORDER BY min_score ASC")
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            cur.execute("SELECT COUNT(*) FROM stages WHERE path=?", (r["path"],))
            r["stages_count"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM lessons l JOIN stages s ON l.stage_id=s.id WHERE s.path=?", (r["path"],))
            r["lessons_count"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM final_exam_questions WHERE path=?", (r["path"],))
            r["exam_questions"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM students WHERE current_path=?", (r["path"],))
            r["students_count"] = cur.fetchone()[0]
        conn.close()
        return jsonify({"paths": rows})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e), "paths": []}), 500


@app.route("/api/admin/paths/<path>/update", methods=["POST", "PUT"])
def api_admin_path_update(path):
    try:
        data = request.get_json(force=True) or {}
        conn = _miniapp_db(); cur = conn.cursor()
        fields, vals = [], []
        for col in ["display_name", "min_score", "max_score", "passing_threshold", "graduation_threshold", "exam_questions_count", "icon", "color"]:
            if col in data:
                fields.append(col + "=?"); vals.append(data[col])
        if not fields: return jsonify({"error": "no fields"}), 400
        vals.append(path)
        cur.execute("UPDATE path_config SET " + ", ".join(fields) + " WHERE path=?", vals)
        conn.commit(); conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# GRADUATION CONTROL (the magic admin button)
# ============================================================
@app.route("/api/admin/students/<user_id>/graduation/unlock", methods=["POST"])
def api_admin_unlock_graduation(user_id):
    try:
        data = request.get_json(force=True) or {}
        admin_id = (data.get("admin_id") or "admin").strip()
        conn = _miniapp_db(); cur = conn.cursor()
        cur.execute("UPDATE students SET graduation_unlocked=1, graduation_unlocked_by=?, graduation_unlocked_at=datetime('now') WHERE user_id=?", (admin_id, user_id))
        conn.commit(); conn.close()
        return jsonify({"ok": True, "message": "graduation gate unlocked for student"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/students/<user_id>/graduation/lock", methods=["POST"])
def api_admin_lock_graduation(user_id):
    try:
        conn = _miniapp_db(); cur = conn.cursor()
        cur.execute("UPDATE students SET graduation_unlocked=0 WHERE user_id=?", (user_id,))
        conn.commit(); conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/students/<user_id>/path/change", methods=["POST"])
def api_admin_change_student_path(user_id):
    try:
        data = request.get_json(force=True) or {}
        new_path = (data.get("path") or "").strip()
        if not new_path: return jsonify({"error": "path required"}), 400
        conn = _miniapp_db(); cur = conn.cursor()
        cur.execute("UPDATE students SET current_path=? WHERE user_id=?", (new_path, user_id))
        conn.commit(); conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/students/<user_id>/progress/reset", methods=["POST"])
def api_admin_reset_progress(user_id):
    try:
        conn = _miniapp_db(); cur = conn.cursor()
        cur.execute("DELETE FROM student_progress WHERE user_id=?", (user_id,))
        cur.execute("UPDATE students SET xp_total=0, streak_days=0, graduated=0, graduation_score=NULL, certificate_url=NULL WHERE user_id=?", (user_id,))
        conn.commit(); conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/students/<user_id>/xp/grant", methods=["POST"])
def api_admin_grant_xp(user_id):
    try:
        data = request.get_json(force=True) or {}
        amount = int(data.get("amount") or 0)
        conn = _miniapp_db(); cur = conn.cursor()
        cur.execute("UPDATE students SET xp_total = COALESCE(xp_total,0) + ? WHERE user_id=?", (amount, user_id))
        conn.commit(); conn.close()
        return jsonify({"ok": True, "amount": amount})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# STUDENT-PATH PROGRESS SUMMARY (for admin view)
# ============================================================
@app.route("/api/admin/students/<user_id>/journey", methods=["GET"])
def api_admin_student_journey(user_id):
    try:
        import sqlite3
        conn = _miniapp_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT user_id, full_name, current_path, xp_total, streak_days, graduation_unlocked, graduated, graduation_score, placement_score FROM students WHERE user_id=?", (user_id,))
        s = cur.fetchone()
        if not s: return jsonify({"error": "not found"}), 404
        out = dict(s)
        path = out.get("current_path") or "foundation"
        cur.execute("SELECT * FROM stages WHERE path=? ORDER BY order_index ASC", (path,))
        stages = [dict(r) for r in cur.fetchall()]
        for st in stages:
            cur.execute("SELECT l.id, l.title, l.order_index, p.status, p.best_score, p.attempts FROM lessons l LEFT JOIN student_progress p ON p.lesson_id=l.id AND p.user_id=? WHERE l.stage_id=? ORDER BY COALESCE(l.order_index,l.id) ASC", (user_id, st["id"]))
            st["lessons"] = [dict(r) for r in cur.fetchall()]
            completed = sum(1 for l in st["lessons"] if l.get("status") == "completed")
            st["completed_lessons"] = completed
            st["total_lessons"] = len(st["lessons"])
            st["progress_pct"] = round(100*completed/max(1,len(st["lessons"])), 1)
        out["stages"] = stages
        out["overall_progress"] = round(sum(s["progress_pct"] for s in stages) / max(1, len(stages)), 1)
        conn.close()
        return jsonify(out)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500





# ═══════════════════════════════════════════════
# Phase 12D — Admin Lessons/Questions Management
# ═══════════════════════════════════════════════
def _ensure_lesson_columns():
    import sqlite3
    try:
        conn = _db_safe()
        c = conn.cursor()
        cols = [r[1] for r in c.execute("PRAGMA table_info(lessons)").fetchall()]
        if "pass_score" not in cols:
            c.execute("ALTER TABLE lessons ADD COLUMN pass_score INTEGER DEFAULT 70")
        if "title" not in cols:
            c.execute("ALTER TABLE lessons ADD COLUMN title TEXT")
        conn.commit()
        conn.close()
    except Exception as e:
        print("ensure_lesson_columns:", e)

_ensure_lesson_columns()

@app.route("/api/admin/lessons/create", methods=["POST"])
def api_admin_lessons_create_v2():
    import sqlite3
    try:
        data = request.get_json() or {}
        stage_id = data.get("stage_id")
        title = data.get("title") or data.get("name") or "درس جديد"
        pass_score = int(data.get("pass_score", 70))
        if not stage_id:
            return jsonify({"success":False,"message":"stage_id required"}), 400
        conn = _db_safe(); c = conn.cursor()
        # أعلى order_index في المرحلة
        row = c.execute("SELECT COALESCE(MAX(order_index),0) FROM lessons WHERE stage_id=?",(stage_id,)).fetchone()
        new_order = (row[0] or 0) + 1
        cols = [r[1] for r in c.execute("PRAGMA table_info(lessons)").fetchall()]
        # محاولة insert ذكي
        fields = ["stage_id","order_index","pass_score"]
        values = [stage_id, new_order, pass_score]
        if "title" in cols: fields.append("title"); values.append(title)
        if "name" in cols: fields.append("name"); values.append(title)
        if "type" in cols: fields.append("type"); values.append(data.get("type","lesson"))
        if "created_at" in cols:
            from datetime import datetime
            fields.append("created_at"); values.append(datetime.now().isoformat())
        placeholders = ",".join(["?"]*len(values))
        c.execute(f"INSERT INTO lessons ({','.join(fields)}) VALUES ({placeholders})", values)
        new_id = c.lastrowid
        conn.commit(); conn.close()
        return jsonify({"success":True,"id":new_id,"order_index":new_order})
    except Exception as e:
        return jsonify({"success":False,"message":str(e)}), 500

@app.route("/api/admin/lessons/<int:lid>/update", methods=["POST"])
def api_admin_lessons_update_v2(lid):
    import sqlite3
    try:
        data = request.get_json() or {}
        conn = _db_safe(); c = conn.cursor()
        cols = [r[1] for r in c.execute("PRAGMA table_info(lessons)").fetchall()]
        updates = []; vals = []
        if "title" in data and "title" in cols: updates.append("title=?"); vals.append(data["title"])
        if ("name" in data or "title" in data) and "name" in cols:
            updates.append("name=?"); vals.append(data.get("name") or data.get("title"))
        if "pass_score" in data: updates.append("pass_score=?"); vals.append(int(data["pass_score"]))
        if not updates:
            return jsonify({"success":False,"message":"nothing to update"}), 400
        vals.append(lid)
        c.execute(f"UPDATE lessons SET {','.join(updates)} WHERE id=?", vals)
        conn.commit(); conn.close()
        return jsonify({"ok":True,"success":True})
    except Exception as e:
        return jsonify({"success":False,"message":str(e)}), 500

@app.route("/api/admin/lessons/<int:lid>/delete", methods=["POST"])
def api_admin_lessons_delete_v2(lid):
    import sqlite3
    try:
        conn = _db_safe(); c = conn.cursor()
        # احذف الأسئلة أولاً
        try: c.execute("DELETE FROM lesson_questions WHERE lesson_id=?",(lid,))
        except: pass
        c.execute("DELETE FROM lessons WHERE id=?",(lid,))
        conn.commit(); conn.close()
        return jsonify({"ok":True,"success":True})
    except Exception as e:
        return jsonify({"success":False,"message":str(e)}), 500

@app.route("/api/admin/lessons/<int:lid>/move", methods=["POST"])
def api_admin_lessons_move_v2(lid):
    import sqlite3
    try:
        data = request.get_json() or {}
        new_stage = data.get("stage_id")
        if not new_stage: return jsonify({"success":False,"message":"stage_id required"}),400
        conn = _db_safe(); c = conn.cursor()
        row = c.execute("SELECT COALESCE(MAX(order_index),0) FROM lessons WHERE stage_id=?",(new_stage,)).fetchone()
        new_order = (row[0] or 0) + 1
        c.execute("UPDATE lessons SET stage_id=?,order_index=? WHERE id=?",(new_stage,new_order,lid))
        conn.commit(); conn.close()
        return jsonify({"ok":True,"success":True})
    except Exception as e:
        return jsonify({"ok":False,"success":False,"error":str(e)}),500

@app.route("/api/admin/lessons/reorder", methods=["POST"])
def api_admin_lessons_reorder_v2():
    import sqlite3
    try:
        data = request.get_json() or {}
        order = data.get("order", [])
        conn = _db_safe(); c = conn.cursor()
        for item in order:
            c.execute("UPDATE lessons SET order_index=? WHERE id=?",(item["order_index"],item["id"]))
        conn.commit(); conn.close()
        return jsonify({"ok":True,"success":True})
    except Exception as e:
        return jsonify({"ok":False,"success":False,"error":str(e)}),500

@app.route("/api/admin/lessons/<int:lid>/questions/create", methods=["POST"])
def api_admin_lesson_question_create_v2(lid):
    import sqlite3
    try:
        data = request.get_json() or {}
        conn = _db_safe(); c = conn.cursor()
        # ensure table
        c.execute("""CREATE TABLE IF NOT EXISTS lesson_questions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER,
            question_text TEXT,
            option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
            correct_answer TEXT,
            order_index INTEGER DEFAULT 0
        )""")
        row = c.execute("SELECT COALESCE(MAX(order_index),0) FROM lesson_questions WHERE lesson_id=?",(lid,)).fetchone()
        order = (row[0] or 0) + 1
        c.execute("""INSERT INTO lesson_questions(lesson_id,question_text,option_a,option_b,option_c,option_d,correct_answer,order_index)
                     VALUES(?,?,?,?,?,?,?,?)""",
                  (lid,data.get("question_text",""),data.get("option_a",""),data.get("option_b",""),
                   data.get("option_c",""),data.get("option_d",""),data.get("correct_answer","A"),order))
        new_id = c.lastrowid
        conn.commit(); conn.close()
        return jsonify({"success":True,"id":new_id})
    except Exception as e:
        return jsonify({"ok":False,"success":False,"error":str(e)}),500

@app.route("/api/admin/questions/<int:qid>/delete", methods=["POST"])
def api_admin_question_delete_v2(qid):
    import sqlite3
    try:
        conn = _db_safe(); c = conn.cursor()
        c.execute("DELETE FROM lesson_questions WHERE id=?",(qid,))
        conn.commit(); conn.close()
        return jsonify({"ok":True,"success":True})
    except Exception as e:
        return jsonify({"ok":False,"success":False,"error":str(e)}),500

@app.route("/api/admin/stages/create", methods=["POST"])
def api_admin_stages_create_v2():
    """Create new stage - FINAL robust version (v5)"""
    try:
        data = request.get_json(force=True) or {}
        track = data.get("track") or data.get("path") or data.get("track_id") or "foundation"
        
        fields = ["name_ar", "name_en", "code", "track", "section_name", "min_score", "order_index"]
        values = [
            data.get("name_ar") or data.get("name") or "مرحلة جديدة",
            data.get("name_en") or data.get("name") or "New Stage",
            data.get("code", "NEW"),
            track,
            data.get("section_name") or data.get("section") or "general",
            int(data.get("min_score") or data.get("pass_score") or 60),
            float(data.get("order_index") or 999.0)
        ]

        placeholders = ",".join(["?"] * len(fields))

        conn = _db_safe()
        c = conn.cursor()
        try:
            c.execute(f"INSERT INTO stages ({','.join(fields)}) VALUES ({placeholders})", values)
            stage_id = c.lastrowid
            conn.commit()
        finally:
            conn.close()
        if "stages_cache" in globals():
            globals()["stages_cache"] = None

        return jsonify({"ok": True, "id": stage_id, "track": track})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/admin/stages/<int:sid>/update", methods=["POST","PUT"])
def api_admin_stages_update_v2(sid):
    """Update a stage with any provided fields (tolerant)."""
    import sqlite3
    try:
        data = request.get_json(force=True) or {}
        conn = _db_safe(); c = conn.cursor()
        cols = [r[1] for r in c.execute("PRAGMA table_info(stages)").fetchall()]
        
        # خريطة الحقول من JSON إلى أعمدة DB
        field_map = {
            "name_ar": "name_ar", "name_en": "name_en", "name": "name",
            "code": "code", "path": "path", "track": "path",
            "section": "section", "section_name": "section",
            "min_score": "min_score", "pass_score": "min_score",
            "order_index": "order_index",
            "description": "description", "description_ar": "description_ar"
        }
        
        updates, vals = [], []
        for json_key, db_col in field_map.items():
            if json_key in data and db_col in cols and not any(u.startswith(db_col+"=") for u in updates):
                updates.append(f"{db_col}=?"); vals.append(data[json_key])
        
        # إذا أُرسلت name_ar فقط، انسخها لـ name أيضاً للتوافق
        if "name_ar" in data and "name" in cols and not any(u.startswith("name=") for u in updates):
            updates.append("name=?"); vals.append(data["name_ar"])
        
        if not updates:
            return jsonify({"success":False,"ok":False,"message":"no valid fields","error":"no valid fields"}), 400
        
        vals.append(sid)
        c.execute(f"UPDATE stages SET {','.join(updates)} WHERE id=?", vals)
        affected = c.rowcount
        conn.commit(); conn.close()
        if affected == 0:
            return jsonify({"success":False,"ok":False,"message":"stage not found","error":"stage not found"}), 404
        return jsonify({"success":True,"ok":True})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"success":False,"ok":False,"error":str(e),"message":str(e)}), 500


@app.route("/api/admin/stages/<int:sid>/delete", methods=["POST"])
def api_admin_stages_delete_v2(sid):
    import sqlite3
    try:
        conn = _db_safe(); c = conn.cursor()
        # حذف الأسئلة والدروس أولاً
        try:
            lesson_ids = [r[0] for r in c.execute("SELECT id FROM lessons WHERE stage_id=?",(sid,)).fetchall()]
            for lid in lesson_ids:
                c.execute("DELETE FROM lesson_questions WHERE lesson_id=?",(lid,))
            c.execute("DELETE FROM lessons WHERE stage_id=?",(sid,))
        except: pass
        c.execute("DELETE FROM stages WHERE id=?",(sid,))
        conn.commit(); conn.close()
        return jsonify({"ok":True,"success":True})
    except Exception as e:
        return jsonify({"ok":False,"success":False,"error":str(e)}),500




# ═══════════════════════════════════════════════
# Phase 12E — Stage Exam System (bank + attempts)
# ═══════════════════════════════════════════════
def _ensure_stage_exam_schema():
    import sqlite3
    try:
        conn = _db_safe()
        c = conn.cursor()

        # students.personal_pass_score + stages_passed
        cols_s = [r[1] for r in c.execute("PRAGMA table_info(students)").fetchall()]
        if "personal_pass_score" not in cols_s:
            c.execute("ALTER TABLE students ADD COLUMN personal_pass_score INTEGER DEFAULT 70")
        if "stages_passed" not in cols_s:
            c.execute("ALTER TABLE students ADD COLUMN stages_passed TEXT DEFAULT '[]'")
        if "current_stage_id" not in cols_s:
            c.execute("ALTER TABLE students ADD COLUMN current_stage_id INTEGER")

        # stages.exam_questions_count
        cols_st = [r[1] for r in c.execute("PRAGMA table_info(stages)").fetchall()]
        if "exam_questions_count" not in cols_st:
            c.execute("ALTER TABLE stages ADD COLUMN exam_questions_count INTEGER DEFAULT 10")

        # stage_exam_questions
        c.execute('''CREATE TABLE IF NOT EXISTS stage_exam_questions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stage_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
            correct_answer TEXT NOT NULL,
            explanation TEXT,
            order_index INTEGER DEFAULT 0,
            created_at TEXT
        )''')

        # stage_exam_attempts
        c.execute('''CREATE TABLE IF NOT EXISTS stage_exam_attempts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            stage_id INTEGER NOT NULL,
            questions_shown TEXT,
            answers TEXT,
            score REAL,
            required_score REAL,
            passed INTEGER DEFAULT 0,
            created_at TEXT
        )''')

        conn.commit()
        conn.close()
        print("[Phase12E] Schema ensured")
    except Exception as e:
        print("[Phase12E] schema error:", e)

_ensure_stage_exam_schema()


# ─── Admin: قائمة بنك الأسئلة لمرحلة ───


@app.route("/api/admin/stages/<int:sid>/exam-questions", methods=["GET"])
def api_admin_stage_exam_list(sid):
    import sqlite3
    try:
        conn = _db_safe(); conn.row_factory = sqlite3.Row
        c = conn.cursor()
        rows = c.execute("SELECT * FROM stage_exam_questions WHERE stage_id=? ORDER BY order_index, id", (sid,)).fetchall()
        # settings
        st = c.execute("SELECT exam_questions_count FROM stages WHERE id=?", (sid,)).fetchone()
        cnt = st[0] if st else 10
        conn.close()
        return jsonify({
            "success": True,
            "questions": [dict(r) for r in rows],
            "total": len(rows),
            "exam_questions_count": cnt
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/stages/<int:sid>/exam-questions/create", methods=["POST"])
def api_admin_stage_exam_create(sid):
    import sqlite3
    from datetime import datetime
    try:
        data = request.get_json() or {}
        conn = _db_safe(); c = conn.cursor()
        row = c.execute("SELECT COALESCE(MAX(order_index),0) FROM stage_exam_questions WHERE stage_id=?",(sid,)).fetchone()
        order = (row[0] or 0) + 1
        c.execute('''INSERT INTO stage_exam_questions
            (stage_id,question_text,option_a,option_b,option_c,option_d,correct_answer,explanation,order_index,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (sid,
             data.get("question_text",""),
             data.get("option_a",""),
             data.get("option_b",""),
             data.get("option_c",""),
             data.get("option_d",""),
             data.get("correct_answer","A"),
             data.get("explanation",""),
             order,
             datetime.now().isoformat()))
        new_id = c.lastrowid
        conn.commit(); conn.close()
        return jsonify({"success": True, "id": new_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/exam-questions/<int:qid>/update", methods=["POST"])
def api_admin_stage_exam_update(qid):
    import sqlite3
    try:
        data = request.get_json() or {}
        fields = []; vals = []
        for k in ["question_text","option_a","option_b","option_c","option_d","correct_answer","explanation","concept_ar","explanation_ar","trap_ar","review_lesson_id","review_lesson_title","difficulty"]:
            if k in data:
                fields.append(f"{k}=?"); vals.append(data[k])
        if not fields:
            return jsonify({"success": False, "message": "nothing"}), 400
        vals.append(qid)
        conn = _db_safe(); c = conn.cursor()
        c.execute(f"UPDATE stage_exam_questions SET {','.join(fields)} WHERE id=?", vals)
        conn.commit(); conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/exam-questions/<int:qid>/delete", methods=["POST"])
def api_admin_stage_exam_delete(qid):
    import sqlite3
    try:
        conn = _db_safe(); c = conn.cursor()
        c.execute("DELETE FROM stage_exam_questions WHERE id=?", (qid,))
        conn.commit(); conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/stages/<int:sid>/exam-settings", methods=["POST"])
def api_admin_stage_exam_settings(sid):
    import sqlite3
    try:
        data = request.get_json() or {}
        cnt = int(data.get("exam_questions_count", 10))
        if cnt < 1 or cnt > 100:
            return jsonify({"success": False, "message": "count must be 1-100"}), 400
        conn = _db_safe(); c = conn.cursor()
        c.execute("UPDATE stages SET exam_questions_count=? WHERE id=?", (cnt, sid))
        conn.commit(); conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ─── Admin: تعديل شرط النجاح الشخصي للطالب ───
@app.route("/api/admin/students/<student_id>/pass-score", methods=["POST"])
def api_admin_student_pass_score(student_id):
    import sqlite3
    try:
        data = request.get_json() or {}
        ps = int(data.get("personal_pass_score", 70))
        if ps < 30 or ps > 95:
            return jsonify({"success": False, "message": "must be 30-95 (so +10 stays valid)"}), 400
        conn = _db_safe(); c = conn.cursor()
        c.execute("UPDATE students SET personal_pass_score=? WHERE user_id=?", (ps, student_id))
        conn.commit(); conn.close()
        return jsonify({"success": True, "personal_pass_score": ps, "required_for_pass": ps + 10})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ─── Student: بدء امتحان مرحلة ───
@app.route("/api/student/stage/<int:sid>/exam-start", methods=["GET"])
def api_student_stage_exam_start(sid):
    import sqlite3, random, json
    try:
        user_id = request.args.get("user_id") or request.args.get("student_id")
        if not user_id:
            return jsonify({"success": False, "message": "user_id required"}), 400
        conn = _db_safe(); conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # شرط النجاح الشخصي
        st = c.execute("SELECT personal_pass_score FROM students WHERE user_id=?", (user_id,)).fetchone()
        personal = (st["personal_pass_score"] if st and st["personal_pass_score"] else 70)
        required = personal + 10

        # عدد الأسئلة المطلوب
        scols2 = [r[1] for r in c.execute("PRAGMA table_info(stages)").fetchall()]
        sel2 = ["exam_questions_count"]
        for col in ["name_ar","name_en","name"]:
            if col in scols2: sel2.append(col)
        stg = c.execute(f"SELECT {','.join(sel2)} FROM stages WHERE id=?", (sid,)).fetchone()
        if not stg:
            return jsonify({"success": False, "message": "stage not found"}), 404
        cnt = stg["exam_questions_count"] or 10

        # كل الأسئلة من البنك
        all_q = c.execute("SELECT * FROM stage_exam_questions WHERE stage_id=?", (sid,)).fetchall()
        if len(all_q) < cnt:
            conn.close()
            return jsonify({
                "success": False,
                "message": f"بنك الأسئلة غير كافٍ. يحتاج {cnt} سؤال، متوفر {len(all_q)}"
            }), 400

        # اختيار عشوائي
        sample = random.sample([dict(r) for r in all_q], cnt)
        # إخفاء الإجابة الصحيحة في الإرسال
        clean = []
        for q in sample:
            # دعم كل من format القديم (option_a/b/c/d) والجديد (options dict)
            clean.append({
                "id": q["id"],
                "question_text": q["question_text"],
                "option_a": q["option_a"],
                "option_b": q["option_b"],
                "option_c": q["option_c"],
                "option_d": q["option_d"],
                "options": {
                    "A": q["option_a"],
                    "B": q["option_b"],
                    "C": q["option_c"],
                    "D": q["option_d"],
                },
                # حقول Phase 13.1 لدعم Split-Screen UI + TOEFL types
                "passage_text": (q["passage_text"] if "passage_text" in q.keys() else None),
                "set_id":       (q["set_id"]       if "set_id"       in q.keys() else None),
                "q_type":       (q["q_type"]       if "q_type"       in q.keys() else None),
                "audio_source": (q["audio_source"] if "audio_source" in q.keys() else None),
                "time_limit_seconds": (q["time_limit_seconds"] if "time_limit_seconds" in q.keys() else None),
                "difficulty":   (q["difficulty"]   if "difficulty"   in q.keys() else None),
                "skill_section":(q["skill_section"]if "skill_section"in q.keys() else None),
            })

        conn.close()
        return jsonify({
            "success": True,
            "stage_id": sid,
            "stage_name": (stg["name_ar"] if "name_ar" in stg.keys() and stg["name_ar"] else None) or (stg["name_en"] if "name_en" in stg.keys() and stg["name_en"] else None) or (stg["name"] if "name" in stg.keys() and stg["name"] else None) or f"المرحلة {sid}",
            "personal_pass_score": personal,
            "required_score": required,
            "total_questions": cnt,
            "questions": clean
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ─── Student: تسليم امتحان مرحلة ───
@app.route("/api/student/stage/<int:sid>/exam-submit", methods=["POST"])
def api_student_stage_exam_submit_v2(sid):
    """Phase 12E-3 v2: Submit answers, record mistakes, return rich feedback."""
    from flask import request, jsonify
    d = request.json or {}
    telegram_id = str(d.get("user_id") or d.get("telegram_id") or "anonymous")
    answers = d.get("answers", {})  # {question_id: "A"/"B"/"C"/"D"}
    if not isinstance(answers, dict):
        return jsonify({"success": False, "error": "answers must be dict"}), 400

    conn = _db_safe()
    c = conn.cursor()
    try:
        # Fetch all questions for this stage
        c.execute("""SELECT id, question_text, option_a, option_b, option_c, option_d,
                            correct_answer, explanation, concept_ar, explanation_ar,
                            trap_ar, review_lesson_id, review_lesson_title,
                            passage_text, strategy_ar, elimination_ar
                     FROM stage_exam_questions WHERE stage_id=?""", (sid,))
        rows = c.fetchall()
        if not rows:
            return jsonify({"success": False, "error": "no questions in this stage"}), 404

        total = len(rows)
        correct_count = 0
        feedback = []
        wrong_lessons = set()

        for row in rows:
            qid = row[0]
            correct_ans = (row[6] or "").strip().upper()
            student_ans = str(answers.get(str(qid)) or answers.get(qid) or "").strip().upper()
            is_correct = (student_ans == correct_ans)
            if is_correct:
                correct_count += 1
            else:
                # Record mistake in error_bank
                try:
                    import quiz_engine as _qe
                    _qe.record_mistake(telegram_id, qid, student_ans or "-", correct_ans)
                except Exception as _me:
                    print(f"[exam-submit] record_mistake skip: {_me}")
                if row[11]:  # review_lesson_id
                    wrong_lessons.add(row[11])

            feedback.append({
                "question_id": qid,
                "question_text": row[1],
                "options": {"A": row[2], "B": row[3], "C": row[4], "D": row[5]},
                "student_answer": student_ans or None,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "explanation": row[7] or "",
                "concept_ar": row[8] or "",
                "explanation_ar": row[9] or "",
                "trap_ar": row[10] or "",
                "review_lesson_id": row[11],
                "review_lesson_title": row[12] or ""
            })

        score = round((correct_count / total) * 100, 1) if total > 0 else 0
        # Get min_score from stage
        c.execute("SELECT min_score FROM stages WHERE id=?", (sid,))
        ms_row = c.fetchone()
        min_score = float(ms_row[0]) if ms_row and ms_row[0] is not None else 70.0
        passed = 1 if score >= min_score else 0

        # Save attempt
        import json as _json
        try:
            c.execute("""INSERT INTO stage_exam_attempts
                         (telegram_id, stage_id, score, total_questions, correct_count, passed, answers_json)
                         VALUES (?,?,?,?,?,?,?)""",
                      (telegram_id, sid, score, total, correct_count, passed, _json.dumps(answers)))
            conn.commit()
        except Exception as _se:
            print(f"[exam-submit] attempt save skip: {_se}")

        return jsonify({
            "success": True,
            "score": score,
            "min_score": min_score,
            "passed": bool(passed),
            "correct": correct_count,
            "total": total,
            "feedback": feedback,
            "wrong_lessons_count": len(wrong_lessons)
        })
    finally:
        conn.close()
# ===== End Phase 12E-3 v2 submit =====


@app.route("/api/student/stages-progress", methods=["GET"])
def api_student_stages_progress():
    import sqlite3, json
    try:
        user_id = request.args.get("user_id") or request.args.get("student_id")
        if not user_id:
            return jsonify({"success": False, "message": "user_id required"}), 400
        conn = _db_safe(); conn.row_factory = sqlite3.Row
        c = conn.cursor()
        st = c.execute("SELECT personal_pass_score, stages_passed FROM students WHERE user_id=?", (user_id,)).fetchone()
        try:
            passed_list = json.loads(st["stages_passed"] or "[]") if st else []
        except:
            passed_list = []
        personal = (st["personal_pass_score"] if st and st["personal_pass_score"] else 70)

        # اكتشاف الأعمدة المتاحة
        scols = [r[1] for r in c.execute("PRAGMA table_info(stages)").fetchall()]
        order_col = "order_index" if "order_index" in scols else "id"
        sel_fields = ["id"]
        for col in ["name_ar","name_en","name","order_index"]:
            if col in scols: sel_fields.append(col)
        stages = c.execute(f"SELECT {','.join(sel_fields)} FROM stages ORDER BY {order_col}, id").fetchall()
        result = []
        for s in stages:
            sid = s["id"]
            # أفضل علامة للمحاولات
            best = c.execute(
                "SELECT MAX(score) FROM stage_exam_attempts WHERE user_id=? AND stage_id=?",
                (user_id, sid)
            ).fetchone()
            best_score = best[0] if best and best[0] is not None else None
            attempts = c.execute(
                "SELECT COUNT(*) FROM stage_exam_attempts WHERE user_id=? AND stage_id=?",
                (user_id, sid)
            ).fetchone()[0]
            result.append({
                "stage_id": sid,
                "name": (s["name_ar"] if "name_ar" in s.keys() and s["name_ar"] else None) or (s["name_en"] if "name_en" in s.keys() and s["name_en"] else None) or (s["name"] if "name" in s.keys() and s["name"] else None) or f"المرحلة {sid}",
                "order_index": (s["order_index"] if "order_index" in s.keys() else s["id"]),
                "passed": (sid in passed_list),
                "best_score": best_score,
                "attempts": attempts
            })
        conn.close()
        return jsonify({
            "success": True,
            "personal_pass_score": personal,
            "required_score": personal + 10,
            "stages": result
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ═══════════════════════════════════════════════
# /Phase 12E
# ═══════════════════════════════════════════════


# ===== Phase 12E-3 v2: Student stage exam page =====
@app.route("/stage-exam/<int:sid>")
def page_stage_exam(sid):
    from flask import render_template, request
    user_id = request.args.get("user_id", "")
    return render_template("stage_exam.html", stage_id=sid, user_id=user_id)
# ===== End Phase 12E-3 v2 route =====



# ===== Phase 13.2d HOTFIX: ensure difficulty column =====
def _ensure_difficulty_column():
    try:
        conn = _db_safe(); c = conn.cursor()
        c.execute("PRAGMA table_info(stage_exam_questions)")
        cols = [r[1] for r in c.fetchall()]
        added = []
        for col, typ in [
            ("difficulty", "TEXT"),
            ("set_id", "TEXT"),
            ("order_in_set", "INTEGER"),
            ("is_active", "INTEGER DEFAULT 1"),
        ]:
            if col not in cols:
                try:
                    c.execute(f"ALTER TABLE stage_exam_questions ADD COLUMN {col} {typ}")
                    added.append(col)
                except Exception as e:
                    print(f"[migration] skip {col}: {e}")
        conn.commit(); conn.close()
        if added:
            print(f"[migration] Added columns: {added}")
        else:
            print("[migration] All columns present")
    except Exception as e:
        print(f"[migration] _ensure_difficulty_column ERROR: {e}")

try:
    _ensure_difficulty_column()
except Exception as _e:
    print(f"[startup] difficulty migration error: {_e}")
# ===== End Phase 13.2d HOTFIX =====


if __name__ == "__main__":
    import os as _os
    _port = int(_os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=_port, debug=False)


# ===================== Phase 9: Admin + Placement Questions CRUD =====================

def _ensure_stages_columns():
    """Phase12F: Ensure stages table has all required columns (idempotent)."""
    import sqlite3
    try:
        db = DB_PATH if "DB_PATH" in globals() else "academy.db"
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(stages)")
        cols = {r[1] for r in cur.fetchall()}
        added = []
        if "order_index" not in cols:
            cur.execute("ALTER TABLE stages ADD COLUMN order_index INTEGER DEFAULT 0")
            cur.execute("UPDATE stages SET order_index = id WHERE order_index IS NULL OR order_index = 0")
            added.append("order_index")
        if "name_ar" not in cols:
            cur.execute("ALTER TABLE stages ADD COLUMN name_ar TEXT")
            added.append("name_ar")
        if "name_en" not in cols:
            cur.execute("ALTER TABLE stages ADD COLUMN name_en TEXT")
            added.append("name_en")
        if "path" not in cols:
            cur.execute("ALTER TABLE stages ADD COLUMN path TEXT DEFAULT 'foundation'")
            added.append("path")
        if "section_name" not in cols:
            cur.execute("ALTER TABLE stages ADD COLUMN section_name TEXT DEFAULT 'grammar'")
            added.append("section_name")
        if "min_score" not in cols:
            cur.execute("ALTER TABLE stages ADD COLUMN min_score REAL DEFAULT 70")
            added.append("min_score")
        if "code" not in cols:
            cur.execute("ALTER TABLE stages ADD COLUMN code TEXT")
            added.append("code")
        # تأكد lessons فيها order_index و pass_score
        cur.execute("PRAGMA table_info(lessons)")
        lcols = {r[1] for r in cur.fetchall()}
        if "order_index" not in lcols:
            cur.execute("ALTER TABLE lessons ADD COLUMN order_index INTEGER DEFAULT 0")
            cur.execute("UPDATE lessons SET order_index = id WHERE order_index IS NULL OR order_index = 0")
            added.append("lessons.order_index")
        if "pass_score" not in lcols:
            cur.execute("ALTER TABLE lessons ADD COLUMN pass_score INTEGER DEFAULT 70")
            added.append("lessons.pass_score")
        if "title" not in lcols:
            cur.execute("ALTER TABLE lessons ADD COLUMN title TEXT")
            added.append("lessons.title")
        conn.commit()
        conn.close()
        if added:
            print(f"[Phase12F] stages/lessons columns ensured: {added}")
        else:
            print("[Phase12F] stages/lessons schema OK")
    except Exception as e:
        print(f"[Phase12F] ERROR: {e}")

_ensure_stages_columns()



@app.route("/admin")
def admin_page():
    from flask import render_template
    return render_template("admin.html")

@app.route("/api/admin/placement-questions", methods=["GET"])
def api_admin_placement_list():
    import sqlite3
    try:
        conn = sqlite3.connect("academy.db"); conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM placement_questions ORDER BY id DESC").fetchall()
        conn.close()
        return _jsonify({"questions": [dict(r) for r in rows]})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/placement-questions", methods=["POST"])
def api_admin_placement_create():
    import sqlite3
    try:
        d = _request.get_json(force=True) or {}
        conn = sqlite3.connect("academy.db")
        conn.execute("""
            INSERT INTO placement_questions
            (question_text, option_a, option_b, option_c, option_d, correct_option, skill, skill_type, difficulty, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d.get("question_text",""), d.get("option_a",""), d.get("option_b",""),
            d.get("option_c",""), d.get("option_d",""), (d.get("correct_option","A") or "A").upper(),
            d.get("skill","grammar"), d.get("skill","grammar"),
            d.get("difficulty","medium"), 1 if d.get("is_active", True) else 0
        ))
        conn.commit(); conn.close()
        return _jsonify({"ok": True})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/placement-questions/<int:qid>", methods=["PUT"])
def api_admin_placement_update(qid):
    import sqlite3
    try:
        d = _request.get_json(force=True) or {}
        conn = sqlite3.connect("academy.db")
        conn.execute("""
            UPDATE placement_questions
            SET question_text=?, option_a=?, option_b=?, option_c=?, option_d=?,
                correct_option=?, skill=?, skill_type=?, difficulty=?, is_active=?
            WHERE id=?
        """, (
            d.get("question_text",""), d.get("option_a",""), d.get("option_b",""),
            d.get("option_c",""), d.get("option_d",""), (d.get("correct_option","A") or "A").upper(),
            d.get("skill","grammar"), d.get("skill","grammar"),
            d.get("difficulty","medium"), 1 if d.get("is_active", True) else 0, qid
        ))
        conn.commit(); conn.close()
        return _jsonify({"ok": True})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/placement-questions/<int:qid>", methods=["DELETE"])
def api_admin_placement_delete(qid):
    import sqlite3
    try:
        conn = sqlite3.connect("academy.db")
        conn.execute("DELETE FROM placement_questions WHERE id=?", (qid,))
        conn.commit(); conn.close()
        return _jsonify({"ok": True})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

@app.route("/api/admin/placement-questions/<int:qid>/toggle", methods=["POST"])
def api_admin_placement_toggle(qid):
    import sqlite3
    try:
        conn = sqlite3.connect("academy.db")
        row = conn.execute("SELECT is_active FROM placement_questions WHERE id=?", (qid,)).fetchone()
        if not row: return _jsonify({"error": "not found"}), 404
        new_val = 0 if row[0] == 1 else 1
        conn.execute("UPDATE placement_questions SET is_active=? WHERE id=?", (new_val, qid))
        conn.commit(); conn.close()
        return _jsonify({"ok": True, "is_active": new_val})
    except Exception as e:
        return _jsonify({"error": str(e)}), 500

