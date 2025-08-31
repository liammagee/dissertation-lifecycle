# Data Model Draft

Users & Roles
- User (Django auth)
  - username, email, password, is_active
- Profile
  - user (OneToOne)
  - role: enum [student, advisor, admin]
  - display_name

Organizations (optional, v1 single org)
- Organization
  - name, slug
  - advisors (M2M User)

Projects
- Project
  - id (UUID), student (FK User), title, field_of_study, expected_defense_date (date)
  - status: enum [active, archived]
  - created_at, updated_at

Milestones & Tasks
- MilestoneTemplate
  - key, name, description, order, is_phd_only (bool)
- TaskTemplate
  - milestone (FK), key, title, description, order, guidance_url, guidance_tips (text)
- Milestone
  - project (FK), template (FK), name, order, completed (bool), completed_at
- Task
  - project (FK), milestone (FK), template (FK nullable), title, description, order
  - due_date (date), priority (enum low/med/high), status (todo/doing/done), completed_at

Tracking & Analytics
- WordLog
  - project (FK), date, words (int), note
- StreakSnapshot (derived)
  - project (FK), start_date, days, longest (cached)

Advisor Feedback
- FeedbackRequest
  - project (FK), task (FK nullable), section (char), note, status (open/resolved)
- FeedbackComment
  - request (FK), author (FK User), message, created_at

Documents
- Document
  - project (FK), task (FK nullable)
  - file (FileField -> volume path), filename, size, content_type
  - uploaded_by (FK User), uploaded_at
  - notes

Notifications (email)
- Notification
  - user (FK), kind (due_soon, inactivity_nudge, feedback_request)
  - payload (JSON), scheduled_for, sent_at

Permissions
- Student can CRUD only own Project/Tasks/WordLogs/Documents.
- Advisor can view all Projects within org, add feedback, download documents.
- Admin full access.

Derived Metrics
- Project completion % = completed tasks / total tasks.
- Per-milestone progress; per-section/chapter progress from templates.
- Writing streak = max consecutive days with WordLog > 0.

