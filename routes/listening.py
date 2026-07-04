# -*- coding: utf-8 -*-
"""
TOEFL Listening Track - Flask Blueprint
Routes for: track overview, stages, lessons (theory + practice), submit API, progress.
Pattern mirrors routes/writing_toefl.py for consistency.
"""
import os, json, sqlite3, time
from flask import Blueprint, render_template, request, jsonify, redirect
from subscription_helpers import require_section_access

listening_bp = Blueprint("listening", __name__)

DB_PATH = os.environ.get("DB_PATH", "academy.db")

# Pass thresholds by tier (same as Writing module)
TIER_THRESHOLDS = {"tier90": 85, "tier69": 75, "tier59": 65}
DEFAULT_THRESHOLD = 65


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _get_tg_id():
    return (request.args.get("user_id")
            or request.args.get("tg_id")
            or request.cookies.get("user_id")
            or request.headers.get("X-User-Id")
            or "guest")


def _get_user_tier(conn, tg_id):
    """Best-effort tier lookup from users table; defaults to tier59."""
    try:
        cur = conn.cursor()
        row = cur.execute("SELECT tier FROM users WHERE telegram_id=?", (str(tg_id),)).fetchone()
        if row and row["tier"]:
            return str(row["tier"]).lower()
    except Exception:
        pass
    return "tier59"


def _threshold_for_tier(tier):
    return TIER_THRESHOLDS.get((tier or "").lower(), DEFAULT_THRESHOLD)


# ═══════════════════════════════════════════════════════════
# PAGE: Listening Track Overview
# ═══════════════════════════════════════════════════════════
@listening_bp.route("/listening")
@require_section_access("listening")
def listening_track_page():
    user_id = request.args.get("user_id") or _get_tg_id()
    conn = _db(); c = conn.cursor()

    # 5 stages with real counts
    stages = [
        {"id":1, "code":"foundation",    "title_ar":"المرحلة 1: التأسيس",        "icon":"📚", "color":"#7c3aed", "table":"listening_lessons",         "where":"stage_id=1 AND is_active=1"},
        {"id":2, "code":"listen_response","title_ar":"المرحلة 2: اسمع واختر الرد","icon":"🎯", "color":"#3b82f6", "table":"listening_choose_response","where":"is_active=1"},
        {"id":3, "code":"conversation",  "title_ar":"المرحلة 3: المحادثات الجامعية","icon":"💬","color":"#10b981","table":"listening_conversation",   "where":"is_active=1"},
        {"id":4, "code":"announcement",  "title_ar":"المرحلة 4: الإعلانات الجامعية","icon":"📢","color":"#f59e0b","table":"listening_announcement",   "where":"is_active=1"},
        {"id":5, "code":"academic_talk", "title_ar":"المرحلة 5: المحاضرات الأكاديمية","icon":"🎓","color":"#ef4444","table":"listening_academic_talk",  "where":"is_active=1"},
    ]
    total_all = 0; done_all = 0
    for s in stages:
        try:
            _tbl = s["table"]; _whr = s["where"]
            s["total"] = c.execute(f"SELECT COUNT(*) FROM {_tbl} WHERE {_whr}").fetchone()[0] or 0
        except Exception:
            s["total"] = 0
        # progress (best-effort, if table exists)
        try:
            s["done"] = c.execute(
                "SELECT COUNT(*) FROM listening_progress WHERE telegram_id=? AND stage_id=? AND status='completed'",
                (str(user_id), s["id"])
            ).fetchone()[0] or 0
        except Exception:
            s["done"] = 0
        s["pct"] = int(s["done"]*100/s["total"]) if s["total"] else 0
        total_all += s["total"]; done_all += s["done"]
    conn.close()

    # Build inline HTML (no template dependency)
    cards = ""
    for s in stages:
        cards += f"""<a href="/listening/stage/{s['id']}?user_id={user_id}" class="stage-card" style="border-right:6px solid {s['color']}">
          <div class="stage-head"><div class="stage-icon" style="background:{s['color']}22;color:{s['color']}">{s['icon']}</div>
            <div><div class="stage-title">{s['title_ar']}</div><div class="stage-sub">{s['done']}/{s['total']} عنصر</div></div></div>
          <div class="bar"><div class="bar-fill" style="width:{s['pct']}%;background:{s['color']}"></div></div>
          <div class="pct">{s['pct']}%</div></a>"""

    pct_all = int(done_all*100/total_all) if total_all else 0
    return f"""<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<title>TOEFL Listening</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;font-family:'Segoe UI',Tahoma,sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;padding:20px}}
.wrap{{max-width:900px;margin:0 auto}}
.back{{display:inline-block;background:rgba(255,255,255,.2);color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none;margin-bottom:20px}}
.hero{{background:rgba(255,255,255,.15);border-radius:20px;padding:30px;text-align:center;color:#fff;margin-bottom:24px;backdrop-filter:blur(10px)}}
.hero h1{{margin:0 0 8px;font-size:32px}}.hero p{{margin:6px 0;opacity:.9}}
.overall{{margin-top:14px;background:rgba(0,0,0,.2);border-radius:10px;height:10px;overflow:hidden}}
.overall-fill{{height:100%;background:#fff;transition:width .4s}}
.stage-card{{display:block;background:#fff;border-radius:16px;padding:20px;margin-bottom:14px;text-decoration:none;color:#1f2937;box-shadow:0 4px 14px rgba(0,0,0,.08);transition:transform .15s}}
.stage-card:hover{{transform:translateY(-2px)}}
.stage-head{{display:flex;align-items:center;gap:14px;margin-bottom:12px}}
.stage-icon{{width:54px;height:54px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:28px}}
.stage-title{{font-weight:bold;font-size:17px;margin-bottom:4px}}.stage-sub{{color:#6b7280;font-size:13px}}
.bar{{background:#e5e7eb;height:8px;border-radius:4px;overflow:hidden}}.bar-fill{{height:100%;transition:width .4s}}
.pct{{text-align:left;font-size:13px;color:#6b7280;margin-top:6px;font-weight:bold}}
</style></head><body><div class="wrap">
<a href="/home?user_id={user_id}" class="back">← العودة للرئيسية</a>
<div class="hero"><h1>🎧 TOEFL Listening</h1><p>تدرّب على الاستماع كالامتحان الفعلي</p>
<p style="font-size:14px">{done_all}/{total_all} عنصر مكتمل · {pct_all}%</p>
<div class="overall"><div class="overall-fill" style="width:{pct_all}%"></div></div></div>
{cards}
</div></body></html>"""


