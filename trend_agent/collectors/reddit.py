import aiohttp
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import Topic

URL = "https://www.reddit.com/r/all/top.json?limit=50&t=day"


async def fetch():
    """Fetch top posts from Reddit's r/all."""
    async with aiohttp.ClientSession() as session:
        async with session.get(URL, headers={"User-Agent": "trend-agent/1.0"}) as resp:
            data = await resp.json()

    topics = []
    for post in data["data"]["children"]:
        p = post["data"]
        topics.append(
            Topic(
                title=p["title"],
                description=p.get("selftext", ""),
                source="reddit",
                url="https://reddit.com" + p["permalink"],
                timestamp=datetime.utcfromtimestamp(p["created_utc"]),
                metrics={"upvotes": p["ups"], "comments": p["num_comments"]},
            )
        )
    return topics
