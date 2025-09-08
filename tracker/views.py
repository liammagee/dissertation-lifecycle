from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Max
from django.db import transaction
from datetime import date, timedelta

from .forms import (
    ProjectCreateForm,
    TaskStatusForm,
    TaskForm,
    TaskCreateForm,
    WordLogForm,
    DocumentForm,
    DocumentNotesForm,
    ProjectNoteForm,
    SignupForm,
    ResendActivationForm,
    AdvisorImportForm,
)
from .models import Profile, Project, Task, Document, ProjectNote
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from .services import (
    apply_templates_to_project,
    compute_streaks,
    task_effort,
    task_combined_percent,
    compute_badges,
    get_progress_weights,
)
from .motivation import QUOTES


def signup(request):
    require_verify = getattr(settings, 'REQUIRE_EMAIL_VERIFICATION', False)
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user: User = form.save(commit=False)
            user.email = form.cleaned_data['email']
            if require_verify:
                user.is_active = False
            user.save()
            # A Profile is normally created via signals; use get_or_create to avoid race/dup.
            Profile.objects.get_or_create(user=user, defaults={'role': 'student'})
            if require_verify:
                # Send activation email
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                try:
                    from django.urls import reverse
                    activate_url = request.build_absolute_uri(reverse('activate', args=[uid, token]))
                except Exception:
                    activate_url = f"/activate/{uid}/{token}/"
                send_mail(
                    subject='Activate your account',
                    message=(
                        'Welcome! Please activate your account by clicking the link below:\n\n'
                        f'{activate_url}\n\n'
                        'If you did not sign up, no action is needed.'
                    ),
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com'),
                    recipient_list=[user.email],
                    fail_silently=True,
                )
                messages.success(request, 'Check your email for an activation link to complete signup.')
                return redirect('login')
            else:
                login(request, user)
                return redirect('project_new')
    else:
        form = SignupForm()
    return render(request, 'tracker/signup.html', {'form': form})


def activate(request, uidb64: str, token: str):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=int(uid))
    except Exception:
        user = None
    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save(update_fields=['is_active'])
        messages.success(request, 'Your account has been activated. You can now use the app.')
        try:
            login(request, user)
        except Exception:
            pass
        return redirect('project_new')
    messages.error(request, 'Activation link is invalid or expired.')
    return redirect('login')


def resend_activation(request):
    require_verify = getattr(settings, 'REQUIRE_EMAIL_VERIFICATION', False)
    if not require_verify:
        messages.info(request, 'Email verification is not required.')
        return redirect('login')
    if request.method == 'POST':
        form = ResendActivationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip()
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = None
            if not user:
                messages.error(request, 'No account found with that email.')
                return redirect('resend_activation')
            if user.is_active:
                messages.info(request, 'Your account is already active. You can log in.')
                return redirect('login')
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            try:
                from django.urls import reverse
                activate_url = request.build_absolute_uri(reverse('activate', args=[uid, token]))
            except Exception:
                activate_url = f"/activate/{uid}/{token}/"
            send_mail(
                subject='Activate your account',
                message=(
                    'Use the link below to activate your account:\n\n'
                    f'{activate_url}\n\n'
                ),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com'),
                recipient_list=[email],
                fail_silently=True,
            )
            messages.success(request, 'Activation email sent if the account exists and needs activation.')
            return redirect('login')
    else:
        form = ResendActivationForm()
    return render(request, 'tracker/resend_activation.html', {'form': form})


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'tracker/home.html')