# ═══════════════════════════════════════════════════════════
# PAGE: Stage detail
# ═══════════════════════════════════════════════════════════
@listening_bp.route("/listening/stage/<int:stage_id>")
@require_section_access("listening")
def view_stage(stage_id):
    tg_id = request.args.get("user_id") or _get_tg_id()
    STAGES = {
        1: {"title": "Stage 1: Foundations", "subtitle": "Strategic listening fundamentals", "table": "listening_lessons", "title_col": "title_en", "has_tier": False, "color": "#3b82f6"},
        2: {"title": "Stage 2: Listen & Choose Response", "subtitle": "Short natural-response exercises", "table": "listening_choose_response", "title_col": "title_en", "has_tier": True, "color": "#8b5cf6"},
        3: {"title": "Stage 3: University Conversations", "subtitle": "Real campus dialogues", "table": "listening_conversation", "title_col": "title_en", "has_tier": True, "color": "#ec4899"},
        4: {"title": "Stage 4: University Announcements", "subtitle": "Campus announcements", "table": "listening_announcement", "title_col": "title_en", "has_tier": True, "color": "#f59e0b"},
        5: {"title": "Stage 5: Academic Lectures", "subtitle": "TOEFL-style academic talks", "table": "listening_academic_talk", "title_col": "title_en", "has_tier": True, "color": "#10b981"},
    }
    s = STAGES.get(stage_id)
    if not s:
        return "Stage not found", 404
    level = request.args.get("level", "easy" if s["has_tier"] else "all")
    conn = _db(); cur = conn.cursor()
    counts = {"easy": 0, "medium": 0, "hard": 0, "all": 0}
    if s["has_tier"]:
        for tier_num, key in [(1, "easy"), (2, "medium"), (3, "hard")]:
            _tbl = s["table"]
            counts[key] = cur.execute(f"SELECT COUNT(*) FROM {_tbl} WHERE is_active=1 AND tier=?", (tier_num,)).fetchone()[0]
        counts["all"] = counts["easy"] + counts["medium"] + counts["hard"]
    else:
        _tbl2 = s["table"]
        counts["all"] = cur.execute(f"SELECT COUNT(*) FROM {_tbl2} WHERE is_active=1").fetchone()[0]
    where = "is_active=1"
    params = []
    if s["has_tier"] and level in ("easy", "medium", "hard"):
        tier_map = {"easy": 1, "medium": 2, "hard": 3}
        where += " AND tier=?"
        params.append(tier_map[level])
    title_col = s["title_col"]
    tier_select = "tier" if s["has_tier"] else "1 as tier"
    tbl = s["table"]
    items = cur.execute(f"SELECT id, COALESCE({title_col}, code) as title, {tier_select} FROM {tbl} WHERE {where} ORDER BY order_index, id", params).fetchall()
    done_ids = set()
    try:
        rows = cur.execute("SELECT lesson_id FROM listening_progress WHERE telegram_id=? AND stage_id=? AND status=?", (str(tg_id), stage_id, "completed")).fetchall()
        done_ids = {r[0] for r in rows}
    except Exception:
        pass
    done_count = len(done_ids)
    total_count = counts["all"]
    pct = int(done_count * 100 / total_count) if total_count else 0
    conn.close()
    tier_labels = {1: ("Easy", "#10b981"), 2: ("Medium", "#f59e0b"), 3: ("Hard", "#ef4444")}
    cards_html = ""
    idx = 0
    for it in items:
        idx += 1
        lid, title, tier = it[0], it[1], it[2]
        is_done = lid in done_ids
        tlabel, tcolor = tier_labels.get(tier, ("", "#888"))
        badge_html = ('<span class="tier-badge" style="background:' + tcolor + '">' + tlabel + '</span>') if s["has_tier"] else ""
        if is_done:
            btn_html = '<span class="btn-done">✓ Completed</span>'
            card_class = "card done"
        else:
            btn_html = '<span class="btn-start">Start →</span>'
            card_class = "card"
        cards_html += (
            '<a href="/listening/lesson/' + str(lid) + '?user_id=' + str(tg_id) + '&stage=' + str(stage_id) + '" class="' + card_class + '" style="border-left-color:' + tcolor + '">'
            + '<div class="card-left">' + btn_html + badge_html + '<span class="card-title">' + str(title) + '</span></div>'
            + '<div class="card-num" style="background:' + tcolor + '">' + str(idx) + '</div>'
            + '</a>'
        )
    if not items:
        cards_html = '<div class="empty">No exercises in this level yet.</div>'
    filter_html = ""
    if s["has_tier"]:
        def btn(key, label, emoji, color):
            active = "active" if level == key else ""
            return ('<a href="?user_id=' + str(tg_id) + '&level=' + key + '" class="flt ' + active + '" style="--c:' + color + '">'
                    + '<span class="flt-emoji">' + emoji + '</span>'
                    + '<span class="flt-label">' + label + '</span>'
                    + '<span class="flt-count">' + str(counts[key]) + '</span></a>')
        filter_html = '<div class="filters">' + btn("easy", "Easy", "🟢", "#10b981") + btn("medium", "Medium", "🟡", "#f59e0b") + btn("hard", "Hard", "🔴", "#ef4444") + '</div>'
    css = """
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
.wrap { max-width: 900px; margin: 0 auto; }
.topbar { display: flex; justify-content: flex-end; margin-bottom: 16px; }
.back { background: rgba(255,255,255,0.95); color: #4c1d95; padding: 10px 18px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: all 0.2s; }
.back:hover { transform: translateY(-2px); }
.header { background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); border-radius: 20px; padding: 32px; color: white; text-align: center; margin-bottom: 28px; border: 1px solid rgba(255,255,255,0.2); }
.header h1 { font-size: 26px; margin-bottom: 8px; font-weight: 700; }
.header .sub { opacity: 0.85; font-size: 14px; margin-bottom: 20px; }
.progress-row { display: flex; align-items: center; gap: 12px; max-width: 500px; margin: 0 auto; }
.progress-bar { flex: 1; height: 10px; background: rgba(255,255,255,0.2); border-radius: 5px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #4ade80, #22c55e); border-radius: 5px; transition: width 0.4s; }
.progress-txt { font-size: 13px; font-weight: 600; white-space: nowrap; }
.filters { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px; }
.flt { background: rgba(255,255,255,0.95); border-radius: 14px; padding: 18px 16px; text-decoration: none; color: #1f2937; display: flex; flex-direction: column; align-items: center; gap: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border: 3px solid transparent; transition: all 0.25s; cursor: pointer; }
.flt:hover { transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,0.15); }
.flt-emoji { font-size: 28px; }
.flt-label { font-size: 15px; font-weight: 700; color: #374151; }
.flt-count { background: #f3f4f6; color: #6b7280; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 700; }
.flt.active { background: var(--c); border-color: var(--c); transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.25); }
.flt.active .flt-label { color: white; }
.flt.active .flt-count { color: white; background: rgba(255,255,255,0.25); }
.cards { display: flex; flex-direction: column; gap: 12px; }
.card { background: white; border-radius: 14px; padding: 18px 22px; display: flex; justify-content: space-between; align-items: center; text-decoration: none; color: #1f2937; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 5px solid #8b5cf6; transition: all 0.2s; }
.card:hover { transform: translateX(4px); box-shadow: 0 6px 16px rgba(0,0,0,0.12); }
.card.done { background: #f0fdf4; border-left-color: #22c55e !important; }
.card-left { display: flex; align-items: center; gap: 12px; flex: 1; }
.card-title { font-weight: 600; font-size: 15px; color: #1f2937; }
.btn-start { background: #4f46e5; color: white; padding: 7px 14px; border-radius: 8px; font-size: 12px; font-weight: 700; }
.btn-done { background: #22c55e; color: white; padding: 7px 14px; border-radius: 8px; font-size: 12px; font-weight: 700; }
.tier-badge { color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; }
.card-num { color: white; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; }
.empty { background: rgba(255,255,255,0.95); padding: 40px; border-radius: 14px; text-align: center; color: #6b7280; font-size: 15px; }
</style>
"""
    html = ('<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + s["title"] + '</title>' + css + '</head><body>'
            + '<div class="wrap">'
            + '<div class="topbar"><a href="/listening?user_id=' + str(tg_id) + '" class="back">← Back to Listening</a></div>'
            + '<div class="header"><h1>' + s["title"] + '</h1><div class="sub">' + s["subtitle"] + '</div>'
            + '<div class="progress-row"><span class="progress-txt">' + str(done_count) + '/' + str(total_count) + '</span>'
            + '<div class="progress-bar"><div class="progress-fill" style="width:' + str(pct) + '%"></div></div>'
            + '<span class="progress-txt">' + str(pct) + '%</span></div></div>'
            + filter_html
            + '<div class="cards">' + cards_html + '</div>'
            + '</div></body></html>')
    return html



