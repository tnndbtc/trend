# Wenxuecity Custom Collector Plugin Example

This is an example of custom plugin code for collecting news from wenxuecity.com.

## Plugin Code Template

Copy this code into the "Plugin Code" field when creating the wenxuecity source in Django admin:

```python
"""
Wenxuecity News Collector
Collects latest news from wenxuecity.com RSS feed or web scraping
"""

from typing import List, Dict, Any
from datetime import datetime
import asyncio

# Import required schemas
from trend_agent.schemas import RawItem, Metrics, SourceType


async def collect(config: Dict[str, Any]) -> List[RawItem]:
    """
    Collect news items from wenxuecity.

    Args:
        config: Configuration dictionary with URL, filters, etc.

    Returns:
        List of RawItem objects
    """
    import httpx
    from bs4 import BeautifulSoup

    items = []
    url = config.get('url', 'https://www.wenxuecity.com/')

    try:
        # Use httpx for async HTTP requests
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Example: Fetch from RSS feed if available
            # Adjust the URL based on wenxuecity's actual RSS feed
            response = await client.get(url)
            response.raise_for_status()

            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')

            # Example: Find news articles (adjust selectors based on actual site structure)
            # This is a PLACEHOLDER - you need to inspect wenxuecity.com and update selectors
            articles = soup.select('.article, .news-item, .post')[:20]  # Get up to 20 articles

            for article in articles:
                try:
                    # Extract article details (adjust selectors for actual site)
                    title_elem = article.select_one('h2, h3, .title, a')
                    link_elem = article.select_one('a')
                    desc_elem = article.select_one('.description, .summary, p')

                    if not title_elem or not link_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = link_elem.get('href', '')
                    description = desc_elem.get_text(strip=True) if desc_elem else ''

                    # Make URL absolute if relative
                    if link and not link.startswith('http'):
                        link = f"https://www.wenxuecity.com{link}"

                    # Create RawItem
                    item = RawItem(
                        source=SourceType.CUSTOM,  # Use CUSTOM for custom sources
                        source_id=link,  # Use URL as unique ID
                        url=link,
                        title=title,
                        description=description,
                        published_at=datetime.utcnow(),  # Use current time if date not available
                        metrics=Metrics(
                            upvotes=0,
                            comments=0,
                            score=0
                        ),
                        metadata={
                            'source_name': 'wenxuecity',
                            'language': 'zh'  # Chinese
                        },
                        language='zh'  # Chinese language code
                    )

                    items.append(item)

                except Exception as e:
                    # Skip articles that fail to parse
                    continue

        return items

    except Exception as e:
        # Log error but don't crash
        print(f"Failed to collect from wenxuecity: {e}")
        return []
```

## Alternative: RSS Feed Version

If wenxuecity has an RSS feed, use this simpler version:

```python
"""
Wenxuecity RSS Collector
"""

from typing import List, Dict, Any
from datetime import datetime
import asyncio

from trend_agent.schemas import RawItem, Metrics, SourceType


async def collect(config: Dict[str, Any]) -> List[RawItem]:
    """Collect from wenxuecity RSS feed."""
    import httpx
    import feedparser
    from dateutil import parser as date_parser

    items = []
    rss_url = config.get('url', 'https://www.wenxuecity.com/news/rss.xml')

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(rss_url)
            response.raise_for_status()

            # Parse RSS feed
            feed = feedparser.parse(response.text)

            for entry in feed.entries[:20]:  # Limit to 20 items
                try:
                    # Parse published date
                    published_at = datetime.utcnow()
                    if hasattr(entry, 'published'):
                        try:
                            published_at = date_parser.parse(entry.published)
                        except:
                            pass

                    item = RawItem(
                        source=SourceType.CUSTOM,
                        source_id=entry.get('id', entry.get('link', '')),
                        url=entry.get('link', ''),
                        title=entry.get('title', ''),
                        description=entry.get('summary', ''),
                        published_at=published_at,
                        metrics=Metrics(upvotes=0, comments=0, score=0),
                        metadata={'source_name': 'wenxuecity'},
                        language='zh'
                    )

                    items.append(item)

                except Exception as e:
                    continue

        return items

    except Exception as e:
        print(f"Failed to collect from wenxuecity RSS: {e}")
        return []
```

## Setup Instructions

1. **Access Django Admin**
   ```bash
   # Navigate to http://localhost:8000/admin/
   # Login with your admin credentials
   ```

2. **Create Wenxuecity Source**
   - Go to **Crawler Sources** section
   - Click **Add Crawler Source**
   - Fill in the following fields:
     - **Name**: `wenxuecity`
     - **Source Type**: `Custom Plugin`
     - **Description**: `Wenxuecity Chinese news`
     - **URL**: `https://www.wenxuecity.com/news/` (or RSS feed URL if available)
     - **Enabled**: ✓ Check this box
     - **Schedule**: `0 */2 * * *` (every 2 hours)
     - **Language**: `zh` (Chinese)
     - **Plugin Code**: Paste one of the code templates above

3. **Important: Update the Selectors**
   - Visit https://www.wenxuecity.com/ in your browser
   - Right-click and "Inspect" to see the HTML structure
   - Update the CSS selectors in the plugin code to match the actual site structure
   - Common selectors to look for:
     - Article containers: `.article`, `.news-item`, `.post`, etc.
     - Title elements: `h2`, `h3`, `.title`, etc.
     - Link elements: `a` tags
     - Description elements: `.summary`, `.description`, `p`, etc.

4. **Test the Collection**
   - Save the source in Django admin
   - Select the wenxuecity source
   - Use the admin action: **"▶ Trigger collection"**
   - Check the logs for any errors
   - Check **Collected Topics** to see if items were collected

## Troubleshooting

### No items collected
- Check the plugin code has a `collect` function
- Verify the URL is correct
- Update CSS selectors to match the actual site
- Check logs for error messages

### "SandboxSecurityError"
- Plugin code is using forbidden functions
- Only use allowed imports: httpx, BeautifulSoup, feedparser, datetime, json, re
- Don't use: open, file, eval, exec, import (except allowed modules)

### Connection timeout
- Increase `timeout_seconds` in source configuration
- Check if the website is accessible
- Try a different URL

## Notes

- The plugin code runs in a **sandboxed environment** for security
- Only whitelisted Python modules can be imported
- Maximum execution time: 30 seconds (configurable)
- Memory limit: 100MB
