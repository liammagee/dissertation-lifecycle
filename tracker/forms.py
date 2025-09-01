from __future__ import annotations

from django import forms
from django.conf import settings
from .models import Project, Task, WordLog, Document, ProjectNote, Milestone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class ProjectCreateForm(forms.ModelForm):
    apply_templates = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Create default milestones and tasks",
        label="Apply dissertation template",
    )
    include_phd = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Include ERP PhD track tasks",
        label="Include ERP PhD tasks",
    )
    include_detailed = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Include detailed scaffolding (chapter-specific checklists)",
        label="Include detailed scaffolding",
    )
    class Meta:
        model = Project
        fields = ['title', 'field_of_study', 'expected_defense_date']
        widgets = {
            'expected_defense_date': forms.DateInput(attrs={'type': 'date'})
        }


class TaskStatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['status']


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'user_notes', 'word_target', 'due_date', 'priority', 'status']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'})
        }


class TaskCreateForm(forms.ModelForm):
    milestone = forms.ModelChoiceField(queryset=Milestone.objects.none())
    class Meta:
        model = Task
        fields = ['milestone', 'title', 'description', 'word_target', 'due_date', 'priority']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'})
        }


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    invite_code = forms.CharField(required=False, help_text="Enter invite code if required")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "invite_code")

    def clean_invite_code(self):
        code = (self.cleaned_data.get('invite_code') or '').strip()
        expected = getattr(settings, 'SIGNUP_INVITE_CODE', '')
        if expected and code != expected:
            raise forms.ValidationError("Invalid invite code.")
        return code

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        allowed = [d.strip().lower() for d in getattr(settings, 'SIGNUP_ALLOWED_EMAIL_DOMAINS', [])]
        if allowed:
            try:
                domain = email.split('@', 1)[1].lower()
            except Exception:
                domain = ''
            if domain not in allowed:
                raise forms.ValidationError("Email domain not allowed.")
        return email


class ResendActivationForm(forms.Form):
    email = forms.EmailField()


class WordLogForm(forms.ModelForm):
    class Meta:
        model = WordLog
        fields = ['date', 'words', 'note', 'task']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})
        }


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['file', 'notes']


class DocumentNotesForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['notes']


class ProjectNoteForm(forms.ModelForm):
    class Meta:
        model = ProjectNote
        fields = ['title', 'body']
