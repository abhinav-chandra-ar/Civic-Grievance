import logging

logger = logging.getLogger(__name__)

# Each key is the natural-language label sent to the NLI model.
# Each value is the department code stored in ml_department_suggestion.
#
# Label design principles:
#   KSEB  — all electrical infrastructure including street lights (not LSG)
#   KWA   — water/drainage SUPPLY INFRASTRUCTURE only; health consequences
#            belong to PUBLIC_HEALTH, not here
#   PWD   — road and public works physical infrastructure
#   PUBLIC_HEALTH — complaints where health outcomes are reported: illness,
#                   disease risk, vectors, contamination causing sickness
#   LSG   — administrative and permit services only; not infrastructure
_LABEL_TO_CODE = {
    "electricity and power supply infrastructure issues such as power outages, transformer failures, electrical poles, street lights not working, wiring faults, or electricity meter problems": "KSEB",
    "water supply and drainage infrastructure failures such as water shortage, no water supply, pipeline leaks, burst pipes, drainage blockage, or sewage system structural failures — not including health consequences of contamination": "KWA",
    "road and public works infrastructure defects such as potholes, broken or damaged roads, road cave-ins, damaged bridges, broken footpaths, or public construction quality failures": "PWD",
    "public health hazards and disease risks such as contaminated water supply causing illness, garbage or waste causing mosquito or fly breeding, sewage overflow causing disease risk, or a disease outbreak reported in the area": "PUBLIC_HEALTH",
    "local government administrative services such as building permits, property tax records, land documents, birth or death certificates, or delays in municipal office processing": "LSG",
}

_LABELS = list(_LABEL_TO_CODE.keys())
_DEFAULT = "LSG"   # safest fallback — catches genuinely ambiguous complaints


def run(translated_text: str, registry) -> str:
    """
    Classify the complaint into one of five departments:
    KSEB | KWA | PWD | PUBLIC_HEALTH | LSG

    Uses zero-shot NLI with descriptive candidate labels. The NLI model
    scores how well the text entails each label hypothesis and returns
    them ranked by score. The highest-scoring label wins.

    Returns _DEFAULT ("LSG") if the model is unavailable or fails.
    """
    if not translated_text or not translated_text.strip():
        return _DEFAULT

    if registry.nli_pipeline is None:
        logger.error("NLI model not loaded; returning default department")
        return _DEFAULT

    try:
        result = registry.nli_pipeline(
            translated_text[:1024],
            candidate_labels=_LABELS,
            hypothesis_template="This complaint is about {}.",
            multi_label=False,
        )
        top_label = result["labels"][0]
        top_score = result["scores"][0]
        department = _LABEL_TO_CODE[top_label]
        logger.debug("Department — %s (score %.3f)", department, top_score)
        return department
    except Exception:
        logger.exception("Department classification failed; returning default")
        return _DEFAULT
