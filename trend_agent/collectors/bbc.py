"""
BBC News collector - Fetches latest news from BBC RSS feed.

BBC News is a major international news source providing comprehensive coverage
of world events, politics, business, technology, and more.

RSS Feed: http://feeds.bbci.co.uk/news/rss.xml
"""

import feedparser
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import Topic
from .utils import extract_rss_entry_data
from . import register_collector

# BBC News RSS feed URLs
RSS_FEEDS = {
    'world': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'main': 'http://feeds.bbci.co.uk/news/rss.xml',
    'technology': 'http://feeds.bbci.co.uk/news/technology/rss.xml',
}

# Use the main feed for general news
RSS_URL = RSS_FEEDS['main']


async def fetch():
    """
    Fetch latest news from BBC RSS feed.

    Returns:
        List of Topic objects
    """
    feed = feedparser.parse(RSS_URL)
    topics = []

    # Limit to 40 most recent articles
    for entry in feed.entries[:40]:
        # Extract standard RSS data using shared utility
        data = extract_rss_entry_data(entry, 'bbc')

        # Skip if no title or URL
        if not data['title'] or not data['url']:
            continue

        topics.append(Topic(**data))

    return topics


# Register this collector
register_collector('bbc', fetch)
