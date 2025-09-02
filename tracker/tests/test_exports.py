from __future__ import annotations

import csv
import io

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tracker.models import Project, Milestone, Task, Profile


class AdvisorExportsTests(TestCase):
    def setUp(self) -> None:
        # Student + project + task
        self.student = User.objects.create_user(username="sue", password="pass", email="sue@example.com")
        self.project = Project.objects.create(student=self.student, title="Sues Thesis")
        m = Milestone.objects.create(project=self.project, name="Intro", order=1)
        Task.objects.create(project=self.project, milestone=m, title="Draft", status="doing", order=1)
        # Advisor
        self.advisor = User.objects.create_user(username="advisor", password="pass", email="advisor@example.com")
        Profile.objects.create(user=self.advisor, role="advisor")
        self.client.login(username="advisor", password="pass")

    def test_advisor_export_json(self):
        url = reverse("advisor_export_json")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/json")
        self.assertIn("Sues Thesis", r.content.decode("utf-8"))

    def test_advisor_export_csv(self):
        url = reverse("advisor_export_csv")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        # Parse minimal CSV to ensure header present
        reader = csv.reader(io.StringIO(r.content.decode("utf-8")))
        header = next(reader)
        self.assertIn("project_id", header)
        rows = list(reader)
        self.assertTrue(any(str(self.project.id) in row for row in rows))

