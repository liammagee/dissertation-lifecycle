from __future__ import annotations

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction

from tracker.models import MilestoneTemplate, TaskTemplate


class Command(BaseCommand):
    help = (
        "Delete all Milestone/Task templates and reseed from seed_templates. "
        "Use --only-core to keep only the five core milestones. Use --exclude-phd to drop ERP/PhD templates."
    )

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument(
            "--only-core",
            action="store_true",
            help="After reseed, remove all templates except those with keys starting with 'core-'.",
        )
        parser.add_argument(
            "--exclude-phd",
            action="store_true",
            help="After reseed, remove templates marked is_phd_only.",
        )
        parser.add_argument(
            "--apply-core",
            action="store_true",
            help="After reseed, apply missing core milestones to all existing projects.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):  # type: ignore[override]
        self.stdout.write("Deleting existing task templates…")
        TaskTemplate.objects.all().delete()
        self.stdout.write("Deleting existing milestone templates…")
        MilestoneTemplate.objects.all().delete()

        self.stdout.write("Seeding fresh templates…")
        call_command("seed_templates")

        if opts.get("only_core"):
            removed = MilestoneTemplate.objects.exclude(key__startswith="core-").count()
            MilestoneTemplate.objects.exclude(key__startswith="core-").delete()
            self.stdout.write(self.style.WARNING(f"Removed non-core templates: {removed}"))

        if opts.get("exclude_phd"):
            removed = MilestoneTemplate.objects.filter(is_phd_only=True).count()
            MilestoneTemplate.objects.filter(is_phd_only=True).delete()
            self.stdout.write(self.style.WARNING(f"Removed PhD-only templates: {removed}"))

        # Clean up any TaskTemplates that may be orphaned by the above filters
        TaskTemplate.objects.filter(milestone__isnull=True).delete()

        self.stdout.write(self.style.SUCCESS("Template reset complete."))

        if opts.get("apply_core"):
            self.stdout.write("Applying core milestones to existing projects…")
            call_command("apply_core")
            self.stdout.write(self.style.SUCCESS("Applied core milestones."))

