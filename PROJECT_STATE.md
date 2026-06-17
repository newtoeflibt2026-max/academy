# Yamen Academy - Project State
Last updated: 2026-06-17

## Mission
TOEFL iBT prep for Arabic-speaking students.

## CANONICAL ARCHITECTURE
- Student dashboard: /student?student_id=<id>
- Lesson with questions: /miniapp/quiz/<id>
- Theory-only lesson: /miniapp/lesson/<id>
- Main API: /api/student/dashboard

## CONTENT (current)
- Foundation: 50 lessons (F1, F2, F3) - has questions
- Reading: 32 lessons (R-01 to R-32) - mixed theory + practice
- Listening / Speaking: NOT BUILT (hidden from UI)
- Writing: BUILT (5 stages, 30 lessons, 70 questions) - routes/writing_toefl.py

## F1-EXAM
Placement test. 20 Q. >=70% skips Foundation, goes to Reading.

## DATABASE
- students PK: user_id (INTEGER). Lookup: telegram_id (TEXT).
- lessons: lesson_code is human key (F1-L01, R-01).
- student_lesson_progress: tracks completion.
- lesson_questions: practice questions per lesson.

## DO NOT
- Create new dashboard pages (/home, /welcome2, etc.)
- Display empty skills - hide them
- Hardcode lesson IDs

## FOR AI ASSISTANTS
Read this file + CHANGELOG.md before any change.


## DAY 2 - Focused Journey (added 2026-06-14)
- New API: /api/student/journey - phase-aware focused view
- Dashboard now shows ONLY: current lesson (big card) + 3 upcoming + phase progress
- 4 phases: F1, F2, F3, reading
- Celebration message when student completes a phase
- Old long lesson list is hidden by default (still accessible via /student lessons tab)