# ═══════════════════════════════════════════════════════════
# PAGE: Lesson detail (theory OR practice with clips/questions)
# ═══════════════════════════════════════════════════════════
@listening_bp.route("/listening/lesson/<int:lesson_id>")
@require_section_access("listening")

def _build_audio_url(item_dict, stage_id):
    """يبني مسار MP3 من code+tier، ويرجع فراغ إذا الملف غير موجود."""
    code = (item_dict.get("code") or "").strip()
    if not code:
        return ""
    tier = int(item_dict.get("tier") or 1)
    tier_letter = {1: "e", 2: "m", 3: "d"}.get(tier, "e")
    static_root = os.path.join(os.getcwd(), "static", "audio", "listening")
    candidates = [code + ".mp3", "stage5/" + code + ".mp3"]
    m = re.match(r"^(conv|lec)_0*(\d+)$", code)
    if m:
        prefix = m.group(1)
        num = m.group(2).zfill(2)
        candidates.append(prefix + "_" + tier_letter + num + ".mp3")
        candidates.append("stage5/" + prefix + "_" + tier_letter + num + ".mp3")
    candidates.append(code.upper() + ".mp3")
    for cand in candidates:
        full = os.path.join(static_root, cand.replace("/", os.sep))
        if os.path.exists(full):
            return "/static/audio/listening/" + cand
    return ""

