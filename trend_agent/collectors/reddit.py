import aiohttp
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import Topic
from .utils import detect_language
from . import register_collector

URL = "https://www.reddit.com/r/all/top.json?limit=50&t=day"


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

        # Determine the correct URL to use based on post type
        # - Text posts (is_self): use permalink
        # - Media posts (images, videos): use permalink
        # - External link posts: use the external URL
        is_self = p.get("is_self", False)
        post_hint = p.get("post_hint", "")
        post_url = p.get("url", "")

        if is_self or post_hint in ["image", "hosted:video", "rich:video"] or "i.redd.it" in post_url or "v.redd.it" in post_url:
            # For self/media posts, use Reddit discussion permalink
            url = "https://reddit.com" + p["permalink"]
        else:
            # For external link posts, use the actual URL
            url = post_url

        topics.append(
            Topic(
                title=title,
                description=description,
                source="reddit",
                url=url,
                timestamp=datetime.utcfromtimestamp(p["created_utc"]),
                metrics={"upvotes": p["ups"], "comments": p["num_comments"]},
                language=language,
            )
        )
    return topics


# Register this collector
register_collector('reddit', fetch)
