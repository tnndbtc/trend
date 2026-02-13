"""
IGN gaming news collector plugin.

Fetches latest gaming news from IGN RSS feed.
"""

from trend_agent.collectors.base_rss import BaseRSSCollector
from trend_agent.ingestion.base import register_collector
from trend_agent.schemas import PluginMetadata, SourceType


@register_collector
class IGNCollector(BaseRSSCollector):
    """
    Collector plugin for IGN gaming news.

    Fetches the latest video game news, reviews, and industry updates.
    """

    rss_url = "https://www.ign.com/articles?tags=news"
    max_items = 30

    metadata = PluginMetadata(
        name="ign",
        version="1.0.0",
        author="Trend Agent Team",
        description="Collects gaming news from IGN RSS feed",
        source_type=SourceType.RSS,
        schedule="*/30 * * * *",  # Every 30 minutes
        enabled=True,
        rate_limit=60,
        timeout_seconds=30,
        retry_count=3,
    )
