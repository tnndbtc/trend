"""
Translation stage for processing pipeline.

Provides automatic translation of trend content to target languages,
with caching and multi-provider support.
"""

import logging
from typing import List, Optional

from trend_agent.processing.interfaces import BaseProcessingStage
from trend_agent.schemas import ProcessedItem, PipelineResult

logger = logging.getLogger(__name__)


class TranslationStage(BaseProcessingStage):
    """
    Translation processing stage.

    Automatically translates content (title, description, key points)
    to one or more target languages using the TranslationManager.

    Features:
    - Multi-language support
    - Automatic source language detection
    - Provider fallback
    - Redis caching
    - Batch translation for efficiency

    The translation adds translated fields to the item metadata:
    - translated_title_{lang}
    - translated_description_{lang}

    Example:
        ```python
        from trend_agent.services import get_service_factory

        factory = get_service_factory()
        translation_manager = factory.get_translation_manager()

        stage = TranslationStage(
            translation_manager=translation_manager,
            target_languages=["es", "fr", "de"],
            translate_title=True,
            translate_description=True,
        )

        # Process items
        result = await stage.process(items)
        ```
    """

    def __init__(
        self,
        translation_manager,  # TranslationManager
        target_languages: List[str],
        translate_title: bool = True,
        translate_description: bool = True,
        translate_content: bool = False,
        min_text_length: int = 3,
    ):
        """
        Initialize translation stage.

        Args:
            translation_manager: TranslationManager instance
            target_languages: List of target language codes (e.g., ["es", "fr", "de"])
            translate_title: Translate item titles
            translate_description: Translate descriptions
            translate_content: Translate full content (can be expensive)
            min_text_length: Minimum text length to translate
        """
        super().__init__()
        self.translation_manager = translation_manager
        self.target_languages = target_languages
        self.translate_title = translate_title
        self.translate_description = translate_description
        self.translate_content = translate_content
        self.min_text_length = min_text_length

        logger.info(
            f"Initialized TranslationStage "
            f"(languages={target_languages}, title={translate_title}, "
            f"description={translate_description})"
        )

    async def process(self, items: List[ProcessedItem]) -> PipelineResult:
        """
        Translate items to target languages.

        Args:
            items: List of items to translate

        Returns:
            PipelineResult with translated items
        """
        if not items:
            return self._create_empty_result()

        logger.info(
            f"Translating {len(items)} items to {len(self.target_languages)} languages"
        )

        translated_items = []
        translation_count = 0

        for item in items:
            try:
                # Translate item
                translated_item = await self._translate_item(item)
                translated_items.append(translated_item)

                # Count translations performed
                for lang in self.target_languages:
                    if f"translated_title_{lang}" in translated_item.metadata:
                        translation_count += 1

            except Exception as e:
                logger.error(f"Translation failed for item {item.id}: {e}")
                # Keep original item even if translation fails
                translated_items.append(item)

        # Get translation stats
        stats = self.translation_manager.get_stats()

        logger.info(
            f"Translation complete: {translation_count} translations, "
            f"cache hit rate: {stats.get('cache_stats', {}).get('hit_rate_percent', 0):.1f}%"
        )

        return PipelineResult(
            status="completed",
            items_collected=len(items),
            items_processed=len(translated_items),
            items_deduplicated=0,
            topics_created=0,
            trends_created=0,
            duration_seconds=0.0,
            started_at=self._get_current_time(),
            metadata={
                "processed_items": translated_items,
                "translations_performed": translation_count,
                "translation_stats": stats,
            },
        )

    async def _translate_item(self, item: ProcessedItem) -> ProcessedItem:
        """
        Translate a single item to all target languages.

        Args:
            item: Item to translate

        Returns:
            Item with translations added to metadata
        """
        # Detect source language if not already set
        source_lang = item.language

        # Prepare texts to translate
        texts_to_translate = []
        text_types = []

        if self.translate_title and item.title:
            if len(item.title) >= self.min_text_length:
                texts_to_translate.append(item.title)
                text_types.append("title")

        if self.translate_description and item.description:
            if len(item.description) >= self.min_text_length:
                texts_to_translate.append(item.description)
                text_types.append("description")

        if self.translate_content and item.content:
            if len(item.content) >= self.min_text_length:
                # Limit content length to avoid excessive costs
                content_preview = item.content[:1000]
                texts_to_translate.append(content_preview)
                text_types.append("content")

        if not texts_to_translate:
            logger.debug(f"No text to translate for item {item.id}")
            return item

        # Translate to each target language
        for target_lang in self.target_languages:
            # Skip if source and target are the same
            if source_lang == target_lang:
                logger.debug(
                    f"Skipping translation to same language: {source_lang} -> {target_lang}"
                )
                continue

            try:
                # Batch translate all texts for this language
                translations = await self.translation_manager.translate_batch(
                    texts_to_translate,
                    target_language=target_lang,
                    source_language=source_lang,
                )

                # Store translations in metadata
                for text_type, translation in zip(text_types, translations):
                    metadata_key = f"translated_{text_type}_{target_lang}"
                    item.metadata[metadata_key] = translation

                logger.debug(
                    f"Translated item {item.id} to {target_lang} "
                    f"({len(text_types)} fields)"
                )

            except Exception as e:
                logger.warning(
                    f"Failed to translate item {item.id} to {target_lang}: {e}"
                )
                # Continue with other languages

        return item

    def _create_empty_result(self) -> PipelineResult:
        """Create empty result for no items."""
        return PipelineResult(
            status="completed",
            items_collected=0,
            items_processed=0,
            items_deduplicated=0,
            topics_created=0,
            trends_created=0,
            duration_seconds=0.0,
            started_at=self._get_current_time(),
            metadata={"processed_items": []},
        )

    def _get_current_time(self):
        """Get current timestamp."""
        from datetime import datetime

        return datetime.utcnow()


