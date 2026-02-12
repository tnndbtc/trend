"""
Hacker News collector plugin.

Collects top stories from Hacker News using the Firebase API.
"""

import asyncio
import logging
from datetime import datetime
from typing import List

import aiohttp

from trend_agent.ingestion.base import CollectorPlugin, register_collector
from trend_agent.schemas import Metrics, PluginMetadata, RawItem, SourceType

logger = logging.getLogger(__name__)

TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"


@register_collector
class HackerNewsCollector(CollectorPlugin):
    """
    Collector plugin for Hacker News top stories.

    Fetches the top 30 stories from Hacker News using the official Firebase API.
    """

    metadata = PluginMetadata(
        name="hackernews",
        version="1.0.0",
        author="Trend Agent Team",
        description="Collects top stories from Hacker News",
        source_type=SourceType.HACKERNEWS,
        schedule="*/20 * * * *",  # Every 20 minutes
        enabled=True,
        rate_limit=120,  # 120 requests per hour
        timeout_seconds=60,  # Longer timeout for multiple requests
        retry_count=3,
    )

    async def collect(self) -> List[RawItem]:
        """
        Collect top stories from Hacker News.

        Returns:
            List of RawItem objects representing HN stories
        """
        logger.info("Collecting data from Hacker News")

        try:
            async with aiohttp.ClientSession() as session:
                # Fetch top story IDs
                async with session.get(TOP_STORIES_URL, timeout=30) as resp:
                    if resp.status != 200:
                        logger.error(f"HN API returned status {resp.status}")
                        return []

                    story_ids = await resp.json()

                # Limit to top 30 stories
                story_ids = story_ids[:30]

                # Fetch story details concurrently
                items = []
                tasks = [
                    self._fetch_story(session, story_id)
                    for story_id in story_ids
                ]

                # Use gather to fetch all stories concurrently
                story_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter out None and exception results
                for result in story_results:
                    if isinstance(result, RawItem):
                        items.append(result)
                    elif isinstance(result, Exception):
                        logger.warning(f"Failed to fetch story: {result}")

        except asyncio.TimeoutError:
            logger.error("Hacker News request timed out")
            return []
        except Exception as e:
            logger.error(f"Error fetching Hacker News data: {e}", exc_info=True)
            return []

        logger.info(f"Collected {len(items)} items from Hacker News")
        return items

    async def _fetch_story(
        self, session: aiohttp.ClientSession, story_id: int
    ) -> RawItem:
        """
        Fetch a single story by ID.

        Args:
            session: aiohttp session
            story_id: Story ID

        Returns:
            RawItem or None if fetch fails
        """
        try:
            async with session.get(
                ITEM_URL.format(story_id), timeout=10
            ) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()

                if not data or not data.get("title"):
                    return None

                # Extract story details
                title = data.get("title", "")
                url = data.get("url", f"https://news.ycombinator.com/item?id={story_id}")
                text = data.get("text", "")
                score = data.get("score", 0)
                descendants = data.get("descendants", 0)  # Comment count
                author = data.get("by", "")
                timestamp = data.get("time", 0)

                # Create metrics
                metrics = Metrics(
                    upvotes=score,
                    downvotes=0,
                    comments=descendants,
                    shares=0,
                    views=0,
                    score=float(score),
                )

                # Create RawItem
                item = RawItem(
                    source=SourceType.HACKERNEWS,
                    source_id=str(story_id),
                    url=url,
                    title=title,
                    description=text if text else None,
                    content=text if text else None,
                    author=author if author else None,
                    published_at=datetime.utcfromtimestamp(timestamp),
                    metrics=metrics,
                    metadata={
                        "story_id": story_id,
                        "type": data.get("type", "story"),
                        "descendants": descendants,
                        "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
                    }
                )

                return item

        except Exception as e:
            logger.warning(f"Failed to fetch HN story {story_id}: {e}")
            return None

    async def validate(self, item: RawItem) -> bool:
        """
        Validate a Hacker News item.

        Args:
            item: The item to validate

        Returns:
            True if item is valid
        """
        # Basic validation
        if not item.title or not item.source_id:
            return False

        # Filter out dead stories
        if item.metadata.get("dead", False):
            logger.debug(f"Filtered dead story: {item.source_id}")
            return False

        return True

    async def on_success(self, items: List[RawItem]) -> None:
        """Hook called after successful collection."""
        logger.info(f"Successfully collected {len(items)} items from Hacker News")

    async def on_error(self, error: Exception) -> None:
        """Hook called when collection fails."""
        logger.error(f"Hacker News collection failed: {error}")
