from __future__ import annotations

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from tracker.models import Profile, Project, Task, WordLog
from tracker.services import apply_templates_to_project


class Command(BaseCommand):
    help = "Create sample admin, advisor, and student with a demo project and logs"

    def add_arguments(self, parser):
        parser.add_argument('--admin-username', default='admin')
        parser.add_argument('--admin-password', default='adminpass')
        parser.add_argument('--admin-email', default='admin@example.com')
        parser.add_argument('--advisor-username', default='advisor')
        parser.add_argument('--advisor-password', default='changeme')
        parser.add_argument('--advisor-email', default='advisor@example.com')
        parser.add_argument('--student-username', default='student')
        parser.add_argument('--student-password', default='changeme')
        parser.add_argument('--student-email', default='student@example.com')
        parser.add_argument('--title', default='Sample Dissertation')
        parser.add_argument('--include-detailed', action='store_true', help='Include detailed scaffolding templates')
        parser.add_argument('--include-phd', action='store_true', help='Include ERP PhD tasks')

    @transaction.atomic
    def handle(self, *args, **opts):
        User = get_user_model()

        # Admin
        admin_u = opts['admin_username']
        admin_e = opts['admin_email']
        admin_p = opts['admin_password']
        admin, created = User.objects.get_or_create(
            username=admin_u,
            defaults={'email': admin_e, 'is_staff': True, 'is_superuser': True},
        )
        if created:
            admin.set_password(admin_p)
            admin.save()
            self.stdout.write(self.style.SUCCESS(f"Created admin {admin_u}"))
        else:
            # Ensure permissions if user pre-exists
            changed = False
            if not admin.is_staff:
                admin.is_staff = True; changed = True
            if not admin.is_superuser:
                admin.is_superuser = True; changed = True
            if changed:
                admin.save(update_fields=['is_staff', 'is_superuser'])
            self.stdout.write(f"Admin {admin_u} already exists")

        # Advisor
        advisor_u = opts['advisor_username']
        advisor_e = opts['advisor_email']
        advisor_p = opts['advisor_password']
        advisor, adv_created = User.objects.get_or_create(
            username=advisor_u, defaults={'email': advisor_e}
        )
        if adv_created:
            advisor.set_password(advisor_p)
            advisor.save()
        Profile.objects.get_or_create(user=advisor, defaults={'role': 'advisor'})
        self.stdout.write(self.style.SUCCESS(f"Advisor ready: {advisor_u}/{advisor_p}"))

        # Student + project
        student_u = opts['student_username']
        student_e = opts['student_email']
        student_p = opts['student_password']
        student, stu_created = User.objects.get_or_create(
            username=student_u, defaults={'email': student_e}
        )
        if stu_created:
            student.set_password(student_p)
            student.save()
        Profile.objects.get_or_create(user=student, defaults={'role': 'student'})

        project, proj_created = Project.objects.get_or_create(
            student=student,
            title=opts['title'],
            defaults={'status': 'active'},
        )
        if proj_created:
            self.stdout.write(self.style.SUCCESS(f"Created project '{project.title}'"))
        else:
            self.stdout.write(f"Project exists: '{project.title}'")

        # Apply templates if project has no milestones
        if project.milestones.count() == 0:
            apply_templates_to_project(
                project,
                include_phd=bool(opts.get('include_phd')),
                include_detailed=bool(opts.get('include_detailed')),
            )
            self.stdout.write("Applied milestone/task templates")

        # Pick a few common tasks to set targets and logs
        draft_lr = (
            project.tasks.filter(title__icontains='draft literature review').first()
            or project.tasks.filter(title__icontains='literature').first()
        )
        draft_meth = project.tasks.filter(title__icontains='draft methodology').first()
        intro = project.tasks.filter(title__icontains='introduction').first()

        # Ensure some targets exist for effort
        for t, default_target in ((draft_lr, 3000), (draft_meth, 1500), (intro, 800)):
            if t and (t.word_target or 0) <= 0:
                t.word_target = default_target
                t.save(update_fields=['word_target'])

        # Create a few logs across last 3 days for variety
        today = date.today()
        created_logs = 0
        for idx, pair in enumerate([(draft_lr, 600), (draft_meth, 400), (intro, 250)]):
            task_obj, words = pair
            if not task_obj:
                continue
            for d_offset in (0, 1):
                wl_date = today - timedelta(days=idx + d_offset)
                WordLog.objects.get_or_create(
                    project=project,
                    task=task_obj,
                    date=wl_date,
                    defaults={'words': words, 'note': f'Sample log ({task_obj.title})'},
                )
                created_logs += 1

        self.stdout.write(self.style.SUCCESS(
            f"Samples ready. Admin: {admin_u}/{admin_p}; Advisor: {advisor_u}/{advisor_p}; Student: {student_u}/{student_p}. Created/ensured {created_logs} writing logs."
        ))

