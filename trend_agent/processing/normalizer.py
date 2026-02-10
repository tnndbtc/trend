"""
Text normalization and entity extraction for processing pipeline.

This module provides text cleaning, normalization, HTML stripping,
and named entity extraction capabilities.
"""

import html
import logging
import re
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from trend_agent.processing.interfaces import BaseNormalizer, BaseProcessingStage
from trend_agent.types import ProcessedItem

logger = logging.getLogger(__name__)


class TextNormalizer(BaseNormalizer):
    """
    Text normalizer implementing the Normalizer interface.

    Provides comprehensive text cleaning, normalization, entity extraction,
    and HTML cleaning with support for multiple languages including CJK and RTL.
    """

    def __init__(
        self,
        enable_entity_extraction: bool = False,
        spacy_model: str = "en_core_web_sm",
    ):
        """
        Initialize text normalizer.

        Args:
            enable_entity_extraction: Enable named entity extraction (requires spaCy)
            spacy_model: spaCy model to use for NER (default: en_core_web_sm)

        Note:
            Entity extraction is optional and requires spaCy to be installed.
            If disabled, extract_entities() will return empty dict.
        """
        self._enable_entity_extraction = enable_entity_extraction
        self._nlp = None

        # Load spaCy model if entity extraction is enabled
        if self._enable_entity_extraction:
            try:
                import spacy

                self._nlp = spacy.load(spacy_model)
                logger.info(f"Loaded spaCy model: {spacy_model}")
            except (ImportError, OSError) as e:
                logger.warning(
                    f"Failed to load spaCy model '{spacy_model}': {e}. "
                    "Entity extraction will be disabled."
                )
                self._enable_entity_extraction = False

    async def normalize_text(self, text: str) -> str:
        """
        Normalize text content.

        Performs the following operations:
        1. HTML entity decoding
        2. Whitespace normalization
        3. Remove control characters
        4. Unicode normalization
        5. Trim and deduplicate spaces

        Args:
            text: Text to normalize

        Returns:
            Normalized text

        Note:
            Preserves language-specific characters (CJK, RTL, accents, etc.)
        """
        if not text:
            return ""

        # Decode HTML entities
        text = html.unescape(text)

        # Remove control characters (except newline and tab)
        text = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", text)

        # Normalize Unicode (NFKC - compatible composition)
        import unicodedata

        text = unicodedata.normalize("NFKC", text)

        # Normalize whitespace
        # Replace multiple spaces with single space
        text = re.sub(r"[ \t]+", " ", text)

        # Replace multiple newlines with double newline (preserve paragraphs)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        # Final trim
        text = text.strip()

        return text

    async def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from text using spaCy.

        Args:
            text: Text to analyze

        Returns:
            Dictionary mapping entity types to entity lists:
            {
                "PERSON": ["John Doe", "Jane Smith"],
                "ORG": ["Google", "Microsoft"],
                "GPE": ["United States", "Tokyo"],
                "DATE": ["2024", "January"],
                ...
            }

        Note:
            Requires spaCy to be enabled. Returns empty dict if disabled.
            Entity types: PERSON, ORG, GPE, LOC, DATE, TIME, MONEY, etc.
        """
        if not self._enable_entity_extraction or not self._nlp:
            return {}

        if not text or len(text.strip()) < 3:
            return {}

        try:
            # Limit text length for performance (spaCy can be slow on large texts)
            max_length = 10000
            if len(text) > max_length:
                text = text[:max_length]
                logger.debug(f"Truncated text to {max_length} chars for entity extraction")

            # Process text with spaCy
            doc = self._nlp(text)

            # Group entities by type
            entities: Dict[str, List[str]] = {}
            for ent in doc.ents:
                entity_type = ent.label_
                entity_text = ent.text.strip()

                if entity_type not in entities:
                    entities[entity_type] = []

                # Avoid duplicates
                if entity_text and entity_text not in entities[entity_type]:
                    entities[entity_type].append(entity_text)

            logger.debug(f"Extracted {sum(len(v) for v in entities.values())} entities")
            return entities

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}", exc_info=True)
            return {}

    async def clean_html(self, html_content: str) -> str:
        """
        Clean HTML content, extracting plain text.

        Args:
            html_content: HTML content to clean

        Returns:
            Clean text without HTML tags

        Note:
            - Removes scripts, styles, and other non-content elements
            - Preserves paragraph structure
            - Handles malformed HTML gracefully
        """
        if not html_content:
            return ""

        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove unwanted elements
            for element in soup(["script", "style", "meta", "link", "noscript"]):
                element.decompose()

            # Get text with some structure preserved
            # get_text() with separator preserves some readability
            text = soup.get_text(separator="\n", strip=True)

            # Further normalize the extracted text
            text = await self.normalize_text(text)

            return text

        except Exception as e:
            logger.error(f"HTML cleaning failed: {e}", exc_info=True)
            # Fallback: regex-based tag removal
            text = re.sub(r"<[^>]+>", "", html_content)
            return await self.normalize_text(text)


class NormalizerStage(BaseProcessingStage):
    """
    Processing stage that normalizes text in items.

    This stage:
    1. Normalizes title and content
    2. Extracts entities (optional)
    3. Cleans HTML content
    4. Stores normalized text in separate fields
    """

    def __init__(
        self,
        normalizer: Optional[TextNormalizer] = None,
        extract_entities: bool = False,
    ):
        """
        Initialize normalizer stage.

        Args:
            normalizer: TextNormalizer instance (creates new if None)
            extract_entities: Enable entity extraction (requires spaCy)
        """
        self._normalizer = normalizer or TextNormalizer(
            enable_entity_extraction=extract_entities
        )

    async def process(self, items: List[ProcessedItem]) -> List[ProcessedItem]:
        """
        Normalize text in processed items.

        Args:
            items: Items to process

        Returns:
            Items with normalized text fields updated

        Note:
            - Updates title_normalized and content_normalized fields
            - Stores entities in metadata if extraction is enabled
            - Cleans HTML if content appears to contain HTML tags
        """
        for item in items:
            # Normalize title
            if item.title:
                item.title_normalized = await self._normalizer.normalize_text(
                    item.title
                )
            else:
                item.title_normalized = ""

            # Normalize content
            if item.content:
                # Check if content contains HTML
                if self._contains_html(item.content):
                    # Clean HTML first
                    clean_content = await self._normalizer.clean_html(item.content)
                    item.content_normalized = clean_content
                else:
                    # Direct normalization
                    item.content_normalized = await self._normalizer.normalize_text(
                        item.content
                    )
            else:
                item.content_normalized = None

            # Normalize description
            if item.description:
                normalized_desc = await self._normalizer.normalize_text(
                    item.description
                )
                item.description = normalized_desc

            # Extract entities if enabled
            if self._normalizer._enable_entity_extraction:
                # Combine title + content for entity extraction
                text_for_entities = item.title_normalized or ""
                if item.content_normalized:
                    text_for_entities += " " + item.content_normalized[:1000]

                entities = await self._normalizer.extract_entities(text_for_entities)

                if entities:
                    item.metadata["entities"] = entities
                    logger.debug(
                        f"Item {item.source_id}: extracted "
                        f"{sum(len(v) for v in entities.values())} entities"
                    )

        logger.info(f"Normalization completed for {len(items)} items")
        return items

    async def validate(self, items: List[ProcessedItem]) -> bool:
        """
        Validate that all items have normalized text.

        Args:
            items: Items to validate

        Returns:
            True if all items have title_normalized
        """
        for item in items:
            if not item.title_normalized:
                logger.error(
                    f"Item {item.source_id} missing title_normalized after normalization"
                )
                return False

        return True

    def get_stage_name(self) -> str:
        """
        Get the name of this processing stage.

        Returns:
            Stage name
        """
        return "normalizer"

    @staticmethod
    def _contains_html(text: str) -> bool:
        """
        Check if text contains HTML tags.

        Args:
            text: Text to check

        Returns:
            True if text appears to contain HTML
        """
        if not text:
            return False

        # Simple heuristic: check for common HTML patterns
        html_patterns = [
            r"<html",
            r"<body",
            r"<div",
            r"<p>",
            r"<span",
            r"<a\s+href",
            r"<img",
            r"<script",
            r"<style",
        ]

        text_lower = text.lower()
        for pattern in html_patterns:
            if re.search(pattern, text_lower):
                return True

        # Check for high density of < and > characters
        tag_count = text.count("<") + text.count(">")
        if tag_count > 10 and len(text) > 0:
            density = tag_count / len(text)
            if density > 0.01:  # More than 1% tag characters
                return True

        return False


# ============================================================================
# Utility Functions
# ============================================================================


def strip_urls(text: str) -> str:
    """
    Remove URLs from text.

    Args:
        text: Text containing URLs

    Returns:
        Text with URLs removed

    Note:
        Matches http://, https://, ftp://, and www. URLs
    """
    if not text:
        return ""

    # URL pattern
    url_pattern = r"https?://\S+|www\.\S+|ftp://\S+"
    text = re.sub(url_pattern, "", text)

    # Clean up extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def strip_mentions(text: str) -> str:
    """
    Remove @mentions from text.

    Args:
        text: Text containing mentions

    Returns:
        Text with mentions removed

    Note:
        Removes Twitter/Reddit style @username mentions
    """
    if not text:
        return ""

    # Mention pattern
    mention_pattern = r"@\w+"
    text = re.sub(mention_pattern, "", text)

    # Clean up extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def strip_hashtags(text: str) -> str:
    """
    Remove #hashtags from text.

    Args:
        text: Text containing hashtags

    Returns:
        Text with hashtags removed
    """
    if not text:
        return ""

    # Hashtag pattern
    hashtag_pattern = r"#\w+"
    text = re.sub(hashtag_pattern, "", text)

    # Clean up extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length, preserving words.

    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to add if truncated (default: "...")

    Returns:
        Truncated text

    Note:
        Tries to break at word boundaries for readability
    """
    if not text or len(text) <= max_length:
        return text

    # Account for suffix length
    max_length -= len(suffix)

    # Find last space before max_length
    truncated = text[:max_length]
    last_space = truncated.rfind(" ")

    if last_space > 0:
        truncated = truncated[:last_space]

    return truncated + suffix


def remove_emojis(text: str) -> str:
    """
    Remove emoji characters from text.

    Args:
        text: Text containing emojis

    Returns:
        Text with emojis removed

    Note:
        Removes most emoji Unicode ranges
    """
    if not text:
        return ""

    # Emoji pattern (covers most common emoji ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002500-\U00002BEF"  # chinese char
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"  # dingbats
        "\u3030"
        "]+",
        flags=re.UNICODE,
    )

    text = emoji_pattern.sub("", text)

    # Clean up extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text
