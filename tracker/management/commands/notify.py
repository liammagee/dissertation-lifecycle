from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from tracker.models import Project, WordLog, Task, Profile
from tracker.services import task_combined_percent


class Command(BaseCommand):
    help = "Send email notifications: due-soon tasks and inactivity nudges."

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument("--due-days", type=int, default=3, help="Days ahead to warn for due dates (default 3)")
        parser.add_argument("--inactivity-days", type=int, default=5, help="Days without logs to nudge (default 5)")
        parser.add_argument("--from-email", default=None, help="Override FROM email (default settings.DEFAULT_FROM_EMAIL)")
        parser.add_argument("--backup-reminder", action="store_true", help="Send monthly backup/export reminders to students")
        parser.add_argument("--advisor-digest", action="store_true", help="Send weekly advisor digest of student progress")
        parser.add_argument("--digest-window-days", type=int, default=7, help="Window for advisor digest activity and due tasks (default 7)")

    def handle(self, *args, **opts):  # type: ignore[override]
        due_days = max(0, int(opts["due_days"]))
        inactivity_days = max(1, int(opts["inactivity_days"]))
        from_email = opts.get("from_email") or getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")

        self._notify_due_soon(due_days, from_email)
        self._notify_inactivity(inactivity_days, from_email)

        if opts.get("backup_reminder"):
            self._backup_reminder(from_email)
        if opts.get("advisor_digest"):
            self._advisor_digest(from_email, int(opts.get("digest_window_days", 7)))

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

    def _backup_reminder(self, from_email: str) -> None:
        today = date.today()
        # Heuristic: only run meaningfully on first 3 days of month to avoid mistakes
        if today.day > 3:
            self.stdout.write(self.style.WARNING("Skipping backup reminders (not first days of month)."))
        sent = 0
        for project in Project.objects.select_related("student").filter(status="active"):
            user = project.student
            if not user or not user.email:
                continue
            msg = (
                f"Hi {user.get_username()},\n\n"
                "Monthly backup reminder — export your data and attachments for safekeeping.\n\n"
                "Download your ZIP backup here (after login): /export.zip\n\n"
                "Tip: keep copies of key documents in your cloud drive as well.\n"
            )
            send_mail(
                subject="Dissertation: monthly backup reminder",
                message=msg,
                from_email=from_email,
                recipient_list=[user.email],
                fail_silently=True,
            )
            sent += 1
        if sent:
            self.stdout.write(self.style.SUCCESS(f"Sent backup reminders to {sent} student(s)."))

    def _advisor_digest(self, from_email: str, window_days: int) -> None:
        from django.db.models import Sum
        today = date.today()
        start = today - timedelta(days=max(1, window_days))
        # Collect advisor/admin recipients
        recipients = list(
            Profile.objects.filter(role__in=["advisor", "admin"], user__email__isnull=False)
            .exclude(user__email="")
            .values_list("user__email", flat=True)
        )
        if not recipients:
            self.stdout.write(self.style.WARNING("No advisors/admins with email for digest."))
            return
        lines = [
            f"Advisor weekly digest ({start} to {today})",
            "",
        ]
        projects = Project.objects.select_related("student").filter(status="active").all()
        for p in projects:
            tasks = list(p.tasks.select_related("milestone").all())
            total = len(tasks)
            done = sum(1 for t in tasks if t.status == "done")
            combined = int(round(sum(task_combined_percent(t) for t in tasks) / total)) if total else 0
            # Due soon inside window
            due_soon = [
                t for t in tasks
                if t.status in ("todo", "doing") and t.due_date and start <= t.due_date <= today + timedelta(days=window_days)
            ]
            # Inactivity days
            last_log = (
                WordLog.objects.filter(project=p).order_by("-date").values_list("date", flat=True).first()
            )
            inactivity = (today - (last_log or date(1970, 1, 1))).days
            # Word count in window
            words_window = int(
                WordLog.objects.filter(project=p, date__gte=start, date__lte=today).aggregate(total=Sum("words"))["total"]
                or 0
            )
            lines.append(
                f"- {p.student.get_username()} — {p.title}: {done}/{total} done, combined {combined}%"
            )
            lines.append(
                f"  Activity: {words_window} words in last {window_days}d; inactivity {inactivity}d"
            )
            if due_soon:
                for t in sorted(due_soon, key=lambda x: (x.due_date, x.milestone.order, x.order))[:5]:
                    lines.append(f"  • Due {t.due_date}: {t.title} ({t.milestone.name})")
            lines.append("")
        send_mail(
            subject="Dissertation: advisor weekly digest",
            message="\n".join(lines),
            from_email=from_email,
            recipient_list=recipients,
            fail_silently=True,
        )
        self.stdout.write(self.style.SUCCESS(f"Sent advisor digest to {len(recipients)} recipient(s)."))
