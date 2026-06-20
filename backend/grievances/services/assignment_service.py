import logging

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from grievances.enums import GrievanceStatus
from grievances.models import AssignmentHistory, OfficerAssignment
from grievances.services.workflow_service import transition_status

logger = logging.getLogger(__name__)


def _validate_department(officer, grievance) -> None:
    """Raise ValidationError if officer does not belong to the grievance's department."""
    if officer.department_id is None or officer.department_id != grievance.department_id:
        raise ValidationError(
            "Officer does not belong to the department responsible for this grievance."
        )


def assign_officer(grievance, officer, assigned_by) -> None:
    """
    Assign an officer to a grievance for the first time.

    Raises ValidationError if the officer's department does not match
    the grievance's routed department.
    """
    _validate_department(officer, grievance)

    OfficerAssignment.objects.create(
        grievance=grievance,
        assigned_officer=officer,
        assigned_by=assigned_by,
        active=True,
    )

    AssignmentHistory.objects.create(
        grievance=grievance,
        from_officer=None,
        to_officer=officer,
        changed_by=assigned_by,
    )

    grievance.assigned_officer = officer
    grievance.assigned_at = timezone.now()
    grievance.save(update_fields=["assigned_officer", "assigned_at"])

    transition_status(grievance, GrievanceStatus.ASSIGNED, changed_by=assigned_by)

    logger.info(
        "Grievance #%s assigned to %s by %s",
        grievance.id, officer, assigned_by,
    )


def reassign_officer(grievance, to_officer, changed_by, remarks: str = "") -> None:
    """
    Reassign a grievance to a different officer.

    Raises ValidationError if the new officer's department does not match
    the grievance's routed department.
    """
    _validate_department(to_officer, grievance)

    from_officer = None

    try:
        current = OfficerAssignment.objects.get(grievance=grievance)
        from_officer = current.assigned_officer
        current.assigned_officer = to_officer
        current.assigned_by = changed_by
        current.save(update_fields=["assigned_officer", "assigned_by"])
    except OfficerAssignment.DoesNotExist:
        OfficerAssignment.objects.create(
            grievance=grievance,
            assigned_officer=to_officer,
            assigned_by=changed_by,
            active=True,
        )

    AssignmentHistory.objects.create(
        grievance=grievance,
        from_officer=from_officer,
        to_officer=to_officer,
        changed_by=changed_by,
        remarks=remarks,
    )

    grievance.assigned_officer = to_officer
    grievance.assigned_at = timezone.now()
    grievance.save(update_fields=["assigned_officer", "assigned_at"])

    logger.info(
        "Grievance #%s reassigned from %s to %s by %s",
        grievance.id, from_officer, to_officer, changed_by,
    )