def toggle_theme(request):
    """Toggle dark/light theme and redirect back."""
    try:
        cur = request.session.get('theme', 'light')
        request.session['theme'] = 'dark' if cur != 'dark' else 'light'
    except Exception:
        pass
    nxt = request.META.get('HTTP_REFERER') or '/'
    return redirect(nxt)


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
    qs = project.tasks.select_related('milestone').all()
    # Quick filters (student)
    status = request.GET.get('status')
    if status in ('todo', 'doing', 'done'):
        qs = qs.filter(status=status)
    if request.GET.get('has_target') == '1':
        qs = qs.filter(word_target__gt=0)
    due_days = request.GET.get('due')
    if due_days:
        try:
            from datetime import date, timedelta
            d = int(due_days)
            today = date.today()
            latest = today + timedelta(days=max(0, d))
            qs = qs.filter(due_date__gte=today, due_date__lte=latest)
        except Exception:
            pass
    if request.GET.get('drafts') == '1':
        qs = qs.filter(title__icontains='draft')
    # Simple search by title/description
    q = (request.GET.get('q') or '').strip()
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    milestone_id = request.GET.get('milestone')
    if milestone_id:
        try:
            qs = qs.filter(milestone_id=int(milestone_id))
        except Exception:
            pass
    milestone_id = request.GET.get('milestone')
    if milestone_id:
        try:
            qs = qs.filter(milestone_id=int(milestone_id))
        except Exception:
            pass
    tasks = list(qs)
    # Stage-gated milestones (must be done in order)
    GATED_KEYS = [
        'core-literature-review-general',
        'core-literature-review-special',
        'core-irb-application',
        'core-preliminary-exam',
        'core-final-defence',
    ]
    # Precompute which gated milestones are done (all tasks done)
    done_by_key: dict[str, bool] = {}
    for key in GATED_KEYS:
        m = project.milestones.select_related('template').filter(template__key=key).first()
        if not m:
            done_by_key[key] = False
        else:
            ts = list(m.tasks.all())
            done_by_key[key] = bool(ts) and all(t.status == 'done' for t in ts)
    # Helper to get display name for a gated key
    name_by_key: dict[str, str] = {}
    for m in project.milestones.select_related('template').all():
        if m.template and m.template.key in GATED_KEYS:
            name_by_key[m.template.key] = m.name
    # Compute can-move flags per task (based on full milestone ordering)
    by_milestone = {}
    for t in project.tasks.select_related('milestone').order_by('milestone__order', 'order', 'pk'):
        by_milestone.setdefault(t.milestone_id, []).append(t.pk)
    pos = {}
    for mid, ids in by_milestone.items():
        for i, tid in enumerate(ids):
            pos[tid] = (i, len(ids))
    for t in tasks:
        i, n = pos.get(t.pk, (0, 1))
        t.can_move_up = (i > 0)
        t.can_move_down = (i < n - 1)
    completion = project.completion_percent()
    # Use global weights from admin settings (not per-student)
    weights = get_progress_weights()
    show_effort = (not getattr(settings, 'SIMPLE_PROGRESS_MODE', False)) and int(weights.get('effort', 0)) > 0
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
        # Stage-gating status for this task
        try:
            key = getattr(getattr(t.milestone, 'template', None), 'key', '')
            if key in GATED_KEYS:
                idx = GATED_KEYS.index(key)
                blocked = False
                wait_for = ''
                if idx > 0:
                    for prev in GATED_KEYS[:idx]:
                        if not done_by_key.get(prev, False):
                            blocked = True
                            wait_for = name_by_key.get(prev, prev)
                            break
                t.gated_blocked = blocked
                t.gated_wait = wait_for
            else:
                t.gated_blocked = False
                t.gated_wait = ''
        except Exception:
            t.gated_blocked = False
            t.gated_wait = ''
    badges = compute_badges(project)
    # Quote of the day (stable per user+date)
    try:
        from datetime import date
        key = (request.user.id or 0) + date.today().toordinal()
        quote = QUOTES[key % len(QUOTES)] if QUOTES else None
    except Exception:
        quote = None
    return render(request, 'tracker/dashboard.html', {
        'project': project,
        'tasks': tasks,
        'completion': completion,
        'milestone_progress': milestone_progress,
        'radar_points': radar_points,
        'radar_show_grid': radar_show_grid,
        'radar_show_labels': radar_show_labels,
        'radar_speed': radar_speed,
        'show_effort': show_effort,
        'badges': badges,
        'quote': quote,
        # filters state
        'status_filter': status or '',
        'has_target': request.GET.get('has_target') == '1',
        'due': due_days or '',
        'drafts': request.GET.get('drafts') == '1',
        'milestone_id': milestone_id or '',
        'milestones': project.milestones.all(),
        'q': q,
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
    task = get_object_or_404(Task, pk=pk)
    # Authorization: student owner or advisor/admin
    owner_ok = (task.project and task.project.student_id == request.user.id)
    role = getattr(getattr(request.user, 'profile', None), 'role', 'student')
    advisor_ok = role in ('advisor', 'admin')
    if not (owner_ok or advisor_ok):
        return redirect('dashboard')
    if request.method == 'POST':
        form = TaskStatusForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save()
            # Optional fine-grained percent from slider
            try:
                pct_raw = request.POST.get('percent')
                if pct_raw is not None:
                    pct = int(pct_raw)
                    if pct < 0:
                        pct = 0
                    elif pct > 100:
                        pct = 100
                    task.progress_percent = pct
                    # Keep status consistent with percent
                    if pct == 0:
                        task.status = 'todo'
                    elif pct == 100:
                        task.status = 'done'
                    else:
                        task.status = 'doing'
                    task.save(update_fields=['progress_percent', 'status'])
            except Exception:
                pass
            # Recompute effort/combined with global weights for HTMX response
            weights = get_progress_weights()
            try:
                task.effort_pct = task_effort(task)[2]
                task.combined_pct = task_combined_percent(task, weights)
            except Exception:
                task.effort_pct = 0
                task.combined_pct = 0
            if request.headers.get('HX-Request'):
                tpl = 'tracker/partials/task_row.html' if owner_ok else 'tracker/partials/advisor_task_row.html'
                show_effort = (not getattr(settings, 'SIMPLE_PROGRESS_MODE', False)) and int(weights.get('effort', 0)) > 0
                return render(request, tpl, {'task': task, 'show_effort': show_effort})
            nxt = request.POST.get('next') or ''
            if nxt:
                return redirect(nxt)
            return redirect('dashboard')
    return redirect('dashboard')


@login_required
def task_target(request, pk: int):
    task = get_object_or_404(Task, pk=pk)
    # Authorization: student owner or advisor/admin
    owner_ok = (task.project and task.project.student_id == request.user.id)
    role = getattr(getattr(request.user, 'profile', None), 'role', 'student')
    advisor_ok = role in ('advisor', 'admin')
    if not (owner_ok or advisor_ok):
        return redirect('dashboard')
    if request.method == 'POST':
        try:
            target = int(request.POST.get('word_target', '0'))
        except Exception:
            target = 0
        task.word_target = max(0, target)
        task.save()
        # Recompute to update badges if HTMX
        weights = get_progress_weights()
        try:
            task.effort_pct = task_effort(task)[2]
            task.combined_pct = task_combined_percent(task, weights)
        except Exception:
            task.effort_pct = 0
            task.combined_pct = 0
        if request.headers.get('HX-Request'):
            # Choose partial based on viewer and flag as just saved (for UI pulse)
            tpl = 'tracker/partials/task_row.html' if owner_ok else 'tracker/partials/advisor_task_row.html'
            show_effort = (not getattr(settings, 'SIMPLE_PROGRESS_MODE', False)) and int(weights.get('effort', 0)) > 0
            ctx = {'task': task, 'just_saved': True, 'show_effort': show_effort}
            if request.POST.get('explicit'):
                ctx['toast_message'] = 'Target saved'
            return render(request, tpl, ctx)
        messages.success(request, 'Updated target')
    return redirect('dashboard')


@login_required
def task_detail(request, pk: int):
    task = get_object_or_404(Task.objects.select_related('template', 'milestone', 'project'), pk=pk, project__student=request.user)
    tpl = task.template
    docs = Document.objects.filter(project=task.project, task=task).order_by('-uploaded_at')
    up_form = DocumentForm()
    words_sum, target, effort_pct = task_effort(task)
    # Compute next task (next todo/doing by milestone order, then task order)
    next_task = None
    try:
        qn = Task.objects.filter(project=task.project, status__in=['todo', 'doing']).select_related('milestone').order_by('milestone__order', 'order', 'pk')
        tasks_seq = list(qn)
        for idx, t in enumerate(tasks_seq):
            if t.pk == task.pk and idx + 1 < len(tasks_seq):
                next_task = tasks_seq[idx + 1]
                break
    except Exception:
        next_task = None
    return render(request, 'tracker/task_detail.html', {
        'task': task,
        'tpl': tpl,
        'docs': docs,
        'upload_form': up_form,
        'words_sum': words_sum,
        'word_target': target,
        'effort_pct': effort_pct,
        'next_task': next_task,
    })


@login_required
def feedback(request):
    project = Project.objects.filter(student=request.user, status='active').first()
    if not project:
        return redirect('project_new')
    # existing feedback requests
    from .models import FeedbackRequest, Document as Doc
    feedback_qs = project.feedback_requests.prefetch_related('comments__author', 'task', 'document').order_by('-created_at')
    tasks = list(project.tasks.select_related('milestone').all())
    docs = list(project.documents.order_by('-uploaded_at').all())
    if request.method == 'POST':
        note = (request.POST.get('note') or '').strip()
        task_id = request.POST.get('task_id')
        doc_id = request.POST.get('document_id')
        if note:
            fr = FeedbackRequest(project=project, note=note)
            if task_id:
                try:
                    fr.task = project.tasks.get(pk=int(task_id))
                except Exception:
                    pass
            if doc_id:
                try:
                    fr.document = Doc.objects.get(pk=int(doc_id), project=project)
                except Exception:
                    pass
            fr.save()
            messages.success(request, 'Feedback request sent to advisors')
            # Email advisors and admins
            advisor_emails = list(
                Profile.objects.filter(role__in=['advisor', 'admin'], user__email__isnull=False)
                .exclude(user__email='')
                .values_list('user__email', flat=True)
            )
            if advisor_emails:
                details = []
                if fr.task:
                    details.append(f"Task: {fr.task.title}")
                if fr.document:
                    details.append(f"Document: {fr.document.filename}")
                extra = ("\n" + "\n".join(details)) if details else ""
                send_mail(
                    subject=f"Student feedback request – {project.title}",
                    message=(
                        f"Student {request.user.get_username()} requested feedback on '{project.title}'.\n\n"
                        f"Message:\n{note}{extra}\n\n"
                        "Advisor dashboard: /advisor\n"
                    ),
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com'),
                    recipient_list=advisor_emails,
                    fail_silently=True,
                )
            return redirect('feedback')
        else:
            messages.error(request, 'Please include a note for your feedback request.')
    return render(request, 'tracker/feedback.html', {
        'project': project,
        'tasks': tasks,
        'docs': docs,
        'feedback': feedback_qs,
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
def task_new(request):
    project = Project.objects.filter(student=request.user, status='active').first()
    if not project:
        return redirect('project_new')
    if request.method == 'POST':
        form = TaskCreateForm(request.POST)
        # Limit milestone choices to this project
        form.fields['milestone'].queryset = project.milestones.order_by('order')
        if form.is_valid():
            t = form.save(commit=False)
            t.project = project
            t.status = 'todo'
            # Best-effort ordering: append at end of chosen milestone
            try:
                agg = project.tasks.filter(milestone=t.milestone).aggregate(max_order=Max('order'))
                max_order = int(agg.get('max_order') or 0)
            except Exception:
                max_order = 0
            t.order = max_order + 1
            t.save()
            messages.success(request, 'Task created')
            return redirect('dashboard')
    else:
        form = TaskCreateForm()
        form.fields['milestone'].queryset = project.milestones.order_by('order')
    return render(request, 'tracker/task_create.html', {'form': form, 'project': project})


@login_required
def task_delete(request, pk: int):
    task = get_object_or_404(Task, pk=pk, project__student=request.user)
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Task deleted')
        return redirect('dashboard')
    return render(request, 'tracker/task_delete_confirm.html', {'task': task})


@login_required
def task_move(request, pk: int, direction: str):
    # Owner-only reordering within the same milestone
    task = get_object_or_404(Task.objects.select_related('milestone', 'project'), pk=pk, project__student=request.user)
    if request.method != 'POST':
        return redirect('dashboard')
    if direction not in ('up', 'down'):
        return redirect('dashboard')
    # Renumber siblings to ensure unique sequential order, then swap with neighbor
    with transaction.atomic():
        siblings = list(
            Task.objects.filter(project=task.project, milestone=task.milestone).order_by('order', 'pk')
        )
        for idx, s in enumerate(siblings, start=1):
            if s.order != idx:
                Task.objects.filter(pk=s.pk).update(order=idx)
                s.order = idx
        # refresh index for target task
        ids = [s.pk for s in siblings]
        try:
            i = ids.index(task.pk)
        except ValueError:
            return redirect('dashboard')
        j = i - 1 if direction == 'up' else i + 1
        if j < 0 or j >= len(siblings):
            # Nothing to do
            pass
        else:
            a, b = siblings[i], siblings[j]
            Task.objects.filter(pk=a.pk).update(order=b.order)
            Task.objects.filter(pk=b.pk).update(order=a.order)
            a.order, b.order = b.order, a.order
    # For HTMX partial replacement
    if request.headers.get('HX-Request'):
        # Recompute badges/effect for this row
        try:
            weights = get_progress_weights()
            task.refresh_from_db()
            task.effort_pct = task_effort(task)[2]
            task.combined_pct = task_combined_percent(task, weights)
            # can_move flags after move
            siblings = list(
                Task.objects.filter(project=task.project, milestone=task.milestone).order_by('order', 'pk').values_list('pk', flat=True)
            )
            idx = siblings.index(task.pk)
            task.can_move_up = idx > 0
            task.can_move_down = idx < len(siblings) - 1
        except Exception:
            task.effort_pct = 0
            task.combined_pct = 0
            task.can_move_up = task.can_move_down = False
        show_effort = (not getattr(settings, 'SIMPLE_PROGRESS_MODE', False)) and int(weights.get('effort', 0)) > 0
        return render(request, 'tracker/partials/task_row.html', {'task': task, 'show_effort': show_effort})
    return redirect('dashboard')


@login_required
def task_reorder(request):
    """Reorder (and optionally move) a task via DnD.

    POST params:
    - task_id: int (required)
    - insert_after_id: int | '' (optional; if not provided, append to end)
    - target_milestone_id: int | '' (optional; if provided, move to that milestone first)
    """
    if request.method != 'POST':
        return redirect('dashboard')
    try:
        task_id = int(request.POST.get('task_id'))
    except Exception:
        return JsonResponse({'error': 'invalid task_id'}, status=400)
    insert_after_id = request.POST.get('insert_after_id')
    try:
        insert_after_id = int(insert_after_id) if insert_after_id else None
    except Exception:
        insert_after_id = None
    target_mid = request.POST.get('target_milestone_id')
    try:
        target_mid = int(target_mid) if target_mid else None
    except Exception:
        target_mid = None
    position = (request.POST.get('position') or '').strip()
    # Fetch owned task
    task = get_object_or_404(Task.objects.select_related('milestone', 'project'), pk=task_id, project__student=request.user)
    with transaction.atomic():
        # If moving to another milestone
        if target_mid and (not task.milestone or task.milestone_id != target_mid):
            try:
                target_m = task.project.milestones.get(pk=target_mid)
            except Exception:
                target_m = None
            if target_m:
                task.milestone = target_m
                # place at end initially
                try:
                    agg = Task.objects.filter(project=task.project, milestone=target_m).aggregate(max_order=Max('order'))
                    max_order = int(agg.get('max_order') or 0)
                except Exception:
                    max_order = 0
                task.order = max_order + 1
                task.save(update_fields=['milestone', 'order'])
        # Now reorder within target/current milestone
        siblings = list(Task.objects.filter(project=task.project, milestone=task.milestone).order_by('order', 'pk'))
        # Build new order list with task placed after insert_after_id (or at end)
        ids = [s.pk for s in siblings if s.pk != task.pk]
        if position == 'top':
            ids.insert(0, task.pk)
        elif insert_after_id and insert_after_id in ids:
            idx = ids.index(insert_after_id) + 1
            ids.insert(idx, task.pk)
        else:
            ids.append(task.pk)
        for idx, tpk in enumerate(ids, start=1):
            if tpk == task.pk and task.order != idx:
                Task.objects.filter(pk=tpk).update(order=idx)
                task.order = idx
            elif tpk != task.pk:
                Task.objects.filter(pk=tpk).update(order=idx)
    # Return updated row for HTMX partial replacement if requested
    if request.headers.get('HX-Request'):
        try:
            weights = get_progress_weights()
            task.refresh_from_db()
            task.effort_pct = task_effort(task)[2]
            task.combined_pct = task_combined_percent(task, weights)
            # can_move flags after reorder
            siblings = list(
                Task.objects.filter(project=task.project, milestone=task.milestone).order_by('order', 'pk').values_list('pk', flat=True)
            )
            idx = siblings.index(task.pk)
            task.can_move_up = idx > 0
            task.can_move_down = idx < len(siblings) - 1
        except Exception:
            task.effort_pct = 0
            task.combined_pct = 0
            task.can_move_up = task.can_move_down = False
        show_effort = (not getattr(settings, 'SIMPLE_PROGRESS_MODE', False)) and int(weights.get('effort', 0)) > 0
        return render(request, 'tracker/partials/task_row.html', {'task': task, 'show_effort': show_effort})
    return JsonResponse({'ok': True})


@login_required
def calendar_ics(request):
    """ICS calendar feed for the current student's due tasks (login required).

    Includes TODO/DOING tasks with a due_date, as all-day events.
    """
    project = Project.objects.filter(student=request.user, status='active').first()
    if not project:
        return HttpResponse('BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//dissertation-lifecycle//EN\nEND:VCALENDAR', content_type='text/calendar')
    tasks = project.tasks.select_related('milestone').filter(due_date__isnull=False, status__in=['todo', 'doing']).order_by('due_date', 'milestone__order', 'order')
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//dissertation-lifecycle//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
    ]
    from datetime import datetime
    for t in tasks:
        dt = t.due_date.strftime('%Y%m%d')
        stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        title = t.title.replace('\n', ' ').strip()
        summary = f"{title}"
        desc = f"Milestone: {t.milestone.name if t.milestone else ''}"
        lines += [
            'BEGIN:VEVENT',
            f'UID:task-{t.pk}@dissertation-lifecycle',
            f'DTSTAMP:{stamp}',
            f'DTSTART;VALUE=DATE:{dt}',
            f'DTEND;VALUE=DATE:{dt}',
            f'SUMMARY:{summary}',
            f'DESCRIPTION:{desc}',
            'END:VEVENT',
        ]
    lines.append('END:VCALENDAR')
    return HttpResponse('\n'.join(lines), content_type='text/calendar')


@login_required
def advisor_calendar_ics(request):
    """ICS calendar feed for advisors/admins showing upcoming student task due dates.

    Query params:
      - days: window forward in days (default 60)
    """
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    try:
        days = int(request.GET.get('days', '60'))
    except Exception:
        days = 60
    today = date.today()
    latest = today + timedelta(days=max(1, days))
    qs = Task.objects.select_related('project__student', 'milestone').filter(
        due_date__gte=today,
        due_date__lte=latest,
        status__in=['todo', 'doing'],
        project__status='active',
    ).order_by('due_date', 'project__student__username', 'milestone__order', 'order')
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//dissertation-lifecycle//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
    ]
    from datetime import datetime
    for t in qs:
        dt = t.due_date.strftime('%Y%m%d')
        stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        student = t.project.student.get_username() if t.project and t.project.student else 'student'
        title = t.title.replace('\n', ' ').strip()
        summary = f"{student}: {title}"
        desc = f"Project: {t.project.title if t.project else ''}\\nMilestone: {t.milestone.name if t.milestone else ''}"
        lines += [
            'BEGIN:VEVENT',
            f'UID:adv-task-{t.pk}@dissertation-lifecycle',
            f'DTSTAMP:{stamp}',
            f'DTSTART;VALUE=DATE:{dt}',
            f'DTEND;VALUE=DATE:{dt}',
            f'SUMMARY:{summary}',
            f'DESCRIPTION:{desc}',
            'END:VEVENT',
        ]
    lines.append('END:VCALENDAR')
    return HttpResponse('\n'.join(lines), content_type='text/calendar')


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
            f = doc.file
            # Basic validation
            max_bytes = getattr(settings, 'UPLOAD_MAX_BYTES', 10 * 1024 * 1024)
            content_type = getattr(getattr(f, 'file', None), 'content_type', '') or ''
            size = getattr(f, 'size', 0) or 0
            allowed_types = tuple(getattr(settings, 'UPLOAD_ALLOWED_TYPES', []))
            if size > max_bytes:
                messages.error(request, 'File too large (max 10 MB).')
            elif content_type and allowed_types and content_type not in allowed_types:
                messages.error(request, 'Unsupported file type.')
            else:
                doc.project = task.project
                doc.task = task
                doc.filename = getattr(f, 'name', '')
                doc.size = size
                doc.content_type = content_type
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


# Public ICS feeds using per-user tokens and a simple settings page to manage tokens
def calendar_ics_token(request, token: str):
    """Public ICS via per-user token (student)."""
    profile = Profile.objects.filter(student_calendar_token=token, role='student').select_related('user').first()
    if not profile:
        return HttpResponse('BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//dissertation-lifecycle//EN\nEND:VCALENDAR', content_type='text/calendar', status=404)
    user = profile.user
    project = Project.objects.filter(student=user, status='active').first()
    if not project:
        return HttpResponse('BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//dissertation-lifecycle//EN\nEND:VCALENDAR', content_type='text/calendar')
    tasks = project.tasks.select_related('milestone').filter(due_date__isnull=False, status__in=['todo', 'doing']).order_by('due_date', 'milestone__order', 'order')
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//dissertation-lifecycle//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
    ]
    from datetime import datetime
    for t in tasks:
        dt = t.due_date.strftime('%Y%m%d')
        stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        title = t.title.replace('\n', ' ').strip()
        summary = f"{title}"
        desc = f"Milestone: {t.milestone.name if t.milestone else ''}"
        lines += [
            'BEGIN:VEVENT',
            f'UID:task-{t.pk}@dissertation-lifecycle',
            f'DTSTAMP:{stamp}',
            f'DTSTART;VALUE=DATE:{dt}',
            f'DTEND;VALUE=DATE:{dt}',
            f'SUMMARY:{summary}',
            f'DESCRIPTION:{desc}',
            'END:VEVENT',
        ]
    lines.append('END:VCALENDAR')
    return HttpResponse('\n'.join(lines), content_type='text/calendar')


def advisor_calendar_ics_token(request, token: str):
    """Public ICS via per-user token (advisor/admin aggregate)."""
    profile = Profile.objects.filter(advisor_calendar_token=token, role__in=['advisor', 'admin']).select_related('user').first()
    if not profile:
        return HttpResponse('BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//dissertation-lifecycle//EN\nEND:VCALENDAR', content_type='text/calendar', status=404)
    try:
        days = int(request.GET.get('days', '60'))
    except Exception:
        days = 60
    today = date.today()
    latest = today + timedelta(days=max(1, days))
    qs = Task.objects.select_related('project__student', 'milestone').filter(
        due_date__gte=today,
        due_date__lte=latest,
        status__in=['todo', 'doing'],
        project__status='active',
    ).order_by('due_date', 'project__student__username', 'milestone__order', 'order')
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//dissertation-lifecycle//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
    ]
    from datetime import datetime
    for t in qs:
        dt = t.due_date.strftime('%Y%m%d')
        stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        student = t.project.student.get_username() if t.project and t.project.student else 'student'
        title = t.title.replace('\n', ' ').strip()
        summary = f"{student}: {title}"
        desc = f"Project: {t.project.title if t.project else ''}\\nMilestone: {t.milestone.name if t.milestone else ''}"
        lines += [
            'BEGIN:VEVENT',
            f'UID:adv-task-{t.pk}@dissertation-lifecycle',
            f'DTSTAMP:{stamp}',
            f'DTSTART;VALUE=DATE:{dt}',
            f'DTEND;VALUE=DATE:{dt}',
            f'SUMMARY:{summary}',
            f'DESCRIPTION:{desc}',
            'END:VEVENT',
        ]
    lines.append('END:VCALENDAR')
    return HttpResponse('\n'.join(lines), content_type='text/calendar')


