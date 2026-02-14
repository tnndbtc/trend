"""
Content Filtering System for Collected Items.

This module provides filtering capabilities for:
1. Keyword-based filtering (include/exclude)
2. Category filtering
3. Language detection and filtering
4. Content length filtering
5. Date range filtering
6. Custom filter expressions
"""

import logging
import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta

from trend_agent.schemas import RawItem, Category

logger = logging.getLogger(__name__)


class FilterResult:
    """Result of applying filters to an item."""

    def __init__(self, passed: bool, reasons: Optional[List[str]] = None):
        """
        Initialize filter result.

        Args:
            passed: Whether item passed all filters
            reasons: Reasons for rejection (if failed)
        """
        self.passed = passed
        self.reasons = reasons or []

    def __bool__(self) -> bool:
        """Allow filter result to be used as boolean."""
        return self.passed


class ContentFilter:
    """
    Applies content filters to collected items.

    Filters can be configured per-source to only collect relevant content.
    """

    def __init__(self, filter_config: Dict[str, Any]):
        """
        Initialize content filter.

        Args:
            filter_config: Filter configuration from source
        """
        self.config = filter_config

        # Extract filter settings
        self.keyword_filters = filter_config.get('keyword_filters', {})
        self.include_keywords = self.keyword_filters.get('include', [])
        self.exclude_keywords = self.keyword_filters.get('exclude', [])

        self.category_filters = filter_config.get('category_filters', [])
        self.language = filter_config.get('language', 'en')

        self.content_filters = filter_config.get('content_filters', {})
        self.min_length = self.content_filters.get('min_length', 0)
        self.max_length = self.content_filters.get('max_length', None)

        # Date filters
        self.max_age_hours = self.content_filters.get('max_age_hours', None)
        self.min_date = self.content_filters.get('min_date', None)
        self.max_date = self.content_filters.get('max_date', None)

        # Compile regex patterns for keywords
        self._include_patterns = [
            re.compile(keyword, re.IGNORECASE)
            for keyword in self.include_keywords
        ]
        self._exclude_patterns = [
            re.compile(keyword, re.IGNORECASE)
            for keyword in self.exclude_keywords
        ]

    def filter_item(self, item: RawItem) -> FilterResult:
        """
        Apply all filters to an item.

        Args:
            item: Item to filter

        Returns:
            FilterResult indicating pass/fail and reasons
        """
        reasons = []

        # Apply keyword filters
        keyword_result = self._filter_keywords(item)
        if not keyword_result.passed:
            reasons.extend(keyword_result.reasons)
            return FilterResult(False, reasons)

        # Apply category filters
        category_result = self._filter_category(item)
        if not category_result.passed:
            reasons.extend(category_result.reasons)
            return FilterResult(False, reasons)

        # Apply language filter
        language_result = self._filter_language(item)
        if not language_result.passed:
            reasons.extend(language_result.reasons)
            return FilterResult(False, reasons)

        # Apply content length filters
        length_result = self._filter_length(item)
        if not length_result.passed:
            reasons.extend(length_result.reasons)
            return FilterResult(False, reasons)

        # Apply date filters
        date_result = self._filter_date(item)
        if not date_result.passed:
            reasons.extend(date_result.reasons)
            return FilterResult(False, reasons)

        # All filters passed
        return FilterResult(True)

    def _filter_keywords(self, item: RawItem) -> FilterResult:
        """
        Filter based on keyword inclusion/exclusion.

        Args:
            item: Item to filter

        Returns:
            FilterResult
        """
        # Get text to search
        text = f"{item.title} {item.description or ''} {item.content or ''}"

        # Check exclude keywords first (blocklist)
        for pattern in self._exclude_patterns:
            if pattern.search(text):
                return FilterResult(
                    False,
                    [f"Matches excluded keyword: {pattern.pattern}"]
                )

        # Check include keywords (allowlist)
        # If include list is specified, item must match at least one
        if self.include_keywords:
            matched = False
            for pattern in self._include_patterns:
                if pattern.search(text):
                    matched = True
                    break

            if not matched:
                return FilterResult(
                    False,
                    [f"Does not match any required keywords: {self.include_keywords}"]
                )

        return FilterResult(True)

    def _filter_category(self, item: RawItem) -> FilterResult:
        """
        Filter based on category.

        Args:
            item: Item to filter

        Returns:
            FilterResult
        """
        # If no category filters specified, pass all
        if not self.category_filters:
            return FilterResult(True)

        # If item has no category, reject if filters specified
        if not item.metadata.get('category'):
            # Try to infer category from content
            inferred_category = self._infer_category(item)
            if inferred_category:
                item.metadata['category'] = inferred_category
            else:
                return FilterResult(True)  # Allow uncategorized items

        item_category = item.metadata.get('category')

        # Check if category is in allowed list
        if item_category not in self.category_filters:
            return FilterResult(
                False,
                [f"Category '{item_category}' not in allowed list: {self.category_filters}"]
            )

        return FilterResult(True)

    def _filter_language(self, item: RawItem) -> FilterResult:
        """
        Filter based on language.

        Args:
            item: Item to filter

        Returns:
            FilterResult
        """
        # If item language matches, pass
        if item.language == self.language:
            return FilterResult(True)

        # Try to detect language from content
        detected_language = self._detect_language(item)

        if detected_language != self.language:
            return FilterResult(
                False,
                [f"Language '{detected_language}' does not match required '{self.language}'"]
            )

        return FilterResult(True)

    def _filter_length(self, item: RawItem) -> FilterResult:
        """
        Filter based on content length.

        Args:
            item: Item to filter

        Returns:
            FilterResult
        """
        # Calculate total content length
        content_length = len(item.title or '')
        content_length += len(item.description or '')
        content_length += len(item.content or '')

        # Check minimum length
        if content_length < self.min_length:
            return FilterResult(
                False,
                [f"Content too short: {content_length} < {self.min_length}"]
            )

        # Check maximum length
        if self.max_length and content_length > self.max_length:
            return FilterResult(
                False,
                [f"Content too long: {content_length} > {self.max_length}"]
            )

        return FilterResult(True)

    def _filter_date(self, item: RawItem) -> FilterResult:
        """
        Filter based on publication date.

        Args:
            item: Item to filter

        Returns:
            FilterResult
        """
        published_at = item.published_at

        # Check max age
        if self.max_age_hours:
            max_age = timedelta(hours=self.max_age_hours)
            age = datetime.utcnow() - published_at

            if age > max_age:
                return FilterResult(
                    False,
                    [f"Content too old: {age.total_seconds() / 3600:.1f}h > {self.max_age_hours}h"]
                )

        # Check date range
        if self.min_date:
            min_date = datetime.fromisoformat(self.min_date)
            if published_at < min_date:
                return FilterResult(
                    False,
                    [f"Published before minimum date: {published_at} < {min_date}"]
                )

        if self.max_date:
            max_date = datetime.fromisoformat(self.max_date)
            if published_at > max_date:
                return FilterResult(
                    False,
                    [f"Published after maximum date: {published_at} > {max_date}"]
                )

        return FilterResult(True)

    def _infer_category(self, item: RawItem) -> Optional[str]:
        """
        Infer category from content using keywords.

        Args:
            item: Item to categorize

        Returns:
            Inferred category or None
        """
        text = f"{item.title} {item.description or ''}".lower()

        # Simple keyword-based categorization
        category_keywords = {
            'Technology': ['tech', 'software', 'ai', 'computer', 'coding', 'programming', 'app', 'digital'],
            'Politics': ['politics', 'election', 'government', 'president', 'congress', 'senate', 'vote'],
            'Entertainment': ['movie', 'music', 'celebrity', 'entertainment', 'film', 'album', 'concert'],
            'Sports': ['sports', 'football', 'basketball', 'soccer', 'game', 'team', 'player', 'match'],
            'Science': ['science', 'research', 'study', 'scientific', 'discovery', 'experiment'],
            'Business': ['business', 'market', 'economy', 'company', 'stock', 'finance', 'trade'],
            'Health': ['health', 'medical', 'doctor', 'hospital', 'disease', 'treatment', 'medicine'],
        }

        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return category

        return None

    def _detect_language(self, item: RawItem) -> str:
        """
        Detect language from content.

        Args:
            item: Item to detect language for

        Returns:
            ISO 639-1 language code
        """
        # Simple heuristic-based detection
        # In production, use langdetect or similar library

        text = f"{item.title} {item.description or ''}"

        # Check for CJK characters
        if re.search(r'[\u4e00-\u9fff]', text):  # Chinese
            return 'zh-Hans'
        if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):  # Japanese
            return 'ja'
        if re.search(r'[\uac00-\ud7af]', text):  # Korean
            return 'ko'

        # Check for Cyrillic
        if re.search(r'[\u0400-\u04ff]', text):
            return 'ru'

        # Check for Arabic
        if re.search(r'[\u0600-\u06ff]', text):
            return 'ar'

        # Default to English
        return 'en'


