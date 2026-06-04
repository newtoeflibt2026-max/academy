# -*- coding: utf-8 -*-
import os, sys, json, sqlite3, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings

CONTENT_DIR = "content/email_scenarios"
DB_PATH = settings.DB_PATH

def j(val):
    if val is None or val == "":
        return None
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    return val

def main():
    files = sorted([f for f in glob.glob(CONTENT_DIR + "/*.json") if not os.path.basename(f).startswith("_")])
    if not files:
        print("[WARN] No scenario files")
        return 0
    print("[INFO] Found " + str(len(files)) + " scenario files")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    inserted, updated, errors = 0, 0, 0
    Q5 = "(?,?,?,?,?,?,?,?,?,?)"
    Q16 = "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    SQL_INS_SC = "INSERT INTO writing_email_scenarios (code, title_ar, title_en, scenario_text, recipient_role, requirements_json, target_tier, min_words, difficulty, order_index) VALUES " + Q5
    SQL_UPD_SC = "UPDATE writing_email_scenarios SET title_ar=?, title_en=?, scenario_text=?, recipient_role=?, requirements_json=?, target_tier=?, min_words=?, difficulty=?, order_index=? WHERE id=?"
    SQL_INS_CC = "INSERT INTO email_coach_content (scenario_id, target_tier, step1_situation_ar, step1_situation_en, step1_recipient_ar, step1_tone_ar, step1_goals_json, step2_structure_json, step3_phrases_json, step4_model_email, step4_annotations_json, step5_fill_template, step5_blanks_hints_json, step6_checklist_json, common_mistakes_json, video_url) VALUES " + Q16
    SQL_UPD_CC = "UPDATE email_coach_content SET target_tier=?, step1_situation_ar=?, step1_situation_en=?, step1_recipient_ar=?, step1_tone_ar=?, step1_goals_json=?, step2_structure_json=?, step3_phrases_json=?, step4_model_email=?, step4_annotations_json=?, step5_fill_template=?, step5_blanks_hints_json=?, step6_checklist_json=?, common_mistakes_json=?, video_url=? WHERE scenario_id=?"
    for idx, fpath in enumerate(files, start=1):
        fname = os.path.basename(fpath)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            sc = data.get("scenario", {})
            cc = data.get("coach_content", {})
            code = sc.get("code", "")
            if not code:
                print("  [SKIP] " + fname)
                continue
            existing = cur.execute("SELECT id FROM writing_email_scenarios WHERE code=?", (code,)).fetchone()
            req_json = json.dumps(sc.get("requirements", []), ensure_ascii=False)
            sc_vals = (sc.get("title_ar",""), sc.get("title_en",""), sc.get("scenario_text",""), sc.get("recipient_role",""), req_json, sc.get("target_tier","tier69"), sc.get("min_words",100), sc.get("difficulty","medium"), sc.get("order_index",idx))
            if existing:
                sid = existing["id"]
                cur.execute(SQL_UPD_SC, sc_vals + (sid,))
                updated += 1
                act = "UPDATE"
            else:
                cur.execute(SQL_INS_SC, (code,) + sc_vals)
                sid = cur.lastrowid
                inserted += 1
                act = "INSERT"
            ecc = cur.execute("SELECT id FROM email_coach_content WHERE scenario_id=?", (sid,)).fetchone()
            cv = (sc.get("target_tier","tier69"), cc.get("step1_situation_ar",""), cc.get("step1_situation_en",""), cc.get("step1_recipient_ar",""), cc.get("step1_tone_ar",""), j(cc.get("step1_goals_json")), j(cc.get("step2_structure_json")), j(cc.get("step3_phrases_json")), cc.get("step4_model_email",""), j(cc.get("step4_annotations_json")), cc.get("step5_fill_template",""), j(cc.get("step5_blanks_hints_json")), j(cc.get("step6_checklist_json")), j(cc.get("common_mistakes_json")), cc.get("video_url",""))
            if ecc:
                cur.execute(SQL_UPD_CC, cv + (sid,))
            else:
                cur.execute(SQL_INS_CC, (sid,) + cv)
            print("  [" + act + "] " + fname + " -> id=" + str(sid))
        except Exception as e:
            print("  [ERROR] " + fname + ": " + str(e))
            errors += 1
    conn.commit()
    total = cur.execute("SELECT COUNT(*) FROM writing_email_scenarios").fetchone()[0]
    print("")
    print("=" * 50)
    print("  Inserted: " + str(inserted) + ", Updated: " + str(updated) + ", Errors: " + str(errors))
    print("  Total scenarios in DB: " + str(total))
    print("=" * 50)
    conn.close()
    return 0 if errors == 0 else 1

if __name__ == "__main__":
    sys.exit(main())