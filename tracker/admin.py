from django.contrib import admin
from .models import AppSettings


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ("status_weight", "effort_weight", "updated_at")

    def has_add_permission(self, request):
        # Allow only one settings row
        from .models import AppSettings as S
        if S.objects.count() >= 1:
            return False
        return super().has_add_permission(request)
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from . import models


@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'role', 'display_name', 'student_calendar_token_short', 'advisor_calendar_token_short'
    )
    list_filter = ('role',)
    actions = ('rotate_student_tokens', 'rotate_advisor_tokens')

    @admin.display(description='Student token')
    def student_calendar_token_short(self, obj):  # type: ignore[no-untyped-def]
        t = obj.student_calendar_token or ''
        return t[:8] + '…' if t else ''

    @admin.display(description='Advisor token')
    def advisor_calendar_token_short(self, obj):  # type: ignore[no-untyped-def]
        t = obj.advisor_calendar_token or ''
        return t[:8] + '…' if t else ''

    @admin.action(description='Rotate student calendar tokens')
    def rotate_student_tokens(self, request, queryset):  # type: ignore[no-untyped-def]
        n = 0
        for p in queryset:
            p.rotate_student_token()
            n += 1
        self.message_user(request, f"Rotated student tokens for {n} profile(s).")

    @admin.action(description='Rotate advisor calendar tokens')
    def rotate_advisor_tokens(self, request, queryset):  # type: ignore[no-untyped-def]
        n = 0
        for p in queryset:
            p.rotate_advisor_token()
            n += 1
        self.message_user(request, f"Rotated advisor tokens for {n} profile(s).")


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


# Inline Profile on the built-in User admin for convenient role edits
class ProfileInline(admin.StackedInline):
    model = models.Profile
    can_delete = False
    fk_name = 'user'


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)


User = get_user_model()
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)