class FilterPipeline:
    """
    Pipeline for applying multiple filters to a list of items.

    Provides batch filtering with statistics.
    """

    def __init__(self, filters: List[ContentFilter]):
        """
        Initialize filter pipeline.

        Args:
            filters: List of filters to apply
        """
        self.filters = filters

    def filter_items(self, items: List[RawItem]) -> tuple[List[RawItem], Dict[str, Any]]:
        """
        Filter a list of items.

        Args:
            items: Items to filter

        Returns:
            Tuple of (filtered_items, statistics)
        """
        filtered_items = []
        rejected_items = []
        rejection_reasons: Dict[str, int] = {}

        for item in items:
            passed = True
            item_reasons = []

            # Apply all filters
            for content_filter in self.filters:
                result = content_filter.filter_item(item)

                if not result.passed:
                    passed = False
                    item_reasons.extend(result.reasons)

                    # Track rejection reasons
                    for reason in result.reasons:
                        rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

            if passed:
                filtered_items.append(item)
            else:
                rejected_items.append((item, item_reasons))

        # Compile statistics
        stats = {
            'total_items': len(items),
            'passed': len(filtered_items),
            'rejected': len(rejected_items),
            'pass_rate': len(filtered_items) / len(items) if items else 0,
            'rejection_reasons': rejection_reasons,
        }

        logger.info(
            f"Filtered {len(items)} items: "
            f"{len(filtered_items)} passed, {len(rejected_items)} rejected "
            f"({stats['pass_rate']:.1%} pass rate)"
        )

        return filtered_items, stats

    @staticmethod
    def create_from_config(filter_config: Dict[str, Any]) -> 'FilterPipeline':
        """
        Create filter pipeline from configuration.

        Args:
            filter_config: Filter configuration

        Returns:
            FilterPipeline instance
        """
        # For now, create a single filter
        # In the future, could support multiple filter stages
        content_filter = ContentFilter(filter_config)
        return FilterPipeline([content_filter])


def apply_filters(items: List[RawItem], filter_config: Dict[str, Any]) -> List[RawItem]:
    """
    Convenience function to filter items with given configuration.

    Args:
        items: Items to filter
        filter_config: Filter configuration

    Returns:
        Filtered items
    """
    if not filter_config:
        return items

    pipeline = FilterPipeline.create_from_config(filter_config)
    filtered_items, stats = pipeline.filter_items(items)

    logger.debug(f"Filter stats: {stats}")

    return filtered_items
