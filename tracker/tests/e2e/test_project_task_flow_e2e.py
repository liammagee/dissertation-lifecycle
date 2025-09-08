from __future__ import annotations

import re

import pytest
from django.contrib.auth.models import User
from tracker.models import Profile, Project, Milestone


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_project_create_and_task_status(page, live_server):  # type: ignore[no-untyped-def]
    # Create a user and login
    u = User.objects.create_user(username='projuser', password='pass#12345A', email='p@example.com')
    Profile.objects.update_or_create(user=u, defaults={'role': 'student'})
    base = live_server.url
    page.goto(f"{base}/login/")
    page.locator('#id_username').fill('projuser')
    page.locator('#id_password').fill('pass#12345A')
    page.get_by_role('button', name=re.compile('Log.?in', re.I)).click()
    page.wait_for_url(re.compile(r"/(dashboard|project/new)/"), timeout=7000)

    # If redirected to dashboard with no project, navigate to project_new
    page.goto(f"{base}/project/new/")
    page.locator('#id_title').fill('My Thesis')
    # apply_templates is usually on by default; submit form
    page.get_by_role('button', name=re.compile('Create', re.I)).click()
    page.wait_for_url(re.compile(r"/dashboard/?$"), timeout=7000)
    # Ensure at least one milestone exists for this project (templates may not be seeded in tests)
    proj = Project.objects.filter(student=u).first()
    if proj and not proj.milestones.exists():
        Milestone.objects.create(project=proj, name='Intro', order=1)

    # Create a new task under first milestone
    page.goto(f"{base}/tasks/new/")
    # Select first non-empty milestone option (skip the blank placeholder). Wait until options are present.
    page.wait_for_function("() => document.querySelectorAll('select#id_milestone option').length >= 2", timeout=3000)
    # Choose the second option (index=1) which should be the first real milestone
    page.locator('select#id_milestone').select_option(index=1)
    page.locator('#id_title').fill('E2E Task')
    page.get_by_role('button', name=re.compile('Create', re.I)).click()
    page.wait_for_url(re.compile(r"/dashboard/?$"), timeout=10000)

    # Change status of the task to Done via the select dropdown
    # Find the row containing our task title
    row = page.locator('tr.task-row', has_text='E2E Task').first
    # In that row, select Done
    row.locator('select[name="status"]').select_option('done')
    # Wait for the row to update (HTMX swap)
    page.wait_for_selector('tr.task-row:has-text("E2E Task")')
    # Verify the select now reflects Done
    val = row.locator('select[name="status"]').input_value()
    assert val == 'done'
