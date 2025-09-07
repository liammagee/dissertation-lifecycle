# Documentation Index

Quick links to project documentation and operational guides.

- Getting Started & Deployment
  - Install, run, testing, and Fly.io deployment: see the top‑level `README.md`.

- Operations Runbook
  - Day‑to‑day admin and troubleshooting steps: `docs/ops.md`

- Roadmap
  - Feature plan and status: `docs/roadmap.md`

- Architecture Decision Records (ADR)
  - 0001 — Architecture and Platform Choices: `docs/adr/0001-architecture.md`
  - New ADRs should follow the pattern `docs/adr/NNNN-title.md`.

- Data Model
  - Draft and key entities: `docs/data-model.md`

- Notifications & Scheduling
  - GitHub Actions workflow: `.github/workflows/notify.yml`
  - App command: `python manage.py notify` (see README for options)

Notes
- If you change environment variables or add new operational tasks, update `docs/ops.md`.
- For user‑facing flows (auth, calendar, uploads), ensure README URLs remain current.
