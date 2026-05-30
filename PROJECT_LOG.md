# Yamen Academy — Project Log

> Source of truth. Updated at the end of every phase.
> If you forget context, read this first.

## Mission
Take a weak student to **TOEFL 90+** in the shortest time with the best UX.

## Non-Negotiable Principles
1. Content/Code separation — adding content = JSON only, zero Python edits.
2. Student experience = real TOEFL 2026 exam (timer, split-screen, mark-for-review, auto-submit).
3. Smart pedagogy — adaptive difficulty, spaced repetition, immediate feedback.
4. Never break what works — Writing System is sacred. Do not touch `main.py`, `db.py`, `bot_database.py`.
5. Every achievement documented here + in README.
6. Rollback always possible — backup before edit, small logical commits.

## TOEFL 2026 Order
Foundation → Reading → Listening → Speaking → Writing → Mock Exam → Graduation

## Structural Facts (do not forget)
- Project path: `C:\Users\nelt2\yamen_academy`
- DB path: `/app/data/academy.db`
- Writing routes: `routes/writing_toefl.py` (48KB, 30 routes)
- Reading types: Complete Words, Daily Reading, Academic Reading
- Shell: PowerShell only
- PowerShell writes BOM → loader uses `utf-8-sig`
- Server reload: manual only (debug=off) — kill PIDs then start
- Backup pattern: `<file>.bak_<timestamp>`
- Telegram: `window.STUDENT_ID` from `/student?user_id=...`

## Progress Log

| Phase | Description | Status | Commit / Tag | Evidence |
|---|---|---|---|---|
| 3.0 | Cleanup 39 backups | DONE | 23f47ac | _backups/auto_cleanup_20260530_145307/ |
| 3.1 | Wire Writing to Dashboard | DONE | 23f47ac + v1.0-writing-live | 12/12 smoke + 36 attempts |
| 4   | (skipped — pivoted to Reading) | SKIP | — | — |
| 5.1 | Reading content structure + sample JSON | DONE | (in 5.2-fix commit) | content/reading/academic/01_biology_cells.json |
| 5.2 | content_loader.py service | DONE (after fix) | (in 5.2-fix commit) | services/content_loader.py |
| 5.2-fix | BOM fix (utf-8-sig) + PROJECT_LOG.md | DONE | THIS COMMIT | smoke test passes |
| 5.3 | exam_screen.html (split-screen + timer + review) | NEXT | — | — |
| 5.4 | routes/reading_exam.py + DB tables | TODO | — | — |
| 5.5 | Wire Reading to Dashboard + smoke + tag v1.1-reading-mvp | TODO | — | — |
| 5.6 | Add Daily + Complete-Words content (generalization test) | TODO | — | — |
| 6   | Cleanup 22 backups in routes/ | DEFERRED | — | — |
| 7   | Decide on 25 unused templates | DEFERRED | — | — |
| 8   | Listening Section | FUTURE | — | — |
| 9   | Speaking Section | FUTURE | — | — |
| 10  | Full Mock Exam | FUTURE | — | — |
| 11  | Graduation + Certificate | FUTURE | — | — |

## Pedagogical Decisions (to apply progressively)
- Spaced Repetition (Ebbinghaus): `next_review_at` in student_progress.
- Adaptive Difficulty (ZPD): `difficulty: 1-5` in JSON schema.
- Immediate Feedback (Hattie): instant result screen in practice mode.
- Worked Examples before practice (Sweller).
- Active Recall always — no silent reading.
- Personal Error Log: `student_errors(type, frequency, last_seen)`.
- Two modes: Practice (with feedback) + Exam (strict simulation).
- Streak + Daily Goal (Duolingo pattern).
---
## 5.2-verify (run on 2026-05-30 16:17)
- Python detected: `py`
- Loader smoke test: PASSED (TOTAL_LOADED >= 1)
- .gitignore installed: hides _*.py, *.bak*, .env, *.db-shm/wal, etc.
- Commit `5706ea7` (5.1+5.2+BOM fix) confirmed working.

---
## 5.2-final (run on 2026-05-30 16:22)
### Evidence of working loader:
### Actions:
- Reverted bloated commit `8a38f95` (302 files, 363K lines) via soft reset.
- Re-committed only `.gitignore` cleanly.
- Loader API confirmed: module-level functions (`load_all`, `get_by_id`, `list_by_type`, `list_all_types`, `reload`). NO class.
- Required JSON fields: id, type, title_ar, title_en, tier, duration_seconds, passage, questions.
- ALLOWED_TYPES: academic_reading, daily_reading, complete_words.
- ALLOWED_TIERS: tier59, tier69, tier90.
### Next: Phase 5.3 — exam_screen.html
