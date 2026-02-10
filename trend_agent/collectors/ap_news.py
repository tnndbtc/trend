"""
Associated Press (AP) News collector plugin.

Fetches latest news from AP News RSS feed.
"""

from trend_agent.collectors.base_rss import BaseRSSCollector
from trend_agent.ingestion.base import register_collector
from trend_agent.types import PluginMetadata, SourceType


@register_collector
class APNewsCollector(BaseRSSCollector):
    """
    Collector plugin for Associated Press News.

    Fetches top news from AP News RSS feed.
    """

    rss_url = "https://rss.apnews.com/rss/topnews"
    max_items = 40

    metadata = PluginMetadata(
        name="ap_news",
        version="1.0.0",
        author="Trend Agent Team",
        description="Collects latest news from Associated Press RSS feed",
        source_type=SourceType.AP_NEWS,
        schedule="*/20 * * * *",  # Every 20 minutes
        enabled=True,
        rate_limit=60,
        timeout_seconds=30,
        retry_count=3,
    )
