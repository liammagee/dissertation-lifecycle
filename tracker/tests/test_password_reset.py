from __future__ import annotations

import re

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetFlowTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username='resetme', password='Oldpass123!', email='reset@example.com')

    def test_password_reset_full_flow(self):
        # Start reset
        # Check form has hint and styled input
        form_get = self.client.get(reverse('password_reset'))
        self.assertContains(form_get, 'Check your spam folder', status_code=200)
        self.assertIn('id="id_email"', form_get.content.decode('utf-8'))
        r = self.client.post(reverse('password_reset'), data={'email': 'reset@example.com'})
        self.assertEqual(r.status_code, 302)
        self.assertGreaterEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        # Extract reset URL (first http(s) link)
        m = re.search(r"https?://[^\s]+/reset/[^\s]+/[^\s]+/", body)
        self.assertIsNotNone(m)
        url = m.group(0)
        # Load confirm page (contains strength meter)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('id="pwbar"', resp.content.decode('utf-8'))
        # Post new strong password
        resp2 = self.client.post(url, data={'new_password1': 'Newpass#12345', 'new_password2': 'Newpass#12345'})
        self.assertEqual(resp2.status_code, 302)
        self.assertIn(reverse('password_reset_complete'), resp2['Location'])
        # New password works; old fails
        self.assertFalse(self.client.login(username='resetme', password='Oldpass123!'))
        self.assertTrue(self.client.login(username='resetme', password='Newpass#12345'))
