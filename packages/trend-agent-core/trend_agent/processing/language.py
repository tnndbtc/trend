"""
Language detection for processing pipeline.

This module provides language detection capabilities using the langdetect library,
with support for batch processing and confidence scoring.
"""

import logging
from typing import List, Optional

from langdetect import DetectorFactory, LangDetectException, detect, detect_langs

from trend_agent.processing.interfaces import BaseProcessingStage
from trend_agent.schemas import ProcessedItem

# Set seed for reproducible results
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)


class LanguageDetector:
    """
    Language detector implementing the LanguageDetector interface.

    Uses langdetect library for fast, accurate language detection
    with support for 55+ languages including CJK, RTL, and European languages.
    """

    def __init__(self):
        """Initialize language detector."""
        self._last_confidence: float = 0.0
        self._default_language: str = "en"

    async def detect(self, text: str) -> str:
        """
        Detect language of text.

        Args:
            text: Text to analyze (minimum 3 characters recommended)

        Returns:
            ISO 639-1 language code (e.g., 'en', 'zh-cn', 'ar', 'ja')

        Raises:
            ValueError: If text is empty or too short
        """
        if not text or len(text.strip()) < 3:
            logger.warning(f"Text too short for language detection: '{text[:50]}'")
            self._last_confidence = 0.0
            return self._default_language

        try:
            # Use detect_langs to get confidence scores
            langs = detect_langs(text)
            if not langs:
                self._last_confidence = 0.0
                return self._default_language

            # Get top result
            top_lang = langs[0]
            self._last_confidence = top_lang.prob

            logger.debug(
                f"Detected language: {top_lang.lang} "
                f"(confidence: {self._last_confidence:.2f})"
            )

            return top_lang.lang

        except LangDetectException as e:
            logger.warning(f"Language detection failed: {e}. Using default '{self._default_language}'")
            self._last_confidence = 0.0
            return self._default_language

    async def detect_batch(self, texts: List[str]) -> List[str]:
        """
        Detect languages for multiple texts.

        Args:
            texts: List of texts to analyze

        Returns:
            List of ISO 639-1 language codes

        Note:
            Batch processing detects each text independently.
            For large batches, consider using asyncio.gather for parallelization.
        """
        results = []
        for text in texts:
            lang = await self.detect(text)
            results.append(lang)

        logger.info(f"Detected languages for {len(texts)} texts")
        return results

    def get_confidence(self) -> float:
        """
        Get confidence score of last detection.

        Returns:
            Confidence score (0-1), where 1.0 is highest confidence
        """
        return self._last_confidence

    def set_default_language(self, language: str) -> None:
        """
        Set default language for fallback.

        Args:
            language: ISO 639-1 language code
        """
        self._default_language = language
        logger.info(f"Default language set to: {language}")


class LanguageDetectorStage(BaseProcessingStage):
    """
    Processing stage that adds language detection to items.

    This stage detects the language of each item's title and content,
    updating the item's language field.
    """

    def __init__(self, detector: Optional[LanguageDetector] = None):
        """
        Initialize language detector stage.

        Args:
            detector: LanguageDetector instance (creates new if None)
        """
        self._detector = detector or LanguageDetector()

    async def process(self, items: List[ProcessedItem]) -> List[ProcessedItem]:
        """
        Detect and assign languages to processed items.

        Args:
            items: Items to process

        Returns:
            Items with language field updated

        Note:
            Language is detected from title + description + content (if available).
            Prioritizes longer text for better accuracy.
        """
        for item in items:
            # Build text for detection (prioritize longer text)
            text_parts = []

            if item.title:
                text_parts.append(item.title)

            if item.description:
                text_parts.append(item.description)

            # Use normalized content if available (cleaner)
            if item.content_normalized:
                text_parts.append(item.content_normalized[:500])  # Limit to 500 chars
            elif item.content:
                text_parts.append(item.content[:500])

            # Combine text
            combined_text = " ".join(text_parts)

            # Detect language
            detected_lang = await self._detector.detect(combined_text)
            item.language = detected_lang

            # Store confidence in metadata
            item.metadata["language_confidence"] = self._detector.get_confidence()

            logger.debug(
                f"Item {item.source_id}: detected language '{detected_lang}' "
                f"(confidence: {self._detector.get_confidence():.2f})"
            )

        logger.info(f"Language detection completed for {len(items)} items")
        return items

    async def validate(self, items: List[ProcessedItem]) -> bool:
        """
        Validate that all items have language field set.

        Args:
            items: Items to validate

        Returns:
            True if all items have valid language codes
        """
        for item in items:
            if not item.language or len(item.language) < 2:
                logger.error(f"Item {item.source_id} has invalid language: {item.language}")
                return False

        return True

    def get_stage_name(self) -> str:
        """
        Get the name of this processing stage.

        Returns:
            Stage name
        """
        return "language_detector"