@login_required
def calendar_settings(request):
    """Simple page to view and rotate ICS calendar tokens and URLs."""
    prof = Profile.objects.select_related('user').filter(user=request.user).first()
    if not prof:
        prof = Profile.objects.create(user=request.user, role='student')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ('rotate', 'rotate_student'):
            prof.rotate_student_token()
            messages.success(request, 'Calendar token rotated.')
            return redirect('calendar_settings')
        if action == 'rotate_advisor' and prof.role in ('advisor', 'admin'):
            prof.rotate_advisor_token()
            messages.success(request, 'Advisor calendar token rotated.')
            return redirect('calendar_settings')
    # Ensure token exists for display
    # Ensure relevant tokens exist for display
    stoken = prof.ensure_student_token()
    atoken = prof.ensure_advisor_token() if prof.role in ('advisor', 'admin') else ''
    # Build absolute URLs
    try:
        from django.urls import reverse
        student_token_url = request.build_absolute_uri(reverse('calendar_ics_token', args=[stoken]))
        student_login_url = request.build_absolute_uri(reverse('calendar_ics'))
        advisor_token_url = request.build_absolute_uri(reverse('advisor_calendar_ics_token', args=[atoken])) if atoken else ''
        advisor_login_url = request.build_absolute_uri(reverse('advisor_calendar_ics')) if prof.role in ('advisor', 'admin') else ''
    except Exception:
        student_token_url = f"/calendar/token/{stoken}.ics"
        student_login_url = "/calendar.ics"
        advisor_token_url = f"/advisor/calendar/token/{atoken}.ics" if atoken else ''
        advisor_login_url = "/advisor/calendar.ics" if prof.role in ('advisor', 'admin') else ''
    return render(request, 'tracker/calendar_settings.html', {
        'profile': prof,
        'student_token_url': student_token_url,
        'student_login_url': student_login_url,
        'advisor_token_url': advisor_token_url,
        'advisor_login_url': advisor_login_url,
    })


