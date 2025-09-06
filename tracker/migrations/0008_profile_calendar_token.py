from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0007_appsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='calendar_token',
            field=models.CharField(max_length=64, blank=True, default=''),
        ),
    ]

