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


class TimelineEventType(models.TextChoices):
    SUBMITTED           = "SUBMITTED",           "Submitted"
    ASSIGNED            = "ASSIGNED",            "Assigned"
    REASSIGNED          = "REASSIGNED",          "Reassigned"
    IN_PROGRESS         = "IN_PROGRESS",         "In Progress"
    PENDING_FIELD_VISIT = "PENDING_FIELD_VISIT",  "Pending Field Visit"
    ESCALATED           = "ESCALATED",           "Escalated"
    RESOLVED            = "RESOLVED",            "Resolved"
    CLOSED              = "CLOSED",              "Closed"
    REOPENED            = "REOPENED",            "Reopened"
    REJECTED            = "REJECTED",            "Rejected"
    EVIDENCE_UPLOADED   = "EVIDENCE_UPLOADED",   "Evidence Uploaded"


class NotificationType(models.TextChoices):
    GRIEVANCE_SUBMITTED = "GRIEVANCE_SUBMITTED", "Grievance Submitted"
    OFFICER_ASSIGNED    = "OFFICER_ASSIGNED",    "Officer Assigned"
    STATUS_CHANGED      = "STATUS_CHANGED",      "Status Changed"
    ESCALATED           = "ESCALATED",           "Escalated"
    RESOLVED            = "RESOLVED",            "Resolved"
    CLOSED              = "CLOSED",              "Closed"
    REOPENED            = "REOPENED",            "Reopened"
    EVIDENCE_UPLOADED   = "EVIDENCE_UPLOADED",   "Evidence Uploaded"