@login_required
def advisor_dashboard(request):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    from django.core.paginator import Paginator
    q = (request.GET.get('q') or '').strip()
    sort = (request.GET.get('sort') or 'student').strip()
    per = max(1, min(100, int(request.GET.get('per', '20'))))
    qs = Project.objects.select_related('student').annotate(total_tasks=Count('tasks'))
    if q:
        qs = qs.filter(title__icontains=q) | qs.filter(student__username__icontains=q)
    projects = list(qs)
    weights = get_progress_weights()
    GATED_KEYS = [
        'core-literature-review-general',
        'core-literature-review-special',
        'core-irb-application',
        'core-preliminary-exam',
        'core-final-defence',
    ]
    for p in projects:
        ts = list(p.tasks.select_related('milestone').all())
        total = len(ts)
        try:
            p.combined_percent = int(round(sum(task_combined_percent(t, weights) for t in ts) / total)) if total else 0
        except Exception:
            p.combined_percent = 0
        p.done_tasks = sum(1 for t in ts if t.status == 'done')
        # Compute next gated stage (if any)
        try:
            done_by_key: dict[str, bool] = {}
            name_by_key: dict[str, str] = {}
            id_by_key: dict[str, int] = {}
            for m in p.milestones.select_related('template').all():
                if m.template and m.template.key in GATED_KEYS:
                    mts = list(m.tasks.all())
                    done_by_key[m.template.key] = bool(mts) and all(t.status == 'done' for t in mts)
                    name_by_key[m.template.key] = m.name
                    id_by_key[m.template.key] = m.id
            p.gated_next = ''
            p.gated_next_id = None
            p.gated_next_index = 999
            for key in GATED_KEYS:
                if not done_by_key.get(key, False):
                    p.gated_next = name_by_key.get(key, key)
                    p.gated_next_id = id_by_key.get(key)
                    p.gated_next_index = GATED_KEYS.index(key)
                    break
        except Exception:
            p.gated_next = ''
            p.gated_next_id = None
            p.gated_next_index = 999
    key_funcs = {
        'student': lambda x: (getattr(x.student, 'username', ''), x.title.lower()),
        'title': lambda x: (x.title.lower(), getattr(x.student, 'username', '')),
        'combined': lambda x: (-int(x.combined_percent or 0), -x.done_tasks, -x.total_tasks),
        'status': lambda x: (-x.completion_percent(), -x.total_tasks),
        'tasks': lambda x: (-int(x.total_tasks or 0), x.title.lower()),
        'gate': lambda x: (int(getattr(x, 'gated_next_index', 999)), x.title.lower()),
    }
    if sort in key_funcs:
        projects.sort(key=key_funcs[sort])
    paginator = Paginator(projects, per)
    page_obj = Paginator(projects, per).get_page(request.GET.get('page'))
    show_effort = (not getattr(settings, 'SIMPLE_PROGRESS_MODE', False)) and int(weights.get('effort', 0)) > 0
    if not show_effort and sort == 'combined':
        sort = 'status'
    return render(request, 'tracker/advisor_dashboard.html', {
        'projects': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'sort': sort,
        'per': per,
        'show_effort': show_effort,
    })



