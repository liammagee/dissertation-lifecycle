#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Applying migrations..."
python manage.py migrate --noinput
echo "[entrypoint] Seeding templates (idempotent)..."
python manage.py seed_templates --verbosity 0 || true

echo "[entrypoint] Starting gunicorn..."
exec gunicorn dissertation_lifecycle.wsgi:application \
  --workers 1 --threads 2 --timeout 60 \
  --access-logfile - --log-level debug \
  --bind 0.0.0.0:${PORT:-8000}