def view_lesson(lesson_id):
    user_id = request.args.get("user_id") or _get_tg_id()
    stage_id = int(request.args.get("stage", 1))
    import sqlite3 as _sq
    conn = _db(); conn.row_factory = _sq.Row; c = conn.cursor()

    STAGE_TABLES = {
        1: "listening_lessons",
        2: "listening_choose_response",
        3: "listening_conversation",
        4: "listening_announcement",
        5: "listening_academic_talk",
    }
    table = STAGE_TABLES.get(stage_id)
    if not table:
        conn.close(); return "Invalid stage", 404

    row = c.execute(f"SELECT * FROM {table} WHERE id=?", (lesson_id,)).fetchone()
    if not row:
        conn.close(); return "Lesson not found", 404
    item = dict(row)
    # ═══ ربط MP3 تلقائياً ═══
    item["audio_url"] = _build_audio_url(item, stage_id)
    conn.close()

    import json as _json
    STAGE_COLORS = {1:"#7c3aed", 2:"#3b82f6", 3:"#10b981", 4:"#f59e0b", 5:"#ef4444"}
    color = STAGE_COLORS[stage_id]

    body = ""
    if stage_id == 1:
        title = item.get("title_ar","درس")
        content = item.get("description") or item.get("transcript") or ""
        body = f'<h1 style="color:{color}">{title}</h1><div class="content">{content}</div><button class="btn-finish" onclick="finishLesson()">✓ فهمت — إنهاء الدرس</button>'

    elif stage_id == 2:
        audio_text = item.get("audio_text","")
        opts_raw = item.get("options_json","[]")
        try: opts = _json.loads(opts_raw) if isinstance(opts_raw,str) else opts_raw
        except: opts = []
        correct_idx = item.get("correct_index", 0)
        explanation = item.get("explanation_ar","")
        opt_html = ""
        for i, opt in enumerate(opts):
            letter = chr(65+i)
            ok = "1" if i==correct_idx else "0"
            opt_html += f'<button class="option" data-correct="{ok}" onclick="pickOption(this)">{letter}. {opt}</button>'
        body = (
            f'<h2 style="color:{color}">🎯 اسمع واختر الرد المناسب</h2>'
            f'<div class="audio-card">'
            f'<audio id="lessonAudio" src="{item.get("audio_url","")}" preload="auto"></audio>'
            f'<button class="btn-listen" onclick="playAudio()">🔊 استمع</button> '
            f'<button class="btn-replay" onclick="replayAudio()">🔁 إعادة</button>'
            f'<div class="audio-bar-wrap"><div class="audio-bar" id="audioBar"></div></div>'
            f'<div class="hint">اضغط للاستماع (يمكنك إعادة الاستماع)</div></div>'
            f'<div class="options">{opt_html}</div>'
            f'<div class="feedback" id="feedback" style="display:none"></div>'
            f'<div class="reveal-box" id="revealBox" style="display:none">'
            f'<div style="background:#f3f4f6;padding:12px;border-radius:8px;margin-top:12px;direction:ltr;text-align:left"><b>Audio text:</b> {audio_text}</div>'
            f'<div style="background:#fef3c7;padding:12px;border-radius:8px;margin-top:8px"><b>الشرح:</b> {explanation}</div></div>'
            f'<button class="btn-finish" id="finishBtn" onclick="finishLesson()" style="display:none">التالي ←</button>'
            f'<script>const AUDIO_URL = {_json.dumps(item.get("audio_url",""))}; const AUDIO_TEXT = {_json.dumps(audio_text, ensure_ascii=False)};</script>'
        )

    else:
        transcript = item.get("transcript","")
        topic = item.get("topic_ar") or item.get("code","")
        qs_raw = item.get("questions_json","[]")
        try: questions = _json.loads(qs_raw) if isinstance(qs_raw,str) else qs_raw
        except: questions = []
        q_html = ""
        for qi, q in enumerate(questions):
            qtext_en = q.get("question_en","")
            qtext_ar = q.get("question_ar","")
            options = q.get("options",{})
            correct = str(q.get("correct","A")).upper()
            explain = q.get("explanation_ar","")
            opts_html = ""
            if isinstance(options, dict):
                for letter, text in options.items():
                    is_correct = "1" if letter.upper()==correct else "0"
                    opts_html += f'<button class="option" data-correct="{is_correct}" onclick="pickQ(this,{qi})">{letter}. {text}</button>'
            elif isinstance(options, list):
                for li, text in enumerate(options):
                    letter = chr(65+li)
                    is_correct = "1" if letter==correct else "0"
                    opts_html += f'<button class="option" data-correct="{is_correct}" onclick="pickQ(this,{qi})">{letter}. {text}</button>'
            ar_div = f'<div class="q-text-ar">{qtext_ar}</div>' if qtext_ar else ''
            q_html += (
                f'<div class="question-block"><div class="q-num">سؤال {qi+1}</div>'
                f'<div class="q-text-en" dir="ltr">{qtext_en}</div>{ar_div}'
                f'<div class="options">{opts_html}</div>'
                f'<div class="q-feedback" id="qfb-{qi}" style="display:none"></div>'
                f'<div class="q-explain" id="qex-{qi}" style="display:none;background:#fef3c7;padding:10px;border-radius:8px;margin-top:8px">{explain}</div></div>'
            )
        body = (
            f'<h2 style="color:{color}">{topic}</h2>'
            f'<div class="audio-card">'
            f'<audio id="lessonAudio" src="{item.get("audio_url","")}" preload="auto"></audio>'
            f'<button class="btn-listen" onclick="playAudio()">🔊 استمع للنص</button> '
            f'<button class="btn-replay" onclick="replayAudio()">🔁 إعادة</button>'
            f'<div class="audio-bar-wrap"><div class="audio-bar" id="audioBar"></div></div>'
            f'<div class="hint">استمع جيداً قبل الإجابة. يمكنك إعادة الاستماع.</div>'
            f'<button class="btn-reveal" onclick="toggleTranscript()">📄 إظهار/إخفاء النص</button></div>'
            f'<div class="transcript" id="transcript" style="display:none" dir="ltr">{transcript}</div>'
            f'<div class="questions">{q_html}</div>'
            f'<button class="btn-finish" id="finishBtn" onclick="finishLesson()" style="display:none">✓ إنهاء الدرس</button>'
            f'<script>const AUDIO_URL = {_json.dumps(item.get("audio_url",""))}; const AUDIO_TEXT = {_json.dumps(transcript, ensure_ascii=False)}; const TOTAL_Q = {len(questions)};</script>'
        )

    return (
        '<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8">'
        '<title>درس الاستماع</title><style>'
        '*{box-sizing:border-box}body{margin:0;font-family:"Segoe UI",Tahoma,sans-serif;background:#f3f4f6;min-height:100vh;padding:20px}'
        '.wrap{max-width:760px;margin:0 auto}'
        '.back{display:inline-block;background:#fff;color:#374151;padding:8px 16px;border-radius:8px;text-decoration:none;margin-bottom:16px;box-shadow:0 2px 6px rgba(0,0,0,.06)}'
        '.card{background:#fff;border-radius:16px;padding:28px;box-shadow:0 4px 20px rgba(0,0,0,.08)}'
        'h1,h2{margin-top:0}.content{line-height:1.8;font-size:16px;color:#374151}'
        f'.content h2,.content h3{{color:{color}}}'
        f'.audio-card{{background:linear-gradient(135deg,{color}15,{color}05);border:2px solid {color}40;border-radius:14px;padding:20px;text-align:center;margin:20px 0}}'
        f'.btn-listen{{background:{color};color:#fff;border:none;padding:14px 32px;border-radius:50px;font-size:18px;font-weight:bold;cursor:pointer;box-shadow:0 4px 14px {color}50}}'
        '.btn-listen:hover{transform:scale(1.03)}'
        f'.btn-reveal{{display:block;margin:12px auto 0;background:#fff;color:{color};border:2px solid {color};padding:8px 20px;border-radius:8px;cursor:pointer;font-weight:bold}}'
        '.hint{color:#6b7280;font-size:13px;margin-top:10px}'
        '.transcript{background:#f9fafb;border:1px solid #e5e7eb;padding:16px;border-radius:10px;margin:16px 0;font-size:14px;line-height:1.7}'
        '.options{display:flex;flex-direction:column;gap:10px;margin:16px 0}'
        '.option{background:#fff;border:2px solid #e5e7eb;padding:14px 18px;border-radius:10px;cursor:pointer;font-size:15px;direction:ltr;text-align:left}'
        f'.option:hover{{border-color:{color};background:{color}08}}'
        '.option.correct{background:#d1fae5;border-color:#10b981;color:#065f46;font-weight:bold}'
        '.option.wrong{background:#fee2e2;border-color:#ef4444;color:#991b1b}'
        '.option:disabled{cursor:default}'
        '.feedback{padding:12px;border-radius:8px;margin:12px 0;font-weight:bold;text-align:center}'
        '.feedback.ok{background:#d1fae5;color:#065f46}.feedback.no{background:#fee2e2;color:#991b1b}'
        '.question-block{background:#fafafa;border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin:16px 0}'
        f'.q-num{{font-weight:bold;color:{color};margin-bottom:6px}}'
        '.q-text-en{font-size:15px;margin-bottom:4px;color:#1f2937}'
        '.q-text-ar{font-size:13px;color:#6b7280;margin-bottom:10px}'
        f'.btn-finish{{display:block;width:100%;background:{color};color:#fff;border:none;padding:14px;border-radius:10px;font-size:16px;font-weight:bold;cursor:pointer;margin-top:20px}}'
        '.btn-finish:hover{opacity:.9}</style></head><body>'
        '<div class="wrap">'
        f'<a href="/listening/stage/{stage_id}?user_id={user_id}" class="back">← العودة للمرحلة</a>'
        f'<div class="card">{body}</div></div>'
        '<script>'
        f'const LESSON_ID = {lesson_id}; const STAGE_ID = {stage_id}; const USER_ID = "{user_id}";'
        'let answeredQuestions = 0;'
        'function playAudio(){var a=document.getElementById("lessonAudio");var bar=document.getElementById("audioBar");if(a&&a.src&&a.src.indexOf(".mp3")>0){a.currentTime=0;var p=a.play();if(p&&p.catch)p.catch(function(e){console.warn("MP3 fail:",e);speakText();});if(bar){a.ontimeupdate=function(){if(a.duration)bar.style.width=(100*a.currentTime/a.duration)+"%";};a.onended=function(){bar.style.width="100%";};}}else{speakText();}}'
        'function replayAudio(){var a=document.getElementById("lessonAudio");if(a){a.pause();a.currentTime=0;}playAudio();}'
        'function speakDialog(){playAudio();}'
        'function cleanForTTS(t){return (t||"").replace(/\//g," ").replace(/[\[\]\(\)\*_~`#]/g," ").replace(/\s+/g," ").trim();}'
        'function speakText(){if(!window.speechSynthesis||!AUDIO_TEXT)return;speechSynthesis.cancel();'
        'const u=new SpeechSynthesisUtterance(cleanForTTS(AUDIO_TEXT));u.lang="en-US";u.rate=0.92;'
        'const voices=speechSynthesis.getVoices();'
        'const usVoices=voices.filter(v=>v.lang==="en-US"&&!/India|Indian|Hindi|Ravi|Heera|Filip|Naayf|Asia/i.test(v.name));const pref=usVoices.find(v=>/Andrew|Emma|Brian|Ava|Aria|Jenny|Christopher|Eric|Guy|Zira|David/i.test(v.name))||usVoices.find(v=>/Microsoft|Google US/i.test(v.name))||usVoices[0]||voices.find(v=>v.lang==="en-US");'
        'if(pref)u.voice=pref;speechSynthesis.speak(u);}'
        'function pickOption(btn){document.querySelectorAll(".option").forEach(b=>b.disabled=true);'
        'const correct=btn.dataset.correct==="1";btn.classList.add(correct?"correct":"wrong");'
        'if(!correct){document.querySelectorAll(".option").forEach(b=>{if(b.dataset.correct==="1")b.classList.add("correct");});}'
        'const fb=document.getElementById("feedback");fb.style.display="block";'
        'fb.className="feedback "+(correct?"ok":"no");fb.textContent=correct?"✓ إجابة صحيحة!":"✗ إجابة غير صحيحة";'
        'document.getElementById("revealBox").style.display="block";'
        'document.getElementById("finishBtn").style.display="block";}'
        'function pickQ(btn,qi){const block=btn.closest(".question-block");'
        'block.querySelectorAll(".option").forEach(b=>b.disabled=true);'
        'const correct=btn.dataset.correct==="1";btn.classList.add(correct?"correct":"wrong");'
        'if(!correct){block.querySelectorAll(".option").forEach(b=>{if(b.dataset.correct==="1")b.classList.add("correct");});}'
        'const fb=document.getElementById("qfb-"+qi);fb.style.display="block";'
        'fb.className="feedback "+(correct?"ok":"no");fb.textContent=correct?"✓ صحيح":"✗ خطأ";'
        'document.getElementById("qex-"+qi).style.display="block";answeredQuestions++;'
        'if(answeredQuestions>=TOTAL_Q){document.getElementById("finishBtn").style.display="block";}}'
        'function toggleTranscript(){const t=document.getElementById("transcript");t.style.display=t.style.display==="none"?"block":"none";}'
        'function finishLesson(){fetch("/api/listening/progress",{method:"POST",headers:{"Content-Type":"application/json"},'
        'body:JSON.stringify({user_id:USER_ID,stage_id:STAGE_ID,lesson_id:LESSON_ID,status:"completed"})})'
        '.catch(e=>console.error(e)).finally(()=>{window.location.href="/listening/stage/"+STAGE_ID+"?user_id="+encodeURIComponent(USER_ID);});}'
        'if(window.speechSynthesis){speechSynthesis.getVoices();speechSynthesis.onvoiceschanged=()=>speechSynthesis.getVoices();}'
        '</script><script src="/static/js/listening_tts.js"></script></body></html>'
    )


