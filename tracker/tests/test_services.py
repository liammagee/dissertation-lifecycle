from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from tracker.models import Project, Milestone, Task, WordLog
from tracker.services import compute_streaks, task_combined_percent


class ServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="alice", password="pass")
        self.project = Project.objects.create(student=self.user, title="Thesis")
        self.milestone = Milestone.objects.create(project=self.project, name="Intro", order=1)

    def test_compute_streaks_empty(self):
        self.assertEqual(compute_streaks(self.project), (0, 0))

    def test_compute_streaks_current_and_longest(self):
        # Create logs for today and yesterday => current streak 2
        WordLog.objects.create(project=self.project, date=date.today() - timedelta(days=1), words=100)
        WordLog.objects.create(project=self.project, date=date.today(), words=150)
        current, longest = compute_streaks(self.project)
        self.assertEqual(current, 2)
        self.assertGreaterEqual(longest, 2)

    def test_task_combined_percent(self):
        task = Task.objects.create(
            project=self.project,
            milestone=self.milestone,
            title="Draft intro",
            status="doing",
            word_target=100,
            order=1,
        )
        WordLog.objects.create(project=self.project, task=task, date=date.today(), words=50)
        # Status=doing -> 50, Effort=50/100 -> 50; weights equal -> 50
        pct = task_combined_percent(task, {"status": 50, "effort": 50})
        self.assertEqual(pct, 50)

