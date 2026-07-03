# -*- coding: utf-8 -*-
"""توليد ملفات صوت الاستماع من قاعدة البيانات باستخدام edge-tts.
يعمل عند بدء التشغيل، يتخطى الملفات الموجودة، آمن للتكرار."""
import os, re, sqlite3, asyncio

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "audio", "listening")
VOICE_MALE = "en-US-GuyNeural"
VOICE_FEMALE = "en-US-JennyNeural"
VOICE_NARR = "en-US-EricNeural"

TABLES = {
    "listening_conversation": "conv",
    "listening_academic_talk": "talk",
    "listening_announcement": "ann",
}

def _db_path():
    try:
        from db import DB_PATH
        return DB_PATH
    except Exception:
        if os.path.isdir("/app/data"):
            return "/app/data/academy.db"
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")

def _strip_speaker(line):
    return re.sub(r"^[A-Za-z][A-Za-z .'\-]{0,30}:\s*", "", line.strip())

def _split_turns(transcript):
    parts = re.split(r"(?=(?:[A-Z][A-Za-z .'\-]{0,30}:))", transcript)
    turns = []
    speakers = {}
    next_voice = 0
    voices = [VOICE_FEMALE, VOICE_MALE]
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = re.match(r"^([A-Z][A-Za-z .'\-]{0,30}):", p)
        if m:
            name = m.group(1).strip()
            if name not in speakers:
                speakers[name] = voices[next_voice % 2]
                next_voice += 1
            voice = speakers[name]
        else:
            voice = VOICE_FEMALE
        text = _strip_speaker(p)
        if text:
            turns.append((voice, text))
    return turns

async def _tts(text, voice, path):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)

async def _gen_dialogue(turns, path):
    import edge_tts
    tmp_files = []
    try:
        for i, (voice, text) in enumerate(turns):
            tf = path + f".part{i}.mp3"
            await _tts(text, voice, tf)
            tmp_files.append(tf)
        with open(path, "wb") as out:
            for tf in tmp_files:
                with open(tf, "rb") as f:
                    out.write(f.read())
    finally:
        for tf in tmp_files:
            try: os.remove(tf)
            except Exception: pass

def generate_all():
    try:
        import edge_tts  # noqa
    except Exception as e:
        print("[gen_audio] edge-tts not available:", e)
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    made = 0
    for table, prefix in TABLES.items():
        try:
            rows = conn.execute(
                f"SELECT code, transcript FROM {table} WHERE transcript IS NOT NULL AND transcript != ''"
            ).fetchall()
        except Exception as e:
            print(f"[gen_audio] skip {table}: {e}")
            continue
        for r in rows:
            code = r["code"]
            transcript = r["transcript"]
            out_path = os.path.join(OUT_DIR, f"{code}.mp3")
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
                continue
            try:
                if prefix == "conv":
                    turns = _split_turns(transcript)
                    if not turns:
                        turns = [(VOICE_FEMALE, transcript)]
                    loop.run_until_complete(_gen_dialogue(turns, out_path))
                elif prefix == "talk":
                    loop.run_until_complete(_tts(transcript, VOICE_NARR, out_path))
                else:
                    loop.run_until_complete(_tts(transcript, VOICE_FEMALE, out_path))
                made += 1
                print(f"[gen_audio] created {code}.mp3 ({os.path.getsize(out_path)} bytes)")
            except Exception as e:
                print(f"[gen_audio] FAILED {code}: {e}")
    conn.close()
    try: loop.close()
    except Exception: pass
    print(f"[gen_audio] done. new files: {made}")

if __name__ == "__main__":
    generate_all()
