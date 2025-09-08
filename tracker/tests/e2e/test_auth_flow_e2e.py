from __future__ import annotations

import re

import pytest
from django.contrib.auth.models import User
from tracker.models import Profile


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_login_change_password_logout_login(page, live_server):  # type: ignore[no-untyped-def]
    # Setup user in DB
    u = User.objects.create_user(username='e2euser', password='oldpass-123A', email='e2e@example.com')
    Profile.objects.update_or_create(user=u, defaults={'role': 'student'})

    base = live_server.url
    # Login
    page.goto(f"{base}/login/")
    page.locator('#id_username').fill('e2euser')
    page.locator('#id_password').fill('oldpass-123A')
    page.get_by_role('button', name=re.compile('Log.?in', re.I)).click()
    # First-time users may be redirected to project_new or dashboard
    page.wait_for_url(re.compile(r"/(dashboard|project/new)/"), timeout=7000)

    # Change password
    page.goto(f"{base}/password-change/")
    page.locator('#id_old_password').fill('oldpass-123A')
    page.locator('#id_new_password1').fill('newpass#12345A')
    page.locator('#id_new_password2').fill('newpass#12345A')
    page.get_by_role('button', name=re.compile('Change Password', re.I)).click()
    page.wait_for_url(re.compile(r"/password-change/done/?$"), timeout=7000)

    # Logout and login with new password
    page.goto(f"{base}/logout/")
    page.goto(f"{base}/login/")
    page.locator('#id_username').fill('e2euser')
    page.locator('#id_password').fill('newpass#12345A')
    page.get_by_role('button', name=re.compile('Log.?in', re.I)).click()
    page.wait_for_url(re.compile(r"/(dashboard|project/new)/"), timeout=7000)

