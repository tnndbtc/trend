"""
Twitter/X Data Collector Plugin.

Collects trending topics, popular tweets, and hashtags from Twitter/X
using the Twitter API v2.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

import aiohttp
from pydantic import HttpUrl

from trend_agent.ingestion.base import CollectorPlugin
from trend_agent.types import PluginMetadata, RawItem, SourceType, Metrics

logger = logging.getLogger(__name__)


class TwitterCollector(CollectorPlugin):
    """
    Collector for Twitter/X trending topics and popular tweets.

    Uses Twitter API v2 to fetch:
    - Trending topics by location
    - Recent tweets with high engagement
    - Trending hashtags
    """

    metadata = PluginMetadata(
        name="twitter",
        version="1.0.0",
        author="Trend Intelligence Platform",
        description="Collects trending topics and popular tweets from Twitter/X",
        source_type=SourceType.TWITTER,
        schedule="0 */1 * * *",  # Every hour
        enabled=True,
        rate_limit=180,  # Requests per 15 minutes
        timeout_seconds=30,
        retry_count=3,
    )

    def __init__(
        self,
        bearer_token: Optional[str] = None,
        woeid: int = 1,  # 1 = Worldwide
        max_results: int = 100,
    ):
        """
        Initialize Twitter collector.

        Args:
            bearer_token: Twitter API v2 Bearer Token (or from env TWITTER_BEARER_TOKEN)
            woeid: Where On Earth ID for trending topics (default: 1 = Worldwide)
            max_results: Maximum tweets to fetch (default: 100, max: 100)
        """
        super().__init__()
        self._bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
        if not self._bearer_token:
            logger.warning("Twitter bearer token not provided, collector will be disabled")

        self._woeid = woeid
        self._max_results = min(max_results, 100)
        self._base_url = "https://api.twitter.com/2"

    async def collect(self) -> List[RawItem]:
        """
        Collect trending content from Twitter/X.

        Returns:
            List of raw items representing tweets
        """
        if not self._bearer_token:
            logger.warning("Twitter bearer token not available, skipping collection")
            return []

        items = []

        headers = {"Authorization": f"Bearer {self._bearer_token}"}

        async with aiohttp.ClientSession(headers=headers) as session:
            # Get recent popular tweets
            search_items = await self._search_recent_tweets(session)
            items.extend(search_items)

        logger.info(f"Collected {len(items)} items from Twitter/X")
        return items

    async def _search_recent_tweets(
        self, session: aiohttp.ClientSession
    ) -> List[RawItem]:
        """Search for recent high-engagement tweets."""
        # Search for tweets with high engagement from last 24 hours
        query = "-is:retweet (has:mentions OR has:hashtags) lang:en"

        params = {
            "query": query,
            "max_results": self._max_results,
            "tweet.fields": "created_at,public_metrics,author_id,entities,referenced_tweets",
            "expansions": "author_id",
            "user.fields": "username,verified",
            "sort_order": "relevancy",
        }

        url = f"{self._base_url}/tweets/search/recent"

        try:
            async with session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 401:
                    logger.error("Twitter API authentication failed - check bearer token")
                    return []

                response.raise_for_status()
                data = await response.json()

                items = []
                tweets = data.get("data", [])
                users = {
                    u["id"]: u for u in data.get("includes", {}).get("users", [])
                }

                for tweet in tweets:
                    item = self._parse_tweet(tweet, users)
                    if item:
                        items.append(item)

                logger.info(f"Fetched {len(items)} tweets from Twitter/X")
                return items

        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch tweets from Twitter/X: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching Twitter/X tweets: {e}")
            return []

    def _parse_tweet(self, tweet: dict, users: dict) -> Optional[RawItem]:
        """Parse Twitter tweet into RawItem."""
        try:
            tweet_id = tweet["id"]
            text = tweet["text"]
            created_at = datetime.fromisoformat(
                tweet["created_at"].replace("Z", "+00:00")
            )

            # Get metrics
            metrics = tweet.get("public_metrics", {})
            retweet_count = metrics.get("retweet_count", 0)
            reply_count = metrics.get("reply_count", 0)
            like_count = metrics.get("like_count", 0)
            quote_count = metrics.get("quote_count", 0)

            # Get author info
            author_id = tweet.get("author_id")
            user = users.get(author_id, {})
            author_username = user.get("username", "unknown")

            # Create URL
            url = f"https://twitter.com/{author_username}/status/{tweet_id}"

            # Extract hashtags
            entities = tweet.get("entities", {})
            hashtags = [tag["tag"] for tag in entities.get("hashtags", [])]

            # Calculate engagement score
            engagement_score = (
                like_count * 1.0
                + retweet_count * 2.0
                + reply_count * 1.5
                + quote_count * 2.0
            )

            return RawItem(
                source=SourceType.TWITTER,
                source_id=tweet_id,
                url=HttpUrl(url),
                title=text[:200] if len(text) > 200 else text,
                description=text,
                content=text,
                author=f"@{author_username}",
                published_at=created_at,
                collected_at=datetime.utcnow(),
                metrics=Metrics(
                    upvotes=like_count,
                    comments=reply_count,
                    shares=retweet_count + quote_count,
                    score=engagement_score,
                ),
                metadata={
                    "author_id": author_id,
                    "author_verified": user.get("verified", False),
                    "hashtags": hashtags,
                    "retweet_count": retweet_count,
                    "quote_count": quote_count,
                },
            )

        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to parse Twitter tweet: {e}")
            return None


def create_plugin() -> TwitterCollector:
    """Factory function to create Twitter collector instance."""
    return TwitterCollector()
