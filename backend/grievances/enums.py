from django.db import models


class GrievanceStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    ASSIGNED = "ASSIGNED", "Assigned"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    PENDING_FIELD_VISIT = "PENDING_FIELD_VISIT", "Pending Field Visit"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"
    REOPENED = "REOPENED", "Reopened"
    ESCALATED = "ESCALATED", "Escalated"
    REJECTED = "REJECTED", "Rejected"


class GrievancePriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"
