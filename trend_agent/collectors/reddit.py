"""
Reddit collector plugin.

Collects trending posts from Reddit's r/all using the Reddit JSON API.
"""

import logging
from datetime import datetime
from typing import List

import aiohttp

from trend_agent.ingestion.base import CollectorPlugin, register_collector
from trend_agent.types import Metrics, PluginMetadata, RawItem, SourceType

logger = logging.getLogger(__name__)

REDDIT_URL = "https://www.reddit.com/r/all/top.json?limit=50&t=day"


@register_collector
class RedditCollector(CollectorPlugin):
    """
    Collector plugin for Reddit r/all top posts.

    Fetches the top 50 posts from the last 24 hours from r/all.
    Handles both self posts and external link posts appropriately.
    """

    metadata = PluginMetadata(
        name="reddit",
        version="1.0.0",
        author="Trend Agent Team",
        description="Collects trending posts from Reddit's r/all",
        source_type=SourceType.REDDIT,
        schedule="*/30 * * * *",  # Every 30 minutes
        enabled=True,
        rate_limit=60,  # 60 requests per hour (well under Reddit's limit)
        timeout_seconds=30,
        retry_count=3,
    )

    async def collect(self) -> List[RawItem]:
        """
        Collect top posts from Reddit.

        Returns:
            List of RawItem objects representing Reddit posts
        """
        logger.info("Collecting data from Reddit")

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": "TrendAgent/1.0 (Trend Intelligence Platform)"}

                async with session.get(REDDIT_URL, headers=headers, timeout=30) as resp:
                    if resp.status != 200:
                        logger.error(f"Reddit API returned status {resp.status}")
                        return []

                    data = await resp.json()

        except asyncio.TimeoutError:
            logger.error("Reddit request timed out")
            return []
        except Exception as e:
            logger.error(f"Error fetching Reddit data: {e}", exc_info=True)
            return []

        items = []

        for post in data.get("data", {}).get("children", []):
            try:
                p = post["data"]

                title = p.get("title", "")
                description = p.get("selftext", "")

                # Determine the correct URL based on post type
                is_self = p.get("is_self", False)
                post_hint = p.get("post_hint", "")
                post_url = p.get("url", "")

                # For self posts or media posts, use Reddit permalink
                # For external links, use the actual URL
                if is_self or post_hint in ["image", "hosted:video", "rich:video"] or \
                   "i.redd.it" in post_url or "v.redd.it" in post_url:
                    url = "https://reddit.com" + p["permalink"]
                else:
                    url = post_url

                # Create metrics
                metrics = Metrics(
                    upvotes=p.get("ups", 0),
                    downvotes=0,  # Reddit doesn't expose downvotes
                    comments=p.get("num_comments", 0),
                    shares=0,
                    views=0,
                    score=float(p.get("score", 0)),
                )

                # Create RawItem
                item = RawItem(
                    source=SourceType.REDDIT,
                    source_id=p.get("id", ""),
                    url=url,
                    title=title,
                    description=description if description else None,
                    content=description if description else None,
                    author=p.get("author", None),
                    published_at=datetime.utcfromtimestamp(p.get("created_utc", 0)),
                    metrics=metrics,
                    metadata={
                        "subreddit": p.get("subreddit", ""),
                        "permalink": p.get("permalink", ""),
                        "is_self": is_self,
                        "post_hint": post_hint,
                        "domain": p.get("domain", ""),
                        "gilded": p.get("gilded", 0),
                        "over_18": p.get("over_18", False),
                    }
                )

                items.append(item)

            except Exception as e:
                logger.warning(f"Failed to parse Reddit post: {e}")
                continue

        logger.info(f"Collected {len(items)} items from Reddit")
        return items

    async def validate(self, item: RawItem) -> bool:
        """
        Validate a Reddit item.

        Args:
            item: The item to validate

        Returns:
            True if item is valid
        """
        # Basic validation
        if not item.title or not item.source_id:
            return False

        # Filter out NSFW content if needed
        if item.metadata.get("over_18", False):
            logger.debug(f"Filtered NSFW post: {item.source_id}")
            return False

        return True

    async def on_success(self, items: List[RawItem]) -> None:
        """Hook called after successful collection."""
        logger.info(f"Successfully collected {len(items)} items from Reddit")

    async def on_error(self, error: Exception) -> None:
        """Hook called when collection fails."""
        logger.error(f"Reddit collection failed: {error}")


# Import asyncio for timeout handling
import asyncio
