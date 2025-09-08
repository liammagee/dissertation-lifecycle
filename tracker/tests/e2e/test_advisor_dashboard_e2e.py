from __future__ import annotations

import re

import pytest
from django.contrib.auth.models import User
from tracker.models import Profile, Project, Milestone, Task


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_advisor_dashboard_lists_projects(page, live_server):  # type: ignore[no-untyped-def]
    # Seed a student with a project+task
    s = User.objects.create_user(username='stud1', password='sPass#12345', email='s1@example.com')
    Profile.objects.update_or_create(user=s, defaults={'role': 'student'})
    p = Project.objects.create(student=s, title='Stud1 Thesis')
    m = Milestone.objects.create(project=p, name='Intro', order=1)
    Task.objects.create(project=p, milestone=m, title='Draft', status='doing', order=1)

    # Create advisor
    a = User.objects.create_user(username='adv1', password='aPass#12345', email='a1@example.com')
    Profile.objects.update_or_create(user=a, defaults={'role': 'advisor'})

    base = live_server.url
    page.goto(f"{base}/login/")
    page.locator('#id_username').fill('adv1')
    page.locator('#id_password').fill('aPass#12345')
    page.get_by_role('button', name=re.compile('Log.?in', re.I)).click()
    page.wait_for_url(re.compile(r"/advisor/?$"), timeout=7000)

    # Should list the student's project
    assert 'Stud1 Thesis' in page.content()

    # Check export JSON contains the project
    page.goto(f"{base}/advisor/export.json")
    assert 'Stud1 Thesis' in page.content()

