import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


_NEW_STATUS_CHOICES = [
    ('SUBMITTED', 'Submitted'),
    ('ASSIGNED', 'Assigned'),
    ('IN_PROGRESS', 'In Progress'),
    ('PENDING_FIELD_VISIT', 'Pending Field Visit'),
    ('RESOLVED', 'Resolved'),
    ('CLOSED', 'Closed'),
    ('REOPENED', 'Reopened'),
    ('ESCALATED', 'Escalated'),
    ('REJECTED', 'Rejected'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('grievances', '0003_grievance_routing_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Update status choices on Grievance and GrievanceStatusLog ---
        migrations.AlterField(
            model_name='grievance',
            name='status',
            field=models.CharField(
                choices=_NEW_STATUS_CHOICES,
                default='SUBMITTED',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='grievancestatuslog',
            name='from_status',
            field=models.CharField(choices=_NEW_STATUS_CHOICES, max_length=20),
        ),
        migrations.AlterField(
            model_name='grievancestatuslog',
            name='to_status',
            field=models.CharField(choices=_NEW_STATUS_CHOICES, max_length=20),
        ),

        # --- OfficerAssignment ---
        migrations.CreateModel(
            name='OfficerAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('active', models.BooleanField(default=True)),
                ('grievance', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='assignment',
                    to='grievances.grievance',
                )),
                ('assigned_officer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='officer_assignments',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('assigned_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_assignments',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),

        # --- AssignmentHistory ---
        migrations.CreateModel(
            name='AssignmentHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('remarks', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('grievance', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='assignment_history',
                    to='grievances.grievance',
                )),
                ('from_officer', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='assignments_from',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('to_officer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='assignments_to',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('changed_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='assignment_changes_made',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),

        # --- OfficerNote ---
        migrations.CreateModel(
            name='OfficerNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('grievance', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='officer_notes',
                    to='grievances.grievance',
                )),
                ('officer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='officer_notes',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),

        # --- ResolutionEvidence ---
        migrations.CreateModel(
            name='ResolutionEvidence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='resolution_evidence/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('grievance', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='evidence',
                    to='grievances.grievance',
                )),
                ('uploaded_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='uploaded_evidence',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