# ═══════════════════════════════════════════════════════════
# API: Submit answers for a practice lesson
# ═══════════════════════════════════════════════════════════
@listening_bp.route("/api/listening/lesson/<int:lesson_id>/submit", methods=["POST"])
def api_lesson_submit(lesson_id):
    tg_id = _get_tg_id()
    payload = request.get_json(silent=True) or {}
    answers = payload.get("answers") or {}   # { "<question_id>": <chosen_index>, ... }

    conn = _db(); c = conn.cursor()
    lesson = c.execute("SELECT * FROM listening_lessons WHERE id=?", (lesson_id,)).fetchone()
    if not lesson:
        conn.close()
        return jsonify(success=False, error="Lesson not found"), 404
    lesson_d = dict(lesson)
    stage_id = lesson_d["stage_id"]

    # Theory lesson (stage 1) -> auto-complete on submit
    if stage_id == 1:
        _save_progress(c, tg_id, lesson_id, stage_id, 100, 0, 0, "completed")
        conn.commit()
        nxt = _next_lesson(c, stage_id, lesson_d.get("order_index", 0))
        conn.close()
        return jsonify(success=True, passed=True, score=100,
                       theory=True,
                       next_lesson_id=nxt["id"] if nxt else None,
                       message="تم إنهاء الدرس النظري")

    # Practice lesson - fetch all questions for this stage
    qs = c.execute("""
        SELECT q.* FROM listening_questions q
        WHERE q.stage_id=? AND (q.is_exam=0 OR q.is_exam IS NULL)
        ORDER BY q.clip_id, q.order_index, q.id
    """, (stage_id,)).fetchall()

    total = len(qs)
    if total == 0:
        conn.close()
        return jsonify(success=False, error="No questions found for this lesson"), 400

    if not answers:
        conn.close()
        return jsonify(success=False,
                       error="يجب الإجابة على جميع الأسئلة قبل التسليم"), 400

    correct = 0
    feedback = []
    for q in qs:
        qd = dict(q)
        qid = str(qd["id"])
        try:
            user_idx = int(answers.get(qid, -1))
        except Exception:
            user_idx = -1
        try:
            correct_idx = int(qd.get("correct_answer") or -1)
        except Exception:
            correct_idx = -1
        is_correct = (user_idx == correct_idx and correct_idx >= 0)
        if is_correct:
            correct += 1
        try:
            opts = json.loads(qd.get("options_json") or "[]")
        except Exception:
            opts = []
        # Smart fallback: if wrong_explanation_ar is empty, generate from explanation
        wrong_exp = qd.get("wrong_explanation_ar") or ""
        elim_hint = qd.get("elimination_hint_ar") or ""
        strat = qd.get("strategy_ar") or ""
        tip = qd.get("listening_tip_ar") or ""
        # Build helpful message for missing fields
        if not elim_hint and not is_correct and correct_idx >= 0 and correct_idx < len(opts):
            elim_hint = f"الإجابة الصحيحة هي الخيار {chr(65+correct_idx)}. اقرأ الشرح بعناية وحاول فهم لماذا الخيارات الأخرى غير دقيقة."
        feedback.append({
            "question_id": qd["id"],
            "clip_id": qd.get("clip_id"),
            "question_ar": qd.get("question_ar") or "",
            "question_en": qd.get("question_en") or "",
            "question_type": qd.get("question_type") or "",
            "user_answer": user_idx,
            "correct_answer": correct_idx,
            "is_correct": is_correct,
            "explanation_ar": qd.get("explanation_ar") or "",
            "wrong_explanation_ar": wrong_exp,
            "elimination_hint_ar": elim_hint,
            "strategy_ar": strat,
            "listening_tip_ar": tip,
            "options": opts,
        })

    score = round((correct / total) * 100, 1) if total else 0
    tier = _get_user_tier(conn, tg_id)
    threshold = _threshold_for_tier(tier)
    passed = score >= threshold

    status = "completed" if passed else "in_progress"
    _save_progress(c, tg_id, lesson_id, stage_id, score, correct, total, status)
    _record_attempt(c, tg_id, lesson_id, stage_id, score, correct, total, answers)
    conn.commit()

    nxt = _next_lesson(c, stage_id, lesson_d.get("order_index", 0))
    conn.close()

    return jsonify(success=True,
                   passed=passed,
                   score=score,
                   correct=correct,
                   total=total,
                   threshold=threshold,
                   tier=tier,
                   feedback=feedback,
                   next_lesson_id=nxt["id"] if nxt else None,
                   message=("ممتاز! اجتزت الدرس" if passed
                            else f"تحتاج {threshold}% للنجاح. حاول مرة أخرى."))


