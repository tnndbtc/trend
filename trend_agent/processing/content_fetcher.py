"""
Content fetcher module for extracting full article content from URLs.
"""
import asyncio
import aiohttp
import trafilatura
from typing import Optional
import logging
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def strip_html_tags(text: str) -> str:
    """
    Remove HTML tags and clean text content.

    Args:
        text: Text that may contain HTML tags

    Returns:
        Cleaned text without HTML tags
    """
    if not text:
        return ""

    try:
        # Use BeautifulSoup to parse and extract text
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()

        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text
    except Exception as e:
        logger.warning(f"Error stripping HTML: {e}")
        # Fallback: simple regex to remove tags
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


async def fetch_url_content(url: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch and extract the main content from a URL.

    Args:
        url: The URL to fetch content from
        timeout: Request timeout in seconds

    Returns:
        Extracted text content or None if fetch fails
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={'User-Agent': 'Mozilla/5.0 (compatible; TrendBot/1.0)'}
            ) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                    return None

                html = await response.text()

                # Use trafilatura to extract main content
                content = trafilatura.extract(
                    html,
                    include_comments=False,
                    include_tables=False,
                    no_fallback=False
                )

                if content:
                    # Limit content length to avoid token limits
                    max_length = 5000
                    if len(content) > max_length:
                        content = content[:max_length] + "..."

                    return content
                else:
                    logger.warning(f"Could not extract content from {url}")
                    return None

    except asyncio.TimeoutError:
        logger.warning(f"Timeout fetching {url}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching {url}: {str(e)}")
        return None


async def fetch_content_for_topic(topic) -> str:
    """
    Fetch full content for a topic based on its source and URL.

    Args:
        topic: Topic object with source, url, and description fields

    Returns:
        Full content text or existing description if fetch fails
    """
    # For Reddit posts with selftext, use the description (cleaned)
    if topic.source == 'reddit' and topic.description:
        return strip_html_tags(topic.description)

    # For other sources, try to fetch the full article
    if topic.url:
        content = await fetch_url_content(topic.url)
        if content:
            return content

    # Fallback to description if available (strip HTML tags)
    if topic.description:
        cleaned = strip_html_tags(topic.description)
        # If after stripping HTML we have very little content, use title
        if len(cleaned) < 20:
            return topic.title
        return cleaned

    # Last resort: just use the title
    return topic.title
