import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grievances', '0004_module6_officer_assignment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ------------------------------------------------------------------
        # 1. Extend Grievance with three nullable SLA/lifecycle timestamps.
        #    All three are null=True so no default is required and no
        #    existing row is affected.
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name='grievance',
            name='resolved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='grievance',
            name='closed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='grievance',
            name='last_status_change_at',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # ------------------------------------------------------------------
        # 2. Extend ResolutionEvidence with before/after images and notes.
        #    before_image / after_image are nullable so the existing image
        #    workflow (Module 6) is untouched.
        #    resolution_notes defaults to blank — no data migration needed.
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name='resolutionevidence',
            name='before_image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='resolution_evidence/before/',
            ),
        ),
        migrations.AddField(
            model_name='resolutionevidence',
            name='after_image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='resolution_evidence/after/',
            ),
        ),
        migrations.AddField(
            model_name='resolutionevidence',
            name='resolution_notes',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),

        # ------------------------------------------------------------------
        # 3. GrievanceTimelineEvent — new table.
        #    Records every notable lifecycle event in insertion order.
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name='GrievanceTimelineEvent',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                )),
                ('event_type', models.CharField(
                    choices=[
                        ('SUBMITTED',           'Submitted'),
                        ('ASSIGNED',            'Assigned'),
                        ('REASSIGNED',          'Reassigned'),
                        ('IN_PROGRESS',         'In Progress'),
                        ('PENDING_FIELD_VISIT', 'Pending Field Visit'),
                        ('ESCALATED',           'Escalated'),
                        ('RESOLVED',            'Resolved'),
                        ('CLOSED',              'Closed'),
                        ('REOPENED',            'Reopened'),
                        ('REJECTED',            'Rejected'),
                        ('EVIDENCE_UPLOADED',   'Evidence Uploaded'),
                    ],
                    max_length=30,
                )),
                ('description', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('grievance', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='timeline',
                    to='grievances.grievance',
                )),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='timeline_events_created',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),

        # ------------------------------------------------------------------
        # 4. Notification — new table.
        #    Per-user, per-grievance notification with read tracking.
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                )),
                ('notification_type', models.CharField(
                    choices=[
                        ('GRIEVANCE_SUBMITTED', 'Grievance Submitted'),
                        ('OFFICER_ASSIGNED',    'Officer Assigned'),
                        ('STATUS_CHANGED',      'Status Changed'),
                        ('ESCALATED',           'Escalated'),
                        ('RESOLVED',            'Resolved'),
                        ('CLOSED',              'Closed'),
                        ('REOPENED',            'Reopened'),
                        ('EVIDENCE_UPLOADED',   'Evidence Uploaded'),
                    ],
                    max_length=30,
                )),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notifications',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('grievance', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notifications',
                    to='grievances.grievance',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),

        # ------------------------------------------------------------------
        # 5. ReopenRequest — new table.
        #    Stores citizen reopen submissions with optional photo evidence.
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name='ReopenRequest',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                )),
                ('reason', models.TextField()),
                ('photo', models.ImageField(
                    blank=True,
                    null=True,
                    upload_to='reopen_requests/',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('grievance', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='reopen_requests',
                    to='grievances.grievance',
                )),
                ('requested_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reopen_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