# ═══════════════════════════════════════════════════════════
# API: Progress summary for a user
# ═══════════════════════════════════════════════════════════
@listening_bp.route("/api/listening/progress", methods=["GET","POST"])
def api_progress():
    # POST: mark a lesson completed
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        tg_id = data.get("user_id") or _get_tg_id()
        lesson_id = data.get("lesson_id")
        stage_id = data.get("stage_id")
        status = data.get("status","completed")
        if not lesson_id or not stage_id:
            return jsonify(success=False, error="lesson_id and stage_id required"), 400
        conn = _db(); c = conn.cursor()
        try:
            existing = c.execute(
                "SELECT id, status FROM listening_progress WHERE telegram_id=? AND lesson_id=?",
                (str(tg_id), int(lesson_id))
            ).fetchone()
            if existing:
                c.execute("""UPDATE listening_progress
                    SET status=?, stage_id=?, completed_at=CURRENT_TIMESTAMP,
                        attempts_count=COALESCE(attempts_count,0)+1
                    WHERE id=?""", (status, int(stage_id), existing["id"]))
            else:
                c.execute("""INSERT INTO listening_progress
                    (telegram_id, stage_id, lesson_id, status, attempts_count, completed_at)
                    VALUES (?,?,?,?,1,CURRENT_TIMESTAMP)""",
                    (str(tg_id), int(stage_id), int(lesson_id), status))
            conn.commit()
            return jsonify(success=True, lesson_id=lesson_id, status=status)
        except Exception as e:
            return jsonify(success=False, error=str(e)), 500
        finally:
            conn.close()
    # GET: list progress
    tg_id = request.args.get("user_id") or _get_tg_id()
    conn = _db(); c = conn.cursor()
    rows = c.execute("""
        SELECT stage_id, lesson_id, status, best_score, attempts_count
        FROM listening_progress WHERE telegram_id=?
        ORDER BY stage_id, lesson_id
    """, (str(tg_id),)).fetchall()
    conn.close()
    return jsonify(success=True, user_id=tg_id, rows=[dict(r) for r in rows])


# ─── Helpers ──────────────────────────────────────────────
def _save_progress(c, tg_id, lesson_id, stage_id, score, correct, total, status):
    existing = c.execute("""
        SELECT id, best_score, attempts_count, status FROM listening_progress
        WHERE telegram_id=? AND lesson_id=?
    """, (str(tg_id), lesson_id)).fetchone()

    if existing:
        prev_best = existing["best_score"] or 0
        prev_attempts = existing["attempts_count"] or 0
        prev_status = existing["status"] or ""
        new_best = max(prev_best, score)
        new_attempts = prev_attempts + 1
        # Don't downgrade a 'completed' status
        new_status = "completed" if (prev_status == "completed" or status == "completed") else status
        completed_at_clause = ", completed_at=CURRENT_TIMESTAMP" if (new_status == "completed" and prev_status != "completed") else ""
        c.execute(f"""
            UPDATE listening_progress
            SET best_score=?, attempts_count=?, status=?{completed_at_clause}
            WHERE id=?
        """, (new_best, new_attempts, new_status, existing["id"]))
    else:
        completed_at_val = "CURRENT_TIMESTAMP" if status == "completed" else "NULL"
        c.execute(f"""
            INSERT INTO listening_progress
                (telegram_id, track_id, stage_id, lesson_id, status,
                 best_score, attempts_count, completed_at)
            VALUES (?, 1, ?, ?, ?, ?, 1, {completed_at_val})
        """, (str(tg_id), stage_id, lesson_id, status, score))

