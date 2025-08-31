from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count

from .forms import (
    ProjectCreateForm,
    TaskStatusForm,
    TaskForm,
    WordLogForm,
    DocumentForm,
    DocumentNotesForm,
    ProjectNoteForm,
)
from .models import Profile, Project, Task, Document, ProjectNote
from .services import apply_templates_to_project, compute_streaks, task_effort, task_combined_percent


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user, role='student')
            login(request, user)
            return redirect('project_new')
    else:
        form = UserCreationForm()
    return render(request, 'tracker/signup.html', {'form': form})


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'tracker/home.html')


@login_required
def dashboard(request):
    # If user is advisor, redirect to advisor dashboard
    profile = getattr(request.user, 'profile', None)
    if profile and profile.role == 'advisor':
        return redirect('advisor_dashboard')
    # Student dashboard
    project = Project.objects.filter(student=request.user, status='active').first()
    if not project:
        return redirect('project_new')
    tasks = list(project.tasks.select_related('milestone').all())
    completion = project.completion_percent()
    # Read weights for combining status+effort and persist in session
    if 'update_weights' in request.GET:
        try:
            w_status = max(0, int(request.GET.get('w_status', '70')))
        except Exception:
            w_status = 70
        try:
            w_effort = max(0, int(request.GET.get('w_effort', '30')))
        except Exception:
            w_effort = 30
        request.session['w_status'] = w_status
        request.session['w_effort'] = w_effort
    else:
        w_status = request.session.get('w_status', 70)
        w_effort = request.session.get('w_effort', 30)
    weights = {'status': w_status, 'effort': w_effort}
    # Per-milestone progress
    milestones = project.milestones.prefetch_related('tasks').all()
    milestone_progress = []
    for m in milestones:
        ts = list(m.tasks.all())
        total = len(ts)
        done = sum(1 for t in ts if t.status == 'done')
        if total:
            avg = int(round(sum(task_combined_percent(t, weights) for t in ts) / total))
        else:
            avg = 0
        milestone_progress.append({'m': m, 'percent': avg, 'total': total, 'done': done})
    radar_points = [{'label': mp['m'].name.split('–')[0].strip(), 'percent': mp['percent']} for mp in milestone_progress]
    # Radar controls with session persistence
    if 'update_radar' in request.GET:
        radar_show_grid = 'show_grid' in request.GET
        radar_show_labels = 'show_labels' in request.GET
        try:
            radar_speed = max(1, min(20, int(request.GET.get('speed', '6'))))
        except Exception:
            radar_speed = 6
        request.session['radar_show_grid'] = radar_show_grid
        request.session['radar_show_labels'] = radar_show_labels
        request.session['radar_speed'] = radar_speed
    else:
        radar_show_grid = request.session.get('radar_show_grid', True)
        radar_show_labels = request.session.get('radar_show_labels', True)
        radar_speed = request.session.get('radar_speed', 6)
    for t in tasks:
        try:
            t.effort_pct = task_effort(t)[2]
            t.combined_pct = task_combined_percent(t, weights)
        except Exception:
            t.effort_pct = 0
            t.combined_pct = 0
    return render(request, 'tracker/dashboard.html', {
        'project': project,
        'tasks': tasks,
        'completion': completion,
        'milestone_progress': milestone_progress,
        'radar_points': radar_points,
        'radar_show_grid': radar_show_grid,
        'radar_show_labels': radar_show_labels,
        'radar_speed': radar_speed,
        'w_status': w_status,
        'w_effort': w_effort,
        # tasks now carry task.effort_pct
    })


@login_required
def project_new(request):
    if request.method == 'POST':
        form = ProjectCreateForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.student = request.user
            project.save()
            if form.cleaned_data.get('apply_templates'):
                apply_templates_to_project(
                    project,
                    include_phd=form.cleaned_data.get('include_phd'),
                    include_detailed=form.cleaned_data.get('include_detailed'),
                )
            messages.success(request, 'Project created.')
            return redirect('dashboard')
    else:
        form = ProjectCreateForm()
    return render(request, 'tracker/project_new.html', {'form': form})


@login_required
def task_status(request, pk: int):
    task = get_object_or_404(Task, pk=pk, project__student=request.user)
    if request.method == 'POST':
        form = TaskStatusForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    return redirect('dashboard')


@login_required
def task_detail(request, pk: int):
    task = get_object_or_404(Task.objects.select_related('template', 'milestone', 'project'), pk=pk, project__student=request.user)
    tpl = task.template
    docs = Document.objects.filter(project=task.project, task=task).order_by('-uploaded_at')
    up_form = DocumentForm()
    words_sum, target, effort_pct = task_effort(task)
    return render(request, 'tracker/task_detail.html', {
        'task': task,
        'tpl': tpl,
        'docs': docs,
        'upload_form': up_form,
        'words_sum': words_sum,
        'word_target': target,
        'effort_pct': effort_pct,
    })


