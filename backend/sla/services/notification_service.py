"""
SLA notification and timeline write service.

Called by the process_sla management command (and by the Celery beat task
in Phase 4). Builds on the primitive create_notification and
create_timeline_event writers from grievances/services/timeline_service.py.

Design rules:
- All public functions are non-fatal: they log and return False on failure.
- Reminders create a Notification only (not a timeline event) because they
  are officer-facing operational alerts, not citizen-visible lifecycle events.
- Breach and escalation create both a Notification AND a timeline event
  because they are lifecycle milestones visible on the grievance history.
- User lookups (senior officer, dept admin) return None silently when no
  match exists; the caller decides whether to log a warning.
"""

import logging

from grievances.enums import NotificationType, TimelineEventType
from grievances.services.timeline_service import create_notification, create_timeline_event

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_user_by_role(department, role: str):
    """
    Return the first active user with the given role in the given department.
    Returns None if no match or department is None.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if department is None:
        return None
    return (
        User.objects
        .filter(role=role, department=department, is_active=True)
        .first()
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_sla_reminder(sla, pct: int) -> bool:
    """
    Notify the assigned officer that pct% of the SLA window has elapsed.

    Creates a Notification only — reminders are internal officer alerts,
    not citizen-visible lifecycle events, so no timeline event is written.

    Returns True if the notification was written, False otherwise.
    """
    officer = sla.grievance.assigned_officer
    if officer is None:
        logger.warning(
            "SLA#%s Grievance#%s: no assigned officer -- skipping %d%% reminder",
            sla.id, sla.grievance_id, pct,
        )
        return False

    grievance = sla.grievance
    notification = create_notification(
        user=officer,
        grievance=grievance,
        notification_type=NotificationType.SLA_REMINDER,
        title=f"SLA Reminder ({pct}%) -- Grievance #{grievance.id}",
        message=(
            f"Grievance #{grievance.id} ({grievance.priority} priority) has used "
            f"{pct}% of its {sla.sla_hours}h SLA window. "
            f"Deadline: {sla.due_at.strftime('%Y-%m-%d %H:%M')} UTC."
        ),
    )
    return notification is not None


def send_sla_breach(sla) -> bool:
    """
    Notify the assigned officer of an SLA breach and write a timeline event.

    The timeline event is citizen-visible: it marks the breach milestone on
    the grievance history. The officer notification is an urgent action prompt.

    Returns True if all writes succeeded (False if any write failed, but does
    not raise -- a partial failure is logged and processing continues).
    """
    grievance = sla.grievance
    officer = grievance.assigned_officer

    notif_ok = True
    if officer is not None:
        notification = create_notification(
            user=officer,
            grievance=grievance,
            notification_type=NotificationType.SLA_BREACHED,
            title=f"SLA Breached -- Grievance #{grievance.id}",
            message=(
                f"Grievance #{grievance.id} ({grievance.priority} priority) has exceeded "
                f"its {sla.sla_hours}h SLA deadline. Immediate action is required."
            ),
        )
        notif_ok = notification is not None
    else:
        logger.warning(
            "SLA#%s Grievance#%s: no assigned officer -- breach officer notification skipped",
            sla.id, sla.grievance_id,
        )

    event = create_timeline_event(
        grievance=grievance,
        event_type=TimelineEventType.SLA_BREACHED,
        description=(
            f"SLA deadline breached for grievance #{grievance.id}. "
            f"The {sla.sla_hours}h resolution window has elapsed."
        ),
        created_by=None,
    )

    return notif_ok and (event is not None)


def send_sla_escalation(sla, level: int) -> bool:
    """
    Send an escalation notification and write a timeline event.

    level=2: notify the first active SENIOR_OFFICER in the grievance's department.
    level=3: notify the first active ADMIN in the grievance's department.

    Returns True if a recipient was found and the notification was written.
    Returns False (without raising) if no recipient is found or writes fail.
    """
    if level not in (2, 3):
        logger.error("send_sla_escalation: invalid level %s for SLA#%s", level, sla.id)
        return False

    grievance = sla.grievance
    department = grievance.department

    role = "SENIOR_OFFICER" if level == 2 else "ADMIN"
    role_label = "Senior Officer" if level == 2 else "Department Admin"
    recipient = _find_user_by_role(department, role)

    if recipient is None:
        logger.warning(
            "SLA#%s Grievance#%s: no active %s in department#%s -- L%s escalation skipped",
            sla.id,
            sla.grievance_id,
            role_label,
            getattr(department, "id", None),
            level,
        )
        return False

    from django.utils import timezone
    hours_since_breach = 0.0
    if sla.breached_at:
        hours_since_breach = round(
            (timezone.now() - sla.breached_at).total_seconds() / 3600, 1
        )

    officer_name = (
        getattr(grievance.assigned_officer, "full_name", None)
        or "Unassigned"
    )

    notification = create_notification(
        user=recipient,
        grievance=grievance,
        notification_type=NotificationType.SLA_ESCALATED,
        title=f"SLA Escalation L{level} -- Grievance #{grievance.id}",
        message=(
            f"Grievance #{grievance.id} ({grievance.priority} priority) has been in breach "
            f"for {hours_since_breach}h. Assigned officer: {officer_name}. "
            f"Escalated to {role_label} ({recipient.full_name}) for review."
        ),
    )

    event = create_timeline_event(
        grievance=grievance,
        event_type=TimelineEventType.SLA_ESCALATED,
        description=(
            f"SLA escalation L{level}: grievance #{grievance.id} has been in breach for "
            f"{hours_since_breach}h. {role_label} ({recipient.full_name}) notified."
        ),
        created_by=None,
    )

    return (notification is not None) and (event is not None)
