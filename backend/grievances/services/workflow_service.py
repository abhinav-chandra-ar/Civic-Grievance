import logging

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from grievances.enums import GrievanceStatus
from grievances.models import GrievanceStatusLog

logger = logging.getLogger(__name__)

# Allowed next states for each current state.
VALID_TRANSITIONS = {
    GrievanceStatus.SUBMITTED: {
        GrievanceStatus.ASSIGNED,
        GrievanceStatus.REJECTED,
    },
    GrievanceStatus.ASSIGNED: {
        GrievanceStatus.IN_PROGRESS,
        GrievanceStatus.ESCALATED,
    },
    GrievanceStatus.IN_PROGRESS: {
        GrievanceStatus.PENDING_FIELD_VISIT,
        GrievanceStatus.RESOLVED,
        GrievanceStatus.ESCALATED,
    },
    GrievanceStatus.PENDING_FIELD_VISIT: {
        GrievanceStatus.IN_PROGRESS,
        GrievanceStatus.RESOLVED,
        GrievanceStatus.ESCALATED,
    },
    GrievanceStatus.RESOLVED: {
        GrievanceStatus.CLOSED,
        GrievanceStatus.REOPENED,
    },
    GrievanceStatus.REOPENED: {
        GrievanceStatus.ASSIGNED,
    },
    GrievanceStatus.ESCALATED: {
        GrievanceStatus.ASSIGNED,
    },
    GrievanceStatus.CLOSED: set(),
    GrievanceStatus.REJECTED: set(),
}

# Transitions that require SENIOR_OFFICER or ADMIN role.
SENIOR_ONLY_TRANSITIONS = {
    (GrievanceStatus.SUBMITTED, GrievanceStatus.REJECTED),
    (GrievanceStatus.RESOLVED, GrievanceStatus.CLOSED),
    (GrievanceStatus.IN_PROGRESS, GrievanceStatus.ESCALATED),
    (GrievanceStatus.PENDING_FIELD_VISIT, GrievanceStatus.ESCALATED),
    (GrievanceStatus.ASSIGNED, GrievanceStatus.ESCALATED),
}


def transition_status(grievance, new_status: str, changed_by) -> None:
    """
    Validate and apply a status transition.

    Raises ValidationError if:
    - new_status is not a valid next state from the current state
    - the transition requires senior/admin role and changed_by lacks it
    """
    current = grievance.status

    allowed = VALID_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise ValidationError(
            f"Cannot transition from {current} to {new_status}. "
            f"Allowed: {sorted(allowed) or 'none (terminal state)'}."
        )

    pair = (current, new_status)
    if pair in SENIOR_ONLY_TRANSITIONS:
        role = getattr(changed_by, "role", None)
        if role not in ("SENIOR_OFFICER", "ADMIN"):
            raise ValidationError(
                f"Transition {current} -> {new_status} requires Senior Officer or Admin role."
            )

    old_status = grievance.status
    now = timezone.now()

    # Apply new status and lifecycle timestamps.
    grievance.status = new_status
    grievance.last_status_change_at = now
    update_fields = ["status", "last_status_change_at"]

    if new_status == GrievanceStatus.RESOLVED:
        grievance.resolved_at = now
        update_fields.append("resolved_at")
    elif new_status == GrievanceStatus.CLOSED:
        grievance.closed_at = now
        update_fields.append("closed_at")

    grievance.save(update_fields=update_fields)

    GrievanceStatusLog.objects.create(
        grievance=grievance,
        from_status=old_status,
        to_status=new_status,
        changed_by=changed_by,
    )

    logger.info(
        "Grievance #%s status: %s -> %s (by %s)",
        grievance.id,
        old_status,
        new_status,
        changed_by,
    )

    # Module 8 hook — timeline event + citizen notification (non-fatal).
    from grievances.services.timeline_service import on_status_changed
    on_status_changed(grievance, new_status, changed_by)
