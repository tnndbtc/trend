"""
Shared utilities for all collectors.

This module contains common functionality used across multiple collectors,
including language detection, RSS parsing, and error handling.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from langdetect import detect, LangDetectException
import feedparser
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """
    Detect language of text, default to 'en' if detection fails.

    Args:
        text: Text to analyze

    Returns:
        ISO 639-1 language code (e.g., 'en', 'es', 'fr')
    """
    if not text or len(text.strip()) < 10:
        return 'en'

    try:
        return detect(text)
    except LangDetectException:
        return 'en'


def parse_rss_timestamp(entry: feedparser.FeedParserDict) -> datetime:
    """
    Extract timestamp from RSS feed entry.

    Tries multiple timestamp fields in order of preference:
    - published_parsed
    - updated_parsed
    - Falls back to current time

    Args:
        entry: RSS feed entry from feedparser

    Returns:
        datetime object
    """
    # Try published_parsed first
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6])
        except (TypeError, ValueError):
            pass

    # Try updated_parsed
    if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        try:
            return datetime(*entry.updated_parsed[:6])
        except (TypeError, ValueError):
            pass

    # Fallback to current time
    logger.warning(f"Could not parse timestamp for entry: {entry.get('title', 'Unknown')}")
    return datetime.now()


def clean_html(html_content: str) -> str:
    """
    Remove HTML tags and clean text content.

    Args:
        html_content: HTML string

    Returns:
        Plain text with HTML removed
    """
    if not html_content:
        return ""

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        return text
    except Exception as e:
        logger.warning(f"Error cleaning HTML: {e}")
        return html_content


def extract_rss_entry_data(entry: feedparser.FeedParserDict, source_name: str) -> Dict[str, Any]:
    """
    Extract standard fields from an RSS feed entry.

    Args:
        entry: RSS feed entry from feedparser
        source_name: Name of the source (e.g., 'bbc', 'reuters')

    Returns:
        Dictionary with extracted data ready for Topic creation
    """
    title = entry.get('title', '').strip()
    description = clean_html(entry.get('summary', '') or entry.get('description', ''))
    url = entry.get('link', '')
    timestamp = parse_rss_timestamp(entry)

    # Detect language
    text_for_detection = f"{title} {description}"
    language = detect_language(text_for_detection)

    return {
        'title': title,
        'description': description,
        'source': source_name,
        'url': url,
        'timestamp': timestamp,
        'metrics': {},
        'language': language,
    }


def safe_get_nested(data: Dict, *keys, default=None) -> Any:
    """
    Safely get nested dictionary values.

    Args:
        data: Dictionary to search
        *keys: Sequence of keys to traverse
        default: Default value if key path doesn't exist

    Returns:
        Value at key path or default

    Example:
        safe_get_nested(data, 'user', 'profile', 'name', default='Anonymous')
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return current if current is not None else default
