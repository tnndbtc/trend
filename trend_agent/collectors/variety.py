"""
Variety entertainment news collector plugin.

Fetches latest entertainment news from Variety RSS feed.
"""

from trend_agent.collectors.base_rss import BaseRSSCollector
from trend_agent.ingestion.base import register_collector
from trend_agent.schemas import PluginMetadata, SourceType


@register_collector
class VarietyCollector(BaseRSSCollector):
    """
    Collector plugin for Variety entertainment news.

    Fetches the latest movie, TV, and entertainment industry news.
    """

    rss_url = "https://variety.com/feed/"
    max_items = 30

    metadata = PluginMetadata(
        name="variety",
        version="1.0.0",
        author="Trend Agent Team",
        description="Collects entertainment news from Variety RSS feed",
        source_type=SourceType.RSS,
        schedule="*/30 * * * *",  # Every 30 minutes
        enabled=True,
        rate_limit=60,
        timeout_seconds=30,
        retry_count=3,
    )
