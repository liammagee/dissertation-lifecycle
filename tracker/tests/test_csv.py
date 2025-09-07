from __future__ import annotations

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tracker.models import Project, Milestone, Task, WordLog, Profile


class CsvExportTests(TestCase):
    def setUp(self) -> None:
        # Student + project
        self.student = User.objects.create_user(username="bob", password="pass", email="bob@example.com")
        self.project = Project.objects.create(student=self.student, title="Project Bob")
        self.m = Milestone.objects.create(project=self.project, name="Intro", order=1)
        self.t = Task.objects.create(project=self.project, milestone=self.m, title="Write", order=1)
        WordLog.objects.create(project=self.project, task=self.t, date=date.today(), words=123)

    def test_student_wordlogs_csv(self):
        self.client.login(username="bob", password="pass")
        url = reverse("wordlogs_csv")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertIn("date,words,note,task_id,task,milestone", body.splitlines()[0])
        self.assertIn("123", body)

    def test_advisor_project_wordlogs_csv(self):
        advisor = User.objects.create_user(username="adv", password="pass", email="adv@example.com")
        Profile.objects.update_or_create(user=advisor, defaults={"role": "advisor"})
        self.client.login(username="adv", password="pass")
        url = reverse("advisor_project_wordlogs_csv", args=[self.project.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertIn("date,words,note,task_id,task,milestone", body.splitlines()[0])
        self.assertIn("123", body)
