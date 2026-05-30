# Yamen Academy - Project Guide

Last update: 2026-05-30

## Architecture Principle
Content/Code SEPARATION:
- content/ = JSON files (anyone can add without touching code)
- routes/, templates/, services/ = Code (stable)

## Completed Phases

### Phase 3.1 - TOEFL Writing Wired (DONE)
- Dashboard writing card now links to /writing
- 30 routes working
- Tag: v1.0-writing-live
- Commit: 23f47ac

### Phase 5.1 - Reading Content Structure (IN PROGRESS)
- content/reading/_schema.json
- content/reading/academic/01_biology_cells.json
- content/reading/_templates/academic_template.json

## TOEFL 2026 Roadmap
1. Foundation - planned
2. Reading - Phase 5 in progress
3. Listening - not started
4. Speaking - not started
5. Writing - COMPLETE
6. Mock Exam - not started
7. Graduation - partial

## Exam Screen Requirements (all sections)
- Real timer (auto-submit at zero)
- Split-screen (text left / question right)
- Mark for review
- Review screen before final submit
- No back after submit
- Instant results screen

## How to Add Content (non-programmers)
1. Copy content/reading/_templates/academic_template.json
2. Rename to XX_topic.json in content/reading/academic/
3. Edit text and questions
4. Save - system auto-detects

## Important Commands
Set-Location C:\Users\nelt2\yamen_academy
$env:PYTHONUTF8 = "1"
py app.py

## Critical Notes for Future Sessions
1. 22 backup files in routes/ need cleanup (Phase 6)
2. 8 unpushed commits to origin/main
3. Template caching - restart py app.py after template edits
4. Always use Out-File -Encoding UTF8

### Phase 5.2 - Content Loader Service (DONE)
- services/content_loader.py created
- Auto-loads all JSON from content/reading/*/
- Validates required fields + types + tiers
- In-memory cache (no repeated disk reads)
- API: load_all(), get_by_id(id), list_by_type(type, tier), reload()
- Test: py services\content_loader.py


---

## Phase 5.6 - Complete the Words (Reading Skill)

### Overview
Complete the Words is a fill-in-the-blank exercise. Students fill missing letters in every other word using context and grammar.

### Content (11 texts)
- Easy (3): Brain, Diet, Internet
- Medium (4): Globalization, Agriculture, Renaissance, Leadership
- Hard (4): Cognitive Psychology, Quantum Mechanics, Determinism, Macroeconomics

Stored as JSON in `content/reading/complete_words/`.

### Routes
- `GET  /reading/cw/learn` - Tutorial page (5 steps + worked example)
- `GET  /reading/cw/exam/<content_id>` - Exam screen with smart inputs
- `POST /reading/cw/submit` - Grading + error bank logging
- `GET  /reading/cw/result/<attempt_id>` - Score + answer review

### Smart Input UX
- One <input maxlength=1> per missing letter
- Auto-advance on input
- Backspace returns to previous letter
- Arrow keys navigate manually
- Lowercase enforced

### Error Bank Integration
Wrong answers logged in `error_bank`:
- error_type: `complete_words:<content_id>:blank_<index>`
- wrong_answer: student's attempt
- correct_answer: expected word

### UI Language Policy (locked from Phase 5.6)
- English: titles, button labels, content
- Arabic: instructions, explanations, hints

### UI/UX Standards (locked from Phase 5.6)
1. Professional Tailwind + Cairo/Inter fonts
2. Mimic real TOEFL exam layout
3. Modal pattern: overlay + centered card + animations + ESC to close
4. Unified design system across all skills
5. Arabic RTL with English LTR inline
6. Fully responsive (mobile + tablet + desktop)
7. Elegant loading/error states

### Future Backlog
- Phase 11: Unified Admin Panel for all skills (post-Listening/Speaking/Mock)
  - Add/edit/delete content via web UI
  - AI-assisted question generation
  - PDF upload + template library
