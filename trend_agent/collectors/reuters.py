"""
Reuters collector plugin.

Fetches latest news from Reuters RSS feed.
"""

from trend_agent.collectors.base_rss import BaseRSSCollector
from trend_agent.ingestion.base import register_collector
from trend_agent.types import PluginMetadata, SourceType


@register_collector
class ReutersCollector(BaseRSSCollector):
    """
    Collector plugin for Reuters.

    Fetches world news from Reuters RSS feed.
    """

    rss_url = "https://www.reutersagency.com/feed/"
    max_items = 40

    metadata = PluginMetadata(
        name="reuters",
        version="1.0.0",
        author="Trend Agent Team",
        description="Collects latest news from Reuters RSS feed",
        source_type=SourceType.REUTERS,
        schedule="*/15 * * * *",  # Every 15 minutes
        enabled=True,
        rate_limit=80,
        timeout_seconds=30,
        retry_count=3,
    )
