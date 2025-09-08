from __future__ import annotations

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def allow_async_unsafe() -> None:
    """Allow Django to access the DB while an event loop is running in E2E tests.

    Playwright's pytest plugin manages an asyncio loop; Django's test DB setup
    is synchronous and normally disallows operations under an active loop.
    Setting DJANGO_ALLOW_ASYNC_UNSAFE=1 for the test session is acceptable here
    because we control concurrency and use a single-threaded live_server.
    """
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")


@pytest.fixture(autouse=True)
def relax_signup_requirements(settings):  # type: ignore[no-untyped-def]
    """Ensure E2E can sign up without invite or email verification.

    Some environments set these via env; override for tests.
    """
    settings.SIGNUP_INVITE_CODE = ''
    settings.REQUIRE_EMAIL_VERIFICATION = False
    # Allow any email domain in tests
    settings.SIGNUP_ALLOWED_EMAIL_DOMAINS = []
