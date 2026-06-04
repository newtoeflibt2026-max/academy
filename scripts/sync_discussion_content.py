# -*- coding: utf-8 -*-
"""Sync discussion scenarios - supports flat and nested JSON, matches actual DB schema"""
import os, sys, json, glob, sqlite3

sys.stdout.reconfigure(encoding="utf-8")

DB = os.environ.get("DB_PATH", "academy.db")
CONTENT_DIR = "content/discussion_scenarios"

def get_field(data, *keys, default=""):
    for key in keys:
        if "." in key:
            parts = key.split(".")
            v = data
            for p in parts:
                if isinstance(v, dict) and p in v:
                    v = v[p]
                else:
                    v = None
                    break
            if v is not None:
                return v
        elif key in data:
            return data[key]
    return default

def main():
    files = sorted([f for f in glob.glob(f"{CONTENT_DIR}/*.json") if not os.path.basename(f).startswith("_")])
    print(f"[INFO] Found {len(files)} scenario files")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    inserted, updated, errors = 0, 0, 0

    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)

            code = get_field(data, "code", "scenario.code")
            if not code:
                print(f"  [SKIP] {os.path.basename(fp)} (no code)")
                continue

            tlm = get_field(data, "time_limit_minutes", default=None)
            time_limit_sec = tlm * 60 if tlm else get_field(data, "time_limit_seconds", "scenario.time_limit_seconds", default=600)

            scenario_data = (
                code,
                get_field(data, "title_ar", "scenario.title_ar"),
                get_field(data, "title_en", "scenario.title_en"),
                get_field(data, "topic_category", "scenario.topic_category"),
                get_field(data, "professor_name", "scenario.professor.name"),
                get_field(data, "professor_title_en", "scenario.professor.title"),
                get_field(data, "professor_avatar", "scenario.professor.avatar"),
                get_field(data, "professor_question", "scenario.professor.question_en"),
                get_field(data, "professor_question_ar", "scenario.professor.question_ar"),
                get_field(data, "target_tier", "scenario.target_tier", default="tier90"),
                get_field(data, "min_words", "scenario.min_words", default=100),
                time_limit_sec,
                get_field(data, "difficulty", "scenario.difficulty", default=3),
                get_field(data, "order_index", "scenario.order_index", default=0),
            )

            cur.execute("SELECT id FROM writing_discussion_scenarios WHERE code=?", (code,))
            row = cur.fetchone()

            if row:
                sid = row["id"]
                cur.execute("""
                    UPDATE writing_discussion_scenarios SET
                    title_ar=?, title_en=?, topic_category=?,
                    professor_name=?, professor_title=?, professor_avatar=?,
                    professor_question_en=?, professor_question_ar=?,
                    target_tier=?, min_words=?, time_limit_seconds=?,
                    difficulty=?, order_index=?
                    WHERE code=?
                """, scenario_data[1:] + (code,))
                print(f"  [UPDATE] {os.path.basename(fp)} -> id={sid}")
                updated += 1
            else:
                cur.execute("""
                    INSERT INTO writing_discussion_scenarios
                    (code, title_ar, title_en, topic_category,
                     professor_name, professor_title, professor_avatar,
                     professor_question_en, professor_question_ar,
                     target_tier, min_words, time_limit_seconds,
                     difficulty, order_index)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, scenario_data)
                sid = cur.lastrowid
                print(f"  [INSERT] {os.path.basename(fp)} -> id={sid}")
                inserted += 1

            # Student replies
            student_replies = get_field(data, "student_replies", default=[])
            cur.execute("DELETE FROM discussion_student_replies WHERE scenario_id=?", (sid,))
            for idx, sr in enumerate(student_replies):
                cur.execute("""
                    INSERT INTO discussion_student_replies
                    (scenario_id, student_name, student_avatar, reply_text_en, reply_text_ar, position, order_index)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    sid,
                    sr.get("name",""),
                    sr.get("avatar",""),
                    sr.get("text", sr.get("reply_text_en","")),
                    sr.get("text_ar", sr.get("reply_text_ar","")),
                    sr.get("position",""),
                    idx
                ))

            # Coach content
            coach = get_field(data, "coach_content", default=None)
            target_tier = get_field(data, "target_tier", "scenario.target_tier", default="tier90")

            if coach:
                step1_ar = coach.get("step1_analyze_question_ar","")
                step1_kw = coach.get("step1_keywords",[])
                step2_ar = coach.get("step2_analyze_replies_ar","")
                step2_an = coach.get("step2_reply_analysis",[])
                step3_ar = coach.get("step3_build_opinion_ar","")
                step3_po = coach.get("step3_position_options",[])
                phrases = coach.get("phrases",{}) or coach.get("step4_phrases",{})
                model = coach.get("model_response","") or coach.get("step5_model_response","")
                annotations = coach.get("annotations",[]) or coach.get("step5_annotations",[])
                checklist = coach.get("checklist",[]) or coach.get("step6_checklist",[])
                mistakes = coach.get("common_mistakes",[]) or coach.get("step6_common_mistakes",[])
                tier_exp = coach.get("tier_explanation_ar","")
            else:
                step1_ar = get_field(data, "step1_analyze_question_ar")
                step1_kw = get_field(data, "step1_keywords", default=[])
                step2_ar = get_field(data, "step2_analyze_replies_ar")
                step2_an = get_field(data, "step2_reply_analysis", default=[])
                step3_ar = get_field(data, "step3_build_opinion_ar")
                step3_po = get_field(data, "step3_position_options", default=[])
                phrases = get_field(data, "phrases", default={})
                model = get_field(data, "model_response")
                annotations = get_field(data, "annotations", default=[])
                checklist = get_field(data, "checklist", default=[])
                mistakes = get_field(data, "common_mistakes", default=[])
                tier_exp = get_field(data, "tier_explanation_ar")

            tier59_exp = tier_exp if target_tier == "tier59" else ""
            tier69_exp = tier_exp if target_tier == "tier69" else ""
            tier90_exp = tier_exp if target_tier == "tier90" else ""

            cur.execute("DELETE FROM discussion_coach_content WHERE scenario_id=?", (sid,))
            cur.execute("""
                INSERT INTO discussion_coach_content
                (scenario_id, target_tier,
                 step1_analyze_question_ar, step1_keywords_json,
                 step2_analyze_replies_ar, step2_reply_analysis_json,
                 step3_build_opinion_ar, step3_position_options_json,
                 step4_phrases_json,
                 step5_model_response, step5_annotations_json,
                 step6_checklist_json, step6_common_mistakes_json,
                 tier59_explanation, tier69_explanation, tier90_explanation)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                sid, target_tier,
                step1_ar, json.dumps(step1_kw, ensure_ascii=False),
                step2_ar, json.dumps(step2_an, ensure_ascii=False),
                step3_ar, json.dumps(step3_po, ensure_ascii=False),
                json.dumps(phrases, ensure_ascii=False),
                model, json.dumps(annotations, ensure_ascii=False),
                json.dumps(checklist, ensure_ascii=False),
                json.dumps(mistakes, ensure_ascii=False),
                tier59_exp, tier69_exp, tier90_exp
            ))

        except Exception as e:
            print(f"  [ERROR] {os.path.basename(fp)}: {e}")
            errors += 1

    conn.commit()
    print()
    print("="*50)
    print(f"  Inserted: {inserted}, Updated: {updated}, Errors: {errors}")
    cur.execute("SELECT COUNT(*) FROM writing_discussion_scenarios")
    print(f"  Total scenarios in DB: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM discussion_student_replies")
    print(f"  Total student replies: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM discussion_coach_content")
    print(f"  Total coach contents: {cur.fetchone()[0]}")
    print("="*50)
    conn.close()

if __name__ == "__main__":
    main()
