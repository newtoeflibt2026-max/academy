import sqlite3
import os

DB_PATH_APP = os.path.join(os.path.dirname(__file__), "data", "yamen_academy.db")
DB_PATH_BOT = os.path.join(os.path.dirname(__file__), "academy.db")

def safe_alter(conn, table, col_def):
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
        print(f"[OK] Added {col_def} to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"[SKIP] Column already exists: {col_def} in {table}")
        else:
            print(f"[ERROR] {e} on {table} -> {col_def}")

def migrate_app_db():
    if not os.path.exists(DB_PATH_APP):
        print("App DB not found.")
        return
    conn = sqlite3.connect(DB_PATH_APP)
    
    # students
    safe_alter(conn, "students", "required_score INTEGER DEFAULT 59")
    safe_alter(conn, "students", "mock_exam_score INTEGER DEFAULT 0")
    safe_alter(conn, "students", "is_graduated INTEGER DEFAULT 0")

    # lessons
    safe_alter(conn, "lessons", "course_type TEXT DEFAULT 'toefl'")
    safe_alter(conn, "lessons", "week_number INTEGER DEFAULT 1")
    safe_alter(conn, "lessons", "day_number INTEGER DEFAULT 1")
    safe_alter(conn, "lessons", "vocab_content TEXT")
    safe_alter(conn, "lessons", "grammar_content TEXT")
    safe_alter(conn, "lessons", "skill_content TEXT")

    # questions
    safe_alter(conn, "questions", "lesson_id INTEGER")
    safe_alter(conn, "questions", "is_mock INTEGER DEFAULT 0")

    conn.commit()
    conn.close()

def migrate_bot_db():
    if not os.path.exists(DB_PATH_BOT):
        print("Bot DB not found.")
        return
    conn = sqlite3.connect(DB_PATH_BOT)
    
    # students
    safe_alter(conn, "students", "required_score INTEGER DEFAULT 59")
    safe_alter(conn, "students", "mock_exam_score INTEGER DEFAULT 0")
    safe_alter(conn, "students", "is_graduated INTEGER DEFAULT 0")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("Migrating App DB...")
    migrate_app_db()
    print("\nMigrating Bot DB...")
    migrate_bot_db()
    print("\nMigration complete.")
