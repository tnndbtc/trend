import feedparser
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import Topic

RSS = "https://news.google.com/rss"


async def fetch():
    """Fetch latest news from Google News RSS feed."""
    feed = feedparser.parse(RSS)
    topics = []

    for e in feed.entries[:40]:
        topics.append(
            Topic(
                title=e.title,
                description=e.get("summary", ""),
                source="google_news",
                url=e.link,
                timestamp=datetime(*e.published_parsed[:6]) if hasattr(e, "published_parsed") else datetime.now(),
                metrics={},
            )
        )
    return topics
