"""
The Guardian collector plugin.

Fetches latest news from The Guardian RSS feed.
"""

from trend_agent.collectors.base_rss import BaseRSSCollector
from trend_agent.ingestion.base import register_collector
from trend_agent.schemas import PluginMetadata, SourceType


@register_collector
class GuardianCollector(BaseRSSCollector):
    """
    Collector plugin for The Guardian.

    Fetches world news from The Guardian's RSS feed.
    """

    rss_url = "https://www.theguardian.com/world/rss"
    max_items = 40

    metadata = PluginMetadata(
        name="guardian",
        version="1.0.0",
        author="Trend Agent Team",
        description="Collects latest news from The Guardian RSS feed",
        source_type=SourceType.GUARDIAN,
        schedule="*/20 * * * *",  # Every 20 minutes
        enabled=True,
        rate_limit=60,
        timeout_seconds=30,
        retry_count=3,
    )
