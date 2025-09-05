from __future__ import annotations

from django.core.management.base import BaseCommand

from tracker.models import MilestoneTemplate, TaskTemplate


MILESTONES = [
    {"key": "core-literature-review-general", "name": "Literature Review - General Field", "is_phd_only": False, "tasks": []},
    {"key": "core-literature-review-special", "name": "Literature Review - Special Field", "is_phd_only": False, "tasks": []},
    {"key": "core-introduction", "name": "Introduction", "is_phd_only": False, "tasks": []},
    {"key": "core-methodology", "name": "Methodology", "is_phd_only": False, "tasks": []},
    {"key": "core-irb-application", "name": "Internal Review Board Application", "is_phd_only": False, "tasks": []},
    {"key": "core-preliminary-exam", "name": "Preliminary Exam", "is_phd_only": False, "tasks": []},
    {"key": "core-findings", "name": "Findings", "is_phd_only": False, "tasks": []},
    {"key": "core-conclusion", "name": "Conclusion", "is_phd_only": False, "tasks": []},
    {"key": "core-final-defence", "name": "Final Defence", "is_phd_only": False, "tasks": []},
]


class Command(BaseCommand):
    help = "Seed milestone and task templates from the dissertation outline"

    def handle(self, *args, **options):
        created_ms = 0
        created_tasks = 0
        order = 1
        for m in MILESTONES:
            mt, ms_created = MilestoneTemplate.objects.get_or_create(
                key=m["key"],
                defaults={
                    "name": m["name"],
                    "description": "",
                    "order": order,
                    "is_phd_only": m["is_phd_only"],
                },
            )
            if not ms_created:
                # Update name/flags/order to latest
                mt.name = m["name"]
                mt.is_phd_only = m["is_phd_only"]
                mt.order = order
                mt.save()
            else:
                created_ms += 1
            order += 1

            # Clear existing tasks for this milestone and do not create any by default
            TaskTemplate.objects.filter(milestone=mt).delete()

        self.stdout.write(self.style.SUCCESS(
            f"Seeded milestones (new: {created_ms}) and tasks (total: {created_tasks})."
        ))
