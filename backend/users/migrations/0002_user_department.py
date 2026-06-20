import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('departments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='department',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='officers',
                to='departments.department',
            ),
        ),
    ]