def _record_attempt(c, tg_id, lesson_id, stage_id, score, correct, total, answers):
    try:
        passed_val = 1 if score >= 65 else 0
        c.execute("""
            INSERT INTO listening_attempts
                (telegram_id, stage_id, score, correct_count, total,
                 answers_json, passed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (str(tg_id), stage_id, score, correct, total,
              json.dumps(answers, ensure_ascii=False), passed_val))
    except Exception as e:
        # attempts table may have a slightly different schema; ignore silently
        pass

def _next_lesson(c, stage_id, current_order):
    row = c.execute("""
        SELECT id FROM listening_lessons
        WHERE stage_id=? AND order_index>?
        ORDER BY order_index ASC LIMIT 1
    """, (stage_id, current_order)).fetchone()
    if row:
        return dict(row)
    # Try first lesson of next stage
    row = c.execute("""
        SELECT l.id FROM listening_lessons l
        WHERE l.stage_id=?
        ORDER BY l.order_index ASC LIMIT 1
    """, (stage_id + 1,)).fetchone()
    return dict(row) if row else None



# ═══════════════════════════════════════════════════════════
# MASTERY MODE - Progressive learning with 3 attempts per lesson
# Each attempt uses a fresh clip+question from the lesson's pool
# After 3 wrong answers → push to student_error_bank, unlock next lesson
# ═══════════════════════════════════════════════════════════

def _get_lesson_question_pool(c, lesson_id):
    """Return list of (clip_dict, question_dict) tuples for a mastery lesson."""
    lesson = c.execute("SELECT * FROM listening_lessons WHERE id=?", (lesson_id,)).fetchone()
    if not lesson:
        return None, []
    ld = dict(lesson)
    try:
        clip_ids = json.loads(ld.get("clip_ids_json") or "[]")
    except Exception:
        clip_ids = []
    if not clip_ids:
        return ld, []

    pool = []
    for cid in clip_ids:
        clip = c.execute("SELECT * FROM listening_audio_clips WHERE id=?", (cid,)).fetchone()
        if not clip:
            continue
        cd = dict(clip)
        qs = c.execute("""
            SELECT * FROM listening_questions
            WHERE clip_id=? AND (is_exam=0 OR is_exam IS NULL)
            ORDER BY order_index, id
        """, (cid,)).fetchall()
        for q in qs:
            qd = dict(q)
            try:
                qd["options"] = json.loads(qd.get("options_json") or "[]")
            except Exception:
                qd["options"] = []
            pool.append((cd, qd))
    return ld, pool


def _is_lesson_unlocked(c, tg_id, lesson_id):
    """ALL_UNLOCKED_FOR_SUBSCRIBERS — كل الدروس مفتوحة للمشترك."""
    return True
    # --- old logic below (kept for reference) ---
    lesson = c.execute("SELECT prev_lesson_id, stage_id FROM listening_lessons WHERE id=?", (lesson_id,)).fetchone()
    if not lesson:
        return False
    prev_id = lesson["prev_lesson_id"]
    if not prev_id:
        return True
    # Did user pass (any correct) or exhaust (3 attempts) the previous lesson?
    row = c.execute("""
        SELECT
            SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END) as wins,
            COUNT(*) as total_attempts
        FROM listening_mastery_attempts
        WHERE user_id=? AND lesson_id=?
    """, (str(tg_id), prev_id)).fetchone()
    if not row:
        return False
    wins = row["wins"] or 0
    total = row["total_attempts"] or 0
    return total >= 3


# ─── ENDPOINT 1: Start / continue mastery lesson ───────────
@listening_bp.route("/api/listening/mastery/<int:lesson_id>/start", methods=["GET"])
def api_mastery_start(lesson_id):
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()

    lesson_d, pool = _get_lesson_question_pool(c, lesson_id)
    if not lesson_d:
        conn.close()
        return jsonify(success=False, error="Lesson not found"), 404
    if not lesson_d.get("mastery_mode"):
        conn.close()
        return jsonify(success=False, error="Not a mastery lesson"), 400
    if not pool:
        conn.close()
        return jsonify(success=False, error="No questions available for this lesson"), 400

    # Check unlock status
    if not _is_lesson_unlocked(c, tg_id, lesson_id):
        conn.close()
        return jsonify(success=False, locked=True,
                       error="Complete the previous lesson first"), 403

    # How many attempts already?
    attempts = c.execute("""
        SELECT attempt_number, question_id, is_correct
        FROM listening_mastery_attempts
        WHERE user_id=? AND lesson_id=?
        ORDER BY attempt_number ASC
    """, (str(tg_id), lesson_id)).fetchall()
    attempts_list = [dict(a) for a in attempts]

    attempt_count = len(attempts_list)
    max_attempts = lesson_d.get("mastery_max_attempts") or 3
    # Lesson complete only after all attempts used
    already_passed = (attempt_count >= max_attempts)

    if already_passed:
        conn.close()
        return jsonify(success=True, completed=True, passed=True,
                       attempt_count=attempt_count,
                       message="Lesson already mastered")

    if attempt_count >= max_attempts:
        conn.close()
        return jsonify(success=True, completed=True, passed=False, exhausted=True,
                       attempt_count=attempt_count,
                       message="All attempts used. Lesson unlocked.")

    # Pick a fresh clip+question (one not used in previous attempts of this lesson)
    used_qids = {a["question_id"] for a in attempts_list}
    available = [(cd, qd) for cd, qd in pool if qd["id"] not in used_qids]
    if not available:
        # fallback: reuse from pool (cycle)
        available = pool

    # Use attempt_count as deterministic index (so refresh doesn't change question)
    idx = attempt_count % len(available)
    clip_d, q_d = available[idx]

    # Build first-clip intro (principle teaching) on attempt 0
    intro_clip = None
    if attempt_count == 0 and pool:
        intro_clip = {
            "id": pool[0][0]["id"],
            "code": pool[0][0].get("code"),
            "title_en": pool[0][0].get("title_en") or pool[0][0].get("title_ar"),
            "audio_url": pool[0][0].get("audio_url"),
            "transcript_en": pool[0][0].get("transcript_en"),
        }

    conn.close()
    return jsonify(
        success=True,
        completed=False,
        lesson={
            "id": lesson_d["id"],
            "code": lesson_d.get("code"),
            "title_ar": lesson_d.get("title_ar"),
            "stage_id": lesson_d.get("stage_id"),
            "sub_lesson_index": lesson_d.get("sub_lesson_index"),
            "principle_en": lesson_d.get("principle_en"),
            "principle_ar": lesson_d.get("principle_ar"),
        },
        attempt_number=attempt_count + 1,
        max_attempts=max_attempts,
        intro_clip=intro_clip,
        current_clip={
            "id": clip_d["id"],
            "code": clip_d.get("code"),
            "title_en": clip_d.get("title_en") or clip_d.get("title_ar"),
            "audio_url": clip_d.get("audio_url"),
            "transcript_en": clip_d.get("transcript_en"),
            "context_ar": clip_d.get("context_ar"),
        },
        question={
            "id": q_d["id"],
            "question_en": q_d.get("question_en"),
            "options": q_d.get("options", []),
            "question_type": q_d.get("question_type"),
        }
    )


# ─── ENDPOINT 2: Submit a mastery answer ───────────────────
@listening_bp.route("/api/listening/mastery/<int:lesson_id>/submit", methods=["POST"])
def api_mastery_submit(lesson_id):
    tg_id = _get_tg_id()
    payload = request.get_json(silent=True) or {}
    question_id = payload.get("question_id")
    user_answer = payload.get("user_answer")
    time_taken = int(payload.get("time_taken_sec") or 0)

    if question_id is None or user_answer is None:
        return jsonify(success=False, error="Missing question_id or user_answer"), 400

    conn = _db(); c = conn.cursor()

    lesson = c.execute("SELECT * FROM listening_lessons WHERE id=?", (lesson_id,)).fetchone()
    if not lesson:
        conn.close()
        return jsonify(success=False, error="Lesson not found"), 404
    lesson_d = dict(lesson)
    max_attempts = lesson_d.get("mastery_max_attempts") or 3

    q = c.execute("SELECT * FROM listening_questions WHERE id=?", (int(question_id),)).fetchone()
    if not q:
        conn.close()
        return jsonify(success=False, error="Question not found"), 404
    qd = dict(q)

    try:
        correct_idx = int(qd.get("correct_answer") or -1)
    except Exception:
        correct_idx = -1
    try:
        user_idx = int(user_answer)
    except Exception:
        user_idx = -1
    is_correct = (user_idx == correct_idx and correct_idx >= 0)

    # Current attempt number
    prev_count = c.execute("""
        SELECT COUNT(*) as n FROM listening_mastery_attempts
        WHERE user_id=? AND lesson_id=?
    """, (str(tg_id), lesson_id)).fetchone()["n"]
    attempt_number = prev_count + 1

    # Record attempt
    c.execute("""
        INSERT INTO listening_mastery_attempts
        (user_id, lesson_id, clip_id, question_id, attempt_number,
         user_answer, is_correct, time_taken_sec, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (str(tg_id), lesson_id, qd.get("clip_id"), qd["id"],
          attempt_number, user_idx, 1 if is_correct else 0, time_taken))

    exhausted = (attempt_number >= max_attempts) and not is_correct
    # Lesson completes only after ALL attempts (deeper training)
    lesson_passed = (attempt_number >= max_attempts)

    # If 3rd wrong attempt → push to error bank
    pushed_to_bank = False
    if exhausted:
        existing = c.execute("""
            SELECT id, error_count FROM student_error_bank
            WHERE telegram_id=? AND question_id=?
        """, (str(tg_id), qd["id"])).fetchone()
        if existing:
            c.execute("""
                UPDATE student_error_bank
                SET error_count=error_count+1, last_attempted=CURRENT_TIMESTAMP
                WHERE id=?
            """, (existing["id"],))
        else:
            c.execute("""
                INSERT INTO student_error_bank
                (telegram_id, question_id, error_count, last_attempted)
                VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            """, (str(tg_id), qd["id"]))
        pushed_to_bank = True

    # Mark lesson complete in listening_progress if passed
    if lesson_passed:
        # Calculate real score: correct_count / max_attempts * 100
        correct_count_row = c.execute(
            "SELECT COUNT(*) FROM listening_mastery_attempts WHERE user_id=? AND lesson_id=? AND is_correct=1",
            (str(tg_id), lesson_id)
        ).fetchone()
        correct_count = correct_count_row[0] if correct_count_row else 0
        score = round((correct_count / max_attempts) * 100)
        status = "completed" if score >= 50 else "exhausted"
        try:
            _save_progress(c, tg_id, lesson_id, lesson_d["stage_id"],
                         score, (1 if is_correct else 0), 1, status)
        except Exception:
            pass

    conn.commit()

    # Find next lesson
    next_lesson_id = None
    if lesson_passed:
        nxt = c.execute("""
            SELECT id FROM listening_lessons
            WHERE prev_lesson_id=? AND mastery_mode=1
            ORDER BY id ASC LIMIT 1
        """, (lesson_id,)).fetchone()
        if nxt:
            next_lesson_id = nxt["id"]

    # Build feedback
    try:
        opts = json.loads(qd.get("options_json") or "[]")
    except Exception:
        opts = []

    feedback = {
        "is_correct": is_correct,
        "correct_answer": correct_idx,
        "user_answer": user_idx,
        "options": opts,
        "explanation_ar": qd.get("explanation_ar") or "",
        "wrong_explanation_ar": qd.get("wrong_explanation_ar") or "",
        "elimination_hint_ar": qd.get("elimination_hint_ar") or "",
        "strategy_ar": qd.get("strategy_ar") or "",
        "listening_tip_ar": qd.get("listening_tip_ar") or "",
        "principle_ar": lesson_d.get("principle_ar") or "",
    }

    conn.close()
    return jsonify(
        success=True,
        is_correct=is_correct,
        attempt_number=attempt_number,
        max_attempts=max_attempts,
        lesson_passed=lesson_passed,
        exhausted=exhausted,
        pushed_to_error_bank=pushed_to_bank,
        next_lesson_id=next_lesson_id,
        feedback=feedback
    )


