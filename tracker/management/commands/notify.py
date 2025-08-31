from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from tracker.models import Project, WordLog, Task
from tracker.services import task_combined_percent


class Command(BaseCommand):
    help = "Send email notifications: due-soon tasks and inactivity nudges."

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument("--due-days", type=int, default=3, help="Days ahead to warn for due dates (default 3)")
        parser.add_argument("--inactivity-days", type=int, default=5, help="Days without logs to nudge (default 5)")
        parser.add_argument("--from-email", default=None, help="Override FROM email (default settings.DEFAULT_FROM_EMAIL)")

    def handle(self, *args, **opts):  # type: ignore[override]
        due_days = max(0, int(opts["due_days"]))
        inactivity_days = max(1, int(opts["inactivity_days"]))
        from_email = opts.get("from_email") or getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")

        self._notify_due_soon(due_days, from_email)
        self._notify_inactivity(inactivity_days, from_email)

    def _notify_due_soon(self, due_days: int, from_email: str) -> None:
        today = date.today()
        latest = today + timedelta(days=due_days)
        # Group tasks by student
        qs = Task.objects.select_related("project", "project__student").filter(
            status__in=["todo", "doing"],
            due_date__gte=today,
            due_date__lte=latest,
            project__status="active",
        ).order_by("project__student__username", "due_date")

        grouped: dict[int, list[Task]] = {}
        for t in qs:
            if not t.project or not t.project.student:
                continue
            grouped.setdefault(t.project.student_id, []).append(t)

        sent = 0
        for student_id, tasks in grouped.items():
            user = tasks[0].project.student
            if not user.email:
                continue
            lines = [
                f"Hi {user.get_username()},",
                "",
                f"You have {len(tasks)} task(s) due within {due_days} day(s):",
                "",
            ]
            for t in tasks:
                pct = task_combined_percent(t)
                lines.append(f"- {t.title} (due {t.due_date}, progress {pct}%)")
            lines.append("\nVisit your dashboard to review and update: /dashboard\n")
            send_mail(
                subject="Dissertation: upcoming task deadlines",
                message="\n".join(lines),
                from_email=from_email,
                recipient_list=[user.email],
                fail_silently=True,
            )
            sent += 1
        if sent:
            self.stdout.write(self.style.SUCCESS(f"Sent due-soon emails to {sent} student(s)."))

    def _notify_inactivity(self, inactivity_days: int, from_email: str) -> None:
        today = date.today()
        cutoff = today - timedelta(days=inactivity_days)
        sent = 0
        for project in Project.objects.select_related("student").filter(status="active"):
            user = project.student
            if not user or not user.email:
                continue
            last_log = (
                WordLog.objects.filter(project=project).order_by("-date").values_list("date", flat=True).first()
            )
            if last_log is None or last_log < cutoff:
                days = (today - (last_log or date(1970, 1, 1))).days
                msg = (
                    f"Hi {user.get_username()},\n\n"
                    f"It looks like you haven't logged writing activity in {days} day(s).\n"
                    "A little progress every day helps a lot — open your Writing page and add an entry.\n\n"
                    "/writing\n"
                )
                send_mail(
                    subject="Dissertation: keep your writing streak going",
                    message=msg,
                    from_email=from_email,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
                sent += 1
        if sent:
            self.stdout.write(self.style.SUCCESS(f"Sent inactivity nudges to {sent} student(s)."))

