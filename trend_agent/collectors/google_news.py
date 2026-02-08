import feedparser
from datetime import datetime
import sys
import os
from langdetect import detect, LangDetectException

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import Topic

RSS = "https://news.google.com/rss"


def detect_language(text: str) -> str:
    """Detect language of text, default to 'en' if detection fails."""
    if not text or len(text.strip()) < 10:
        return 'en'
    try:
        return detect(text)
    except LangDetectException:
        return 'en'


async def fetch():
    """Fetch latest news from Google News RSS feed."""
    feed = feedparser.parse(RSS)
    topics = []

    for e in feed.entries[:40]:
        title = e.title
        description = e.get("summary", "")

        # Detect language from title and description
        text_for_detection = f"{title} {description}"
        language = detect_language(text_for_detection)

        topics.append(
            Topic(
                title=title,
                description=description,
                source="google_news",
                url=e.link,
                timestamp=datetime(*e.published_parsed[:6]) if hasattr(e, "published_parsed") else datetime.now(),
                metrics={},
                language=language,
            )
        )
    return topics
