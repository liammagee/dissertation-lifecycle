from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0009_split_profile_calendar_tokens'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='progress_percent',
            field=models.PositiveIntegerField(default=0),
        ),
    ]

