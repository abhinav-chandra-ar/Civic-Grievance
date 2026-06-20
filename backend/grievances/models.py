from django.db import models

# Create your models here.
from django.conf import settings

from departments.models import Department
from .enums import GrievanceStatus, GrievancePriority


class Grievance(models.Model):

    citizen = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="grievances"
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grievances"
    )

    # Routing fields (ward set by citizen; jurisdiction resolved by routing service)

    ward = models.ForeignKey(
        "routing.Ward",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grievances"
    )

    jurisdiction = models.ForeignKey(
        "routing.Jurisdiction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grievances"
    )

    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_grievances"
    )

    # Raw Submission

    raw_text = models.TextField()

    image = models.ImageField(
        upload_to="grievances/images/",
        null=True,
        blank=True
    )

    location_manual_note = models.TextField(
        blank=True
    )

    # ML Output (filled later)

    ml_translated_text = models.TextField(blank=True)

    ml_summary = models.TextField(blank=True)

    ml_department_suggestion = models.CharField(
        max_length=50,
        blank=True
    )

    ml_priority_suggestion = models.CharField(
        max_length=20,
        blank=True
    )

    ml_is_spam = models.BooleanField(
        null=True,
        blank=True
    )

    ml_is_duplicate = models.BooleanField(
        null=True,
        blank=True
    )

    ml_duplicate_type = models.CharField(
        max_length=10,
        blank=True
    )

    ml_image_valid = models.BooleanField(
        null=True,
        blank=True
    )

    ml_location_extracted = models.TextField(
        blank=True
    )

    ml_processed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Status

    status = models.CharField(
        max_length=20,
        choices=GrievanceStatus.choices,
        default=GrievanceStatus.SUBMITTED
    )

    priority = models.CharField(
        max_length=20,
        choices=GrievancePriority.choices,
        default=GrievancePriority.MEDIUM
    )

    # Resolution

    resolution_note = models.TextField(
        blank=True
    )

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_grievances"
    )

    # Reopen Tracking

    reopen_count = models.PositiveIntegerField(
        default=0
    )

    last_reopened_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # SLA Tracking

    assigned_at = models.DateTimeField(
        null=True,
        blank=True
    )

    escalated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Timestamps

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Grievance #{self.id}"


class GrievanceStatusLog(models.Model):
    """Track status changes for grievances"""
    
    grievance = models.ForeignKey(
        Grievance,
        on_delete=models.CASCADE,
        related_name="status_logs"
    )
    
    from_status = models.CharField(
        max_length=20,
        choices=GrievanceStatus.choices
    )
    
    to_status = models.CharField(
        max_length=20,
        choices=GrievanceStatus.choices
    )
    
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_changes"
    )
    
    changed_at = models.DateTimeField(
        auto_now_add=True
    )
    
    def __str__(self):
        return f"Grievance #{self.grievance.id}: {self.from_status} -> {self.to_status}"


class OfficerAssignment(models.Model):
    """Active assignment linking a grievance to the officer currently responsible."""

    grievance = models.OneToOneField(
        Grievance,
        on_delete=models.CASCADE,
        related_name="assignment",
    )
    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="officer_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"Grievance #{self.grievance_id} -> {self.assigned_officer}"


class AssignmentHistory(models.Model):
    """Audit trail of every officer assignment and reassignment."""

    grievance = models.ForeignKey(
        Grievance,
        on_delete=models.CASCADE,
        related_name="assignment_history",
    )
    from_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assignments_from",
    )
    to_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignments_to",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assignment_changes_made",
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Grievance #{self.grievance_id} reassigned to {self.to_officer}"


class OfficerNote(models.Model):
    """Internal notes visible only to officers — never exposed to citizens."""

    grievance = models.ForeignKey(
        Grievance,
        on_delete=models.CASCADE,
        related_name="officer_notes",
    )
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="officer_notes",
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note on Grievance #{self.grievance_id} by {self.officer}"


class ResolutionEvidence(models.Model):
    """Photo evidence uploaded by officers to prove a grievance was resolved."""

    grievance = models.ForeignKey(
        Grievance,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_evidence",
    )
    image = models.ImageField(upload_to="resolution_evidence/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidence for Grievance #{self.grievance_id}"