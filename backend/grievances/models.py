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
        return f"Grievance #{self.grievance.id}: {self.from_status} → {self.to_status}"