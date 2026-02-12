"""
Base RSS collector for news sources.

This module provides a reusable base class for RSS-based collectors,
reducing code duplication and standardizing RSS handling.
"""

import logging
from datetime import datetime
from typing import List

import feedparser
from bs4 import BeautifulSoup

from trend_agent.ingestion.base import CollectorPlugin
from trend_agent.schemas import Metrics, RawItem, SourceType

logger = logging.getLogger(__name__)


class BaseRSSCollector(CollectorPlugin):
    """
    Base class for RSS feed collectors.

    Subclasses only need to:
    1. Define metadata
    2. Set rss_url class attribute
    3. Optionally override parse_entry() for custom parsing
    """

    # Subclasses should set this
    rss_url: str = None
    max_items: int = 40  # Default number of items to fetch

    def _clean_html(self, html_content: str) -> str:
        """
        Remove HTML tags and clean text content.

        Args:
            html_content: HTML string

        Returns:
            Plain text with HTML removed
        """
        if not html_content:
            return ""

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            return text
        except Exception as e:
            logger.warning(f"Error cleaning HTML: {e}")
            return html_content

    def _parse_timestamp(self, entry: feedparser.FeedParserDict) -> datetime:
        """
        Extract timestamp from RSS feed entry.

        Args:
            entry: RSS feed entry

        Returns:
            datetime object
        """
        # Try published_parsed first
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass

        # Try updated_parsed
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6])
            except (TypeError, ValueError):
                pass

        # Fallback to current time
        logger.debug(f"Could not parse timestamp for: {entry.get('title', 'Unknown')}")
        return datetime.utcnow()

    async def parse_entry(self, entry: feedparser.FeedParserDict) -> RawItem:
        """
        Parse an RSS entry into a RawItem.

        Override this method in subclasses for custom parsing logic.

        Args:
            entry: RSS feed entry

        Returns:
            RawItem or None if parsing fails
        """
        try:
            title = entry.get('title', '').strip()
            description = self._clean_html(
                entry.get('summary', '') or entry.get('description', '')
            )
            url = entry.get('link', '')
            timestamp = self._parse_timestamp(entry)

            # Get unique ID (use link as fallback)
            source_id = entry.get('id', url)

            if not title or not url:
                return None

            # Create metrics (RSS doesn't usually have engagement metrics)
            metrics = Metrics()

            # Create RawItem
            item = RawItem(
                source=self.metadata.source_type,
                source_id=source_id,
                url=url,
                title=title,
                description=description if description else None,
                content=description if description else None,
                author=entry.get('author', None),
                published_at=timestamp,
                metrics=metrics,
                metadata={
                    'feed_url': self.rss_url,
                    'entry_id': entry.get('id', ''),
                    'tags': [tag.get('term', '') for tag in entry.get('tags', [])],
                }
            )

            return item

        except Exception as e:
            logger.warning(f"Failed to parse RSS entry: {e}")
            return None

    async def collect(self) -> List[RawItem]:
        """
        Collect items from RSS feed.

        Returns:
            List of RawItem objects
        """
        if not self.rss_url:
            logger.error(f"{self.__class__.__name__} must set rss_url attribute")
            return []

        logger.info(f"Collecting from RSS feed: {self.rss_url}")

        try:
            # Parse RSS feed (feedparser is synchronous)
            feed = feedparser.parse(self.rss_url)

            if feed.get('bozo', False):
                logger.warning(f"RSS feed may have issues: {feed.get('bozo_exception', '')}")

            items = []

            # Process entries
            for entry in feed.entries[:self.max_items]:
                item = await self.parse_entry(entry)
                if item:
                    items.append(item)

            logger.info(f"Collected {len(items)} items from {self.metadata.name}")
            return items

        except Exception as e:
            logger.error(f"Error fetching RSS feed {self.rss_url}: {e}", exc_info=True)
            return []

    async def validate(self, item: RawItem) -> bool:
        """
        Validate an RSS item.

        Args:
            item: The item to validate

        Returns:
            True if item is valid
        """
        # Basic validation
        if not item.title or not item.url or not item.source_id:
            return False

        return True

    async def on_success(self, items: List[RawItem]) -> None:
        """Hook called after successful collection."""
        logger.info(f"Successfully collected {len(items)} items from {self.metadata.name}")

    async def on_error(self, error: Exception) -> None:
        """Hook called when collection fails."""
        logger.error(f"{self.metadata.name} collection failed: {error}")
