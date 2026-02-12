"""
Data Collector Plugins.

This package contains collector plugins for various data sources.
"""

from trend_agent.ingestion.plugins.youtube import YouTubeCollector
from trend_agent.ingestion.plugins.twitter import TwitterCollector
from trend_agent.ingestion.plugins.google_trends import GoogleTrendsCollector
from trend_agent.ingestion.plugins.rss import RSSCollector

__all__ = [
    "YouTubeCollector",
    "TwitterCollector",
    "GoogleTrendsCollector",
    "RSSCollector",
]
