# Documentation Index

Quick links to project documentation and operational guides.

- Getting Started & Deployment
  - Install, run, testing, and Fly.io deployment: see the top‑level `README.md`.

<div class="hero">
  <img class="logo" src="assets/logo.svg" alt="Dissertation Lifecycle" />
  <h1>Dissertation Lifecycle</h1>
  <p class="tagline">Track milestones, writing progress, documents and advisor feedback.</p>
  <div class="buttons">
    <a class="md-button md-button--primary" href="ops.md">Operations Runbook</a>
    <a class="md-button" href="roadmap.md">Roadmap</a>
    <a class="md-button" href="adr/0001-architecture.md">Architecture</a>
  </div>
</div>

## About This Project

This project’s full README (overview, quickstart, and deployment) lives in the repository root:

- GitHub: https://github.com/your-org/dissertation-lifecycle

We mirror key operational docs here, and keep the main README as the concise starting point for developers.

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
