from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('advisor', 'Advisor'),
        ('admin', 'Admin'),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    display_name = models.CharField(max_length=120, blank=True)
    student_calendar_token = models.CharField(max_length=64, blank=True, default='')
    advisor_calendar_token = models.CharField(max_length=64, blank=True, default='')

    def __str__(self) -> str:
        return self.display_name or self.user.get_username()

    def ensure_student_token(self) -> str:
        if not self.student_calendar_token:
            import secrets
            self.student_calendar_token = secrets.token_urlsafe(32)
            self.save(update_fields=['student_calendar_token'])
        return self.student_calendar_token

    def rotate_student_token(self) -> str:
        import secrets
        self.student_calendar_token = secrets.token_urlsafe(32)
        self.save(update_fields=['student_calendar_token'])
        return self.student_calendar_token

    def ensure_advisor_token(self) -> str:
        if not self.advisor_calendar_token:
            import secrets
            self.advisor_calendar_token = secrets.token_urlsafe(32)
            self.save(update_fields=['advisor_calendar_token'])
        return self.advisor_calendar_token

    def rotate_advisor_token(self) -> str:
        import secrets
        self.advisor_calendar_token = secrets.token_urlsafe(32)
        self.save(update_fields=['advisor_calendar_token'])
        return self.advisor_calendar_token


class Project(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('archived', 'Archived'),
    )
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=255)
    field_of_study = models.CharField(max_length=255, blank=True)
    expected_defense_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def completion_percent(self) -> int:
        total = self.tasks.count()
        if total == 0:
            return 0
        done = self.tasks.filter(status='done').count()
        return int(round(100 * done / total))

    def __str__(self) -> str:
        return f"{self.title} ({self.student})"


class MilestoneTemplate(models.Model):
    key = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_phd_only = models.BooleanField(default=False)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self) -> str:
        return self.name


class TaskTemplate(models.Model):
    milestone = models.ForeignKey(MilestoneTemplate, on_delete=models.CASCADE, related_name='tasks')
    key = models.SlugField(max_length=64)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    guidance_url = models.URLField(blank=True)
    guidance_tips = models.TextField(blank=True)

    class Meta:
        unique_together = [('milestone', 'key')]
        ordering = ['milestone', 'order']

    def __str__(self) -> str:
        return self.title


class Milestone(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    template = models.ForeignKey(MilestoneTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self) -> str:
        user = getattr(self.project.student, 'username', str(self.project.student)) if self.project else 'UnknownUser'
        project_title = self.project.title if self.project else 'UnknownProject'
        label = self.name or (self.template.name if self.template else 'Milestone')
        tmpl = f" | tmpl: {self.template.name}" if self.template else ""
        return f"{user} • {project_title} • {label}{tmpl}"


class Task(models.Model):
    PRIORITY_CHOICES = (
        ('low', 'Low'), ('med', 'Medium'), ('high', 'High')
    )
    STATUS_CHOICES = (
        ('todo', 'To Do'), ('doing', 'Doing'), ('done', 'Done')
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='tasks')
    template = models.ForeignKey(TaskTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    user_notes = models.TextField(blank=True)
    word_target = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=8, choices=PRIORITY_CHOICES, default='med')
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default='todo')
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['milestone', 'order']

    def __str__(self) -> str:
        user = getattr(self.project.student, 'username', str(self.project.student)) if self.project else 'UnknownUser'
        project_title = self.project.title if self.project else 'UnknownProject'
        milestone_name = self.milestone.name if self.milestone else 'UnknownMilestone'
        label = self.title or (self.template.title if self.template else 'Task')
        tmpl = f" | tmpl: {self.template.title}" if self.template else ""
        return f"{user} • {project_title} • {milestone_name} • {label}{tmpl}"


class WordLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='word_logs')
    task = models.ForeignKey('Task', null=True, blank=True, on_delete=models.SET_NULL, related_name='word_logs')
    date = models.DateField(default=timezone.now)
    words = models.PositiveIntegerField()
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [('project', 'date', 'task')]
        ordering = ['-date']


class FeedbackRequest(models.Model):
    STATUS_CHOICES = (('open', 'Open'), ('resolved', 'Resolved'))
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='feedback_requests')
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL)
    document = models.ForeignKey('Document', null=True, blank=True, on_delete=models.SET_NULL)
    section = models.CharField(max_length=64, blank=True)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)


class FeedbackComment(models.Model):
    request = models.ForeignKey(FeedbackRequest, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Document(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL)
    file = models.FileField(upload_to='uploads/%Y/%m/')
    filename = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=255, blank=True)


class ProjectNote(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Notification(models.Model):
    KIND_CHOICES = (
        ('due_soon', 'Due Soon'), ('inactivity', 'Inactivity Nudge'), ('feedback', 'Feedback Request'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    payload = models.JSONField(default=dict, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    project = models.ForeignKey('Project', null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:  # pragma: no cover
        u = getattr(self.user, 'username', 'system')
        return f"{self.created_at:%Y-%m-%d %H:%M} • {u} • {self.action}"


class AppSettings(models.Model):
    """Global app settings editable in the admin.

    We use this to control weighting between status and effort for progress.
    Default hides effort in the UI by setting effort_weight=0.
    """
    status_weight = models.PositiveIntegerField(default=100)
    effort_weight = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "App Settings"
        verbose_name_plural = "App Settings"

    def __str__(self) -> str:
        return f"Settings (status={self.status_weight}%, effort={self.effort_weight}%)"

    @classmethod
    def get(cls) -> "AppSettings":
        obj = cls.objects.first()
        if obj:
            return obj
        # Create with defaults on first access
        return cls.objects.create()
