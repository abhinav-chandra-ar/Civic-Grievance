from django.conf import settings
from django.db import models

from grievances.enums import GrievancePriority


class SLAPolicy(models.Model):
    """
    Defines the SLA time limit (in hours) for a given priority level.

    A policy with department=NULL is the system-wide default.
    A policy with a department set overrides the default for that department.

    Only one policy should be active per (department, priority) pair.
    The sla_service enforces this at write time.
    """

    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sla_policies",
        help_text="Leave blank for the system-wide default policy.",
    )
    priority = models.CharField(
        max_length=10,
        choices=GrievancePriority.choices,
    )
    sla_hours = models.PositiveIntegerField(
        help_text="Hours from officer assignment to resolution deadline.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["department", "priority"]
        verbose_name = "SLA Policy"
        verbose_name_plural = "SLA Policies"

    def __str__(self):
        dept = self.department.name if self.department_id else "Default"
        return f"{dept} | {self.priority} | {self.sla_hours}h"


class GrievanceSLA(models.Model):
    """
    Runtime SLA record created when a grievance is assigned to an officer.

    One record per assignment cycle. When a grievance is reopened and
    reassigned, the old record is marked SUPERSEDED and a new one is
    created for the new cycle.

    The sla_hours field is snapshotted from the policy at creation time
    so that policy changes do not affect in-flight grievances.
    """

    class Status(models.TextChoices):
        ACTIVE           = "ACTIVE",           "Active"
        BREACHED         = "BREACHED",         "Breached"
        RESOLVED_ON_TIME = "RESOLVED_ON_TIME", "Resolved On Time"
        RESOLVED_LATE    = "RESOLVED_LATE",    "Resolved Late"
        CLOSED           = "CLOSED",           "Closed"
        SUPERSEDED       = "SUPERSEDED",       "Superseded"

    grievance = models.ForeignKey(
        "grievances.Grievance",
        on_delete=models.CASCADE,
        related_name="sla_records",
    )
    policy = models.ForeignKey(
        SLAPolicy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sla_records",
        help_text="Source policy. sla_hours is the authoritative snapshot.",
    )

    # ------------------------------------------------------------------
    # Snapshot — set once at creation, never modified.
    # ------------------------------------------------------------------
    sla_hours = models.PositiveIntegerField(
        help_text="Hours from started_at to due_at, copied from policy at creation.",
    )

    # ------------------------------------------------------------------
    # Clock — no pausing per approved architecture.
    # ------------------------------------------------------------------
    started_at = models.DateTimeField(
        help_text="Timestamp when assign_officer() was called.",
    )
    due_at = models.DateTimeField(
        help_text="Deadline: started_at + sla_hours.",
    )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    breached_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Reminder deduplication — prevents duplicate notifications.
    # ------------------------------------------------------------------
    reminder_50_sent = models.BooleanField(default=False)
    reminder_75_sent = models.BooleanField(default=False)
    reminder_90_sent = models.BooleanField(default=False)

    # ------------------------------------------------------------------
    # Escalation tracking.
    # 0 = no escalation yet
    # 1 = officer notified at breach
    # 2 = senior officer notified
    # 3 = department admin notified
    # ------------------------------------------------------------------
    escalation_level = models.PositiveSmallIntegerField(default=0)
    l1_escalated_at = models.DateTimeField(null=True, blank=True)
    l2_escalated_at = models.DateTimeField(null=True, blank=True)
    l3_escalated_at = models.DateTimeField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Grievance SLA"
        verbose_name_plural = "Grievance SLAs"
        indexes = [
            # Beat job: find active SLAs approaching or past their deadline.
            models.Index(fields=["status", "due_at"], name="sla_active_due_idx"),
            # Beat job: find breached SLAs pending escalation.
            models.Index(fields=["status", "escalation_level"], name="sla_breach_escalation_idx"),
        ]

    def __str__(self):
        return f"SLA#{self.id} Grievance#{self.grievance_id} [{self.status}]"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_breached(self):
        return self.status == self.Status.BREACHED
