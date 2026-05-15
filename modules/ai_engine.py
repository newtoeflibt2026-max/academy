from modules.models import query_db, execute_db

def get_ai_config():
    rows = query_db("SELECT config_key, config_value FROM ai_config")
    return {r["config_key"]: r["config_value"] for r in rows}

def assess_speaking_submission(submission_id):
    row = query_db("SELECT * FROM audio_submissions WHERE id=?", (submission_id,), one=True)
    if not row: return None
    from modules.audio_logic import evaluate_speaking
    result = evaluate_speaking(row["file_path"])
    execute_db(
        "UPDATE audio_submissions SET ai_score=?, ai_feedback=?, transcript=? WHERE id=?",
        (result["score"], f"Score: {result['score']}/10, Duration: {result['duration']}s", result["transcript"], submission_id)
    )
    return result

def assess_writing_submission(submission_id):
    row = query_db("SELECT * FROM writing_submissions WHERE id=?", (submission_id,), one=True)
    if not row: return None
    from modules.audio_logic import evaluate_writing
    result = evaluate_writing(row["content"])
    execute_db(
        "UPDATE writing_submissions SET ai_score=?, ai_feedback=? WHERE id=?",
        (result["score"], f"Word count: {result['word_count']}, Score: {result['score']}/10", submission_id)
    )
    return result

def log_activity(student_id, action, details=""):
    execute_db(
        "INSERT INTO activity_log (student_id, action, details) VALUES (?,?,?)",
        (student_id, action, details)
    )
