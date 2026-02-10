import aiohttp
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import Topic
from .utils import detect_language
from . import register_collector

TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"


async def fetch():
    """Fetch top stories from Hacker News."""
    async with aiohttp.ClientSession() as session:
        async with session.get(TOP_URL) as resp:
            ids = await resp.json()

        topics = []
        for i in ids[:30]:
            async with session.get(
                f"https://hacker-news.firebaseio.com/v0/item/{i}.json"
            ) as r:
                item = await r.json()

            if item and item.get("title"):
                title = item.get("title", "")
                language = detect_language(title)

                topics.append(
                    Topic(
                        title=title,
                        description="",
                        source="hackernews",
                        url=item.get("url", f"https://news.ycombinator.com/item?id={i}"),
                        timestamp=datetime.utcfromtimestamp(item["time"]),
                        metrics={"score": item.get("score", 0)},
                        language=language,
                    )
                )
    return topics


# Register this collector
register_collector('hackernews', fetch)
