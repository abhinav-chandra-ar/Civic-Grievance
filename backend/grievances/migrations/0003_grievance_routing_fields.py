import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grievances', '0002_grievancestatuslog'),
        ('routing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='grievance',
            name='ward',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='grievances',
                to='routing.ward',
            ),
        ),
        migrations.AddField(
            model_name='grievance',
            name='jurisdiction',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='grievances',
                to='routing.jurisdiction',
            ),
        ),
    ]
