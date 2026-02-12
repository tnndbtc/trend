"""
Google Trends Data Collector Plugin.

Collects trending search queries and topics from Google Trends using the
pytrends library (unofficial Google Trends API).
"""

import logging
import os
from datetime import datetime
from typing import List, Optional

from pydantic import HttpUrl

from trend_agent.ingestion.base import CollectorPlugin
from trend_agent.schemas import PluginMetadata, RawItem, SourceType, Metrics

logger = logging.getLogger(__name__)


class GoogleTrendsCollector(CollectorPlugin):
    """
    Collector for Google Trends data.

    Uses pytrends (unofficial API) to fetch:
    - Trending searches by region
    - Related queries for topics
    - Interest over time for keywords
    """

    metadata = PluginMetadata(
        name="google_trends",
        version="1.0.0",
        author="Trend Intelligence Platform",
        description="Collects trending search queries from Google Trends",
        source_type=SourceType.CUSTOM,
        schedule="0 */3 * * *",  # Every 3 hours
        enabled=True,
        rate_limit=60,  # Conservative limit to avoid blocking
        timeout_seconds=60,
        retry_count=3,
    )

    def __init__(
        self,
        geo: str = "US",
        max_trends: int = 20,
    ):
        """
        Initialize Google Trends collector.

        Args:
            geo: Geographic location code (default: US)
            max_trends: Maximum trends to collect (default: 20)
        """
        super().__init__()
        self._geo = geo
        self._max_trends = max_trends
        self._pytrends = None

    async def collect(self) -> List[RawItem]:
        """
        Collect trending searches from Google Trends.

        Returns:
            List of raw items representing trending searches
        """
        try:
            # Import pytrends (lazy import to avoid hard dependency)
            from pytrends.request import TrendReq

            # Initialize pytrends
            if self._pytrends is None:
                self._pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))

            items = []

            # Get trending searches
            trending_items = await self._get_trending_searches()
            items.extend(trending_items)

            # Get realtime trends
            realtime_items = await self._get_realtime_trends()
            items.extend(realtime_items)

            logger.info(f"Collected {len(items)} items from Google Trends")
            return items

        except ImportError:
            logger.error(
                "pytrends library not installed. Install with: pip install pytrends"
            )
            return []
        except Exception as e:
            logger.error(f"Failed to collect from Google Trends: {e}")
            return []

    async def _get_trending_searches(self) -> List[RawItem]:
        """Get daily trending searches."""
        try:
            # Use asyncio to run sync pytrends methods
            import asyncio

            loop = asyncio.get_event_loop()

            # trending_searches_df returns DataFrame of daily trends
            df = await loop.run_in_executor(
                None, self._pytrends.trending_searches, self._geo
            )

            items = []
            for idx, row in df.head(self._max_trends).iterrows():
                trend_query = str(row[0])

                # Create a search URL
                url = f"https://trends.google.com/trends/explore?q={trend_query}&geo={self._geo}"

                # Create RawItem
                item = RawItem(
                    source=SourceType.CUSTOM,
                    source_id=f"google_trends_{self._geo}_{idx}_{datetime.utcnow().strftime('%Y%m%d')}",
                    url=HttpUrl(url),
                    title=f"Trending: {trend_query}",
                    description=f"Trending search query on Google in {self._geo}",
                    content=trend_query,
                    author="Google Trends",
                    published_at=datetime.utcnow(),
                    collected_at=datetime.utcnow(),
                    metrics=Metrics(
                        score=float(self._max_trends - idx),  # Higher rank = higher score
                    ),
                    metadata={
                        "geo": self._geo,
                        "rank": int(idx) + 1,
                        "query": trend_query,
                        "source_name": "Google Trends",
                    },
                )
                items.append(item)

            logger.info(f"Fetched {len(items)} trending searches from Google Trends")
            return items

        except Exception as e:
            logger.error(f"Failed to fetch trending searches: {e}")
            return []

    async def _get_realtime_trends(self) -> List[RawItem]:
        """Get realtime trending searches."""
        try:
            import asyncio

            loop = asyncio.get_event_loop()

            # Get realtime trends
            trending_data = await loop.run_in_executor(
                None, self._pytrends.realtime_trending_searches, self._geo
            )

            items = []

            for idx, trend in enumerate(trending_data.head(10)):  # Top 10 realtime
                if isinstance(trend, dict):
                    title = trend.get("title", "")
                    traffic = trend.get("formattedTraffic", "")

                    url = f"https://trends.google.com/trends/trendingsearches/realtime?geo={self._geo}&category=all"

                    item = RawItem(
                        source=SourceType.CUSTOM,
                        source_id=f"google_trends_realtime_{self._geo}_{idx}_{datetime.utcnow().strftime('%Y%m%d%H')}",
                        url=HttpUrl(url),
                        title=f"Realtime Trend: {title}",
                        description=f"Realtime trending search with {traffic} searches",
                        content=title,
                        author="Google Trends Realtime",
                        published_at=datetime.utcnow(),
                        collected_at=datetime.utcnow(),
                        metrics=Metrics(
                            score=float(10 - idx),  # Higher position = higher score
                        ),
                        metadata={
                            "geo": self._geo,
                            "traffic": traffic,
                            "is_realtime": True,
                            "source_name": "Google Trends",
                        },
                    )
                    items.append(item)

            logger.info(f"Fetched {len(items)} realtime trends from Google Trends")
            return items

        except Exception as e:
            logger.warning(f"Failed to fetch realtime trends (may not be available): {e}")
            return []


def create_plugin() -> GoogleTrendsCollector:
    """Factory function to create Google Trends collector instance."""
    return GoogleTrendsCollector()