# ============================================================================
# Utility Functions
# ============================================================================


def is_cjk(text: str) -> bool:
    """
    Check if text contains CJK (Chinese, Japanese, Korean) characters.

    Args:
        text: Text to check

    Returns:
        True if text contains CJK characters

    Note:
        Useful for determining if special processing is needed.
    """
    if not text:
        return False

    # CJK Unicode ranges
    cjk_ranges = [
        (0x4E00, 0x9FFF),  # CJK Unified Ideographs
        (0x3400, 0x4DBF),  # CJK Extension A
        (0x20000, 0x2A6DF),  # CJK Extension B
        (0x2A700, 0x2B73F),  # CJK Extension C
        (0x2B740, 0x2B81F),  # CJK Extension D
        (0x3040, 0x309F),  # Hiragana
        (0x30A0, 0x30FF),  # Katakana
        (0xAC00, 0xD7AF),  # Hangul
    ]

    for char in text:
        code_point = ord(char)
        for start, end in cjk_ranges:
            if start <= code_point <= end:
                return True

    return False


def is_rtl(language: str) -> bool:
    """
    Check if language uses right-to-left script.

    Args:
        language: ISO 639-1 language code

    Returns:
        True if language uses RTL script

    Note:
        Covers Arabic, Hebrew, Persian, Urdu, and other RTL languages.
    """
    rtl_languages = {
        "ar",  # Arabic
        "he",  # Hebrew
        "fa",  # Persian
        "ur",  # Urdu
        "yi",  # Yiddish
        "ji",  # Yiddish (alternative code)
        "iw",  # Hebrew (old code)
        "ps",  # Pashto
        "sd",  # Sindhi
    }

    return language.lower() in rtl_languages


def get_language_family(language: str) -> str:
    """
    Get language family for a language code.

    Args:
        language: ISO 639-1 language code

    Returns:
        Language family name

    Note:
        Useful for applying family-specific processing rules.
    """
    language_families = {
        # Germanic
        "en": "Germanic",
        "de": "Germanic",
        "nl": "Germanic",
        "sv": "Germanic",
        "no": "Germanic",
        "da": "Germanic",
        # Romance
        "es": "Romance",
        "fr": "Romance",
        "it": "Romance",
        "pt": "Romance",
        "ro": "Romance",
        # Slavic
        "ru": "Slavic",
        "pl": "Slavic",
        "cs": "Slavic",
        "sk": "Slavic",
        "uk": "Slavic",
        "bg": "Slavic",
        # CJK
        "zh-cn": "Sinitic",
        "zh-tw": "Sinitic",
        "ja": "Japonic",
        "ko": "Koreanic",
        # Semitic
        "ar": "Semitic",
        "he": "Semitic",
        # Indo-Aryan
        "hi": "Indo-Aryan",
        "bn": "Indo-Aryan",
        "pa": "Indo-Aryan",
        "ur": "Indo-Aryan",
    }

    return language_families.get(language.lower(), "Other")
