#!/usr/bin/env bash
set -euo pipefail

# Set Fly.io secrets for production with Postgres + SMTP
# Usage:
#   EMAIL_HOST=smtp.example.com \
#   EMAIL_HOST_USER=your_user \
#   EMAIL_HOST_PASSWORD=your_password \
#   DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/DBNAME \
#   FLY_APP_NAME=dissertation-lifecycle \
#   ./scripts/fly-secrets-postgres.sh
#
# Notes:
# - SECRET_KEY is generated if not provided.
# - ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS default to <FLY_APP_NAME>.fly.dev
# - If your app name is set in fly.toml, you can omit FLY_APP_NAME.

SECRET_KEY_VAL="${SECRET_KEY:-$(openssl rand -hex 32)}"
APP_NAME="${FLY_APP_NAME:-dissertation-lifecycle}"
ALLOWED_HOSTS_VAL="${ALLOWED_HOSTS:-${APP_NAME}.fly.dev}"
CSRF_ORIGINS_VAL="${CSRF_TRUSTED_ORIGINS:-https://${APP_NAME}.fly.dev}"

: "${EMAIL_HOST:?set EMAIL_HOST}"
: "${EMAIL_HOST_USER:?set EMAIL_HOST_USER}"
: "${EMAIL_HOST_PASSWORD:?set EMAIL_HOST_PASSWORD}"
: "${DATABASE_URL:?set DATABASE_URL}"

fly secrets set \
  SECRET_KEY="${SECRET_KEY_VAL}" \
  DEBUG="0" \
  FLY_APP_NAME="${APP_NAME}" \
  ALLOWED_HOSTS="${ALLOWED_HOSTS_VAL}" \
  CSRF_TRUSTED_ORIGINS="${CSRF_ORIGINS_VAL}" \
  DEFAULT_FROM_EMAIL="${DEFAULT_FROM_EMAIL:-no-reply@example.com}" \
  EMAIL_BACKEND="${EMAIL_BACKEND:-django.core.mail.backends.smtp.EmailBackend}" \
  EMAIL_HOST="${EMAIL_HOST}" \
  EMAIL_PORT="${EMAIL_PORT:-587}" \
  EMAIL_HOST_USER="${EMAIL_HOST_USER}" \
  EMAIL_HOST_PASSWORD="${EMAIL_HOST_PASSWORD}" \
  EMAIL_USE_TLS="${EMAIL_USE_TLS:-1}" \
  DATABASE_URL="${DATABASE_URL}"

echo "Secrets set for app ${APP_NAME}."

# Optional signup controls
# Export these before running to enable:
#   SIGNUP_INVITE_CODE=letmein
#   SIGNUP_ALLOWED_EMAIL_DOMAINS="university.edu,dept.edu"
#   REQUIRE_EMAIL_VERIFICATION=1
if [[ -n "${SIGNUP_INVITE_CODE:-}" ]]; then
  fly secrets set SIGNUP_INVITE_CODE="${SIGNUP_INVITE_CODE}"
  echo "Applied SIGNUP_INVITE_CODE."
fi
if [[ -n "${SIGNUP_ALLOWED_EMAIL_DOMAINS:-}" ]]; then
  fly secrets set SIGNUP_ALLOWED_EMAIL_DOMAINS="${SIGNUP_ALLOWED_EMAIL_DOMAINS}"
  echo "Applied SIGNUP_ALLOWED_EMAIL_DOMAINS."
fi
if [[ -n "${REQUIRE_EMAIL_VERIFICATION:-}" ]]; then
  fly secrets set REQUIRE_EMAIL_VERIFICATION="${REQUIRE_EMAIL_VERIFICATION}"
  echo "Applied REQUIRE_EMAIL_VERIFICATION=${REQUIRE_EMAIL_VERIFICATION}."
fi
