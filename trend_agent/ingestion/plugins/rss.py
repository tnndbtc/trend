"""
Generic RSS Feed Collector Plugin.

Collects content from any RSS/Atom feed using feedparser.
Supports multiple feeds with customizable parsing rules.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from pydantic import HttpUrl

from trend_agent.ingestion.base import CollectorPlugin
from trend_agent.schemas import PluginMetadata, RawItem, SourceType, Metrics

logger = logging.getLogger(__name__)


class RSSCollector(CollectorPlugin):
    """
    Generic collector for RSS/Atom feeds.

    Supports:
    - RSS 2.0
    - Atom 1.0
    - Custom feed formats
    - Multiple feed sources
    """

    metadata = PluginMetadata(
        name="rss",
        version="1.0.0",
        author="Trend Intelligence Platform",
        description="Collects content from RSS/Atom feeds",
        source_type=SourceType.RSS,
        schedule="0 */4 * * *",  # Every 4 hours
        enabled=True,
        rate_limit=None,  # No strict limit
        timeout_seconds=30,
        retry_count=3,
    )

    def __init__(
        self,
        feed_urls: Optional[List[str]] = None,
        max_items_per_feed: int = 50,
    ):
        """
        Initialize RSS collector.

        Args:
            feed_urls: List of RSS feed URLs to collect from
            max_items_per_feed: Maximum items to collect per feed (default: 50)
        """
        super().__init__()
        self._feed_urls = feed_urls or self._get_default_feeds()
        self._max_items_per_feed = max_items_per_feed

    def _get_default_feeds(self) -> List[str]:
        """Get default RSS feeds to collect from."""
        return [
            # Tech news
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://www.wired.com/feed/rss",
            # General news
            "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://www.reuters.com/rssFeed/topNews",
            # Science
            "https://www.sciencedaily.com/rss/all.xml",
            "https://www.scientificamerican.com/feed/",
            # Entertainment - Movies & TV
            "https://variety.com/feed/",
            "https://www.hollywoodreporter.com/feed/",
            "https://deadline.com/feed/",
            "https://ew.com/feed/",
            # Entertainment - Music
            "https://www.billboard.com/feed/",
            "https://www.rollingstone.com/feed/",
            "https://pitchfork.com/rss/news/",
            # Entertainment - Gaming
            "https://www.ign.com/articles?tags=news",
            "https://www.polygon.com/rss/index.xml",
            "https://kotaku.com/rss",
            # Entertainment - General Pop Culture
            "https://www.vulture.com/feed/",
            "https://www.avclub.com/rss",
        ]

    async def collect(self) -> List[RawItem]:
        """
        Collect items from all configured RSS feeds.

        Returns:
            List of raw items from RSS feeds
        """
        try:
            # Import feedparser (lazy import)
            import feedparser
            import aiohttp

            items = []

            async with aiohttp.ClientSession() as session:
                for feed_url in self._feed_urls:
                    feed_items = await self._collect_from_feed(session, feed_url, feedparser)
                    items.extend(feed_items)

            logger.info(f"Collected {len(items)} items from {len(self._feed_urls)} RSS feeds")
            return items

        except ImportError:
            logger.error("feedparser library not installed. Install with: pip install feedparser")
            return []
        except Exception as e:
            logger.error(f"Failed to collect from RSS feeds: {e}")
            return []

    async def _collect_from_feed(
        self, session: aiohttp.ClientSession, feed_url: str, feedparser
    ) -> List[RawItem]:
        """Collect items from a single RSS feed."""
        try:
            # Fetch feed
            async with session.get(feed_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                content = await response.text()

            # Parse feed
            feed = feedparser.parse(content)

            items = []
            for entry in feed.entries[: self._max_items_per_feed]:
                item = self._parse_entry(entry, feed_url, feed)
                if item:
                    items.append(item)

            logger.info(f"Fetched {len(items)} items from RSS feed: {feed_url}")
            return items

        except Exception as e:
            logger.error(f"Failed to fetch RSS feed {feed_url}: {e}")
            return []

    def _parse_entry(
        self, entry: Any, feed_url: str, feed: Any
    ) -> Optional[RawItem]:
        """Parse RSS entry into RawItem."""
        try:
            # Get title
            title = entry.get("title", "Untitled")

            # Get link
            link = entry.get("link") or entry.get("id")
            if not link:
                logger.warning(f"No link found for RSS entry: {title}")
                return None

            # Get description/summary
            description = (
                entry.get("summary")
                or entry.get("description")
                or entry.get("content", [{}])[0].get("value", "")
            )

            # Get content
            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].get("value", "")
            else:
                content = description

            # Get author
            author = (
                entry.get("author")
                or feed.feed.get("title", "")
                or urlparse(feed_url).netloc
            )

            # Get published date
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                from time import mktime
                published_at = datetime.fromtimestamp(mktime(entry.published_parsed))
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                from time import mktime
                published_at = datetime.fromtimestamp(mktime(entry.updated_parsed))
            else:
                published_at = datetime.utcnow()

            # Generate source ID
            source_id = entry.get("id") or link

            # Extract tags
            tags = []
            if hasattr(entry, "tags"):
                tags = [tag.get("term", "") for tag in entry.tags]

            return RawItem(
                source=SourceType.RSS,
                source_id=source_id,
                url=HttpUrl(link),
                title=title,
                description=description[:500] if description else "",
                content=content[:1000] if content else "",
                author=author,
                published_at=published_at,
                collected_at=datetime.utcnow(),
                metrics=Metrics(
                    score=1.0,  # RSS feeds don't have engagement metrics
                ),
                metadata={
                    "feed_url": feed_url,
                    "feed_title": feed.feed.get("title", ""),
                    "tags": tags,
                    "source_name": "RSS",
                },
            )

        except (KeyError, ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse RSS entry: {e}")
            return None


def create_plugin() -> RSSCollector:
    """Factory function to create RSS collector instance."""
    return RSSCollector()