@login_required
def advisor_project(request, pk: int):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    project = get_object_or_404(Project.objects.select_related('student'), pk=pk)
    # Clear saved export filters for this project
    if request.GET.get('clear_export'):
        try:
            store = request.session.get('advisor_logs_export', {})
            key = f'p{pk}'
            if key in store:
                del store[key]
                request.session['advisor_logs_export'] = store
        except Exception:
            pass
    qs = project.tasks.select_related('milestone').all()
    # Quick filters
    status = request.GET.get('status')
    if status in ('todo', 'doing', 'done'):
        qs = qs.filter(status=status)
    if request.GET.get('has_target') == '1':
        qs = qs.filter(word_target__gt=0)
    due_days = request.GET.get('due')
    if due_days:
        try:
            from datetime import date, timedelta
            d = int(due_days)
            today = date.today()
            latest = today + timedelta(days=max(0, d))
            qs = qs.filter(due_date__gte=today, due_date__lte=latest)
        except Exception:
            pass
    if request.GET.get('drafts') == '1':
        qs = qs.filter(title__icontains='draft')
    # Milestone filter for task table
    milestone_id = request.GET.get('milestone')
    if milestone_id:
        try:
            qs = qs.filter(milestone_id=int(milestone_id))
        except Exception:
            pass
    # Search and ordering
    q = (request.GET.get('q') or '').strip()
    if q:
        qs = qs.filter(title__icontains=q)
    order = (request.GET.get('order') or 'milestone').strip()
    if order == 'due':
        qs = qs.order_by('due_date__isnull', 'due_date', 'milestone__order', 'order', 'pk')
    elif order == 'priority':
        qs = qs.order_by('priority', 'milestone__order', 'order', 'pk')
    else:
        qs = qs.order_by('milestone__order', 'order', 'pk')
    # Pagination
    from django.core.paginator import Paginator
    per = max(1, min(100, int(request.GET.get('per', '25'))))
    page_obj = Paginator(qs, per).get_page(request.GET.get('page'))
    tasks = list(page_obj.object_list)
    # Stage-gating for advisor view (informational locks)
    GATED_KEYS = [
        'core-literature-review-general',
        'core-literature-review-special',
        'core-irb-application',
        'core-preliminary-exam',
        'core-final-defence',
    ]
    done_by_key: dict[str, bool] = {}
    name_by_key: dict[str, str] = {}
    for m in project.milestones.select_related('template').all():
        if m.template and m.template.key in GATED_KEYS:
            ts = list(m.tasks.all())
            done_by_key[m.template.key] = bool(ts) and all(t.status == 'done' for t in ts)
            name_by_key[m.template.key] = m.name
    for t in tasks:
        try:
            key = getattr(getattr(t.milestone, 'template', None), 'key', '')
            if key in GATED_KEYS:
                idx = GATED_KEYS.index(key)
                blocked = False
                wait_for = ''
                if idx > 0:
                    for prev in GATED_KEYS[:idx]:
                        if not done_by_key.get(prev, False):
                            blocked = True
                            wait_for = name_by_key.get(prev, prev)
                            break
                t.gated_blocked = blocked
                t.gated_wait = wait_for
            else:
                t.gated_blocked = False
                t.gated_wait = ''
        except Exception:
            t.gated_blocked = False
            t.gated_wait = ''
    notes = project.notes.select_related('author').all()
    docs = project.documents.select_related('task').order_by('-uploaded_at')
    from .models import FeedbackRequest, FeedbackComment, Document
    if request.method == 'POST':
        if 'new_feedback' in request.POST:
            fr_note = request.POST.get('note', '').strip()
            task_id = request.POST.get('task_id')
            doc_id = request.POST.get('document_id')
            if fr_note:
                fr = FeedbackRequest(project=project, note=fr_note)
                if task_id:
                    try:
                        fr.task = project.tasks.get(pk=int(task_id))
                    except Exception:
                        pass
                if doc_id:
                    try:
                        fr.document = Document.objects.get(pk=int(doc_id), project=project)
                    except Exception:
                        pass
                fr.save()
                messages.success(request, 'Feedback request created')
                to = getattr(project.student, 'email', None)
                if to:
                    send_mail(
                        subject=f"Feedback request for {project.title}",
                        message=(f"Your advisor requested feedback on your project.\n\n{fr_note}\n\n"
                                 "Visit your dashboard to respond."),
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com'),
                        recipient_list=[to],
                        fail_silently=True,
                    )
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
                to = getattr(project.student, 'email', None)
                if to:
                    send_mail(
                        subject=f"New comment on feedback request #{fr.pk}",
                        message=(f"Advisor commented:\n\n{msg}\n\n"
                                 "Visit your dashboard to view."),
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com'),
                        recipient_list=[to],
                        fail_silently=True,
                    )
                return redirect('advisor_project', pk=pk)
    # Per-milestone progress summary
    milestones = project.milestones.prefetch_related('tasks').all()
    milestone_progress = []
    weights = get_progress_weights()
    show_effort = (not getattr(settings, 'SIMPLE_PROGRESS_MODE', False)) and int(weights.get('effort', 0)) > 0
    for m in milestones:
        ts = list(m.tasks.all())
        total = len(ts)
        done = sum(1 for t in ts if t.status == 'done')
        if total:
            avg = int(round(sum(task_combined_percent(t, weights) for t in ts) / total))
        else:
            avg = 0
        milestone_progress.append({'m': m, 'percent': avg, 'total': total, 'done': done})

    feedback = project.feedback_requests.prefetch_related('comments__author').all()
    badges = compute_badges(project)
    # Persisted export filters for this project
    export_filters = (request.session.get('advisor_logs_export', {}) or {}).get(f'p{pk}', {})
    return render(request, 'tracker/advisor_project.html', {
        'project': project,
        'tasks': tasks,
        'notes': notes,
        'docs': docs,
        'feedback': feedback,
        'badges': badges,
        'status_filter': status or '',
        'has_target': request.GET.get('has_target') == '1',
        'due': due_days or '',
        'drafts': request.GET.get('drafts') == '1',
        'milestone_progress': milestone_progress,
        'milestone_id': milestone_id or '',
        'milestones': milestones,
        'export_filters': export_filters,
        'page_obj': page_obj,
        'order': order,
        'q': q,
        'per': per,
        'show_effort': show_effort,
    })


