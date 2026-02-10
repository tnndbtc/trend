"""
Reuters collector - Fetches latest news from Reuters RSS feed.

Reuters is a global news organization providing trusted business, financial,
national, and international news coverage.

RSS Feed: https://www.reutersagency.com/feed/
"""

import feedparser
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import Topic
from .utils import extract_rss_entry_data
from . import register_collector

# Reuters RSS feed URL
# Note: Reuters has multiple feeds. Using the main feed.
RSS_URL = 'https://www.reutersagency.com/feed/'


async def fetch():
    """
    Fetch latest news from Reuters RSS feed.

    Returns:
        List of Topic objects
    """
    feed = feedparser.parse(RSS_URL)
    topics = []

    # Limit to 40 most recent articles
    for entry in feed.entries[:40]:
        # Extract standard RSS data using shared utility
        data = extract_rss_entry_data(entry, 'reuters')

        # Skip if no title or URL
        if not data['title'] or not data['url']:
            continue

        topics.append(Topic(**data))

    return topics


# Register this collector
register_collector('reuters', fetch)
