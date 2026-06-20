"""
grievances/services/timeline_service.py

Central hub for all Module 8 timeline and notification writes.
Every public function is intentionally non-fatal: exceptions are logged
but never re-raised, so a failure here cannot roll back the caller's
primary database operation (status transition, assignment, etc.).

Public surface consumed by other services:
    on_grievance_submitted(grievance)          ← CreateGrievanceView (Phase 3)
    on_status_changed(grievance, new_status, changed_by)  ← workflow_service
    on_officer_assigned(grievance, officer, assigned_by)  ← assignment_service
    on_officer_reassigned(grievance, to_officer, changed_by) ← assignment_service
    on_evidence_uploaded(grievance, uploaded_by)           ← Phase 3 view

Primitive writers (also importable for one-off use, e.g. reopen view):
    create_timeline_event(grievance, event_type, description, created_by)
    create_notification(user, grievance, notification_type, title, message)
"""

import logging

from grievances.enums import GrievanceStatus, TimelineEventType, NotificationType
from grievances.models import GrievanceTimelineEvent, Notification

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

# Maps GrievanceStatus → TimelineEventType for on_status_changed.
# SUBMITTED is excluded: it is emitted by on_grievance_submitted, not by
# transition_status (which only handles changes FROM an existing status).
_STATUS_TO_EVENT: dict[str, str] = {
    GrievanceStatus.ASSIGNED:            TimelineEventType.ASSIGNED,
    GrievanceStatus.IN_PROGRESS:         TimelineEventType.IN_PROGRESS,
    GrievanceStatus.PENDING_FIELD_VISIT: TimelineEventType.PENDING_FIELD_VISIT,
    GrievanceStatus.ESCALATED:           TimelineEventType.ESCALATED,
    GrievanceStatus.RESOLVED:            TimelineEventType.RESOLVED,
    GrievanceStatus.CLOSED:              TimelineEventType.CLOSED,
    GrievanceStatus.REOPENED:            TimelineEventType.REOPENED,
    GrievanceStatus.REJECTED:            TimelineEventType.REJECTED,
}

# Maps GrievanceStatus → NotificationType for the citizen notification.
_STATUS_TO_NOTIFICATION_TYPE: dict[str, str] = {
    GrievanceStatus.ASSIGNED:            NotificationType.OFFICER_ASSIGNED,
    GrievanceStatus.IN_PROGRESS:         NotificationType.STATUS_CHANGED,
    GrievanceStatus.PENDING_FIELD_VISIT: NotificationType.STATUS_CHANGED,
    GrievanceStatus.ESCALATED:           NotificationType.ESCALATED,
    GrievanceStatus.RESOLVED:            NotificationType.RESOLVED,
    GrievanceStatus.CLOSED:              NotificationType.CLOSED,
    GrievanceStatus.REOPENED:            NotificationType.REOPENED,
    GrievanceStatus.REJECTED:            NotificationType.STATUS_CHANGED,
}

# Short notification titles for the citizen per status.
_STATUS_TO_TITLE: dict[str, str] = {
    GrievanceStatus.ASSIGNED:            "Officer Assigned",
    GrievanceStatus.IN_PROGRESS:         "Work In Progress",
    GrievanceStatus.PENDING_FIELD_VISIT: "Field Visit Scheduled",
    GrievanceStatus.ESCALATED:           "Grievance Escalated",
    GrievanceStatus.RESOLVED:            "Grievance Resolved",
    GrievanceStatus.CLOSED:              "Grievance Closed",
    GrievanceStatus.REOPENED:            "Grievance Reopened",
    GrievanceStatus.REJECTED:            "Grievance Rejected",
}

# Citizen notification message templates.  {id} is replaced at call time.
_STATUS_TO_MESSAGE: dict[str, str] = {
    GrievanceStatus.ASSIGNED: (
        "Your grievance #{id} has been assigned to an officer."
    ),
    GrievanceStatus.IN_PROGRESS: (
        "An officer has started working on your grievance #{id}."
    ),
    GrievanceStatus.PENDING_FIELD_VISIT: (
        "A field visit has been scheduled for your grievance #{id}."
    ),
    GrievanceStatus.ESCALATED: (
        "Your grievance #{id} has been escalated for senior review."
    ),
    GrievanceStatus.RESOLVED: (
        "Your grievance #{id} has been marked as resolved. "
        "If the issue persists you may reopen it within 7 days."
    ),
    GrievanceStatus.CLOSED: (
        "Your grievance #{id} has been closed."
    ),
    GrievanceStatus.REOPENED: (
        "Your grievance #{id} has been reopened and is being addressed again."
    ),
    GrievanceStatus.REJECTED: (
        "Your grievance #{id} has been rejected."
    ),
}

