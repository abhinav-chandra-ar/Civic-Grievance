import logging

logger = logging.getLogger(__name__)

# Label design principles:
#   CRITICAL — direct physical danger OR medical dependency on the failed service.
#              "insulin storage" and "medical equipment" are explicitly named so
#              the NLI model does not need multi-step inference for T10.
#   HIGH     — significant disruption to many people OR vulnerable populations
#              affected (schools, elderly, hospital-adjacent). No life risk.
#   MEDIUM   — single-location inconvenience, no health or safety dimension.
#   LOW      — administrative delay or improvement request, no urgency.
_LABEL_TO_CODE = {
    "a critical emergency requiring immediate action, such as a live electrical hazard, an explosion or fire risk, complete power or water outage affecting medical equipment or insulin storage, a disease outbreak, a fallen high-voltage line, or any situation with direct risk to human life": "CRITICAL",
    "an urgent high priority issue causing significant disruption to many households, such as a prolonged neighbourhood power outage, water shortage affecting many families, open sewage overflow, or a service failure affecting schools, elderly residents, or healthcare facilities — needs resolution within a day but no immediate life risk": "HIGH",
    "a moderate medium priority issue causing inconvenience to some residents, such as a single street light not working, a small pipeline leak, a broken footpath, or a delayed municipal response that can be addressed within a few days": "MEDIUM",
    "a minor low priority issue or administrative request with no immediate safety or health impact, such as a certificate delay, permit approval pending, property tax record error, or a routine maintenance or improvement request that can be scheduled at convenience": "LOW",
}

_LABELS = list(_LABEL_TO_CODE.keys())
_DEFAULT = "MEDIUM"

# Score below which a CRITICAL or HIGH result is flagged for manual review
# during testing. Does NOT change the output — only surfaces low-confidence
# escalations in logs.
_LOW_SCORE_THRESHOLD = 0.40


def run(translated_text: str, registry) -> str:
    """
    Classify the complaint into one of four priority levels:
    CRITICAL | HIGH | MEDIUM | LOW

    Uses the same shared NLI model instance as spam and department
    classification — no additional RAM cost.

    Returns _DEFAULT ("MEDIUM") if the model is unavailable or fails.
    """
    if not translated_text or not translated_text.strip():
        return _DEFAULT

    if registry.nli_pipeline is None:
        logger.error("NLI model not loaded; returning default priority")
        return _DEFAULT

    try:
        result = registry.nli_pipeline(
            translated_text[:1024],
            candidate_labels=_LABELS,
            hypothesis_template="This complaint describes {}.",
            multi_label=False,
        )
        top_label = result["labels"][0]
        top_score = result["scores"][0]
        priority = _LABEL_TO_CODE[top_label]
        logger.debug("Priority — %s (score %.3f)", priority, top_score)
        if top_score < _LOW_SCORE_THRESHOLD and priority in ("CRITICAL", "HIGH"):
            logger.info(
                "Priority — low-confidence %s (score %.3f): "
                "review this escalation manually during testing",
                priority, top_score,
            )
        return priority
    except Exception:
        logger.exception("Priority classification failed; returning default")
        return _DEFAULT
