from __future__ import annotations

from django.db import migrations, models


def forwards(apps, schema_editor):
    Profile = apps.get_model('tracker', 'Profile')
    # Migrate any existing single calendar_token (from 0008) to student token
    if hasattr(Profile, 'calendar_token'):
        for p in Profile.objects.all():
            token = getattr(p, 'calendar_token', '') or ''
            if token and not getattr(p, 'student_calendar_token', ''):
                p.student_calendar_token = token
                p.save(update_fields=['student_calendar_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0008_profile_calendar_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='student_calendar_token',
            field=models.CharField(max_length=64, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='profile',
            name='advisor_calendar_token',
            field=models.CharField(max_length=64, blank=True, default=''),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='profile',
            name='calendar_token',
        ),
    ]

