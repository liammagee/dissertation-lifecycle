from __future__ import annotations

from django.core.management.base import BaseCommand

from tracker.models import Project, MilestoneTemplate, TaskTemplate, Milestone, Task


class Command(BaseCommand):
    help = "Apply missing core milestones (Introduction, Literature Review, Methodology, Findings, Conclusion) to all projects"

    def handle(self, *args, **options):
        core_templates = list(MilestoneTemplate.objects.filter(key__startswith='core-').order_by('order', 'id'))
        if not core_templates:
            self.stdout.write(self.style.WARNING('No core-* milestone templates found. Run seed_templates first.'))
            return
        applied = 0
        for project in Project.objects.all():
            existing = {m.template_id for m in project.milestones.select_related('template') if m.template_id}
            order = project.milestones.count() + 1
            for mt in core_templates:
                if mt.id in existing:
                    continue
                milestone = Milestone.objects.create(project=project, template=mt, name=mt.name, order=order)
                order += 1
                t_order = 1
                for tt in TaskTemplate.objects.filter(milestone=mt).order_by('order', 'id'):
                    target = 0
                    title_lower = (tt.title or '').lower()
                    if mt.key == 'core-literature-review' and 'draft literature review' in title_lower:
                        target = 5500
                    Task.objects.create(
                        project=project,
                        milestone=milestone,
                        template=tt,
                        title=tt.title,
                        description=tt.description,
                        order=t_order,
                        word_target=target,
                    )
                    t_order += 1
                applied += 1
        self.stdout.write(self.style.SUCCESS(f'Applied core milestones to {applied} project(s).'))

