from __future__ import annotations

import re

import pytest
from django.contrib.auth.models import User
from tracker.models import Profile


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_calendar_settings_token_urls(page, live_server):  # type: ignore[no-untyped-def]
    u = User.objects.create_user(username='caluser', password='pass#12345B', email='c@example.com')
    Profile.objects.update_or_create(user=u, defaults={'role': 'student'})
    base = live_server.url
    page.goto(f"{base}/login/")
    page.locator('#id_username').fill('caluser')
    page.locator('#id_password').fill('pass#12345B')
    page.get_by_role('button', name=re.compile('Log.?in', re.I)).click()
    page.wait_for_url(re.compile(r"/(dashboard|project/new)/"), timeout=7000)

    page.goto(f"{base}/calendar/settings/")
    # Ensure token URL is present
    body = page.content()
    assert '/calendar/token/' in body
    # Rotate token and ensure it changes
    before = page.locator('code', has_text='/calendar/token/').first.inner_text()
    page.get_by_role('button', name=re.compile('Rotate Student Token', re.I)).click()
    page.wait_for_load_state('networkidle')
    after = page.locator('code', has_text='/calendar/token/').first.inner_text()
    assert before != after

