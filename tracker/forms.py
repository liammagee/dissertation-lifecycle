from __future__ import annotations

from django import forms
from .models import Project, Task, WordLog, Document, ProjectNote


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
