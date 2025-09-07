from __future__ import annotations

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tracker.models import Project, Milestone, Task


class TaskReorderTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username='dnd', password='pass')
        self.client.login(username='dnd', password='pass')
        self.project = Project.objects.create(student=self.user, title='DnD')
        self.m1 = Milestone.objects.create(project=self.project, name='M1', order=1)
        self.m2 = Milestone.objects.create(project=self.project, name='M2', order=2)
        self.t1 = Task.objects.create(project=self.project, milestone=self.m1, title='A', order=1)
        self.t2 = Task.objects.create(project=self.project, milestone=self.m1, title='B', order=2)
        self.t3 = Task.objects.create(project=self.project, milestone=self.m2, title='C', order=1)

    def test_reorder_within_milestone(self):
        url = reverse('task_reorder')
        # Move t2 before t1 using insert_before (by specifying insert_after of None and then position top within m1)
        # Simulate dropping t2 on top half of t1: insert_after_id of previous row (none) and same milestone
        resp = self.client.post(url, data={
            'task_id': self.t2.id,
            'insert_after_id': '',
            'target_milestone_id': self.m1.id,
            'position': 'top'
        }, HTTP_HX_REQUEST='true')
        self.assertEqual(resp.status_code, 200)
        # Refresh and check order
        self.t1.refresh_from_db(); self.t2.refresh_from_db()
        self.assertEqual(self.t2.order, 1)
        self.assertEqual(self.t1.order, 2)

    def test_move_across_milestone(self):
        url = reverse('task_reorder')
        # Move t1 to top of milestone 2
        resp = self.client.post(url, data={
            'task_id': self.t1.id,
            'insert_after_id': '',
            'target_milestone_id': self.m2.id,
            'position': 'top'
        }, HTTP_HX_REQUEST='true')
        self.assertEqual(resp.status_code, 200)
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.milestone_id, self.m2.id)
        self.assertEqual(self.t1.order, 1)
        # Existing t3 should be pushed to order 2
        self.t3.refresh_from_db()
        # Note: our implementation renumbers all siblings; verify t3 is not order 1 anymore
        self.assertNotEqual(self.t3.order, 1)

