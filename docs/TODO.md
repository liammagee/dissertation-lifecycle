# Dissertation Tracking Software — TODO Plan

Legend: [ ] pending, [~] in progress, [x] done

1. Foundation
   - [x] Select stack and architecture (ADR-001)
   - [x] Define data model and permissions
   - [x] Bootstrap Django project + core app + auth

2. Project Setup
   - [x] Project creation wizard (title, field, expected defense date)
   - [x] Milestone template selection (5-chapter, ERP PhD addon)
   - [x] Apply templates to create tasks/milestones

3. Tasks & Guidance
   - [ ] Task CRUD (title, description, due date, priority, status) — create/delete later; edit/status exists
   - [x] Guidance popups + links per task
   - [x] Progress logic (checkbox complete; next‑task link on detail)

4. Tracking & Visuals
   - [x] Dashboard with overall completion % and per-section bars/donuts
   - [x] Word count logs + writing streaks
   - [x] Analytics: trends, per-week totals (weekly panel on Writing page)

5. Advisor Features
   - [x] Advisor directory of students
   - [x] Per-student overview + feedback flags
   - [x] CSV/JSON export of student progress

6. Notifications
   - [x] Email reminders for due dates (management command `notify`)
   - [x] Nudges after inactivity (management command `notify`)

7. Documents
   - [x] Upload Word/PDF to tasks
   - [x] Advisor feedback on uploads
   - [x] Volume backup: ZIP exports + docs (README)

8. Motivation & Community (ideal)
   - [x] Badges (streaks + wordcount)
   - [x] Quotes surface area
   - [x] Data export/backup

9. Deployment
   - [x] Fly configuration (volumes, env, secrets)
   - [x] Admin seeding, initial templates
   - [x] README and ops runbook (notifications + backups)
