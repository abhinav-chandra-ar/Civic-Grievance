import logging
import re

import torch

logger = logging.getLogger(__name__)

# Malayalam Unicode block: U+0D00–U+0D7F
_MALAYALAM_START = 0x0D00
_MALAYALAM_END = 0x0D7F

# Minimum token count below which lingua confidence is considered unreliable.
# Logged as INFO so short-text detection failures surface during testing (T15–T21).
_SHORT_TEXT_TOKEN_THRESHOLD = 12

# Word-level ITRANS corrections for Manglish informal spellings.
#
# ITRANS is case-sensitive: uppercase letters encode retroflex sounds (L=ള, T=ട,
# N=ണ, R=റ). Manglish users always type lowercase, causing ITRANS to produce the
# wrong Malayalam letter. This table maps the most impactful Manglish words to
# their correct ITRANS representations before transliteration.
#
# Only words where the mismatch produces a semantically unrelated Malayalam word
# are included — imperfect phonetics alone do not qualify for an entry.
_MANGLISH_ITRANS_CORRECTIONS = {
    # water: vellam → veLLam
    # Without fix: "vellam" → ITRANS → "വെല്ലം" (palm jaggery, not water)
    # With fix:    "veLLam" → ITRANS → "വെള്ളം" (water) ✓
    "vellam":    "veLLam",
    "vellathu":  "veLLathu",   # the water (common accusative form in complaints)
    "vellathil": "veLLathil",  # in the water (locative, flooding complaints)
    # house: veedu/veetil → vITu/vITTil
    # Without fix: "veedu" → ITRANS → "വീദു" (nonsense)
    # With fix:    "vITu"  → ITRANS → "വീടു" (house) ✓
    "veedu":   "vITu",
    "veetil":  "vITTil",   # in the house / at home (most common form)
    "veettil": "vITTil",   # alternate Manglish spelling, same target
}


def _normalize_manglish(text: str) -> str:
    """
    Apply word-level ITRANS corrections before feeding to indic-transliteration.
    Matches whole words only, case-insensitively, to avoid substring collisions.
    """
    for manglish_word, itrans_word in _MANGLISH_ITRANS_CORRECTIONS.items():
        text = re.sub(
            r"\b" + re.escape(manglish_word) + r"\b",
            itrans_word,
            text,
            flags=re.IGNORECASE,
        )
    return text


# English confidence threshold for lingua-language-detector.
#
# Pure English grievances score 0.88–0.99 with lingua's character n-gram model.
# Manglish text scores 0.40–0.72 because Malayalam phoneme clusters (nj, ll,
# kk, -anu, -undu, -alle) produce character n-grams with near-zero probability
# in English corpora. 0.80 sits comfortably between the two distributions.
_ENGLISH_CONFIDENCE_THRESHOLD = 0.80


def _has_malayalam_script(text: str) -> bool:
    return any(_MALAYALAM_START <= ord(ch) <= _MALAYALAM_END for ch in text)


def _detect_script(text: str, registry) -> str:
    """
    Returns 'malayalam', 'manglish', or 'english'.

    Priority:
      1. Any Malayalam Unicode character → 'malayalam'  (deterministic, O(n))
      2. lingua English confidence ≥ threshold → 'english'
      3. Confidence below threshold → 'manglish'

    Falls back to 'english' if lang_detector is unavailable so the pipeline
    degrades gracefully rather than crashing.
    """
    if _has_malayalam_script(text):
        return "malayalam"

    if registry.lang_detector is None:
        logger.warning("lang_detector not loaded; defaulting to English")
        return "english"

    try:
        from lingua import Language
        token_count = len(text.split())
        if token_count < _SHORT_TEXT_TOKEN_THRESHOLD:
            logger.info(
                "Short text detected (%d tokens < %d threshold) — "
                "lingua confidence may be unreliable; observe T15–T21 failures",
                token_count,
                _SHORT_TEXT_TOKEN_THRESHOLD,
            )
        confidence = registry.lang_detector.compute_language_confidence(
            text, Language.ENGLISH
        )
        logger.debug(
            "lingua English confidence: %.3f (tokens=%d)", confidence, token_count
        )
        return "english" if confidence >= _ENGLISH_CONFIDENCE_THRESHOLD else "manglish"
    except Exception:
        logger.exception("lingua detection failed; defaulting to English")
        return "english"


def _transliterate_manglish(text: str) -> str:
    """
    Convert Manglish (Malayalam in Roman letters) to Malayalam Unicode script.

    Step 1: Apply ITRANS word corrections for high-impact Manglish spellings
            where lowercase input produces the wrong Malayalam word.
    Step 2: Feed corrected text through ITRANS → Malayalam transliteration.

    Result is then passed to the MarianMT translation model.
    """
    text = _normalize_manglish(text)
    try:
        from indic_transliteration.sanscript import transliterate, ITRANS, MALAYALAM
        return transliterate(text, ITRANS, MALAYALAM)
    except Exception:
        logger.warning("indic-transliteration failed; treating Manglish as English")
        return text


def run(raw_text: str, registry) -> str:
    """
    Translate raw_text to formal English.

    Pipeline:
      English  → return as-is
      Manglish → transliterate to Malayalam script → translate via MarianMT
      Malayalam script → translate directly via MarianMT
    """
    if not raw_text or not raw_text.strip():
        return ""

    script = _detect_script(raw_text.strip(), registry)
    logger.debug("Detected script: %s", script)

    if script == "english":
        return raw_text.strip()

    source_text = raw_text.strip()

    if script == "manglish":
        source_text = _transliterate_manglish(source_text)
        logger.debug("After transliteration: %s", source_text[:80])

    tokenizer = registry.translation_tokenizer
    model = registry.translation_model

    if tokenizer is None or model is None:
        logger.error("Translation model not loaded; returning raw text")
        return raw_text.strip()

    try:
        inputs = tokenizer(
            source_text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                num_beams=4,
                max_length=512,
                early_stopping=True,
            )
        translated = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        logger.debug("Translation output: %s", translated[:120])
        return translated.strip()
    except Exception:
        logger.exception("Translation inference failed; returning raw text")
        return raw_text.strip()
