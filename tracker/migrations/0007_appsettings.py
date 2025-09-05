from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0006_alter_wordlog_unique_together'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status_weight', models.PositiveIntegerField(default=100)),
                ('effort_weight', models.PositiveIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'App Settings',
                'verbose_name_plural': 'App Settings',
            },
        ),
    ]