# ─── ENDPOINT 3: Get next clip+question for next attempt ───
@listening_bp.route("/api/listening/mastery/<int:lesson_id>/next-attempt", methods=["GET"])
def api_mastery_next_attempt(lesson_id):
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()

    lesson_d, pool = _get_lesson_question_pool(c, lesson_id)
    if not lesson_d or not pool:
        conn.close()
        return jsonify(success=False, error="Lesson or pool not available"), 404

    attempts = c.execute("""
        SELECT question_id, is_correct FROM listening_mastery_attempts
        WHERE user_id=? AND lesson_id=?
        ORDER BY attempt_number ASC
    """, (str(tg_id), lesson_id)).fetchall()
    attempt_count = len(attempts)
    max_attempts = lesson_d.get("mastery_max_attempts") or 3

    if attempt_count >= max_attempts:
        conn.close()
        return jsonify(success=True, completed=True, passed=False, exhausted=True)

    used_qids = {a["question_id"] for a in attempts}
    available = [(cd, qd) for cd, qd in pool if qd["id"] not in used_qids]
    if not available:
        available = pool

    idx = attempt_count % len(available)
    clip_d, q_d = available[idx]

    conn.close()
    return jsonify(
        success=True,
        completed=False,
        attempt_number=attempt_count + 1,
        max_attempts=max_attempts,
        current_clip={
            "id": clip_d["id"],
            "code": clip_d.get("code"),
            "title_en": clip_d.get("title_en") or clip_d.get("title_ar"),
            "audio_url": clip_d.get("audio_url"),
            "transcript_en": clip_d.get("transcript_en"),
            "context_ar": clip_d.get("context_ar"),
        },
        question={
            "id": q_d["id"],
            "question_en": q_d.get("question_en"),
            "options": q_d.get("options", []),
            "question_type": q_d.get("question_type"),
        }
    )



# ═══════════════════════════════════════════════════════════
# VIEW: Mastery lesson page (renders mastery_lesson.html)
# ═══════════════════════════════════════════════════════════
@listening_bp.route("/listening/mastery/<int:lesson_id>")
@require_section_access("listening")
def view_mastery_lesson(lesson_id):
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()
    lesson = c.execute("SELECT * FROM listening_lessons WHERE id=?", (lesson_id,)).fetchone()
    if not lesson:
        conn.close()
        return "Lesson not found", 404
    lesson_d = dict(lesson)
    if not lesson_d.get("mastery_mode"):
        conn.close()
        return redirect(f"/listening/lesson/{lesson_id}?user_id={tg_id}")
    stage = c.execute("SELECT * FROM listening_stages WHERE id=?", (lesson_d["stage_id"],)).fetchone()
    conn.close()
    return render_template("toefl_listening/mastery_lesson.html",
                         lesson=lesson_d,
                         stage=dict(stage) if stage else {},
                         user_id=tg_id)



# ─── ENDPOINT 4: Reset mastery progress for a lesson (re-take) ───
@listening_bp.route("/api/listening/mastery/<int:lesson_id>/reset", methods=["POST"])
def api_mastery_reset(lesson_id):
    tg_id = _get_tg_id()
    conn = _db(); c = conn.cursor()
    c.execute("DELETE FROM listening_mastery_attempts WHERE user_id=? AND lesson_id=?",
              (str(tg_id), lesson_id))
    n1 = c.rowcount
    c.execute("DELETE FROM listening_progress WHERE telegram_id=? AND lesson_id=?",
              (str(tg_id), lesson_id))
    n2 = c.rowcount
    conn.commit()
    conn.close()
    return jsonify(success=True, deleted_attempts=n1, deleted_progress=n2)