@login_required
def advisor_project_export_json(request, pk: int):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    import json
    from django.http import HttpResponse
    project = get_object_or_404(Project.objects.select_related('student'), pk=pk)
    tasks = list(project.tasks.select_related('milestone').all())
    weights = get_progress_weights()
    data = {
        'project_id': project.id,
        'author': project.student.get_username(),
        'email': project.student.email,
        'title': project.title,
        'tasks': [
            {
                'id': t.id,
                'milestone': t.milestone.name if t.milestone else None,
                'title': t.title,
                'status': t.status,
                'priority': t.priority,
                'word_target': t.word_target,
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'combined_percent': task_combined_percent(t, weights),
            }
            for t in tasks
        ],
    }
    payload = json.dumps(data, indent=2)
    return HttpResponse(payload, content_type='application/json')


@login_required
def advisor_project_export_csv(request, pk: int):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    import csv
    from django.http import HttpResponse
    project = get_object_or_404(Project.objects.select_related('student'), pk=pk)
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="project_{project.id}_tasks.csv"'
    writer = csv.writer(resp)
    writer.writerow(['task_id', 'milestone', 'title', 'status', 'priority', 'word_target', 'due_date', 'combined_percent'])
    weights = get_progress_weights()
    for t in project.tasks.select_related('milestone').all():
        writer.writerow([
            t.id,
            t.milestone.name if t.milestone else '',
            t.title,
            t.status,
            t.priority,
            t.word_target,
            t.due_date.isoformat() if t.due_date else '',
            task_combined_percent(t, weights),
        ])
    return resp


@login_required
def advisor_export_json(request):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    import json
    from django.http import HttpResponse
    weights = get_progress_weights()
    data = []
    for p in Project.objects.select_related('student').all():
        tasks = list(p.tasks.select_related('milestone').all())
        total = len(tasks)
        combined = int(round(sum(task_combined_percent(t, weights) for t in tasks) / total)) if total else 0
        done = sum(1 for t in tasks if t.status == 'done')
        data.append({
            'project_id': p.id,
            'author': p.student.get_username(),
            'email': p.student.email,
            'title': p.title,
            'total_tasks': total,
            'done_tasks': done,
            'combined_percent': combined,
        })
    payload = json.dumps(data, indent=2)
    return HttpResponse(payload, content_type='application/json')


