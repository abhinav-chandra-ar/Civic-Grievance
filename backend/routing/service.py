import logging

from .models import RoutingRule

logger = logging.getLogger(__name__)


def run_routing(grievance) -> None:
    """
    Resolve department and jurisdiction from the ML-predicted category and
    the citizen's ward, then persist both on the grievance.

    Category source: grievance.ml_department_suggestion (set by ML pipeline).
    Lookup key:      RoutingRule(ward, category) — unique per ward/category pair.

    Does nothing if ward is missing or ml_department_suggestion is blank
    (e.g. ML pipeline did not run or was skipped as spam).
    """
    ward = grievance.ward
    category = grievance.ml_department_suggestion

    if not ward or not category:
        logger.info(
            "Grievance #%s skipped routing — ward or ml_department_suggestion not set",
            grievance.id,
        )
        return

    try:
        rule = RoutingRule.objects.select_related("department", "jurisdiction").get(
            ward=ward,
            category=category,
        )
    except RoutingRule.DoesNotExist:
        logger.warning(
            "No routing rule for ward=%s category=%s (grievance #%s)",
            ward,
            category,
            grievance.id,
        )
        return

    grievance.department = rule.department
    grievance.jurisdiction = rule.jurisdiction
    grievance.save(update_fields=["department", "jurisdiction"])

    logger.info(
        "Grievance #%s routed — dept=%s jurisdiction=%s",
        grievance.id,
        rule.department,
        rule.jurisdiction,
    )
