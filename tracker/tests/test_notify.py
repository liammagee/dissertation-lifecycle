from __future__ import annotations

from datetime import date

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings

from tracker.models import Project, Milestone, Task


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class NotifyCommandTests(TestCase):
    def setUp(self) -> None:
        self.student = User.objects.create_user(username='charlie', password='pass', email='charlie@example.com')
        self.project = Project.objects.create(student=self.student, title='Notify Test')
        m = Milestone.objects.create(project=self.project, name='Intro', order=1)
        Task.objects.create(project=self.project, milestone=m, title='Due Soon', status='todo', order=1, due_date=date.today())

    def test_notify_due_soon_sends_email(self):
        call_command('notify', '--due-days', '3', '--inactivity-days', '5')
        # At least one email should be queued (due-soon notification)
        self.assertGreaterEqual(len(mail.outbox), 1)