@login_required
def advisor_export_csv(request):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    import csv
    from django.http import HttpResponse
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="advisor_export.csv"'
    writer = csv.writer(resp)
    writer.writerow(['project_id', 'author', 'email', 'title', 'total_tasks', 'done_tasks', 'combined_percent'])
    weights = get_progress_weights()
    for p in Project.objects.select_related('student').all():
        tasks = list(p.tasks.select_related('milestone').all())
        total = len(tasks)
        combined = int(round(sum(task_combined_percent(t, weights) for t in tasks) / total)) if total else 0
        done = sum(1 for t in tasks if t.status == 'done')
        writer.writerow([p.id, p.student.get_username(), p.student.email, p.title, total, done, combined])
    return resp


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
        # Preselect a task from query param for convenience
        tid = (request.GET.get('task') or '').strip()
        if tid:
            try:
                t = project.tasks.get(pk=int(tid))
                form.fields['task'].initial = t.pk
            except Exception:
                pass
    # Limit task choices to this project
    form.fields['task'].queryset = project.tasks.select_related('milestone').order_by('milestone__order', 'order')
    logs = list(project.word_logs.order_by('-date'))
    current_streak, longest_streak = compute_streaks(project)
    today = date.today()
    last_days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    by_date = {wl.date: wl.words for wl in logs}
    series = [by_date.get(d, 0) for d in last_days]
    maxv = max(series) if series else 0
    chart_h = 80
    bars = []
    for idx, v in enumerate(series):
        h = 0
        if maxv > 0:
            h = max(1, int(v / maxv * (chart_h - 4)))
        bars.append({'idx': idx, 'value': v, 'height': h, 'x': idx * 20, 'y': chart_h - h, 'date': last_days[idx]})
    # Weekly totals (last 8 weeks, Monday-start)
    def week_start(d: date) -> date:
        return d - timedelta(days=d.weekday())
    weeks = []
    start_this_week = week_start(today)
    for i in range(7, -1, -1):
        ws = start_this_week - timedelta(weeks=i)
        we = ws + timedelta(days=6)
        weeks.append((ws, we))
    logs_by_date = {wl.date: wl.words for wl in project.word_logs.order_by('date')}
    weekly_totals = []
    for ws, we in weeks:
        total = 0
        d = ws
        while d <= we:
            total += int(logs_by_date.get(d, 0) or 0)
            d += timedelta(days=1)
        weekly_totals.append({'start': ws, 'end': we, 'total': total})
    return render(request, 'tracker/wordlogs.html', {
        'project': project,
        'form': form,
        'logs': logs,
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'spark_days': last_days,
        'spark_values': series,
        'spark_bars': bars,
        'spark_h': chart_h,
        'weekly_totals': weekly_totals,
        'milestones': project.milestones.order_by('order').all(),
        'export_filters': request.session.get('logs_export', {}),
    })


@login_required
def wordlogs_csv(request):
    project = Project.objects.filter(student=request.user, status='active').first()
    if not project:
        return redirect('project_new')
    import csv
    # Optional filters: start, end (YYYY-MM-DD), milestone (id)
    start_s = (request.GET.get('start') or '').strip()
    end_s = (request.GET.get('end') or '').strip()
    ms_id = (request.GET.get('milestone') or '').strip()
    start_d = end_d = None
    try:
        if start_s:
            start_d = date.fromisoformat(start_s)
    except Exception:
        start_d = None
    try:
        if end_s:
            end_d = date.fromisoformat(end_s)
    except Exception:
        end_d = None
    # Save last used filters for UI defaults
    try:
        request.session['logs_export'] = {'start': start_s, 'end': end_s, 'milestone': ms_id}
    except Exception:
        pass
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="writing_logs.csv"'
    w = csv.writer(resp)
    w.writerow(['date', 'words', 'note', 'task_id', 'task', 'milestone'])
    qs = project.word_logs.select_related('task', 'task__milestone').order_by('date').all()
    if start_d:
        qs = qs.filter(date__gte=start_d)
    if end_d:
        qs = qs.filter(date__lte=end_d)
    if ms_id:
        try:
            qs = qs.filter(task__milestone_id=int(ms_id))
        except Exception:
            pass
    for wl in qs:
        task_title = wl.task.title if wl.task else ''
        milestone_name = wl.task.milestone.name if wl.task and wl.task.milestone else ''
        w.writerow([
            wl.date.isoformat(),
            wl.words,
            wl.note,
            wl.task_id or '',
            task_title,
            milestone_name,
        ])
    return resp


@login_required
def advisor_project_wordlogs_csv(request, pk: int):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    import csv
    project = get_object_or_404(Project.objects.select_related('student'), pk=pk)
    # Optional filters: start, end (YYYY-MM-DD), milestone (id)
    start_s = (request.GET.get('start') or '').strip()
    end_s = (request.GET.get('end') or '').strip()
    ms_id = (request.GET.get('milestone') or '').strip()
    start_d = end_d = None
    try:
        if start_s:
            start_d = date.fromisoformat(start_s)
    except Exception:
        start_d = None
    try:
        if end_s:
            end_d = date.fromisoformat(end_s)
    except Exception:
        end_d = None
    # Save last used filters for this project for UI defaults
    try:
        store = request.session.get('advisor_logs_export', {})
        store[f'p{pk}'] = {'start': start_s, 'end': end_s, 'milestone': ms_id}
        request.session['advisor_logs_export'] = store
    except Exception:
        pass
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="project_{project.id}_wordlogs.csv"'
    w = csv.writer(resp)
    w.writerow(['date', 'words', 'note', 'task_id', 'task', 'milestone'])
    qs = project.word_logs.select_related('task', 'task__milestone').order_by('date').all()
    if start_d:
        qs = qs.filter(date__gte=start_d)
    if end_d:
        qs = qs.filter(date__lte=end_d)
    if ms_id:
        try:
            qs = qs.filter(task__milestone_id=int(ms_id))
        except Exception:
            pass
    for wl in qs:
        task_title = wl.task.title if wl.task else ''
        milestone_name = wl.task.milestone.name if wl.task and wl.task.milestone else ''
        w.writerow([
            wl.date.isoformat(),
            wl.words,
            wl.note,
            wl.task_id or '',
            task_title,
            milestone_name,
        ])
    return resp


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


def healthz(request):
    """Lightweight health check endpoint for Fly.io."""
    return JsonResponse({"status": "ok"})


@login_required
def advisor_project_export_zip(request, pk: int):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    import io, zipfile, csv, json, os
    project = get_object_or_404(Project.objects.select_related('student'), pk=pk)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        tasks = list(project.tasks.select_related('milestone').all())
        tasks_json = [
            {
                'id': t.id,
                'milestone': t.milestone.name if t.milestone else None,
                'title': t.title,
                'status': t.status,
                'priority': t.priority,
                'word_target': t.word_target,
                'due_date': t.due_date.isoformat() if t.due_date else None,
            }
            for t in tasks
        ]
        zf.writestr('tasks.json', json.dumps(tasks_json, indent=2))
        csv_buf = io.StringIO(); w = csv.writer(csv_buf)
        w.writerow(['task_id','milestone','title','status','priority','word_target','due_date'])
        for t in tasks:
            w.writerow([t.id, t.milestone.name if t.milestone else '', t.title, t.status, t.priority, t.word_target, t.due_date.isoformat() if t.due_date else ''])
        zf.writestr('tasks.csv', csv_buf.getvalue())
        logs = list(project.word_logs.order_by('date').all())
        logs_json = [{'date': wl.date.isoformat(), 'words': wl.words, 'note': wl.note} for wl in logs]
        zf.writestr('logs.json', json.dumps(logs_json, indent=2))
        csv_buf = io.StringIO(); w = csv.writer(csv_buf)
        w.writerow(['date','words','note'])
        for wl in logs:
            w.writerow([wl.date.isoformat(), wl.words, wl.note])
        zf.writestr('logs.csv', csv_buf.getvalue())
        for d in project.documents.all():
            try:
                if d.file:
                    with d.file.open('rb') as fp:
                        safe_name = f"{d.id}_{os.path.basename(d.filename)}"
                        zf.writestr(f"attachments/{safe_name}", fp.read())
            except Exception:
                continue
    resp = HttpResponse(buf.getvalue(), content_type='application/zip')
    resp['Content-Disposition'] = f'attachment; filename="project_{project.id}_export.zip"'
    return resp


