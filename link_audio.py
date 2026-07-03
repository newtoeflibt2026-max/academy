# -*- coding: utf-8 -*-
"""ربط حقل audio_file في جداول الاستماع بمسارات الملفات الحقيقية."""
import sqlite3, os

TABLES = ["listening_conversation", "listening_academic_talk", "listening_announcement"]

def _db_path():
    try:
        from db import DB_PATH
        return DB_PATH
    except Exception:
        if os.path.isdir("/app/data"):
            return "/app/data/academy.db"
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")

def link_all():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    updated = 0
    audio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "audio", "listening")
    for table in TABLES:
        try:
            rows = conn.execute(f"SELECT id, code FROM {table}").fetchall()
        except Exception as e:
            print(f"[link_audio] skip {table}: {e}")
            continue
        for r in rows:
            code = r["code"]
            rel_path = f"/static/audio/listening/{code}.mp3"
            file_path = os.path.join(audio_dir, f"{code}.mp3")
            exists = os.path.exists(file_path)
            try:
                conn.execute(
                    f"UPDATE {table} SET audio_url=? WHERE id=?",
                    (rel_path, r["id"])
                )
                updated += 1
                mark = "OK" if exists else "MISSING-FILE"
                print(f"[link_audio] {code} -> {rel_path} [{mark}]")
            except Exception as e:
                print(f"[link_audio] FAILED {code}: {e}")
    conn.commit()
    conn.close()
    print(f"[link_audio] done. rows updated: {updated}")

if __name__ == "__main__":
    link_all()
