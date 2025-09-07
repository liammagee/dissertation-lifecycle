from __future__ import annotations

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tracker.models import Profile


class CalendarSettingsTests(TestCase):
    def setUp(self) -> None:
        self.student = User.objects.create_user(username='stud', password='pass', email='s@example.com')
        self.advisor = User.objects.create_user(username='adv', password='pass', email='a@example.com')
        Profile.objects.update_or_create(user=self.advisor, defaults={'role': 'advisor'})

    def test_student_calendar_settings_shows_token_url(self):
        self.client.login(username='stud', password='pass')
        r = self.client.get(reverse('calendar_settings'))
        self.assertEqual(r.status_code, 200)
        body = r.content.decode('utf-8')
        self.assertIn('/calendar.ics', body)
        # Token ensured and URL included
        self.assertIn('/calendar/token/', body)

    def test_advisor_calendar_settings_shows_both_urls(self):
        self.client.login(username='adv', password='pass')
        r = self.client.get(reverse('calendar_settings'))
        self.assertEqual(r.status_code, 200)
        body = r.content.decode('utf-8')
        self.assertIn('/advisor/calendar.ics', body)
        self.assertIn('/advisor/calendar/token/', body)

    def test_rotate_student_token_changes_url(self):
        self.client.login(username='stud', password='pass')
        r1 = self.client.get(reverse('calendar_settings'))
        t1 = _extract_token_url(r1.content.decode('utf-8'), '/calendar/token/')
        # Rotate
        self.client.post(reverse('calendar_settings'), data={'action': 'rotate_student'})
        r2 = self.client.get(reverse('calendar_settings'))
        t2 = _extract_token_url(r2.content.decode('utf-8'), '/calendar/token/')
        self.assertNotEqual(t1, t2)


def _extract_token_url(body: str, prefix: str) -> str:
    import re
    m = re.search(rf"{prefix}([A-Za-z0-9_\-]+)\.ics", body)
    return m.group(0) if m else ''

