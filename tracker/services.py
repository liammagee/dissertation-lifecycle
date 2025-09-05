from __future__ import annotations

from typing import Iterable, Tuple
from django.db import models as dj_models

from .models import MilestoneTemplate, TaskTemplate, Project, Milestone, Task, AppSettings
from django.conf import settings


def apply_templates_to_project(project: Project, include_phd: bool = False, include_detailed: bool = False) -> None:
    """Apply milestone/task templates to a project.
    Safe to call multiple times: skips templates already applied.
    """
    mts: Iterable[MilestoneTemplate] = (
        MilestoneTemplate.objects.all().order_by('order', 'id')
    )
    # Track already-applied templates (by template id and by name as a fallback)
    existing_tmpl_ids = set(
        project.milestones.filter(template__isnull=False).values_list('template_id', flat=True)
    )
    existing_names = set(project.milestones.values_list('name', flat=True))
    order = 1
    for mt in mts:
        if mt.is_phd_only and not include_phd:
            continue
        # Apply core milestones always; apply detailed ones only if requested
        is_core = str(mt.key).startswith('core-')
        if not is_core and not include_detailed and not mt.is_phd_only:
            continue
        # Skip if template already applied (or name already present)
        if (mt.id in existing_tmpl_ids) or (mt.name in existing_names):
            continue
        milestone = Milestone.objects.create(
            project=project,
            template=mt,
            name=mt.name,
            order=order,
        )
        order += 1
        t_order = 1
        for tt in TaskTemplate.objects.filter(milestone=mt).order_by('order', 'id'):
            # Heuristics to set default word targets for literature reviews
            target = 0
            title_lower = tt.title.lower()
            if mt.key in ('chapter2-general', 'core-literature-review-general'):
                if 'start general field writing' in title_lower:
                    target = 5500
                if 'goal' in title_lower and '5000' in title_lower:
                    target = 5500
            if mt.key in ('chapter2-special', 'core-literature-review-special'):
                if 'start special field writing' in title_lower:
                    target = 4500
                if 'goal' in title_lower and '4000' in title_lower:
                    target = 4500
            # Core literature review default target for Draft
            if mt.key in ('core-literature-review', 'core-literature-review-general', 'core-literature-review-special'):
                if 'draft literature review' in title_lower:
                    target = 5500
            # Core methodology/findings/conclusion default targets for Draft
            if mt.key == 'core-methodology':
                if 'draft methodology' in title_lower:
                    target = 2500
            if mt.key == 'core-findings':
                if 'draft findings' in title_lower:
                    target = 2500
            if mt.key == 'core-conclusion':
                if 'draft conclusion' in title_lower:
                    target = 1500

            Task.objects.create(
                project=project,
                milestone=milestone,
                template=tt,
                title=tt.title,
                description=tt.description,
                order=t_order,
                word_target=target,
            )
            t_order += 1


def compute_streaks(project: Project) -> tuple[int, int]:
    """Return (current_streak_days, longest_streak_days) based on WordLog with words>0.
    A streak is consecutive calendar days with any positive words.
    """
    from datetime import date, timedelta
    logs = list(project.word_logs.filter(words__gt=0).order_by('date').values_list('date', flat=True))
    if not logs:
        return 0, 0
    longest = 1
    current = 1 if logs[-1] == date.today() else 0
    run = 1
    for i in range(1, len(logs)):
        if logs[i] == logs[i-1] + timedelta(days=1):
            run += 1
        elif logs[i] == logs[i-1]:
            # same day duplicate handled by unique_together but be defensive
            continue
        else:
            if run > longest:
                longest = run
            run = 1
    if run > longest:
        longest = run
    # recompute current streak from today backwards
    current = 0
    day = date.today()
    s = set(logs)
    while day in s:
        current += 1
        day = day - timedelta(days=1)
    return current, longest


def task_status_percent(task: Task) -> int:
    return {
        'todo': 0,
        'doing': 50,
        'done': 100,
    }.get(task.status, 0)


def task_effort(task: Task) -> Tuple[int, int, int]:
    """Return (words_sum, target, percent) for a task."""
    target = int(task.word_target or 0)
    words = 0
    if target > 0:
        words = int(task.word_logs.aggregate(total=dj_models.Sum('words'))['total'] or 0)
    percent = 0 if target <= 0 else min(100, int(round(100 * words / max(1, target))))
    return words, target, percent


def get_progress_weights() -> dict:
    """Return current global weights as a dict {'status': int, 'effort': int}.

    Defaults to status=100, effort=0 so effort is hidden by default.
    """
    try:
        s = AppSettings.get()
        return {'status': int(s.status_weight or 0), 'effort': int(s.effort_weight or 0)}
    except Exception:
        return {'status': 100, 'effort': 0}


def task_combined_percent(task: Task, weights: dict | None = None) -> int:
    # In simple mode, ignore effort entirely and use status only
    if getattr(settings, 'SIMPLE_PROGRESS_MODE', False):
        return task_status_percent(task)
    weights = weights or get_progress_weights()
    sp = task_status_percent(task)
    _, __, ep = task_effort(task)
    tot = max(1, int(weights.get('status', 0)) + int(weights.get('effort', 0)))
    return int(round((int(weights.get('status', 0)) * sp + int(weights.get('effort', 0)) * ep) / tot))


def compute_badges(project: Project) -> list[str]:
    """Return a list of simple badge labels for the project (streak/wordcount)."""
    # Streak badges
    current, longest = compute_streaks(project)
    badges: list[str] = []
    for days, label in [(3, 'Streak 3+'), (7, 'Streak 7+'), (14, 'Streak 14+'), (30, 'Streak 30+')]:
        if current >= days:
            badges.append(label)
    # Wordcount badges (lifetime words logged)
    total_words = int(project.word_logs.aggregate(total=dj_models.Sum('words'))['total'] or 0)
    for thresh, label in [(1000, '1k Words'), (5000, '5k Words'), (10000, '10k Words')]:
        if total_words >= thresh:
            badges.append(label)
    return badges
