import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("departments", "0001_initial"),
        ("grievances", "0005_module8_tracking"),
    ]

    operations = [

        # ------------------------------------------------------------------
        # 1. SLAPolicy — defines the resolution time limit per priority.
        #    department=NULL means the policy is a system-wide default.
        #    is_active allows a policy to be retired without deletion.
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="SLAPolicy",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("LOW",      "Low"),
                            ("MEDIUM",   "Medium"),
                            ("HIGH",     "High"),
                            ("CRITICAL", "Critical"),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    "sla_hours",
                    models.PositiveIntegerField(
                        help_text="Hours from officer assignment to resolution deadline.",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "department",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sla_policies",
                        to="departments.department",
                        help_text="Leave blank for the system-wide default policy.",
                    ),
                ),
            ],
            options={
                "verbose_name": "SLA Policy",
                "verbose_name_plural": "SLA Policies",
                "ordering": ["department", "priority"],
            },
        ),

        # ------------------------------------------------------------------
        # 2. GrievanceSLA — runtime SLA record per assignment cycle.
        #    Created when assign_officer() runs; closed on resolution/closure;
        #    superseded on reopen.
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="GrievanceSLA",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                # Snapshot
                (
                    "sla_hours",
                    models.PositiveIntegerField(
                        help_text="Hours from started_at to due_at, copied from policy at creation.",
                    ),
                ),
                # Clock
                (
                    "started_at",
                    models.DateTimeField(
                        help_text="Timestamp when assign_officer() was called.",
                    ),
                ),
                (
                    "due_at",
                    models.DateTimeField(
                        help_text="Deadline: started_at + sla_hours.",
                    ),
                ),
                # Status
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE",           "Active"),
                            ("BREACHED",         "Breached"),
                            ("RESOLVED_ON_TIME", "Resolved On Time"),
                            ("RESOLVED_LATE",    "Resolved Late"),
                            ("CLOSED",           "Closed"),
                            ("SUPERSEDED",       "Superseded"),
                        ],
                        default="ACTIVE",
                        max_length=20,
                    ),
                ),
                ("breached_at",  models.DateTimeField(blank=True, null=True)),
                ("resolved_at",  models.DateTimeField(blank=True, null=True)),
                # Reminder flags
                ("reminder_50_sent", models.BooleanField(default=False)),
                ("reminder_75_sent", models.BooleanField(default=False)),
                ("reminder_90_sent", models.BooleanField(default=False)),
                # Escalation tracking
                ("escalation_level", models.PositiveSmallIntegerField(default=0)),
                ("l1_escalated_at",  models.DateTimeField(blank=True, null=True)),
                ("l2_escalated_at",  models.DateTimeField(blank=True, null=True)),
                ("l3_escalated_at",  models.DateTimeField(blank=True, null=True)),
                # Audit
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                # FKs
                (
                    "grievance",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sla_records",
                        to="grievances.grievance",
                    ),
                ),
                (
                    "policy",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sla_records",
                        to="sla.slapolicy",
                        help_text="Source policy. sla_hours is the authoritative snapshot.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Grievance SLA",
                "verbose_name_plural": "Grievance SLAs",
                "ordering": ["-created_at"],
            },
        ),

        # ------------------------------------------------------------------
        # 3. Indexes — support the Celery beat job queries.
        # ------------------------------------------------------------------
        migrations.AddIndex(
            model_name="grievancesla",
            index=models.Index(
                fields=["status", "due_at"],
                name="sla_active_due_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="grievancesla",
            index=models.Index(
                fields=["status", "escalation_level"],
                name="sla_breach_escalation_idx",
            ),
        ),
    ]
