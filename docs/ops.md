# Operations Runbook

Common maintenance and troubleshooting steps for administrators.

## Reseed Templates vs. Apply Core Only

- Reseed simplified templates (deletes and recreates milestone/task templates):
  - Local: `python manage.py reset_templates`
  - Fly: `fly ssh console -C "python manage.py reset_templates"`
- Apply core milestones to all projects (no reseed):
  - Local: `python manage.py apply_core`
  - Fly: `fly ssh console -C "python manage.py apply_core"`
- Reconcile project milestones (remove duplicates, migrate old):
  - Local: `python manage.py sync_milestones`
  - Fly: `fly ssh console -C "python manage.py sync_milestones"`

## Rotate a User’s Calendar Token

- Admin UI: go to `/admin/tracker/profile/`, select one or more profiles.
- Actions: “Rotate student calendar tokens” or “Rotate advisor calendar tokens”.
- Or users can self‑rotate at `/calendar/settings/` (invalidates old token URLs).

## Email Delivery Troubleshooting

- Verify env secrets: `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`/`EMAIL_USE_SSL`, `DEFAULT_FROM_EMAIL`.
- In DEBUG, the console email backend is used by default (emails appear in server logs).
- In production, check app logs: `fly logs` or the hosting provider’s logging.
- For password reset issues: confirm the reset email contains a valid `/reset/<uidb64>/<token>/` link and that your external URL/host matches CSRF/host settings.

## Slack/Teams Webhook Troubleshooting

- Verify `SLACK_WEBHOOK_URL` and/or `TEAMS_WEBHOOK_URL` are set.
- Limit payload size with `WEBHOOK_MAX_LINES` (default 80) if messages get truncated.
- Trigger manually:
  - `fly ssh console -C "python manage.py notify --advisor-digest --digest-window-days 7"`
  - `fly ssh console -C "python manage.py notify --due-days 3 --inactivity-days 5"`
- Check app logs for any webhook errors; posting is best‑effort and will not fail the job.

## Backups

- Students can self‑export at `/export.zip`.
- Advisors can export per‑project ZIP at `/advisor/projects/<id>/export.zip`.
- Recommend monthly reminders via `python manage.py notify --backup-reminder` (see Notifications & Scheduling in the README).

## Database and Schema Upgrades

- Local/dev: `python manage.py migrate` after pulling updates.
- Fly: `fly deploy` will run the release command to migrate.
- Postgres: ensure `DATABASE_URL` is set correctly and the app has network access to the DB.

## Security & Hosts

- Ensure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` include your production domain(s).
- On Fly, `FLY_APP_NAME` is used to allow `*.fly.dev` by default.

## Scheduling Notifications

- GitHub Actions workflow `.github/workflows/notify.yml` runs daily at 09:00 UTC; set `FLY_API_TOKEN` secret and `FLY_APP_NAME` variable.
- Or run from any external scheduler via `fly ssh console -C "python manage.py notify ..."`.

