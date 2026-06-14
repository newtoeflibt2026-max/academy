# Yamen Academy - Project State
Last updated: 2026-06-14

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
- Listening / Writing / Speaking: NOT BUILT (hidden from UI)

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