class CrossLanguageNormalizer(BaseProcessingStage):
    """
    Cross-language normalization stage.

    Normalizes text across different languages to enable better
    cross-language deduplication and clustering.

    Features:
    - Transliteration of non-Latin scripts
    - Case normalization
    - Diacritic removal
    - Common word stemming

    This stage prepares text for cross-language comparison by
    converting all text to a normalized Latin representation.

    Example:
        ```python
        stage = CrossLanguageNormalizer()
        result = await stage.process(items)
        # Items now have 'normalized_title_latin' in metadata
        ```
    """

    def __init__(self):
        """Initialize cross-language normalizer."""
        super().__init__()

        # Try to import transliteration library
        try:
            from unidecode import unidecode

            self.unidecode = unidecode
        except ImportError:
            logger.warning(
                "unidecode not installed. Latin normalization will be limited."
            )
            self.unidecode = None

        logger.info("Initialized CrossLanguageNormalizer")

    async def process(self, items: List[ProcessedItem]) -> PipelineResult:
        """
        Normalize items for cross-language comparison.

        Args:
            items: Items to normalize

        Returns:
            PipelineResult with normalized items
        """
        if not items:
            return self._create_empty_result()

        normalized_items = []

        for item in items:
            try:
                # Normalize title
                if item.title:
                    normalized_title = self._normalize_to_latin(item.title)
                    item.metadata["normalized_title_latin"] = normalized_title

                # Normalize description
                if item.description:
                    normalized_desc = self._normalize_to_latin(item.description)
                    item.metadata["normalized_description_latin"] = normalized_desc

                normalized_items.append(item)

            except Exception as e:
                logger.error(f"Normalization failed for item {item.id}: {e}")
                normalized_items.append(item)

        logger.info(f"Normalized {len(normalized_items)} items for cross-language comparison")

        return PipelineResult(
            status="completed",
            items_collected=len(items),
            items_processed=len(normalized_items),
            items_deduplicated=0,
            topics_created=0,
            trends_created=0,
            duration_seconds=0.0,
            started_at=self._get_current_time(),
            metadata={"processed_items": normalized_items},
        )

    def _normalize_to_latin(self, text: str) -> str:
        """
        Normalize text to Latin script.

        Converts non-Latin scripts (CJK, Cyrillic, Arabic) to Latin
        representation for cross-language comparison.

        Args:
            text: Text to normalize

        Returns:
            Normalized Latin text
        """
        if not text:
            return ""

        # Convert to lowercase
        normalized = text.lower()

        # Transliterate to Latin if available
        if self.unidecode:
            normalized = self.unidecode(normalized)

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        return normalized

    def _create_empty_result(self) -> PipelineResult:
        """Create empty result."""
        from datetime import datetime

        return PipelineResult(
            status="completed",
            items_collected=0,
            items_processed=0,
            items_deduplicated=0,
            topics_created=0,
            trends_created=0,
            duration_seconds=0.0,
            started_at=datetime.utcnow(),
            metadata={"processed_items": []},
        )

    def _get_current_time(self):
        """Get current timestamp."""
        from datetime import datetime

        return datetime.utcnow()
