import logging

from django.utils import timezone

from .model_registry import ModelRegistry
from .processors import (
    department,
    priority,
    spam,
    summarisation,
    translation,
)

logger = logging.getLogger(__name__)


def run_ml_pipeline(grievance) -> None:
    """
    Phase 1 synchronous ML pipeline.

    Execution order:
      1. Translation      — prerequisite for all downstream tasks
      2. Spam detection   — on translated text; stops pipeline if spam
      3. Summarisation    — abstractive summary of translated text
      4. Department       — zero-shot NLI classification (5 classes)
      5. Priority         — zero-shot NLI classification (4 classes)

    Fields populated on success:
      ml_translated_text, ml_is_spam, ml_summary,
      ml_department_suggestion, ml_priority_suggestion, ml_processed_at

    Fields left untouched (Phase 2):
      ml_is_duplicate, ml_duplicate_type,
      ml_location_extracted, ml_image_valid

    On any unhandled exception the function logs and returns without
    saving, leaving ml_processed_at as None — the caller can detect
    this and retry or alert.
    """
    logger.info("ML pipeline started for grievance #%s", grievance.id)

    try:
        registry = ModelRegistry.get()
    except Exception:
        logger.exception("ModelRegistry failed to load for grievance #%s", grievance.id)
        return

    results = {}

    # ------------------------------------------------------------------
    # Step 1 — Translation
    # ------------------------------------------------------------------
    try:
        translated = translation.run(grievance.raw_text, registry)
    except Exception:
        logger.exception("Translation step failed for grievance #%s", grievance.id)
        return

    results["ml_translated_text"] = translated

    # ------------------------------------------------------------------
    # Step 2 — Spam detection (gate: stop if spam)
    # ------------------------------------------------------------------
    try:
        is_spam = spam.run(translated, registry)
    except Exception:
        logger.exception("Spam step failed for grievance #%s; treating as not-spam", grievance.id)
        is_spam = False

    results["ml_is_spam"] = is_spam
    results["ml_processed_at"] = timezone.now()

    if is_spam:
        logger.info("Grievance #%s flagged as spam — stopping pipeline", grievance.id)
        _save(grievance, results)
        return

    # ------------------------------------------------------------------
    # Step 3 — Summarisation
    # ------------------------------------------------------------------
    try:
        results["ml_summary"] = summarisation.run(translated, registry)
    except Exception:
        logger.exception("Summarisation step failed for grievance #%s", grievance.id)
        results["ml_summary"] = ""

    # ------------------------------------------------------------------
    # Step 4 — Department classification
    # ------------------------------------------------------------------
    try:
        results["ml_department_suggestion"] = department.run(translated, registry)
    except Exception:
        logger.exception("Department step failed for grievance #%s", grievance.id)
        results["ml_department_suggestion"] = ""

    # ------------------------------------------------------------------
    # Step 5 — Priority classification
    # ------------------------------------------------------------------
    try:
        results["ml_priority_suggestion"] = priority.run(translated, registry)
    except Exception:
        logger.exception("Priority step failed for grievance #%s", grievance.id)
        results["ml_priority_suggestion"] = ""

    _save(grievance, results)
    logger.info(
        "ML pipeline complete for grievance #%s — dept=%s priority=%s spam=%s",
        grievance.id,
        results.get("ml_department_suggestion"),
        results.get("ml_priority_suggestion"),
        results.get("ml_is_spam"),
    )


def _save(grievance, results: dict) -> None:
    """Write ml_* results to the grievance row in a single UPDATE."""
    for field, value in results.items():
        setattr(grievance, field, value)
    grievance.save(update_fields=list(results.keys()))
