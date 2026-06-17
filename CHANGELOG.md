
## 2026-06-17 - Day 3: Writing curriculum + 500 fix

### Built (days prior, now documented)
- Full Writing curriculum: 5 stages, 30 lessons, 70 questions
  - Stage 1 Foundation, Stage 2 Build-Sentence, Stage 3 Email, Stage 4 Discussion, Stage 5 Mastery
- Linked 30 orphan exercises to lessons (writing_questions.lesson_id)
- Tier-aware practice button on email/discussion lessons -> /writing/email/<id> and /writing/discussion/<id>/exam

### Fixed (critical 500)
- /api/writing/lesson/<id>/submit returned HTTP 500 -> browser saw "Unexpected token '<'... not valid JSON"
- Root cause: query used sentence_building_exercises.lesson_id and .is_exam, BUT THOSE COLUMNS DO NOT EXIST
- Fix: sb_count hardcoded to 0; lesson exercises live entirely in writing_questions
- File: routes/writing_toefl.py (backup: .bak_fixsb_*)

### KEY SCHEMA FACTS (do not re-discover)
- sentence_building_exercises columns: id, code, target_tier, difficulty, word_count, correct_sentence,
  arabic_translation, scrambled_words_json, rule_applied, strategy_ar, explanation_ar, common_error_ar,
  hint_ar, order_index, is_active, created_at  -- NO lesson_id, NO is_exam
- writing_questions has lesson_id -> use it for per-lesson exercises
- writing_email_scenarios (5) + writing_discussion_scenarios (3): tier-based scenario tables for Gemini practice
- Railway uses Volume at /app/data/academy.db; app.py AUTO_SYNC copies repo db when newer (by mtime)

---

## 2026-06-14 - Day 2 Hotfix

### Fixed
- Critical: <div id="journeyContainer"> was missing from HTML (only CSS existed)
- loadJourney() had nowhere to render → entire focused journey card invisible

### Files
- templates/student_dashboard.html (backup: .bak_addjourney)


## 2026-06-14 - Day 2 Polish

### Fixed
- `loadJourney()` was using `await` without being `async` → SyntaxError broke all JS on dashboard
- `planCTA` button (#افتح خطتي الكاملة) had no onclick handler
- Missing professional CSS for `.journey-hero`, `.phase-progress`, `.upcoming-section`

### Added
- `scrollToJourney()` helper to smooth-scroll plan button to journey card
- 8pt grid CSS system (max-width 720px, gap 16px, radius 16-20px)
- Responsive breakpoint @480px for mobile

### Files
- templates/student_dashboard.html (backup: .bak_day2polish)

## 2026-06-14 - Day 2: Focused Journey

### Added
- /api/student/journey endpoint - returns current lesson + next 3 + phase progress
- Big hero card on /student showing ONLY the current lesson
- Phase progress bar (F1 -> F2 -> F3 -> Reading)
- Phase completion celebration screen
- "Upcoming 3 lessons" preview (no overwhelming long list)

### Why
Reduce student confusion. Long lesson list (82 items) was overwhelming.
Now the student sees ONE clear next action at any moment.

### TOEFL methodology
Progressive disclosure + spaced repetition. Student focuses on current
challenge, sees just enough future to feel direction, celebrates milestones.

### Files touched
- app.py (new endpoint)
- templates/student_dashboard.html (new hero, new JS)
- PROJECT_STATE.md, CHANGELOG.md

---

## 2026-06-14 - Day 1: Unify student journey

### Done
- /home now redirects to /student (no more duplicate dashboards)
- Removed listening/writing/speaking fake cards (0/0 lessons)
- Reading section links updated to /student
- Created PROJECT_STATE.md and CHANGELOG.md
- API /api/student/dashboard returns smart URLs (quiz vs lesson)
- Daily mission card opens correct lesson based on student progress

### Architecture decisions
- Single canonical dashboard: /student
- F1-EXAM = placement test (20 Q, 70% pass to skip Foundation)
- Smart URL routing in next-lesson API

---

