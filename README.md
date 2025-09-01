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
## Django Web App (new)

Local setup
- Python 3.10+
- Install: `pip install -r requirements.txt`
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

Storage on Fly.io
- Use a Fly Volume mounted at `/data`; set `UPLOAD_ROOT=/data/uploads`.
- Collect static in CI or at release: `python manage.py collectstatic --noinput` (optional if you later add static files)

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

Schedule it with your preferred mechanism (e.g., a GitHub Actions workflow calling `fly ssh console -C "python manage.py notify ..."` on a cron, or an external scheduler hitting it via SSH).

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
