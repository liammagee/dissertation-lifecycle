from django.contrib import admin
from . import models


@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'display_name')
    list_filter = ('role',)


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'status', 'expected_defense_date')
    list_filter = ('status',)
    search_fields = ('title', 'student__username')

@admin.register(models.MilestoneTemplate)
class MilestoneTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'order', 'is_phd_only')
    list_filter = ('is_phd_only',)
    search_fields = ('name', 'key')


@admin.register(models.TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'milestone', 'order')
    search_fields = ('title', 'milestone__name')
    list_select_related = ('milestone',)


@admin.register(models.Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'student', 'template', 'order', 'completed')
    list_filter = ('completed', 'template')
    search_fields = ('name', 'project__title', 'project__student__username', 'template__name')
    list_select_related = ('project', 'project__student', 'template')

    def student(self, obj):  # type: ignore[no-untyped-def]
        return getattr(obj.project.student, 'username', '')


@admin.register(models.Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'student', 'milestone', 'status', 'priority', 'word_target', 'due_date')
    list_filter = ('status', 'priority', 'milestone')
    search_fields = (
        'title', 'project__title', 'project__student__username',
        'milestone__name', 'template__title'
    )
    list_select_related = ('project', 'project__student', 'milestone', 'template')

    def student(self, obj):  # type: ignore[no-untyped-def]
        return getattr(obj.project.student, 'username', '')
admin.site.register(models.WordLog)
admin.site.register(models.FeedbackRequest)
admin.site.register(models.FeedbackComment)
admin.site.register(models.Document)
admin.site.register(models.Notification)
admin.site.register(models.ProjectNote)
