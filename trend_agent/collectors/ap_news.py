"""
Associated Press News collector - Fetches latest news from AP RSS feed.

The Associated Press is a trusted independent global news organization
dedicated to factual reporting.

RSS Feed: https://apnews.com/hub/ap-top-news
"""

import feedparser
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import Topic
from .utils import extract_rss_entry_data
from . import register_collector

# AP News RSS feed URLs
# Note: AP News provides various topic feeds
RSS_FEEDS = {
    'top_news': 'https://apnews.com/ap-top-news',
    'world': 'https://apnews.com/world-news',
    'us': 'https://apnews.com/us-news',
    'politics': 'https://apnews.com/politics',
    'technology': 'https://apnews.com/technology',
}

# Use top news feed
RSS_URL = 'https://rss.apnews.com/rss/topnews'


async def fetch():
    """
    Fetch latest news from Associated Press RSS feed.

    Returns:
        List of Topic objects
    """
    feed = feedparser.parse(RSS_URL)
    topics = []

    # Limit to 40 most recent articles
    for entry in feed.entries[:40]:
        # Extract standard RSS data using shared utility
        data = extract_rss_entry_data(entry, 'ap_news')

        # Skip if no title or URL
        if not data['title'] or not data['url']:
            continue

        topics.append(Topic(**data))

    return topics


# Register this collector
register_collector('ap_news', fetch)
