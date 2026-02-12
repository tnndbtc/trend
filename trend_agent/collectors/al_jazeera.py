"""
Al Jazeera collector plugin.

Fetches latest news from Al Jazeera RSS feed.
"""

from trend_agent.collectors.base_rss import BaseRSSCollector
from trend_agent.ingestion.base import register_collector
from trend_agent.schemas import PluginMetadata, SourceType


@register_collector
class AlJazeeraCollector(BaseRSSCollector):
    """
    Collector plugin for Al Jazeera.

    Fetches news from Al Jazeera English RSS feed.
    """

    rss_url = "https://www.aljazeera.com/xml/rss/all.xml"
    max_items = 40

    metadata = PluginMetadata(
        name="al_jazeera",
        version="1.0.0",
        author="Trend Agent Team",
        description="Collects latest news from Al Jazeera RSS feed",
        source_type=SourceType.AL_JAZEERA,
        schedule="*/20 * * * *",  # Every 20 minutes
        enabled=True,
        rate_limit=60,
        timeout_seconds=30,
        retry_count=3,
    )
