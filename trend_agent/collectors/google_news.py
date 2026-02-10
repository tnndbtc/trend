"""
Google News collector plugin.

Fetches latest news from Google News RSS feed.
"""

import feedparser
import logging
from datetime import datetime
from typing import List

from bs4 import BeautifulSoup

from trend_agent.collectors.base_rss import BaseRSSCollector
from trend_agent.ingestion.base import register_collector
from trend_agent.types import Metrics, PluginMetadata, RawItem, SourceType

logger = logging.getLogger(__name__)


@register_collector
class GoogleNewsCollector(BaseRSSCollector):
    """
    Collector plugin for Google News.

    Fetches top headlines from Google News RSS feed.
    Google News aggregates headlines from multiple sources,
    so this collector extracts the primary article from each entry.
    """

    rss_url = "https://news.google.com/rss"
    max_items = 50

    metadata = PluginMetadata(
        name="google_news",
        version="1.0.0",
        author="Trend Agent Team",
        description="Collects latest news from Google News RSS feed",
        source_type=SourceType.GOOGLE_NEWS,
        schedule="*/15 * * * *",  # Every 15 minutes
        enabled=True,
        rate_limit=80,
        timeout_seconds=30,
        retry_count=3,
    )

    def _extract_first_article_info(self, summary_html: str) -> tuple:
        """
        Extract the first article's title from Google News summary HTML.

        Google News RSS summary contains aggregated headlines from multiple sources.
        This function parses the HTML to extract just the first article's information.

        Args:
            summary_html: HTML content from Google News RSS summary field

        Returns:
            Tuple of (article_title, source_name) or (None, None) if not found
        """
        if not summary_html:
            return None, None

        try:
            soup = BeautifulSoup(summary_html, 'html.parser')

            # Find first <li> which contains the primary article
            first_li = soup.find('li')
            if not first_li:
                return None, None

            # Extract the article title from the first link
            first_link = first_li.find('a')
            if first_link:
                article_title = first_link.get_text(strip=True)
            else:
                article_title = None

            # Extract source name from the <font> tag
            source_font = first_li.find('font')
            if source_font:
                source_name = source_font.get_text(strip=True)
            else:
                source_name = None

            return article_title, source_name

        except Exception as e:
            logger.warning(f"Failed to parse Google News summary: {e}")
            return None, None

    async def parse_entry(self, entry: feedparser.FeedParserDict) -> RawItem:
        """
        Parse a Google News RSS entry.

        Overrides base class to handle Google News's aggregated format.

        Args:
            entry: RSS feed entry

        Returns:
            RawItem or None if parsing fails
        """
        try:
            title = entry.get('title', '').strip()
            url = entry.get('link', '')
            timestamp = self._parse_timestamp(entry)

            # Extract article info from summary
            summary_html = entry.get("summary", "")
            article_title, source_name = self._extract_first_article_info(summary_html)

            # Use extracted article title as description
            description = article_title if article_title else ""

            # Get unique ID
            source_id = entry.get('id', url)

            if not title or not url:
                return None

            # Create metrics
            metrics = Metrics()

            # Create RawItem
            item = RawItem(
                source=SourceType.GOOGLE_NEWS,
                source_id=source_id,
                url=url,
                title=title,
                description=description if description else None,
                content=description if description else None,
                author=source_name,  # Original source
                published_at=timestamp,
                metrics=metrics,
                metadata={
                    'feed_url': self.rss_url,
                    'original_source': source_name,
                    'entry_id': entry.get('id', ''),
                }
            )

            return item

        except Exception as e:
            logger.warning(f"Failed to parse Google News entry: {e}")
            return None
