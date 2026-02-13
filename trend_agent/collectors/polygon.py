"""
Polygon gaming/entertainment news collector plugin.

Fetches latest gaming and pop culture news from Polygon RSS feed.
"""

from trend_agent.collectors.base_rss import BaseRSSCollector
from trend_agent.ingestion.base import register_collector
from trend_agent.schemas import PluginMetadata, SourceType


@register_collector
class PolygonCollector(BaseRSSCollector):
    """
    Collector plugin for Polygon gaming news.

    Fetches the latest gaming, entertainment, and pop culture news.
    """

    rss_url = "https://www.polygon.com/rss/index.xml"
    max_items = 30

    metadata = PluginMetadata(
        name="polygon",
        version="1.0.0",
        author="Trend Agent Team",
        description="Collects gaming/entertainment news from Polygon RSS feed",
        source_type=SourceType.RSS,
        schedule="*/30 * * * *",  # Every 30 minutes
        enabled=True,
        rate_limit=60,
        timeout_seconds=30,
        retry_count=3,
    )
