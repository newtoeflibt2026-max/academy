# Yamen Academy - TOEFL iBT 2026 - PROJECT MAP
Last updated: 2026-05-28 07:05

## DATABASE PATH
C:\Users\nelt2\yamen_academy\academy.db

## ARCHITECTURE
- Backend: Flask, Blueprints in routes/
- Templates: templates/*.html (UTF-8, RTL Arabic)
- Services: services/hearts_api.py
- Database: SQLite, 81 tables

## COMPLETED PHASES

### Phase A1 - Infrastructure (DONE)
- Added 10 new tables: hearts_log, reading_complete_words, reading_daily_life, reading_academic, listening_choose_response, listening_conversation, listening_announcement, listening_academic_talk, speaking_listen_repeat, speaking_interview
- Added 3 columns to students: hearts (default 5), hearts_updated_at, hearts_unlimited

### Phase A2 - Hearts API (DONE)
- File: services/hearts_api.py
- Functions: get_hearts_status, lose_heart, refill_hearts, can_practice
- Logic: 5 hearts max, regen 1 per 5 hours, premium = unlimited

### Phase A3 - Home + Learning Path (DONE)
- File: routes/home_routes.py
- Routes: /home, /path/<section>, /mock-exam, /api/hearts/*
- Templates: home.html (professional Duolingo-style), learning_path.html
- Added mini_lessons table (15 lessons seeded) + user_lesson_progress table

## CRITICAL TECHNICAL NOTES (DO NOT FORGET)
1. PowerShell heredoc CORRUPTS Arabic encoding (cp1256/cp1252).
   ALWAYS write Arabic as \uXXXX escapes in Python strings.
2. High emoji (U+1F300+) BREAK Python heredoc.
   Use BMP-only chars: heart ?, star ?, lock ?, check ?, triangle ?
3. After editing .py files: MUST restart server (py app.py)
   After editing .html files: only Ctrl+F5 needed
4. app.py has try/except blocks at lines 16-31. NEVER inject inside them.
   Safe injection point: AFTER line 'placement_bp not loaded'

## EXISTING DB STRUCTURE (KEY TABLES)
- students (60 columns): user_id, telegram_id, name, xp, streak, hearts, subscription_type, current_band, target_band, target_score
- subscription_plans (7 rows): free_trial, monthly, etc.
- subscription_limits (4 rows): hearts/lessons limits per plan
- stages (22 rows): foundation/grammar/vocabulary tracks
- lessons (32 rows): existing lessons, 13 are reading
- mini_lessons (15 rows): NEW Duolingo-style path (5 reading, 4 listening, 4 writing, 2 speaking)
- user_lesson_progress: tracks completion/stars per mini_lesson
- hearts_log: every heart change recorded
- error_bank (24 rows): student errors for review
- sentence_building_exercises (50 rows): Writing Task 1 ready
- writing_email_scenarios (5 rows): Writing Task 2
- writing_discussion_scenarios (3 rows): Writing Task 3

## ALL REGISTERED ROUTES (key ones)
- /home -> home page
- /path/<section> -> learning path per section (reading/listening/writing/speaking)
- /lesson/<id> -> EXISTING route (lesson_page)
- /writing/sentence-building -> Writing Task 1
- /writing/email -> Writing Task 2
- /writing/discussion/list -> Writing Task 3
- /placement -> placement test
- /weekly-task -> weekly mission
- /student -> student dashboard
- /admin -> admin panel
- /miniapp/* -> Telegram mini-app routes
- /api/hearts/* -> hearts API

## NEXT STEPS (IN ORDER)
1. Phase B - Content for Reading (3 types) - JSON files in content/reading/
2. Phase C - Content for Listening (4 types) - JSON files + audio
3. Phase D - Lesson player (/lesson/<id>) - connect mini_lesson to content
4. Phase E - Quiz system with 80% pass threshold
5. Phase F - Speaking tasks (Listen-Repeat + Interview)
6. Phase G - Mock Exam aggregating all sections
7. Phase H - Telegram bot integration
8. Phase I - Certificate generation on graduation

## HOW TO RESUME WORK (NEW SESSION)
1. Open this file: notepad C:\Users\nelt2\yamen_academy\PROJECT_MAP.md
2. Copy entire content to Claude
3. Say: "We are continuing the project. Current state in PROJECT_MAP.md. Continue from Phase X"

## COMMON COMMANDS
- Start server: cd C:\Users\nelt2\yamen_academy ; $env:DB_PATH = "C:\Users\nelt2\yamen_academy\academy.db" ; py app.py
- Stop server: Get-Process python | Stop-Process -Force
- DB inspect: py -c "import sqlite3; c=sqlite3.connect(r'C:\Users\nelt2\yamen_academy\academy.db'); print(c.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall())"
