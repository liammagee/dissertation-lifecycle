from __future__ import annotations

import re
import uuid

import pytest


@pytest.mark.e2e
def test_signup_password_suggest_and_submit(page, live_server):  # type: ignore[no-untyped-def]
    base = live_server.url
    page.goto(f"{base}/signup/")

    # Fill username/email
    uname = f"user_{uuid.uuid4().hex[:8]}"
    page.locator('#id_username').fill(uname)
    page.locator('#id_email').fill(f"{uname}@example.com")

    # Click Suggest to ensure a strong password is generated
    page.locator('#btn-suggest').click()
    pw1 = page.locator('#id_password1').input_value()
    assert len(pw1) >= 12, 'suggested password should be reasonably long'
    # Confirm password is copied into confirmation field as well
    assert page.locator('#id_password2').input_value() == pw1

    # Toggle reveal (should switch type)
    t_before = page.locator('#id_password1').get_attribute('type')
    page.locator('#btn-reveal').click()
    t_after = page.locator('#id_password1').get_attribute('type')
    assert t_before != t_after

    # Submit
    page.get_by_role('button', name=re.compile('Create account', re.I)).click()
    page.wait_for_url(re.compile(r"/project/new/?$"), timeout=5000)

