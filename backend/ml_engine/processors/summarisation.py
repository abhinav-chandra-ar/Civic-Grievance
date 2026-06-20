import logging

logger = logging.getLogger(__name__)

# Grievance texts are short. If the translated text is already brief,
# skip abstractive summarisation and return it as-is.
_MIN_WORDS_FOR_SUMMARY = 40


def run(translated_text: str, registry) -> str:
    """
    Generate a 1–2 sentence summary of the translated complaint using
    DistilBART (sshleifer/distilbart-cnn-12-6).

    For texts shorter than _MIN_WORDS_FOR_SUMMARY words, returns the
    text directly — the BART decoder performs poorly on very short inputs.

    Fallback: returns the first 200 characters of the text on any error.
    """
    if not translated_text or not translated_text.strip():
        return ""

    word_count = len(translated_text.split())
    if word_count < _MIN_WORDS_FOR_SUMMARY:
        logger.debug("Text too short for summarisation (%d words); returning as-is", word_count)
        return translated_text.strip()

    if registry.summarisation_pipeline is None:
        logger.error("Summarisation model not loaded; returning truncated text")
        return translated_text[:200].strip()

    try:
        result = registry.summarisation_pipeline(
            translated_text,
            max_length=80,
            min_length=20,
            do_sample=False,
            num_beams=4,
            truncation=True,
        )
        summary = result[0]["summary_text"].strip()
        logger.debug("Summary: %s", summary)
        return summary
    except Exception:
        logger.exception("Summarisation failed; returning truncated text")
        return translated_text[:200].strip()
