from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from tracker.models import Project, Milestone, Task
from django.db import models
from tracker.models import MilestoneTemplate


class Command(BaseCommand):
    help = (
        "Reconcile project milestones with current templates: \n"
        "- Merge duplicate milestones with the same name (keep the one tied to a current template).\n"
        "- Migrate old 'Literature Review' to 'Literature Review - General Field'.\n"
        "- Reassign tasks to the kept milestone and delete duplicates.\n"
        "Safe to run multiple times."
    )

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument("--dry-run", action="store_true", help="Print actions without applying changes")

    @transaction.atomic
    def handle(self, *args, **opts):  # type: ignore[override]
        dry = bool(opts.get("dry_run"))
        current_keys = set(MilestoneTemplate.objects.values_list("key", flat=True))
        # Preferred keeper name set to dedupe
        canonical_names = [
            "Literature Review - General Field",
            "Literature Review - Special Field",
            "Introduction",
            "Methodology",
            "Internal Review Board Application",
            "Preliminary Exam",
            "Findings",
            "Conclusion",
            "Final Defence",
        ]
        # Template helpers
        tmpl_by_name = {mt.name: mt for mt in MilestoneTemplate.objects.all()}
        general_mt = tmpl_by_name.get("Literature Review - General Field")

        projects = list(Project.objects.all())
        total_moves = total_deleted = 0
        for p in projects:
            # 1) Migrate old single LR -> General Field
            old_lr = list(Milestone.objects.filter(project=p, name="Literature Review").order_by("order", "id"))
            if old_lr and general_mt:
                # Ensure target milestone exists
                target = Milestone.objects.filter(project=p, template=general_mt).first()
                if not target:
                    order = (p.milestones.aggregate(_max_order=models.Max("order")).get("_max_order") or 0) + 1  # type: ignore[name-defined]
                    target = Milestone(project=p, template=general_mt, name=general_mt.name, order=order)
                    if not dry:
                        target.save()
                # Move tasks
                for m in old_lr:
                    tasks = list(Task.objects.filter(project=p, milestone=m))
                    if tasks:
                        self.stdout.write(f"[{p.id}] Move {len(tasks)} task(s): '{m.name}' -> '{target.name}'")
                    total_moves += len(tasks)
                    if not dry:
                        Task.objects.filter(pk__in=[t.pk for t in tasks]).update(milestone=target)
                    # Delete old milestone
                    self.stdout.write(f"[{p.id}] Delete old milestone '{m.name}' (id={m.id})")
                    total_deleted += 1
                    if not dry:
                        m.delete()

            # 2) Merge duplicates by exact name
            by_name: dict[str, list[Milestone]] = {}
            for m in Milestone.objects.filter(project=p).order_by("order", "id"):
                by_name.setdefault(m.name, []).append(m)
            for name, items in by_name.items():
                if len(items) <= 1:
                    continue
                # Prefer a milestone tied to a current template; fallback to first
                keeper = None
                for m in items:
                    if m.template and m.template.key in current_keys:
                        keeper = m
                        break
                if keeper is None:
                    keeper = items[0]
                for m in items:
                    if m.id == keeper.id:
                        continue
                    tasks = list(Task.objects.filter(project=p, milestone=m))
                    if tasks:
                        self.stdout.write(f"[{p.id}] Merge {len(tasks)} task(s): '{name}' -> keeper id={keeper.id}")
                    total_moves += len(tasks)
                    if not dry:
                        Task.objects.filter(pk__in=[t.pk for t in tasks]).update(milestone=keeper)
                    self.stdout.write(f"[{p.id}] Delete duplicate milestone '{name}' (id={m.id})")
                    total_deleted += 1
                    if not dry:
                        m.delete()

            # 3) Renumber orders compactly
            if not dry:
                ordered = list(Milestone.objects.filter(project=p).order_by("order", "id"))
                for idx, m in enumerate(ordered, start=1):
                    if m.order != idx:
                        Milestone.objects.filter(pk=m.pk).update(order=idx)

        self.stdout.write(self.style.SUCCESS(
            f"Sync complete. Tasks moved: {total_moves}; milestones deleted: {total_deleted}."
        ))
