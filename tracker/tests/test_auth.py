from __future__ import annotations

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class PasswordChangeTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username='alice', password='oldpass', email='a@example.com')
        self.client.login(username='alice', password='oldpass')

    def test_password_change_flow(self):
        # GET form
        r = self.client.get(reverse('password_change'))
        self.assertEqual(r.status_code, 200)
        # POST valid change
        resp = self.client.post(reverse('password_change'), data={
            'old_password': 'oldpass',
            'new_password1': 'newpass-12345',
            'new_password2': 'newpass-12345',
        })
        # Django redirects to done page on success
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('password_change_done'), resp['Location'])
        # Old password no longer valid; new works
        self.client.logout()
        self.assertFalse(self.client.login(username='alice', password='oldpass'))
        self.assertTrue(self.client.login(username='alice', password='newpass-12345'))

    def test_change_password_form_has_meter(self):
        r = self.client.get(reverse('password_change'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('id="pwbar"', r.content.decode('utf-8'))


class SignupViewTests(TestCase):
    def setUp(self) -> None:
        # Logged-in user for dashboard/account menu tests
        self.user = User.objects.create_user(username='bob', password='pass123#A', email='b@example.com')
        self.client.login(username='bob', password='pass123#A')

    def test_signup_get_renders(self):
        r = self.client.get(reverse('signup'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('Sign Up', r.content.decode('utf-8'))

    def test_signup_post_success(self):
        resp = self.client.post(reverse('signup'), data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'Newpass#12345A',
            'password2': 'Newpass#12345A',
        })
        # Redirect to project_new on success per views.signup
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('project_new'), resp['Location'])

    def test_account_menu_links_present(self):
        # Create a project so dashboard renders without redirect
        from tracker.models import Project
        Project.objects.create(student=self.user, title='Proj')
        r = self.client.get(reverse('dashboard'))
        html = r.content.decode('utf-8')
        self.assertIn('Account', html)
        self.assertIn(reverse('calendar_settings'), html)
        self.assertIn(reverse('password_change'), html)
        self.assertIn(reverse('logout'), html)

    def test_password_change_done_has_change_again(self):
        # Ensure logged in and page renders with the extra link
        r = self.client.get(reverse('password_change_done'))
        self.assertEqual(r.status_code, 200)
        body = r.content.decode('utf-8')
        self.assertIn('Change Again', body)
        self.assertIn(reverse('password_change'), body)
