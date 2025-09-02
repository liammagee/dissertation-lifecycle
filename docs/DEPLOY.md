# Deploying to Fly.io

This document consolidates the exact steps to deploy the Django web app to Fly.io with persistent storage and email notifications.

## Prerequisites
- flyctl installed and logged in
- A Fly app created (or create on first deploy)

## 1) Create a volume
Uploads are stored under `/data/uploads` (configured via `fly.toml`). Create a volume named `data`:

```
fly volumes create data --size 1 --region den -a dissertation-lifecycle
```

Adjust size/region/app as needed.

## 2) Set production secrets
Minimal set (edit values):

```
fly secrets set \
  SECRET_KEY=$(openssl rand -hex 32) \
  DEBUG=0 \
  FLY_APP_NAME=dissertation-lifecycle \
  ALLOWED_HOSTS=dissertation-lifecycle.fly.dev \
  CSRF_TRUSTED_ORIGINS=https://dissertation-lifecycle.fly.dev \
  DEFAULT_FROM_EMAIL=no-reply@example.com
```

SMTP for email:

```
fly secrets set \
  EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend \
  EMAIL_HOST=smtp.example.com \
  EMAIL_PORT=587 \
  EMAIL_HOST_USER=apikey-or-user \
  EMAIL_HOST_PASSWORD=secret \
  EMAIL_USE_TLS=1
```

Signup controls (optional):

```
fly secrets set SIGNUP_INVITE_CODE=letmein REQUIRE_EMAIL_VERIFICATION=1 \
  SIGNUP_ALLOWED_EMAIL_DOMAINS=university.edu,dept.edu
```

## 3) Database
- SQLite (default): good for single‑VM setups; data persists on the Fly volume.
- Postgres: provision a Fly Postgres cluster and set `DATABASE_URL`.

```
fly secrets set DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/DBNAME
```

## 4) Deploy

`fly.toml` config uses a `release_command` to run `migrate` and idempotently seed templates on each deploy.

```
fly deploy
```

## 5) Bootstrap users

Create an advisor user to access the advisor dashboard.

```
USERNAME=advisor PASSWORD=changeme EMAIL=advisor@example.com \
  fly ssh console -C "python manage.py bootstrap_local --username '$USERNAME' --password '$PASSWORD' --email '$EMAIL'"
```

Or use the Makefile helper:

```
USERNAME=advisor PASSWORD=changeme EMAIL=advisor@example.com make advisor
```

## 6) Notifications via GitHub Actions
Configure the repo:
- Secret: `FLY_API_TOKEN`
- Variable: `FLY_APP_NAME` (e.g., `dissertation-lifecycle`)
- Optional variables: `NOTIFY_DUE_DAYS`, `NOTIFY_INACTIVE_DAYS`, `NOTIFY_DIGEST_WINDOW_DAYS`

The workflow `.github/workflows/notify.yml` runs daily at 09:00 UTC and can be triggered manually.

## 7) Verify
- Open the app URL shown after deploy (e.g., `https://dissertation-lifecycle.fly.dev`).
- Check `/healthz` returns `ok`.
- Login, create project, upload test file, and export ZIP.

