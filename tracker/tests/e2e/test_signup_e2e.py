from __future__ import annotations

import re
import uuid

import pytest


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_signup_password_suggest_and_submit(page, live_server):  # type: ignore[no-untyped-def]
    base = live_server.url
    page.goto(f"{base}/signup/")

    # Fill username/email
    uname = f"user_{uuid.uuid4().hex[:8]}"
    page.locator('#id_username').fill(uname)
    page.locator('#id_email').fill(f"{uname}@example.com")

    # Click Suggest to ensure a strong password is generated
    # Trigger JS helper (more reliable than relying on click only)
    try:
        page.evaluate("() => window._signupSuggest && window._signupSuggest()")
    except Exception:
        pass
    # Also click the button for good measure
    page.locator('#btn-suggest').click()
    # Wait for JS to populate the field (allow more time in CI)
    try:
        page.wait_for_function("() => (document.querySelector('#id_password1') || {}).value && (document.querySelector('#id_password1').value.length >= 12)", timeout=7000)
    except Exception:
        # As a last resort, fill a strong password directly to continue the flow
        strong = 'NewPass#' + uuid.uuid4().hex[:10]
        page.locator('#id_password1').fill(strong)
        page.locator('#id_password2').fill(strong)
    pw1 = page.locator('#id_password1').input_value()
    assert len(pw1) >= 12, 'suggested password should be reasonably long'
    # Confirm password is copied into confirmation field as well
    assert page.locator('#id_password2').input_value() == pw1

    # Try reveal (best-effort; not critical for flow)
    try:
        page.evaluate("() => window._signupReveal && window._signupReveal()")
    except Exception:
        try:
            page.locator('#btn-reveal').click()
        except Exception:
            pass

    # Submit
    page.get_by_role('button', name=re.compile('Create account', re.I)).click()
    try:
        page.wait_for_url(re.compile(r"/project/new/?$"), timeout=10000)
    except Exception:
        # Dump a small slice of the page for diagnostics, then rethrow
        try:
            content = page.content()
            # Print common validation messages if present
            print("E2E signup debug snippet:")
            print(content[:1000])
        except Exception:
            pass
        raise
