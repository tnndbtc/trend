"""
Billboard music news collector plugin.

Fetches latest music news from Billboard RSS feed.
"""

from trend_agent.collectors.base_rss import BaseRSSCollector
from trend_agent.ingestion.base import register_collector
from trend_agent.schemas import PluginMetadata, SourceType


@register_collector
class BillboardCollector(BaseRSSCollector):
    """
    Collector plugin for Billboard music news.

    Fetches the latest music industry news, charts, and artist updates.
    """

    rss_url = "https://www.billboard.com/feed/"
    max_items = 30

    metadata = PluginMetadata(
        name="billboard",
        version="1.0.0",
        author="Trend Agent Team",
        description="Collects music news from Billboard RSS feed",
        source_type=SourceType.RSS,
        schedule="*/30 * * * *",  # Every 30 minutes
        enabled=True,
        rate_limit=60,
        timeout_seconds=30,
        retry_count=3,
    )
