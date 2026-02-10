"""
The Guardian collector - Fetches latest news from The Guardian RSS feed.

The Guardian is a major British international daily newspaper known for
its quality journalism and independent editorial stance.

RSS Feed: https://www.theguardian.com/world/rss
"""

import feedparser
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import Topic
from .utils import extract_rss_entry_data
from . import register_collector

# The Guardian RSS feed URLs
RSS_FEEDS = {
    'world': 'https://www.theguardian.com/world/rss',
    'uk': 'https://www.theguardian.com/uk/rss',
    'us': 'https://www.theguardian.com/us-news/rss',
    'technology': 'https://www.theguardian.com/technology/rss',
}

# Use world news feed
RSS_URL = RSS_FEEDS['world']


async def fetch():
    """
    Fetch latest news from The Guardian RSS feed.

    Returns:
        List of Topic objects
    """
    feed = feedparser.parse(RSS_URL)
    topics = []

    # Limit to 40 most recent articles
    for entry in feed.entries[:40]:
        # Extract standard RSS data using shared utility
        data = extract_rss_entry_data(entry, 'guardian')

        # Skip if no title or URL
        if not data['title'] or not data['url']:
            continue

        topics.append(Topic(**data))

    return topics


# Register this collector
register_collector('guardian', fetch)