@login_required
def task_edit(request, pk: int):
    task = get_object_or_404(Task, pk=pk, project__student=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated')
            return redirect('task_detail', pk=task.pk)
    else:
        form = TaskForm(instance=task)
    return render(request, 'tracker/task_form.html', {'form': form, 'task': task})


@login_required
def task_guidance(request, pk: int):
    task = get_object_or_404(Task.objects.select_related('template'), pk=pk, project__student=request.user)
    tpl = task.template
    return render(request, 'tracker/partials/guidance.html', {'task': task, 'tpl': tpl})


@login_required
def upload_document(request, pk: int):
    task = get_object_or_404(Task, pk=pk, project__student=request.user)
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.project = task.project
            doc.task = task
            f = doc.file
            doc.filename = getattr(f, 'name', '')
            doc.size = getattr(f, 'size', 0) or 0
            doc.content_type = getattr(getattr(f, 'file', None), 'content_type', '') or ''
            doc.uploaded_by = request.user
            doc.save()
            messages.success(request, 'File uploaded')
    return redirect('task_detail', pk=task.pk)


@login_required
def delete_document(request, pk: int):
    doc = get_object_or_404(Document, pk=pk, project__student=request.user)
    task_pk = doc.task.pk if doc.task else None
    try:
        # remove file from storage
        if doc.file:
            doc.file.delete(save=False)
    except Exception:
        pass
    doc.delete()
    if task_pk:
        return redirect('task_detail', pk=task_pk)
    return redirect('dashboard')


@login_required
def edit_document(request, pk: int):
    doc = get_object_or_404(Document, pk=pk, project__student=request.user)
    if request.method == 'POST':
        form = DocumentNotesForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            messages.success(request, 'Updated attachment notes')
            if doc.task_id:
                return redirect('task_detail', pk=doc.task_id)
            return redirect('dashboard')
    else:
        form = DocumentNotesForm(instance=doc)
    return render(request, 'tracker/document_form.html', {'form': form, 'doc': doc})


@login_required
def advisor_dashboard(request):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    projects = Project.objects.select_related('student').annotate(total_tasks=Count('tasks'))
    return render(request, 'tracker/advisor_dashboard.html', {'projects': projects})



@login_required
def advisor_project(request, pk: int):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    project = get_object_or_404(Project.objects.select_related('student'), pk=pk)
    tasks = project.tasks.select_related('milestone').all()
    notes = project.notes.select_related('author').all()
    docs = project.documents.select_related('task').order_by('-uploaded_at')
    from .models import FeedbackRequest, FeedbackComment
    if request.method == 'POST':
        if 'new_feedback' in request.POST:
            fr_note = request.POST.get('note', '').strip()
            if fr_note:
                FeedbackRequest.objects.create(project=project, note=fr_note)
                messages.success(request, 'Feedback request created')
                return redirect('advisor_project', pk=pk)
        elif 'add_comment' in request.POST:
            req_id = request.POST.get('request_id')
            msg = request.POST.get('message', '').strip()
            try:
                fr = FeedbackRequest.objects.get(pk=int(req_id), project=project)
            except Exception:
                fr = None
            if fr and msg:
                FeedbackComment.objects.create(request=fr, author=request.user, message=msg)
                messages.success(request, 'Comment added')
                return redirect('advisor_project', pk=pk)
    feedback = project.feedback_requests.prefetch_related('comments__author').all()
    return render(request, 'tracker/advisor_project.html', {
        'project': project,
        'tasks': tasks,
        'notes': notes,
        'docs': docs,
        'feedback': feedback,
    })


@login_required
def wordlogs(request):
    project = Project.objects.filter(student=request.user, status='active').first()
    if not project:
        return redirect('project_new')
    if request.method == 'POST':
        form = WordLogForm(request.POST)
        if form.is_valid():
            wl = form.save(commit=False)
            wl.project = project
            wl.save()
            messages.success(request, 'Word log saved')
            return redirect('wordlogs')
    else:
        form = WordLogForm()
    # Limit task choices to this project
    form.fields['task'].queryset = project.tasks.select_related('milestone').order_by('milestone__order', 'order')
    logs = list(project.word_logs.order_by('-date'))
    current_streak, longest_streak = compute_streaks(project)
    from datetime import date, timedelta
    today = date.today()
    last_days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    by_date = {wl.date: wl.words for wl in logs}
    series = [by_date.get(d, 0) for d in last_days]
    return render(request, 'tracker/wordlogs.html', {
        'project': project,
        'form': form,
        'logs': logs,
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'spark_days': last_days,
        'spark_values': series,
    })


@login_required
def project_notes(request):
    project = Project.objects.filter(student=request.user, status='active').first()
    if not project:
        return redirect('project_new')
    if request.method == 'POST':
        form = ProjectNoteForm(request.POST)
        if form.is_valid():
            n = form.save(commit=False)
            n.project = project
            n.author = request.user
            n.save()
            messages.success(request, 'Note added')
            return redirect('project_notes')
    else:
        form = ProjectNoteForm()
    notes = project.notes.select_related('author').all()
    return render(request, 'tracker/notes.html', {'project': project, 'form': form, 'notes': notes})


@login_required
def project_note_edit(request, pk: int):
    note = get_object_or_404(ProjectNote.objects.select_related('project'), pk=pk, project__student=request.user)
    if note.author != request.user:
        messages.error(request, 'You can only edit your own note.')
        return redirect('project_notes')
    if request.method == 'POST':
        form = ProjectNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Note updated')
            return redirect('project_notes')
    else:
        form = ProjectNoteForm(instance=note)
    return render(request, 'tracker/note_form.html', {'form': form, 'note': note})


@login_required
def project_note_delete(request, pk: int):
    note = get_object_or_404(ProjectNote.objects.select_related('project'), pk=pk, project__student=request.user)
    if note.author != request.user:
        messages.error(request, 'You can only delete your own note.')
        return redirect('project_notes')
    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Note deleted')
        return redirect('project_notes')
    return render(request, 'tracker/note_delete_confirm.html', {'note': note})

