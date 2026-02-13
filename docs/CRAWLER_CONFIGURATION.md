# Crawler Configuration Guide

This guide explains how to configure the trend collection crawler, including post limits, source diversity, and category settings.

---

## Table of Contents

1. [Overview](#overview)
2. [Default Configuration](#default-configuration)
3. [Command-Line Options](#command-line-options)
4. [Usage Examples](#usage-examples)
5. [Database Size Considerations](#database-size-considerations)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The `collect_trends` management command crawls multiple sources for trending topics, processes them through AI summarization, and organizes them into categories. The crawler's behavior can be customized through command-line arguments.

**Key Features:**
- Collects trending topics from multiple sources (Reddit, Hacker News, etc.)
- Automatically categorizes and clusters related topics
- Generates AI summaries for each topic
- Supports source diversity controls
- Configurable post limits per category

---

## Default Configuration

### Post Limit per Category

**Default:** 1000 posts per category

This means each category (e.g., Technology, Politics, Health) can contain up to 1000 trending posts after processing.

**Why 1000?**
- Provides comprehensive coverage of trending topics
- Balances between data richness and database size
- Suitable for production environments with regular cleanup
- Can be adjusted based on your specific needs

---

## Command-Line Options

### `--max-posts-per-category`

Controls the maximum number of posts to keep in each category after clustering and deduplication.

**Type:** Integer
**Default:** 1000
**Range:** 1 - unlimited (practical limit: 10,000)

**Syntax:**
```bash
python manage.py collect_trends --max-posts-per-category <number>
```

---

## Usage Examples

### Basic Usage (Default Settings)

Run the crawler with default settings (1000 posts per category):

```bash
# Using docker-compose
docker compose exec web python manage.py collect_trends

# Direct Python (if running locally)
python manage.py collect_trends
```

### Testing with Smaller Limits

**Recommended for initial testing:**

```bash
# Very small test (10 posts per category)
docker compose exec web python manage.py collect_trends --max-posts-per-category 10

# Medium test (50 posts per category)
docker compose exec web python manage.py collect_trends --max-posts-per-category 50

# Production trial (100 posts per category)
docker compose exec web python manage.py collect_trends --max-posts-per-category 100
```

### Production Usage

**For production environments:**

```bash
# Conservative limit (useful for frequent runs)
docker compose exec web python manage.py collect_trends --max-posts-per-category 200

# Standard limit (good balance)
docker compose exec web python manage.py collect_trends --max-posts-per-category 500

# Maximum coverage (default)
docker compose exec web python manage.py collect_trends --max-posts-per-category 1000

# Extended coverage (for research/archival)
docker compose exec web python manage.py collect_trends --max-posts-per-category 2000
```

### Scheduled Runs with Cron

Set up automated collection with different limits:

```bash
# Crontab example: Run every hour with conservative limit
0 * * * * cd /app && python manage.py collect_trends --max-posts-per-category 100

# Run every 6 hours with higher limit
0 */6 * * * cd /app && python manage.py collect_trends --max-posts-per-category 500

# Daily comprehensive collection
0 0 * * * cd /app && python manage.py collect_trends --max-posts-per-category 1000
```

---

## Database Size Considerations

### Estimating Database Growth

**Per Post Storage:**
- Topic metadata: ~2 KB
- Full content: ~5-20 KB (varies by source)
- AI summary: ~1-2 KB
- **Average per post:** ~10 KB

**Example Calculations:**

| Posts/Category | Categories | Total Posts | Est. Database Size |
|---------------|-----------|-------------|-------------------|
| 10            | 10        | 100         | ~1 MB             |
| 50            | 10        | 500         | ~5 MB             |
| 100           | 10        | 1,000       | ~10 MB            |
| 500           | 10        | 5,000       | ~50 MB            |
| 1000          | 10        | 10,000      | ~100 MB           |
| 2000          | 10        | 20,000      | ~200 MB           |

**Note:** These are estimates per collection run. Multiple runs will accumulate data.

### Database Maintenance

**Regular Cleanup Recommended:**

```bash
# Delete collections older than 7 days
docker compose exec web python manage.py shell
>>> from trends_viewer.models import CollectionRun
>>> from django.utils import timezone
>>> from datetime import timedelta
>>> old_date = timezone.now() - timedelta(days=7)
>>> CollectionRun.objects.filter(timestamp__lt=old_date).delete()
```

**Create a cleanup management command** (future enhancement):

```python
# manage.py cleanup_old_collections --days 7
```

---

## Best Practices

### 1. Start Small, Scale Up

**Recommended Testing Sequence:**
```bash
# Step 1: Verify setup works (10 posts)
docker compose exec web python manage.py collect_trends --max-posts-per-category 10

# Step 2: Test performance (50 posts)
docker compose exec web python manage.py collect_trends --max-posts-per-category 50

# Step 3: Production trial (100-200 posts)
docker compose exec web python manage.py collect_trends --max-posts-per-category 100

# Step 4: Full deployment (500-1000 posts)
docker compose exec web python manage.py collect_trends --max-posts-per-category 500
```

### 2. Monitor Resource Usage

**Watch for:**
- Database disk space
- Memory usage during collection
- API rate limits (for content fetching)
- LLM API costs (for summarization)

### 3. Frequency vs. Limit Trade-offs

**High Frequency + Low Limit:**
- Run every hour with 100-200 posts
- Keeps data fresh
- Lower storage needs
- Good for real-time dashboards

**Low Frequency + High Limit:**
- Run daily with 1000-2000 posts
- Comprehensive coverage
- Higher storage needs
- Good for research/archival

### 4. Source Diversity

The crawler includes source diversity controls (see `trend_agent/config.py`):

```python
# Ensure balanced representation across sources
MAX_PERCENTAGE_PER_SOURCE = 0.20  # 20% max from any single source
```

This prevents any single source from dominating the results.

---

## Troubleshooting

### Issue: "Out of memory during collection"

**Solution:** Reduce the `--max-posts-per-category` limit:
```bash
docker compose exec web python manage.py collect_trends --max-posts-per-category 100
```

### Issue: "Collection takes too long"

**Causes:**
- Too many posts (reduce limit)
- Slow content fetching (check network)
- LLM summarization delays (check API quotas)

**Solutions:**
```bash
# Reduce posts per category
--max-posts-per-category 200

# Check which step is slow by monitoring logs
docker compose logs -f web
```

### Issue: "Database disk full"

**Solution:** Clean up old collections:
```bash
# Access Django shell
docker compose exec web python manage.py shell

# Delete old data
>>> from trends_viewer.models import CollectionRun
>>> from django.utils import timezone
>>> from datetime import timedelta
>>> CollectionRun.objects.filter(
...     timestamp__lt=timezone.now() - timedelta(days=7)
... ).delete()
```

### Issue: "API rate limits exceeded"

**Causes:**
- Too many posts triggering too many API calls
- Summarization batches too large

**Solutions:**
```bash
# Reduce posts per category
--max-posts-per-category 100

# Adjust batch size in collect_trends.py (line 263)
BATCH_SIZE = 10  # Reduce from 15
```

---

## Related Configuration

### Categories

Categories are defined in `trend_agent/categories.py`. Each category gets its own post limit:

```python
CATEGORIES = [
    "Technology",
    "Politics",
    "Health",
    "Science",
    "Business",
    # ... add more categories
]
```

**Total posts = `--max-posts-per-category` × number of categories**

### Source Diversity

Configured in `trend_agent/config.py`:

```python
# Enable source diversity limiting
ENABLE_SOURCE_DIVERSITY = True

# Maximum percentage per source (default: 20%)
MAX_PERCENTAGE_PER_SOURCE = 0.20
```

---

## Summary

- **Default:** 1000 posts per category
- **Start with:** 10-50 posts for testing
- **Production:** 100-500 posts depending on frequency
- **Monitor:** Database size, API costs, memory usage
- **Clean up:** Regularly delete old collections

For more information:
- See `DYNAMIC_SOURCE_MANAGEMENT.md` for adding new sources
- See `TRANSLATION.md` for translation configuration
- See `MONITORING.md` for observability setup

---

**Last Updated:** February 2024
**Version:** 1.0
