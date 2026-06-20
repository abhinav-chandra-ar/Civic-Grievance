import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('departments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ward',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=20, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Jurisdiction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='RoutingRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(help_text='Matches ml_department_suggestion values: KSEB, KWA, PWD, PUBLIC_HEALTH, LSG', max_length=50)),
                ('ward', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='routing_rules',
                    to='routing.ward',
                )),
                ('department', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='routing_rules',
                    to='departments.department',
                )),
                ('jurisdiction', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='routing_rules',
                    to='routing.jurisdiction',
                )),
            ],
            options={
                'unique_together': {('ward', 'category')},
            },
        ),
    ]
