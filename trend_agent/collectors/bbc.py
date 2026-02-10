"""
BBC News collector plugin.

Fetches latest news from BBC RSS feed.
"""

from trend_agent.collectors.base_rss import BaseRSSCollector
from trend_agent.ingestion.base import register_collector
from trend_agent.types import PluginMetadata, SourceType


@register_collector
class BBCCollector(BaseRSSCollector):
    """
    Collector plugin for BBC News.

    Fetches the latest news from BBC's main RSS feed.
    """

    rss_url = "http://feeds.bbci.co.uk/news/rss.xml"
    max_items = 40

    metadata = PluginMetadata(
        name="bbc",
        version="1.0.0",
        author="Trend Agent Team",
        description="Collects latest news from BBC News RSS feed",
        source_type=SourceType.BBC,
        schedule="*/20 * * * *",  # Every 20 minutes
        enabled=True,
        rate_limit=60,
        timeout_seconds=30,
        retry_count=3,
    )
