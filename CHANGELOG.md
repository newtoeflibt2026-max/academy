
## 2026-06-17 - Day 3 (part 3): stage exam MCQ fix -> unlocking works

### Fixed (stage unlock blocker)
- Stage exam MCQ grading had SAME json-array bug as lessons (line ~504)
- Browser sends ["answer"], correct_answer is plain text -> all MCQ marked wrong -> never reach 80%
- Result: exam never 'completed' -> next stage stayed locked (dynamic lock logic depends on completion)
- Fix: parse json array, take first element before compare (api_stage_exam_submit)

### How unlocking works (documented)
- writing_stages lock is DYNAMIC (computed in /writing/stage route lines 96-107), NOT a stored flag
- A lesson unlocks when previous lesson status='completed'
- Stage exam unlocks when ALL non-exam lessons completed
- Passing exam (>=80%) writes writing_progress status='completed' -> unlocks next

### Note
- Stage exam questions use is_exam=1 (correct); inventory '0 exercises' is expected (counts is_exam=0 only)

### Files
- routes/writing_toefl.py (backup: .bak_fixexam_*)

---

## 2026-06-17 - Day 3 (part 2): grading logic + is_exam data fix

### Fixed (grading)
- MCQ answers always marked WRONG: browser sends JSON array '["answer"]' but correct_answer stored as plain text
- sentence_order needs words joined with spaces, MCQ needs first element
- Fix in api_lesson_submit: detect q_type -> sentence_order = join words, else = first element

### Fixed (data: writing_questions)
- Stage 2 exercises (ids 23-42, lessons 5-11) were wrongly is_exam=1
- Effect: total_available query (is_exam=0) found 0 -> lessons auto-completed at 100% with NO exercises shown
- Fix: UPDATE is_exam=0 for the 20 sentence_order rows (lessons 5-11)

### KNOWN REMAINING (next)
- Email lesson page shows "manual review 24h" instead of Gemini copy-paste UI (api/writing/email/submit)
- Email/discussion scenarios not varying ('new scenario' returns same topic)
- 8 duplicate questions in stages 3-5 (ids on lessons 18,24,29) to remove

### Files
- routes/writing_toefl.py (backup: .bak_fixall_*)
- academy.db (backup: .bak_fixexam_*)

---

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

