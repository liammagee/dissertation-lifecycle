from __future__ import annotations

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tracker.models import Project, Milestone, Task, Profile


class CalendarIcsTokenTests(TestCase):
    def setUp(self) -> None:
        # Student + project + task with due date
        self.student = User.objects.create_user(username="sue", password="pass", email="sue@example.com")
        self.project = Project.objects.create(student=self.student, title="Sues Thesis")
        m = Milestone.objects.create(project=self.project, name="Intro", order=1)
        Task.objects.create(project=self.project, milestone=m, title="Draft", status="doing", order=1, due_date=date.today())
        # Ensure tokens
        prof, _ = Profile.objects.update_or_create(user=self.student, defaults={"role": "student"})
        self.student_token = prof.ensure_student_token()
        # Advisor
        self.advisor = User.objects.create_user(username="advisor", password="pass", email="advisor@example.com")
        aprof, _ = Profile.objects.update_or_create(user=self.advisor, defaults={"role": "advisor"})
        self.advisor_token = aprof.ensure_advisor_token()

    def test_student_token_ics_ok(self):
        url = reverse("calendar_ics_token", args=[self.student_token])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        body = r.content.decode("utf-8")
        self.assertIn("BEGIN:VCALENDAR", body)
        self.assertIn("BEGIN:VEVENT", body)
        self.assertIn("SUMMARY:Draft", body)

    def test_student_token_invalid(self):
        url = reverse("calendar_ics_token", args=["not-a-token"]) 
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_advisor_token_ics_ok(self):
        url = reverse("advisor_calendar_ics_token", args=[self.advisor_token])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        body = r.content.decode("utf-8")
        self.assertIn("BEGIN:VCALENDAR", body)
        self.assertIn("BEGIN:VEVENT", body)
        self.assertIn("SUMMARY:sue: Draft", body)

