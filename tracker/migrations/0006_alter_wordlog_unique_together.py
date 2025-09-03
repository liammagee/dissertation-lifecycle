from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0005_feedbackrequest_document_delete_coresectionprogress'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='wordlog',
            unique_together={('project', 'date', 'task')},
        ),
    ]

