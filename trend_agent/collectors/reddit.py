import aiohttp
from datetime import datetime
import sys
import os
from langdetect import detect, LangDetectException

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import Topic

URL = "https://www.reddit.com/r/all/top.json?limit=50&t=day"


def detect_language(text: str) -> str:
    """Detect language of text, default to 'en' if detection fails."""
    if not text or len(text.strip()) < 10:
        return 'en'
    try:
        return detect(text)
    except LangDetectException:
        return 'en'


async def fetch():
    """Fetch top posts from Reddit's r/all."""
    async with aiohttp.ClientSession() as session:
        async with session.get(URL, headers={"User-Agent": "trend-agent/1.0"}) as resp:
            data = await resp.json()

    topics = []
    for post in data["data"]["children"]:
        p = post["data"]
        title = p["title"]
        description = p.get("selftext", "")

        # Detect language from title and description
        text_for_detection = f"{title} {description}"
        language = detect_language(text_for_detection)

        topics.append(
            Topic(
                title=title,
                description=description,
                source="reddit",
                url="https://reddit.com" + p["permalink"],
                timestamp=datetime.utcfromtimestamp(p["created_utc"]),
                metrics={"upvotes": p["ups"], "comments": p["num_comments"]},
                language=language,
            )
        )
    return topics
