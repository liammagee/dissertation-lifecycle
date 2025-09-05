# dissertation-lifecycle

Lightweight Python CLI for managing a dissertation from introduction to literature review, methodology, findings, and conclusion. It scaffolds a project, tracks section word counts against targets, and exports a combined Markdown document.

## Quickstart

- Requires Python 3.8+
- Run the CLI via module mode: `python -m dissertation_manager ...`

## Web App (no dependencies)

- Start single-project server in your project folder:

```
python3 -m dissertation_manager web . --host 127.0.0.1 --port 8000
```

- Open `http://127.0.0.1:8000`
  - If no project exists, fill the init form.
  - Edit sections in-browser, adjust targets, and export Markdown.
  - Report: `http://127.0.0.1:8000/report` for a printable progress report (use the browser's Print to PDF).

### Consolidated Mode (students + advisor in one app)

- Choose a shared directory to hold all student projects, e.g. `/path/to/students`.
- Run server with `--data-root`:

```
python3 -m dissertation_manager web . --data-root /path/to/students --host 127.0.0.1 --port 8000
```

- Open `http://127.0.0.1:8000`:
  - Students: click “Sign Up” to create a project (no authentication yet). You’ll be redirected to `/student/<slug>/` to work on your dissertation.
  - Advisors: view the dashboard (all students), Overview, Summary, Heatmap, JSON/CSV exports, and per-student pages and Report.

### Legacy Advisor Dashboard (separate process, optional)

- Place each student's project in a subfolder under a common directory. Each project must contain `.dissertation/config.json`.
- Run:

```
python3 -m dissertation_manager web-advisor /path/to/students --host 127.0.0.1 --port 8001
```

- Open `http://127.0.0.1:8001` to see all students with progress donuts. Click a student to view and edit their project pages.

- Summary and exports:
  - Lifecycle summary grid: `http://127.0.0.1:8001/summary` (rows = students, columns = sections)
  - Overview: `http://127.0.0.1:8001/overview` (average combined progress + per-section averages)
  - JSON rollup: `http://127.0.0.1:8001/export.json` (array of student status objects)
  - CSV rollup: `http://127.0.0.1:8001/export.csv` (combined/words/lifecycle and per-section columns)
  - Lifecycle heatmap: `http://127.0.0.1:8001/heatmap?section=literature_review` (students × phases with mini donuts)
  - Per-student report: `http://127.0.0.1:8001/student/<folder>/report` (print to PDF from browser)

### 1) Initialize a project

```
python -m dissertation_manager init . \
  --title "My Dissertation" \
  --author "Your Name" \
  --degree "MSc" \
  --institution "Your University" \
  --supervisor "Dr. Advisor" \
  --targets "introduction=1500,literature_review=4000,methodology=2500,findings=2500,conclusion=1500"
```

This creates:

- `.dissertation/config.json`: project metadata and targets
- `sections/*.md`: one Markdown file per section with a starter template
- `notes/todo.md`: simple task list
- `exports/`: default export folder

### 2) Check status and progress

```
python -m dissertation_manager status
```

Shows each section’s word count and targets, plus total progress.

### 3) Update a section from a file

```
python -m dissertation_manager set introduction path/to/intro.md
```

Replaces the `sections/introduction.md` with your provided file content.

### 4) Adjust targets later (optional)

```
python -m dissertation_manager targets --targets "findings=3000"
```

### 5) Export a combined Markdown document

```
python -m dissertation_manager export --out exports/dissertation.md
```

The export includes a title page and concatenates all section files.

## Sections

The default managed sections are:

- introduction
- literature_review
- methodology
- findings
- conclusion

Each is stored under `sections/<name>.md` and initialized with a brief template.

## Notes

- This tool uses only the Python standard library (no installs required).
- You can organize references and assets however you like; this tool only manages section files and metadata.
- For more sections or customization, you can manually add Markdown files and include them during export by copying content into the canonical section files.

## Visual Progress & Lifecycles

- The web dashboard shows circular (donut) charts for overall and per-section progress (combined from words and lifecycle; default weights 70% words, 30% lifecycle).
- Each section has a Lifecycle page with default phases: Plan, Collect, Synthesize, Draft, Revise, Finalize. Set per-phase progress (0–100) and see mini donuts per phase.

### Weights (words vs lifecycle)

- Adjust under the Targets page. Default is 70% words and 30% lifecycle.
- Weights do not need to sum to 100; they are normalized by their sum.

### Simple Progress Mode (status‑only)

- To use the app purely as a task progress tracker (no word‑based effort), set:

```
fly secrets set SIMPLE_PROGRESS_MODE=1
```

- Effects:
  - Progress is based on task status only (To Do=0, Doing=50, Done=100).
  - Dashboard hides word targets and effort/combined badges.
  - Writing navigation is hidden (you can re‑enable anytime by clearing the flag).
## Django Web App (new)

Local setup
- Python 3.10+
- Install: `pip install -r requirements.txt`
- Dev/test deps: `pip install -r requirements-dev.txt`
- Env: copy `.env.example` to `.env` (or export same vars)
- Init DB: `python manage.py migrate`
- Seed templates: `python manage.py seed_templates`
- Create admin: `python manage.py createsuperuser`
- Quick bootstrap (advisor user + open URLs): `python manage.py bootstrap_local --username advisor --password changeme --open`
- Run: `python manage.py runserver`

Key URLs
- `/signup` student self‑registration
- `/login` and `/logout`
- `/dashboard` student dashboard (tasks and completion)
- `/advisor` advisor dashboard (simple list of projects)
- Advisor exports: `/advisor/export.json`, `/advisor/export.csv`
- Advisor per‑project logs CSV: `/advisor/projects/<id>/wordlogs.csv`
  - Optional query params: `start=YYYY-MM-DD`, `end=YYYY-MM-DD`, `milestone=<id>`
- `/admin/` Django admin (manage templates, tasks, etc.)
- Task detail/edit: `/tasks/<id>/` and `/tasks/<id>/edit/`
- Writing logs CSV (student): `/writing/export.csv`
  - Optional query params: `start=YYYY-MM-DD`, `end=YYYY-MM-DD`, `milestone=<id>`
 - Auth: password reset — `/password-reset/`, `/password-reset/done/`, `/reset/<uidb64>/<token>/`, `/reset/done/`
 - Auth: resend activation — `/resend-activation/`

Storage on Fly.io
- Use a Fly Volume mounted at `/data`; set `UPLOAD_ROOT=/data/uploads`.
- Collect static in CI or at release: `python manage.py collectstatic --noinput` (optional if you later add static files)

### Testing

- Install dev dependencies: `pip install -r requirements-dev.txt`
- Run tests: `pytest -q` or `make test`

### Milestone Templates (Simplified)

This app ships with a simplified, milestone‑only template set (no default tasks):

- Literature Review - General Field
- Literature Review - Special Field
- Introduction
- Methodology
- Internal Review Board Application
- Preliminary Exam
- Findings
- Conclusion
- Final Defence

You can apply these to projects via the New Project form (check “apply templates”), or from the command line (see below).

### Reset / Reseed Templates

- Reseed the simplified templates (deletes existing milestone/task templates):
  - `python manage.py reset_templates`
- Reseed and apply the core milestones to all existing projects:
  - `python manage.py reset_templates --apply_core`
- Just apply core milestones (no reseed):
  - `python manage.py apply_core`

Notes
- “Core” means milestone templates whose keys start with `core-` (the simplified set uses this).
- The simplified templates do not create any default tasks. You can add tasks per project as needed.

### Full Reset (Data)

Local (SQLite)
- Option A — flush data, keep schema:
  - `python manage.py flush --noinput`
  - `python manage.py seed_templates`
  - Create users again (e.g., `python manage.py createsuperuser` or `bootstrap_local`).
- Option B — drop DB file and re‑init:
  - Stop the server.
  - Delete `db.sqlite3` (and optionally the `uploads/` folder).
  - `python manage.py migrate`
  - `python manage.py seed_templates`
  - Recreate users.

Postgres
- Drop and recreate the database using your preferred method, then:
  - `python manage.py migrate`
  - `python manage.py seed_templates`
  - Recreate users.

Fly.io (production)
- Reseed templates only:
  - `fly ssh console -C "python manage.py reset_templates"`
- Reseed and apply to all projects:
  - `fly ssh console -C "python manage.py reset_templates --apply_core"`
- Caution: For a full data reset in production, you’ll need to drop/recreate the database used by `DATABASE_URL` and then run migrations. Only do this if you intend to wipe all data.

### Notifications & Scheduling

- Send reminders locally:

```
python manage.py notify --due-days 3 --inactivity-days 5
```

- On Fly.io, use the Makefile target (runs inside the app VM):

```
make notify DUE=3 INACTIVE=5
```

- Options:
  - `--backup-reminder` to send monthly backup emails to students (first days of month).
  - `--advisor-digest --digest-window-days 7` to email a weekly advisor digest.

Schedule it with your preferred mechanism:
- GitHub Actions: see `.github/workflows/notify.yml` (runs daily at 09:00 UTC by default)
  - Set repository secret: `FLY_API_TOKEN`
  - Set repository variable: `FLY_APP_NAME` (e.g., `dissertation-lifecycle`)
  - Optional variables: `NOTIFY_DUE_DAYS`, `NOTIFY_INACTIVE_DAYS`, `NOTIFY_DIGEST_WINDOW_DAYS`
  - You can also run it manually via the “Run workflow” UI with overrides.
- Or any external scheduler that runs: `fly ssh console -C "python manage.py notify ..."`

### Backups

- Students can download a ZIP of their data and attachments at `/export.zip` (after login).
- Advisors can download per‑project ZIPs under `/advisor/projects/<id>/export.zip`.
- Recommend scheduling monthly backup reminders via `python manage.py notify --backup-reminder`.

### Security & Environment

- In production (`DEBUG=0`), security flags are enabled: HTTPS redirect, secure cookies, HSTS, and proxy SSL header.
- Configure hosts and CSRF via env:
  - `ALLOWED_HOSTS=your.domain,other.domain`
  - `CSRF_TRUSTED_ORIGINS=https://your.domain,https://other.domain`
- On Fly.io, defaults allow `*.fly.dev`. Set `FLY_APP_NAME` to your app for ALLOWED_HOSTS default.

## Production Deploy (Fly.io)

Quick checklist
- Fly app: created and `fly.toml` present (`app` name matches).
- Volume: create a volume named `data` and mount at `/data` (uploads).
- Secrets: set production env (see below, minimal list included).
- Database: decide SQLite (single machine) or Postgres (`DATABASE_URL`).
- Deploy: `fly deploy` and let `release_command` run migrations + seed templates.
- Bootstrap: create an advisor user to log in.

Create volume
```
fly volumes create data --size 1 --region den -a dissertation-lifecycle
```

Minimal secrets (copy/paste and edit)
```
fly secrets set \
  SECRET_KEY=$(openssl rand -hex 32) \
  DEBUG=0 \
  FLY_APP_NAME=dissertation-lifecycle \
  ALLOWED_HOSTS=dissertation-lifecycle.fly.dev \
  CSRF_TRUSTED_ORIGINS=https://dissertation-lifecycle.fly.dev \
  DEFAULT_FROM_EMAIL=no-reply@example.com
```

Email (SMTP) — required for password reset/notifications
```
fly secrets set \
  EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend \
  EMAIL_HOST=smtp.example.com \
  EMAIL_PORT=587 \
  EMAIL_HOST_USER=apikey-or-user \
  EMAIL_HOST_PASSWORD=secret \
  EMAIL_USE_TLS=1
```

Optional signup controls
```
fly secrets set SIGNUP_INVITE_CODE=letmein REQUIRE_EMAIL_VERIFICATION=1 \
  SIGNUP_ALLOWED_EMAIL_DOMAINS=university.edu,dept.edu
```

Database options
- SQLite (default): fine for a single VM and light use. Data lives on the Fly volume.
- Postgres: provision a Fly Postgres cluster and set `DATABASE_URL`.

Example Postgres secret
```
fly secrets set DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/DBNAME
```

Deploy and bootstrap
```
make deploy          # or: fly deploy
make migrate         # not needed if using release_command
USERNAME=advisor PASSWORD=changeme EMAIL=advisor@example.com make advisor
fly ssh console -C "python manage.py create_samples"   # optional: admin/advisor/student + sample project/logs
```

Scheduled notifications (GitHub Actions)
- Repo secret: `FLY_API_TOKEN`
- Repo variable: `FLY_APP_NAME` (e.g., dissertation-lifecycle)
- Optional repo variables: `NOTIFY_DUE_DAYS`, `NOTIFY_INACTIVE_DAYS`, `NOTIFY_DIGEST_WINDOW_DAYS`
The workflow `.github/workflows/notify.yml` runs daily at 09:00 UTC or on demand.

### Signup Controls & Verification

- Invite code: set `SIGNUP_INVITE_CODE` to require a matching code at signup.
- Allowed email domains: set `SIGNUP_ALLOWED_EMAIL_DOMAINS=university.edu,dept.edu` to restrict signups.
- Email verification: set `REQUIRE_EMAIL_VERIFICATION=1` to require activation via emailed link.
  - Ensure email backend/secrets are configured in production (`EMAIL_*` settings).
### Uploads & Storage

- Local storage (default): uploads stored under `UPLOAD_ROOT` (defaults to `uploads/` or `/data/uploads` on Fly volume).
- Upload policy (override via env):
  - `UPLOAD_MAX_BYTES` (default `10485760` for 10 MB)
  - `UPLOAD_ALLOWED_TYPES` (comma‑separated MIME types; default includes pdf, images, doc/docx)
- S3 storage (optional): set `S3_ENABLED=1` and provide:
  - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`
  - Optional: `AWS_S3_REGION_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_SIGNATURE_VERSION`, `AWS_S3_CUSTOM_DOMAIN`, `AWS_QUERYSTRING_AUTH=1`
  - This switches `DEFAULT_FILE_STORAGE` to S3 via `django-storages`.
