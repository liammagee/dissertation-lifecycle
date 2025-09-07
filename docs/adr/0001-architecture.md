# ADR-001: Architecture and Platform Choices

Status: Accepted

Context
- We are building a multi-tenant web app where students manage dissertation projects and advisors track progress. Deploying on Fly.io.

Decisions
- Framework: Django (built-in auth, admin, ORM, forms). Future API via Django REST Framework.
- Database: PostgreSQL (Fly Postgres cluster in prod; SQLite for dev). All core data in DB.
- Storage (Fly.io): Fly Volumes for document uploads and generated exports.
  - Mount path: `/data` (configurable via `UPLOAD_ROOT` env). Django `FileField` will use a custom storage pointing to this path.
  - Backups: nightly job archives `/data/uploads` and attaches to releases; optional offsite copy can be added later.
  - Reason: No built-in object storage in Fly; volumes provide persistent disk colocated with the app.
- Email: SMTP (e.g., Mailgun/SendGrid). Configure via env vars.
- Caching/queues: Start without external services. Use Django’s DB-backed locks and periodic management commands. Optional: Upstash Redis later.
- AuthN/Z: Django auth; roles via `Profile.role` (student, advisor, admin). Per-object permissions for project ownership.
- Templating/UI: Django templates + HTMX for progressive enhancement; Bootstrap for styling.
- Files/limits: Modest doc uploads (Word/PDF). Virus scanning optional later.

Implications
- Single-region volume implies one primary region for writes; scale reads with multiple machines if needed.
- Backups must be explicit (DB + volume snapshots). We’ll document a `fly volumes snapshot` + DB backup cadence.
- If later we require global object storage, we can add a pluggable storage backend without changing models.