@login_required
def my_export_zip(request):
    project = Project.objects.filter(student=request.user, status='active').first()
    if not project:
        return redirect('project_new')
    import io, zipfile, csv, json, os
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        tasks = list(project.tasks.select_related('milestone').all())
        tasks_json = [
            {
                'id': t.id,
                'milestone': t.milestone.name if t.milestone else None,
                'title': t.title,
                'status': t.status,
                'priority': t.priority,
                'word_target': t.word_target,
                'due_date': t.due_date.isoformat() if t.due_date else None,
            }
            for t in tasks
        ]
        zf.writestr('tasks.json', json.dumps(tasks_json, indent=2))
        csv_buf = io.StringIO(); w = csv.writer(csv_buf)
        w.writerow(['task_id','milestone','title','status','priority','word_target','due_date'])
        for t in tasks:
            w.writerow([t.id, t.milestone.name if t.milestone else '', t.title, t.status, t.priority, t.word_target, t.due_date.isoformat() if t.due_date else ''])
        zf.writestr('tasks.csv', csv_buf.getvalue())
        logs = list(project.word_logs.order_by('date').all())
        logs_json = [{'date': wl.date.isoformat(), 'words': wl.words, 'note': wl.note} for wl in logs]
        zf.writestr('logs.json', json.dumps(logs_json, indent=2))
        csv_buf = io.StringIO(); w = csv.writer(csv_buf)
        w.writerow(['date','words','note'])
        for wl in logs:
            w.writerow([wl.date.isoformat(), wl.words, wl.note])
        zf.writestr('logs.csv', csv_buf.getvalue())
        for d in project.documents.all():
            try:
                if d.file:
                    with d.file.open('rb') as fp:
                        safe_name = f"{d.id}_{os.path.basename(d.filename)}"
                        zf.writestr(f"attachments/{safe_name}", fp.read())
            except Exception:
                continue
    resp = HttpResponse(buf.getvalue(), content_type='application/zip')
    resp['Content-Disposition'] = f'attachment; filename="my_project_export.zip"'
    return resp


@login_required
def advisor_import_template(request):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    import csv
    from django.http import HttpResponse
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="advisor_import_template.csv"'
    w = csv.writer(resp)
    w.writerow(['username', 'email', 'title', 'apply_templates', 'status', 'password'])
    w.writerow(['alice', 'alice@example.com', 'Sample Dissertation', '1', 'active', ''])
    return resp


@login_required
def advisor_import(request):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    results = []
    if request.method == 'POST':
        form = AdvisorImportForm(request.POST, request.FILES)
        if form.is_valid():
            import csv, io
            f = form.cleaned_data['file']
            try:
                data = f.read().decode('utf-8')
            except Exception:
                data = f.read().decode('latin-1', errors='ignore')
            reader = csv.DictReader(io.StringIO(data))
            from django.contrib.auth import get_user_model
            User = get_user_model()
            created_users = updated_users = created_projects = updated_projects = 0
            from .models import Profile, Project
            for row in reader:
                uname = (row.get('username') or '').strip()
                email = (row.get('email') or '').strip()
                title = (row.get('title') or '').strip() or 'Untitled Project'
                display_name = (row.get('display_name') or '').strip()
                new_title = (row.get('new_title') or '').strip()
                apply_templates = (row.get('apply_templates') or '0').strip().lower() in ('1', 'true', 'yes', 'y')
                status = (row.get('status') or 'active').strip() or 'active'
                pwd = (row.get('password') or '').strip()
                if not uname:
                    results.append(('error', 'Missing username'))
                    continue
                # Fetch or create user
                user = User.objects.filter(username=uname).first()
                u_created = False
                update_only = bool(form.cleaned_data.get('update_only'))
                dry_run = bool(form.cleaned_data.get('dry_run'))
                allow_user_create = bool(form.cleaned_data.get('create_missing_users'))
                allow_project_create = bool(form.cleaned_data.get('create_missing_projects'))
                if not user:
                    if update_only and not allow_user_create:
                        results.append(('error', f"User missing (update-only): {uname}"))
                        continue
                    user = User(username=uname, email=email)
                    if not dry_run:
                        if pwd:
                            user.set_password(pwd)
                        else:
                            user.set_unusable_password()
                        user.save()
                    u_created = True
                    created_users += 1
                else:
                    if email and user.email != email:
                        if not dry_run:
                            user.email = email
                            user.save(update_fields=['email'])
                        updated_users += 1
                # Ensure / update Profile and display name
                prof = Profile.objects.filter(user=user).first()
                if not prof:
                    if not update_only and not dry_run:
                        Profile.objects.create(user=user, role='student')
                elif display_name and prof.display_name != display_name and not dry_run:
                    prof.display_name = display_name
                    prof.save(update_fields=['display_name'])
                # Fetch or create project
                proj = Project.objects.filter(student=user, title=title).first()
                p_created = False
                if not proj:
                    if update_only and not allow_project_create:
                        results.append(('error', f"Project missing (update-only): {uname} / {title}"))
                        continue
                    proj = Project(student=user, title=title, status=status)
                    if not dry_run:
                        proj.save()
                    p_created = True
                    created_projects += 1
                if not p_created:
                    changed = False
                    if status and proj.status != status:
                        proj.status = status; changed = True
                    if new_title and new_title != proj.title:
                        proj.title = new_title; changed = True
                    if changed and not dry_run:
                        proj.save(update_fields=['status', 'title'])
                        updated_projects += 1
                else:
                    if apply_templates and not dry_run:
                        try:
                            apply_templates_to_project(proj)
                        except Exception:
                            pass
                results.append(('ok', f"{uname} / {title} ({'new' if p_created else 'updated'})"))
            messages.success(request, f"Import complete. Users: +{created_users}/{updated_users} updated. Projects: +{created_projects}/{updated_projects} updated.")
    else:
        form = AdvisorImportForm()
    return render(request, 'tracker/advisor_import.html', {'form': form, 'results': results})


@login_required
def advisor_export_import_csv(request):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role not in ('advisor', 'admin'):
        return redirect('dashboard')
    import csv
    from django.http import HttpResponse
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="advisor_export_import.csv"'
    w = csv.writer(resp)
    # Export in a format that can be re-imported directly
    w.writerow(['username', 'email', 'title', 'apply_templates', 'status', 'password', 'display_name', 'new_title'])
    for p in Project.objects.select_related('student').all():
        user = p.student
        prof = getattr(user, 'profile', None)
        display = getattr(prof, 'display_name', '') if prof else ''
        w.writerow([
            user.get_username(),
            user.email or '',
            p.title,
            '',  # apply_templates
            p.status,
            '',  # password
            display,
            '',  # new_title
        ])
    return resp
