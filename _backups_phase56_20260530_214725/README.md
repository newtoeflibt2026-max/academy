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
