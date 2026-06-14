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

