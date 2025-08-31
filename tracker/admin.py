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


admin.site.register(models.MilestoneTemplate)
admin.site.register(models.TaskTemplate)
admin.site.register(models.Milestone)
admin.site.register(models.Task)
admin.site.register(models.WordLog)
admin.site.register(models.FeedbackRequest)
admin.site.register(models.FeedbackComment)
admin.site.register(models.Document)
admin.site.register(models.Notification)
admin.site.register(models.ProjectNote)
admin.site.register(models.CoreSectionProgress)
