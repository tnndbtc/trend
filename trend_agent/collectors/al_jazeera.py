"""
Al Jazeera collector - Fetches latest news from Al Jazeera RSS feed.

Al Jazeera is a major international news organization providing comprehensive
coverage from the Middle East and around the world.

RSS Feed: https://www.aljazeera.com/xml/rss/all.xml
"""

import feedparser
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import Topic
from .utils import extract_rss_entry_data
from . import register_collector

# Al Jazeera RSS feed URL
RSS_URL = 'https://www.aljazeera.com/xml/rss/all.xml'


async def fetch():
    """
    Fetch latest news from Al Jazeera RSS feed.

    Returns:
        List of Topic objects
    """
    feed = feedparser.parse(RSS_URL)
    topics = []

    # Limit to 40 most recent articles
    for entry in feed.entries[:40]:
        # Extract standard RSS data using shared utility
        data = extract_rss_entry_data(entry, 'al_jazeera')

        # Skip if no title or URL
        if not data['title'] or not data['url']:
            continue

        topics.append(Topic(**data))

    return topics


# Register this collector
register_collector('al_jazeera', fetch)
