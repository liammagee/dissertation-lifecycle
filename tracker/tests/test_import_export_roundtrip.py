from __future__ import annotations

import io

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tracker.models import Profile, Project


class ImportExportRoundTripTests(TestCase):
    def setUp(self) -> None:
        # Advisor
        self.advisor = User.objects.create_user(username="advisor", password="pass", email="advisor@example.com")
        Profile.objects.update_or_create(user=self.advisor, defaults={"role": "advisor"})
        # Students
        s1 = User.objects.create_user(username="s1", password="x", email="s1@example.com")
        Profile.objects.update_or_create(user=s1, defaults={"role": "student", "display_name": "Student One"})
        Project.objects.create(student=s1, title="P1", status="active")
        s2 = User.objects.create_user(username="s2", password="x", email="s2@example.com")
        Profile.objects.update_or_create(user=s2, defaults={"role": "student", "display_name": "Student Two"})
        Project.objects.create(student=s2, title="P2", status="archived")
        self.client.login(username="advisor", password="pass")

    def test_export_import_roundtrip(self):
        # Export re-importable CSV
        url = reverse("advisor_export_import_csv")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        content = r.content.decode("utf-8")
        # Import with update_only=True to ensure no creations
        import_url = reverse("advisor_import")
        f = io.BytesIO(content.encode("utf-8"))
        f.name = "export.csv"
        resp = self.client.post(import_url, {"file": f, "update_only": "on"}, format="multipart")
        self.assertEqual(resp.status_code, 200)
        # Verify counts unchanged
        self.assertEqual(User.objects.filter(profile__role="student").count(), 2)
        self.assertEqual(Project.objects.count(), 2)
        # Verify basic fields remain the same
        self.assertEqual(Project.objects.get(title="P1").status, "active")
        self.assertEqual(Project.objects.get(title="P2").status, "archived")
