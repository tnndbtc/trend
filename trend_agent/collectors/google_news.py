import feedparser
from datetime import datetime
import sys
import os
from langdetect import detect, LangDetectException
from bs4 import BeautifulSoup

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


def extract_first_article_info(summary_html: str) -> tuple:
    """
    Extract the first article's title from Google News summary HTML.

    Google News RSS summary contains aggregated headlines from multiple sources.
    This function parses the HTML to extract just the first article's information.

    Args:
        summary_html: HTML content from Google News RSS summary field

    Returns:
        Tuple of (article_title, source_name) or (None, None) if not found
    """
    if not summary_html:
        return None, None

    try:
        soup = BeautifulSoup(summary_html, 'html.parser')

        # Find first <li> which contains the primary article
        first_li = soup.find('li')
        if not first_li:
            return None, None

        # Extract the article title from the first link
        first_link = first_li.find('a')
        if first_link:
            article_title = first_link.get_text(strip=True)
        else:
            article_title = None

        # Extract source name from the <font> tag
        source_font = first_li.find('font')
        if source_font:
            source_name = source_font.get_text(strip=True)
        else:
            source_name = None

        return article_title, source_name

    except Exception as e:
        # If parsing fails, return None
        pass

    return None, None


async def fetch():
    """Fetch latest news from Google News RSS feed."""
    feed = feedparser.parse(RSS)
    topics = []

    for e in feed.entries[:40]:
        title = e.title
        summary_html = e.get("summary", "")

        # Extract first article info from aggregated summary
        article_title, source_name = extract_first_article_info(summary_html)

        # Use the extracted article title as description, or empty string
        # This gives us clean, single-article content instead of aggregated headlines
        description = article_title if article_title else ""

        # Detect language from title
        language = detect_language(title)

        # Use Google News wrapper URL (we skip it in content fetcher anyway)
        url = e.link

        topics.append(
            Topic(
                title=title,
                description=description,
                source="google_news",
                url=url,
                timestamp=datetime(*e.published_parsed[:6]) if hasattr(e, "published_parsed") else datetime.now(),
                metrics={},
                language=language,
            )
        )
    return topics
