"""
YouTube Data Collector Plugin.

Collects trending videos, popular content, and video metadata from YouTube
using the YouTube Data API v3.
"""

import logging
import os
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlencode

import aiohttp
from pydantic import HttpUrl

from trend_agent.ingestion.base import CollectorPlugin
from trend_agent.types import PluginMetadata, RawItem, SourceType, Metrics

logger = logging.getLogger(__name__)


class YouTubeCollector(CollectorPlugin):
    """
    Collector for YouTube trending videos and popular content.

    Uses YouTube Data API v3 to fetch:
    - Trending videos by region
    - Most popular videos
    - Search results for trending topics
    """

    metadata = PluginMetadata(
        name="youtube",
        version="1.0.0",
        author="Trend Intelligence Platform",
        description="Collects trending videos and popular content from YouTube",
        source_type=SourceType.YOUTUBE,
        schedule="0 */2 * * *",  # Every 2 hours
        enabled=True,
        rate_limit=100,  # API quota units per hour
        timeout_seconds=30,
        retry_count=3,
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        region_code: str = "US",
        max_results: int = 50,
        category_id: Optional[str] = None,
    ):
        """
        Initialize YouTube collector.

        Args:
            api_key: YouTube Data API v3 key (or from env YOUTUBE_API_KEY)
            region_code: Region code for trending videos (default: US)
            max_results: Maximum videos to fetch per request (default: 50, max: 50)
            category_id: Optional category ID to filter (e.g., "28" for Science & Tech)
        """
        super().__init__()
        self._api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self._api_key:
            logger.warning("YouTube API key not provided, collector will be disabled")

        self._region_code = region_code
        self._max_results = min(max_results, 50)  # API limit
        self._category_id = category_id
        self._base_url = "https://www.googleapis.com/youtube/v3"

    async def collect(self) -> List[RawItem]:
        """
        Collect trending videos from YouTube.

        Returns:
            List of raw items representing YouTube videos
        """
        if not self._api_key:
            logger.warning("YouTube API key not available, skipping collection")
            return []

        items = []

        async with aiohttp.ClientSession() as session:
            # Get trending videos
            trending_items = await self._get_trending_videos(session)
            items.extend(trending_items)

            # Get most popular videos
            popular_items = await self._get_popular_videos(session)
            items.extend(popular_items)

        logger.info(f"Collected {len(items)} items from YouTube")
        return items

    async def _get_trending_videos(self, session: aiohttp.ClientSession) -> List[RawItem]:
        """Fetch trending videos using videos.list with chart=mostPopular."""
        params = {
            "part": "snippet,contentDetails,statistics",
            "chart": "mostPopular",
            "regionCode": self._region_code,
            "maxResults": self._max_results,
            "key": self._api_key,
        }

        if self._category_id:
            params["videoCategoryId"] = self._category_id

        url = f"{self._base_url}/videos?{urlencode(params)}"

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()

                items = []
                for video in data.get("items", []):
                    item = self._parse_video(video)
                    if item:
                        items.append(item)

                logger.info(f"Fetched {len(items)} trending videos from YouTube")
                return items

        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch trending videos from YouTube: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching YouTube trending videos: {e}")
            return []

    async def _get_popular_videos(self, session: aiohttp.ClientSession) -> List[RawItem]:
        """Fetch most viewed videos from last 24 hours using search."""
        from datetime import timedelta

        published_after = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"

        params = {
            "part": "snippet",
            "type": "video",
            "order": "viewCount",
            "publishedAfter": published_after,
            "maxResults": min(self._max_results, 25),  # Lower limit for search
            "key": self._api_key,
        }

        url = f"{self._base_url}/search?{urlencode(params)}"

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()

                # Get video IDs
                video_ids = [item["id"]["videoId"] for item in data.get("items", [])]

                if not video_ids:
                    return []

                # Fetch full video details
                return await self._get_video_details(session, video_ids)

        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch popular videos from YouTube: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching popular YouTube videos: {e}")
            return []

    async def _get_video_details(
        self, session: aiohttp.ClientSession, video_ids: List[str]
    ) -> List[RawItem]:
        """Fetch detailed video information."""
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": ",".join(video_ids),
            "key": self._api_key,
        }

        url = f"{self._base_url}/videos?{urlencode(params)}"

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()

                items = []
                for video in data.get("items", []):
                    item = self._parse_video(video)
                    if item:
                        items.append(item)

                return items

        except Exception as e:
            logger.error(f"Failed to fetch video details: {e}")
            return []

    def _parse_video(self, video: dict) -> Optional[RawItem]:
        """Parse YouTube video into RawItem."""
        try:
            video_id = video["id"]
            snippet = video["snippet"]
            statistics = video.get("statistics", {})

            # Extract metrics
            view_count = int(statistics.get("viewCount", 0))
            like_count = int(statistics.get("likeCount", 0))
            comment_count = int(statistics.get("commentCount", 0))

            # Parse published date
            published_at = datetime.fromisoformat(
                snippet["publishedAt"].replace("Z", "+00:00")
            )

            # Create URL
            url = f"https://www.youtube.com/watch?v={video_id}"

            # Calculate engagement score
            engagement_score = view_count * 0.1 + like_count * 2 + comment_count * 3

            return RawItem(
                source=SourceType.YOUTUBE,
                source_id=video_id,
                url=HttpUrl(url),
                title=snippet["title"],
                description=snippet.get("description", ""),
                content=snippet.get("description", ""),
                author=snippet.get("channelTitle", "Unknown"),
                published_at=published_at,
                collected_at=datetime.utcnow(),
                metrics=Metrics(
                    upvotes=like_count,
                    comments=comment_count,
                    views=view_count,
                    score=engagement_score,
                ),
                metadata={
                    "channel_id": snippet.get("channelId"),
                    "channel_title": snippet.get("channelTitle"),
                    "category_id": snippet.get("categoryId"),
                    "tags": snippet.get("tags", []),
                    "thumbnail": snippet.get("thumbnails", {})
                    .get("high", {})
                    .get("url"),
                },
            )

        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to parse YouTube video: {e}")
            return None


def create_plugin() -> YouTubeCollector:
    """Factory function to create YouTube collector instance."""
    return YouTubeCollector()
