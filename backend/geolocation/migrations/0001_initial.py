import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('grievances', '0004_module6_officer_assignment'),
        ('routing', '0002_ward_boundary'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeolocationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submitted_lat', models.DecimalField(
                    decimal_places=6,
                    max_digits=9,
                    help_text="Raw latitude submitted by the citizen's device.",
                )),
                ('submitted_lng', models.DecimalField(
                    decimal_places=6,
                    max_digits=9,
                    help_text="Raw longitude submitted by the citizen's device.",
                )),
                ('detection_method', models.CharField(
                    choices=[
                        ('GPS_AUTO', 'GPS Auto-Detected'),
                        ('MANUAL_FALLBACK', 'Manual Ward Selection'),
                    ],
                    max_length=20,
                )),
                ('accuracy_meters', models.FloatField(
                    blank=True,
                    null=True,
                    help_text='Device-reported GPS accuracy radius in metres, if provided.',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('detected_ward', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='geolocation_logs',
                    to='routing.ward',
                    help_text='Ward found by point-in-polygon lookup. Null if coordinates were outside all boundaries.',
                )),
                ('grievance', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='geolocation_log',
                    to='grievances.grievance',
                )),
            ],
            options={
                'verbose_name': 'Geolocation Log',
                'verbose_name_plural': 'Geolocation Logs',
            },
        ),
    ]
