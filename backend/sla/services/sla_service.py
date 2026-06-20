"""
SLA service — creation, closure, and supersede logic.

All public functions are non-fatal by design: they are called from
assignment_service and workflow_service inside try/except blocks, so
any exception here must never reach the caller.

Import strategy: all model/enum imports are deferred to function scope
to avoid circular imports at Django startup (same pattern as
grievances/services/timeline_service.py).
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Fallback SLA hours used when no SLAPolicy record exists in the database.
_DEFAULT_SLA_HOURS = {
    "CRITICAL": 24,
    "HIGH":     48,
    "MEDIUM":   72,
    "LOW":      120,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_sla_hours(department, priority):
    """
    Return (sla_hours, policy_or_None) for the given department + priority.

    Lookup order:
      1. Active SLAPolicy for this specific department + priority.
      2. Active system-default SLAPolicy (department=None) for this priority.
      3. SLA_DEFAULT_HOURS dict from settings (falls back to _DEFAULT_SLA_HOURS).
    """
    from sla.models import SLAPolicy

    # Department-specific policy.
    if department is not None:
        policy = SLAPolicy.objects.filter(
            department=department,
            priority=priority,
            is_active=True,
        ).first()
        if policy:
            return policy.sla_hours, policy

    # System-default policy.
    policy = SLAPolicy.objects.filter(
        department__isnull=True,
        priority=priority,
        is_active=True,
    ).first()
    if policy:
        return policy.sla_hours, policy

    # Hard-coded fallback.
    defaults = getattr(settings, "SLA_DEFAULT_HOURS", _DEFAULT_SLA_HOURS)
    sla_hours = defaults.get(priority, 72)
    logger.warning(
        "No SLAPolicy found for priority=%s department=%s — falling back to %dh",
        priority,
        getattr(department, "id", None),
        sla_hours,
    )
    return sla_hours, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_grievance_sla(grievance) -> None:
    """
    Create a GrievanceSLA for the given grievance.

    Called at the end of assign_officer() after every successful assignment.

    Guards:
    - If an ACTIVE or BREACHED SLA already exists for this grievance, skip
      creation. This handles the ESCALATED → ASSIGNED re-assignment case
      where the SLA clock must continue running, not reset.
    """
    from sla.models import GrievanceSLA

    # Guard: do not reset a running SLA.
    if GrievanceSLA.objects.filter(
        grievance=grievance,
        status__in=[GrievanceSLA.Status.ACTIVE, GrievanceSLA.Status.BREACHED],
    ).exists():
        logger.debug(
            "Grievance #%s already has a running SLA — skipping creation.",
            grievance.id,
        )
        return

    sla_hours, policy = _get_sla_hours(grievance.department, grievance.priority)
    now = timezone.now()
    due_at = now + timedelta(hours=sla_hours)

    GrievanceSLA.objects.create(
        grievance=grievance,
        policy=policy,
        sla_hours=sla_hours,
        started_at=now,
        due_at=due_at,
        status=GrievanceSLA.Status.ACTIVE,
    )

    logger.info(
        "GrievanceSLA created for Grievance #%s | priority=%s | %dh | due=%s",
        grievance.id,
        grievance.priority,
        sla_hours,
        due_at.strftime("%Y-%m-%d %H:%M UTC"),
    )


def close_grievance_sla(grievance, new_status: str) -> None:
    """
    Close the active SLA when a grievance reaches a terminal-resolution state.

    Called from transition_status() for: RESOLVED, CLOSED, REJECTED.

    - RESOLVED before due_at  → RESOLVED_ON_TIME
    - RESOLVED after  due_at  → RESOLVED_LATE
    - CLOSED or REJECTED      → CLOSED  (administrative / dismissed)

    If no active SLA exists the call is a no-op (grievance may have been
    assigned before Module 9 was deployed).
    """
    from sla.models import GrievanceSLA
    from grievances.enums import GrievanceStatus

    sla = GrievanceSLA.objects.filter(
        grievance=grievance,
        status__in=[GrievanceSLA.Status.ACTIVE, GrievanceSLA.Status.BREACHED],
    ).first()

    if sla is None:
        return

    now = timezone.now()
    update_fields = ["status", "updated_at"]

    if new_status == GrievanceStatus.RESOLVED:
        if now <= sla.due_at:
            sla.status = GrievanceSLA.Status.RESOLVED_ON_TIME
        else:
            sla.status = GrievanceSLA.Status.RESOLVED_LATE
        sla.resolved_at = now
        update_fields.append("resolved_at")
    else:
        # CLOSED or REJECTED — administrative end, no resolution timestamp.
        sla.status = GrievanceSLA.Status.CLOSED

    sla.save(update_fields=update_fields)

    logger.info(
        "GrievanceSLA #%s closed as %s for Grievance #%s",
        sla.id,
        sla.status,
        grievance.id,
    )


def supersede_grievance_sla(grievance) -> None:
    """
    Supersede any active/breached SLA when a grievance is reopened.

    Called from transition_status() for: REOPENED.

    In the normal flow the SLA is already CLOSED (via close_grievance_sla on
    RESOLVED) before REOPENED is reached. This function is therefore a
    defensive safety net — it handles edge cases where an active SLA exists
    at reopen time and logs a warning so the anomaly is visible.

    The new SLA for the next resolution cycle is created by the next
    assign_officer() call.
    """
    from sla.models import GrievanceSLA

    updated = GrievanceSLA.objects.filter(
        grievance=grievance,
        status__in=[GrievanceSLA.Status.ACTIVE, GrievanceSLA.Status.BREACHED],
    ).update(status=GrievanceSLA.Status.SUPERSEDED)

    if updated:
        logger.warning(
            "GrievanceSLA superseded for Grievance #%s on REOPENED — "
            "an active SLA was found when none was expected.",
            grievance.id,
        )
