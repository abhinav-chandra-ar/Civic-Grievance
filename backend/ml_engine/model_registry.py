import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Thread-safe singleton. Loads all Phase 1 ML models once on first use
    and keeps them in memory for the lifetime of the process.

    Phase 2 slots (duplicate, location, image) exist but are always None
    until that phase is implemented. Every processor must guard:
        if registry.<model> is None: return default
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    # Phase 1 models
                    obj.translation_model = None
                    obj.translation_tokenizer = None
                    obj.summarisation_pipeline = None
                    obj.nli_pipeline = None
                    obj.lang_detector = None
                    # Phase 2 placeholders — never loaded here
                    obj.sentence_transformer = None
                    obj.indic_ner = None
                    obj.bert_ner = None
                    obj.clip_model = None
                    obj.clip_processor = None
                    obj._loaded = False
                    cls._instance = obj
        return cls._instance

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    @classmethod
    def get(cls):
        """Return the singleton, loading models if not yet loaded."""
        instance = cls()
        if not instance._loaded:
            instance._load()
        return instance

    # ------------------------------------------------------------------
    # Internal loading
    # ------------------------------------------------------------------

    def _load(self):
        with self._lock:
            if self._loaded:
                return
            logger.info("ModelRegistry: starting model load — this takes 30–90 s on first run")
            cache = getattr(settings, "ML_MODELS_DIR", None)
            self._load_translation(cache)
            self._load_summarisation(cache)
            self._load_nli(cache)
            self._load_lang_detector()
            self._loaded = True
            logger.info("ModelRegistry: all Phase 1 models loaded")

    def _load_translation(self, cache):
        from transformers import MarianMTModel, MarianTokenizer
        name = "Helsinki-NLP/opus-mt-ml-en"
        logger.info("Loading translation model: %s", name)
        self.translation_tokenizer = MarianTokenizer.from_pretrained(
            name, cache_dir=cache
        )
        self.translation_model = MarianMTModel.from_pretrained(
            name, cache_dir=cache
        )
        self.translation_model.eval()
        logger.info("Translation model ready")

    def _load_summarisation(self, cache):
        from transformers import pipeline as hf_pipeline
        name = "sshleifer/distilbart-cnn-12-6"
        logger.info("Loading summarisation model: %s", name)
        self.summarisation_pipeline = hf_pipeline(
            "summarization",
            model=name,
            tokenizer=name,
            device=-1,          # CPU
            model_kwargs={"cache_dir": cache},
        )
        logger.info("Summarisation model ready")

    def _load_nli(self, cache):
        from transformers import pipeline as hf_pipeline
        name = "cross-encoder/nli-deberta-v3-small"
        logger.info("Loading NLI model: %s", name)
        self.nli_pipeline = hf_pipeline(
            "zero-shot-classification",
            model=name,
            device=-1,
            model_kwargs={"cache_dir": cache},
        )
        logger.info("NLI model ready (serves spam + department + priority)")

    def _load_lang_detector(self):
        from lingua import Language, LanguageDetectorBuilder
        logger.info("Loading lingua language detector (English + Malayalam)")
        self.lang_detector = (
            LanguageDetectorBuilder
            .from_languages(Language.ENGLISH, Language.MALAYALAM)
            .with_preloaded_language_models()
            .build()
        )
        logger.info("Language detector ready")