# SLA hours by priority — used by Phase 3 detail serializer.
SLA_HOURS: dict[str, int] = {
    "CRITICAL": 24,
    "HIGH":     48,
    "MEDIUM":   72,
    "LOW":      120,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _actor_name(user) -> str:
    """Return a displayable name for any user object (or None)."""
    if user is None:
        return "System"
    return getattr(user, "full_name", None) or str(user)


def _build_event_description(new_status: str, grievance, changed_by) -> str:
    """Return a human-readable description for a status-change timeline event."""
    gid   = grievance.id
    actor = _actor_name(changed_by)

    templates: dict[str, str] = {
        GrievanceStatus.ASSIGNED: (
            f"Grievance #{gid} assigned to "
            f"{_actor_name(getattr(grievance, 'assigned_officer', None))} by {actor}."
        ),
        GrievanceStatus.IN_PROGRESS:         f"Work started on grievance #{gid} by {actor}.",
        GrievanceStatus.PENDING_FIELD_VISIT:  f"Field visit requested for grievance #{gid} by {actor}.",
        GrievanceStatus.ESCALATED:            f"Grievance #{gid} escalated by {actor}.",
        GrievanceStatus.RESOLVED:             f"Grievance #{gid} marked as resolved by {actor}.",
        GrievanceStatus.CLOSED:               f"Grievance #{gid} closed by {actor}.",
        GrievanceStatus.REOPENED:             f"Grievance #{gid} reopened by {actor}.",
        GrievanceStatus.REJECTED:             f"Grievance #{gid} rejected by {actor}.",
    }
    return templates.get(
        new_status,
        f"Grievance #{gid} status changed to {new_status} by {actor}.",
    )


# ---------------------------------------------------------------------------
# Primitive writers
# ---------------------------------------------------------------------------

def create_timeline_event(grievance, event_type: str, description: str, created_by=None):
    """
    Persist a GrievanceTimelineEvent and return it, or None on failure.
    Non-fatal: the caller's transaction is not affected if this fails.
    """
    try:
        return GrievanceTimelineEvent.objects.create(
            grievance=grievance,
            event_type=event_type,
            description=description,
            created_by=created_by,
        )
    except Exception:
        logger.exception(
            "Failed to create timeline event '%s' for grievance #%s",
            event_type, getattr(grievance, "id", "?"),
        )
        return None


def create_notification(user, grievance, notification_type: str, title: str, message: str):
    """
    Persist a Notification and return it, or None on failure.
    Non-fatal: the caller's transaction is not affected if this fails.
    """
    try:
        return Notification.objects.create(
            user=user,
            grievance=grievance,
            notification_type=notification_type,
            title=title,
            message=message,
        )
    except Exception:
        logger.exception(
            "Failed to create notification '%s' for user #%s grievance #%s",
            notification_type,
            getattr(user, "id", "?"),
            getattr(grievance, "id", "?"),
        )
        return None


# ---------------------------------------------------------------------------
# Composite event hooks (called by services)
# ---------------------------------------------------------------------------

def on_grievance_submitted(grievance) -> None:
    """
    Call immediately after a new grievance is saved for the first time.
    Emits the SUBMITTED timeline event and notifies the citizen.
    Invoked from CreateGrievanceView.perform_create (Phase 3).
    """
    create_timeline_event(
        grievance=grievance,
        event_type=TimelineEventType.SUBMITTED,
        description=f"Grievance #{grievance.id} submitted by {_actor_name(grievance.citizen)}.",
        created_by=grievance.citizen,
    )
    create_notification(
        user=grievance.citizen,
        grievance=grievance,
        notification_type=NotificationType.GRIEVANCE_SUBMITTED,
        title="Grievance Submitted",
        message=f"Your grievance #{grievance.id} has been received and is under review.",
    )
    logger.debug("Module 8: SUBMITTED timeline + notification written for grievance #%s", grievance.id)


def on_status_changed(grievance, new_status: str, changed_by) -> None:
    """
    Called by workflow_service.transition_status after every successful
    status transition.  Writes a timeline event and a citizen notification.
    SUBMITTED status is NOT handled here — use on_grievance_submitted.
    """
    event_type = _STATUS_TO_EVENT.get(new_status)
    if event_type is None:
        logger.warning(
            "Module 8: on_status_changed received unrecognised status '%s' "
            "for grievance #%s — skipping timeline write.",
            new_status, grievance.id,
        )
        return

    # --- Timeline event ---
    create_timeline_event(
        grievance=grievance,
        event_type=event_type,
        description=_build_event_description(new_status, grievance, changed_by),
        created_by=changed_by,
    )

    # --- Citizen notification ---
    notif_type = _STATUS_TO_NOTIFICATION_TYPE.get(new_status)
    if notif_type:
        create_notification(
            user=grievance.citizen,
            grievance=grievance,
            notification_type=notif_type,
            title=_STATUS_TO_TITLE.get(new_status, "Grievance Update"),
            message=_STATUS_TO_MESSAGE.get(
                new_status,
                f"Your grievance #{grievance.id} has been updated.",
            ).format(id=grievance.id),
        )

    logger.debug(
        "Module 8: %s timeline event + citizen notification written for grievance #%s",
        new_status, grievance.id,
    )


def on_officer_assigned(grievance, officer, assigned_by) -> None:
    """
    Called by assignment_service.assign_officer after transition_status(ASSIGNED)
    has already fired.  The ASSIGNED timeline event and citizen notification are
    already written by on_status_changed; this function creates only the
    officer-facing notification so they know a case was assigned to them.
    """
    create_notification(
        user=officer,
        grievance=grievance,
        notification_type=NotificationType.OFFICER_ASSIGNED,
        title="New Grievance Assigned",
        message=f"Grievance #{grievance.id} has been assigned to you.",
    )
    logger.debug(
        "Module 8: officer assignment notification written for grievance #%s → officer #%s",
        grievance.id, officer.id,
    )


def on_officer_reassigned(grievance, to_officer, changed_by) -> None:
    """
    Called by assignment_service.reassign_officer.
    Reassignment does NOT pass through transition_status, so this function
    is responsible for both the REASSIGNED timeline event and both
    citizen + incoming-officer notifications.
    """
    # --- Timeline event ---
    create_timeline_event(
        grievance=grievance,
        event_type=TimelineEventType.REASSIGNED,
        description=(
            f"Grievance #{grievance.id} reassigned to "
            f"{_actor_name(to_officer)} by {_actor_name(changed_by)}."
        ),
        created_by=changed_by,
    )

    # --- Citizen notification ---
    create_notification(
        user=grievance.citizen,
        grievance=grievance,
        notification_type=NotificationType.STATUS_CHANGED,
        title="Officer Reassigned",
        message=f"Your grievance #{grievance.id} has been reassigned to a new officer.",
    )

    # --- Incoming officer notification ---
    create_notification(
        user=to_officer,
        grievance=grievance,
        notification_type=NotificationType.OFFICER_ASSIGNED,
        title="New Grievance Assigned",
        message=f"Grievance #{grievance.id} has been reassigned to you.",
    )
    logger.debug(
        "Module 8: REASSIGNED timeline + notifications written for grievance #%s → officer #%s",
        grievance.id, to_officer.id,
    )


def on_evidence_uploaded(grievance, uploaded_by) -> None:
    """
    Called by the ResolutionEvidenceListCreateView (Phase 3) after evidence
    is saved.  Writes an EVIDENCE_UPLOADED timeline event and notifies the citizen.
    """
    create_timeline_event(
        grievance=grievance,
        event_type=TimelineEventType.EVIDENCE_UPLOADED,
        description=(
            f"Resolution evidence uploaded for grievance #{grievance.id} "
            f"by {_actor_name(uploaded_by)}."
        ),
        created_by=uploaded_by,
    )
    create_notification(
        user=grievance.citizen,
        grievance=grievance,
        notification_type=NotificationType.EVIDENCE_UPLOADED,
        title="Resolution Evidence Uploaded",
        message=(
            f"An officer has uploaded resolution evidence for your grievance #{grievance.id}. "
            "You can view it in the grievance detail."
        ),
    )
    logger.debug(
        "Module 8: EVIDENCE_UPLOADED timeline + notification written for grievance #%s",
        grievance.id,
    )
