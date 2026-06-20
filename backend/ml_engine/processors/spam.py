import logging

logger = logging.getLogger(__name__)

# Label design principles:
#   GENUINE — requires three elements: a specific CURRENT problem, with a
#             specific infrastructure or service subject, requesting action.
#             Past-tense praise, political content, and testimonials do not
#             qualify even when they mention civic topics like roads.
#   SPAM    — explicitly names political endorsements and "past government work"
#             testimonials so the NLI model has a direct semantic anchor for T24.
_CANDIDATE_LABELS = [
    "a genuine civic complaint reporting a specific current problem with government infrastructure or services, describing what is broken or failing right now and requesting action to fix it",
    "spam, test message, gibberish, promotional or commercial content, political endorsement, praise for a government official, testimonial about past government work, or any content that does not report a specific problem currently requiring action",
]

# The label at index 0 is "genuine complaint".
# If the model ranks the spam label first, the submission is spam.
_SPAM_LABEL = _CANDIDATE_LABELS[1]

# Confidence margin below which a result is logged as uncertain.
# Does NOT change the classification result — only surfaces borderline cases
# in logs during the T22–T25 test phase.
_LOW_CONFIDENCE_MARGIN = 0.15


def run(translated_text: str, registry) -> bool:
    """
    Return True if the translated text is spam / not a genuine complaint.

    Uses zero-shot NLI: the NLI model scores how well the text entails
    each candidate label. The label with the highest score wins.

    Fallback: if the model is unavailable or inference fails, return False
    (treat as genuine) so the pipeline continues rather than silently
    discarding real grievances.
    """
    if not translated_text or not translated_text.strip():
        logger.warning("Spam check received empty text — marking as spam")
        return True

    if registry.nli_pipeline is None:
        logger.error("NLI model not loaded; skipping spam check")
        return False

    try:
        result = registry.nli_pipeline(
            translated_text[:1024],   # guard against very long inputs
            candidate_labels=_CANDIDATE_LABELS,
            hypothesis_template="This text is {}.",
        )
        top_label = result["labels"][0]
        top_score = result["scores"][0]
        second_score = result["scores"][1]
        margin = top_score - second_score
        logger.debug("Spam check — top label: %r  score: %.3f  margin: %.3f", top_label, top_score, margin)
        if margin < _LOW_CONFIDENCE_MARGIN:
            logger.info(
                "Spam check — low-confidence result (margin=%.3f): "
                "top=%r score=%.3f — review this submission manually during testing",
                margin, top_label, top_score,
            )
        return top_label == _SPAM_LABEL
    except Exception:
        logger.exception("Spam detection failed; defaulting to not-spam")
        return False
