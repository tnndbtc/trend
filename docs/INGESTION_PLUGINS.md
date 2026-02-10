```markdown
# Ingestion Plugin System

## Overview

The Trend Intelligence Platform uses a flexible, plugin-based architecture for data collection. This allows easy addition of new data sources without modifying core code.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                   Scheduler                              │
│  • Cron-based scheduling                                │
│  • On-demand triggering                                 │
│  • Job tracking                                         │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ├──► PluginManager ──► PluginRegistry
                  │     • Discovery                  │
                  │     • Enable/Disable             │
                  │     • Status tracking            │
                  │                                  │
                  ├──► HealthChecker                │
                  │     • Success/failure tracking  │
                  │     • Health history            │
                  │     • Failure threshold         │
                  │                                  │
                  └──► RateLimiter                  │
                        • Sliding window             │
                        • Per-plugin quotas          │
                        • Redis-backed (optional)    │
                                                     │
                                                     ▼
                        ┌─────────────────────────────────┐
                        │    CollectorPlugin (ABC)        │
                        │  • collect()                    │
                        │  • validate()                   │
                        │  • on_success()                 │
                        │  • on_error()                   │
                        └─────────────────────────────────┘
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           │                          │                          │
      RedditCollector        HackerNewsCollector         BBCCollector
      GuardianCollector      ReutersCollector           APNewsCollector
      AlJazeeraCollector     GoogleNewsCollector        ...
```

## Creating a New Collector

### 1. Basic Collector

```python
from trend_agent.ingestion.base import CollectorPlugin, register_collector
from trend_agent.types import PluginMetadata, RawItem, SourceType
from typing import List

@register_collector
class MyCollector(CollectorPlugin):
    """Collector for My Data Source."""

    metadata = PluginMetadata(
        name="my_source",
        version="1.0.0",
        author="Your Name",
        description="Collects data from My Source",
        source_type=SourceType.CUSTOM,
        schedule="*/30 * * * *",  # Every 30 minutes
        enabled=True,
        rate_limit=60,  # 60 requests per hour
        timeout_seconds=30,
        retry_count=3,
    )

    async def collect(self) -> List[RawItem]:
        """Collect data from the source."""
        # Your collection logic here
        items = []

        # Example: Fetch from API
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.example.com/data") as resp:
                data = await resp.json()

                for entry in data:
                    item = RawItem(
                        source=SourceType.CUSTOM,
                        source_id=entry["id"],
                        url=entry["url"],
                        title=entry["title"],
                        description=entry.get("description"),
                        published_at=datetime.fromisoformat(entry["published"]),
                        metrics=Metrics(
                            upvotes=entry.get("likes", 0),
                            comments=entry.get("comments", 0),
                        ),
                    )
                    items.append(item)

        return items

    async def validate(self, item: RawItem) -> bool:
        """Validate collected items."""
        return item.title and item.url
```

### 2. RSS-Based Collector

For RSS feeds, use the `BaseRSSCollector`:

```python
from trend_agent.collectors.base_rss import BaseRSSCollector
from trend_agent.ingestion.base import register_collector
from trend_agent.types import PluginMetadata, SourceType

@register_collector
class MyNewsCollector(BaseRSSCollector):
    """Collector for My News Source."""

    rss_url = "https://mynewssite.com/rss"
    max_items = 40

    metadata = PluginMetadata(
        name="my_news",
        version="1.0.0",
        author="Your Name",
        description="Collects from My News RSS feed",
        source_type=SourceType.CUSTOM,
        schedule="*/20 * * * *",
        enabled=True,
        rate_limit=60,
        timeout_seconds=30,
        retry_count=3,
    )
```

### 3. Custom RSS Parsing

Override `parse_entry()` for custom RSS parsing:

```python
@register_collector
class CustomRSSCollector(BaseRSSCollector):
    rss_url = "https://example.com/rss"

    metadata = PluginMetadata(...)

    async def parse_entry(self, entry) -> RawItem:
        """Custom RSS entry parsing."""
        # Your custom parsing logic
        title = entry.title
        url = entry.link

        # Extract custom fields
        custom_data = entry.get("custom_namespace:field")

        return RawItem(...)
```

## Plugin Manager

### Initialization

```python
from trend_agent.ingestion import DefaultPluginManager

manager = DefaultPluginManager(
    plugin_dir="/path/to/collectors",  # Optional
    auto_discover=True
)
```

### Loading Plugins

```python
# Load all plugins from directory
plugins = await manager.load_plugins()
print(f"Loaded {len(plugins)} plugins")

# Get plugin by name
plugin = manager.get_plugin("reddit")

# Get enabled plugins only
enabled_plugins = manager.get_enabled_plugins()
```

### Plugin Control

```python
# Enable/disable plugins
await manager.enable_plugin("reddit")
await manager.disable_plugin("bbc")

# Get plugin status
status = await manager.get_plugin_status("reddit")
print(f"Version: {status['version']}")
print(f"Enabled: {status['enabled']}")

# Get all plugin status
all_status = await manager.get_all_plugin_status()
```

## Health Monitoring

### Initialization

```python
from trend_agent.ingestion import DefaultHealthChecker

checker = DefaultHealthChecker(
    max_history_size=1000,
    health_check_interval=60,
    failure_threshold=3  # Mark unhealthy after 3 consecutive failures
)
```

### Tracking Health

```python
# Record success
await checker.record_success("reddit")

# Record failure
await checker.record_failure("reddit", "Connection timeout")

# Check plugin health
health = await checker.check_health(plugin)
print(f"Healthy: {health.is_healthy}")
print(f"Consecutive failures: {health.consecutive_failures}")
print(f"Success rate: {health.success_rate:.1%}")

# Get health history
history = await checker.get_health_history("reddit", hours=24)

# Get unhealthy plugins
unhealthy = checker.get_unhealthy_plugins()
```

## Rate Limiting

### In-Memory Rate Limiter

```python
from trend_agent.ingestion import InMemoryRateLimiter

limiter = InMemoryRateLimiter(
    default_limit=100,  # Requests per hour
    window_seconds=3600
)
```

### Redis Rate Limiter (Distributed)

```python
from trend_agent.ingestion import RedisRateLimiter
import redis.asyncio as redis

redis_client = await redis.from_url("redis://localhost:6379")

limiter = RedisRateLimiter(
    redis_client=redis_client,
    default_limit=100,
    window_seconds=3600,
    key_prefix="ratelimit"
)
```

### Using Rate Limiter

```python
# Check if request is allowed
can_run = await limiter.check_rate_limit("reddit")

if can_run:
    # Record the request
    await limiter.record_request("reddit")

    # Execute collection
    items = await plugin.collect()

# Get remaining quota
remaining = await limiter.get_remaining_quota("reddit")
print(f"Remaining: {remaining} requests")

# Reset quota (admin use)
await limiter.reset_quota("reddit")
```

## Scheduler

### Initialization

```python
from trend_agent.ingestion import DefaultScheduler

scheduler = DefaultScheduler(
    health_checker=checker,  # Optional
    rate_limiter=limiter,    # Optional
    storage_repo=repo        # Optional
)

await scheduler.start()
```

### Scheduling Plugins

```python
# Schedule with cron expression
job_id = await scheduler.schedule_plugin(plugin, "*/30 * * * *")

# Common cron expressions:
# "*/15 * * * *"  - Every 15 minutes
# "0 * * * *"     - Every hour
# "0 */2 * * *"   - Every 2 hours
# "0 0 * * *"     - Daily at midnight
# "0 0 * * 0"     - Weekly on Sunday

# Schedule all enabled plugins
scheduled = await scheduler.schedule_all_plugins()
```

### Manual Triggering

```python
# Trigger immediate execution
task_id = await scheduler.trigger_now("reddit")

# Get next run time
next_run = await scheduler.get_next_run("reddit")
print(f"Next run: {next_run}")

# Get full schedule
schedule = await scheduler.get_schedule()
for plugin_name, next_time in schedule.items():
    print(f"{plugin_name}: {next_time}")
```

### Cleanup

```python
# Unschedule a plugin
await scheduler.unschedule_plugin("reddit")

# Shutdown scheduler
await scheduler.shutdown()
```

## Complete Example

```python
import asyncio
from trend_agent.ingestion import (
    DefaultPluginManager,
    DefaultHealthChecker,
    InMemoryRateLimiter,
    DefaultScheduler,
)

async def main():
    # Initialize components
    manager = DefaultPluginManager()
    checker = DefaultHealthChecker(failure_threshold=3)
    limiter = InMemoryRateLimiter(default_limit=100)
    scheduler = DefaultScheduler(
        health_checker=checker,
        rate_limiter=limiter
    )

    # Load plugins
    plugins = await manager.load_plugins()
    print(f"Loaded {len(plugins)} plugins")

    # Start scheduler
    await scheduler.start()

    try:
        # Schedule all enabled plugins
        scheduled = await scheduler.schedule_all_plugins()
        print(f"Scheduled {len(scheduled)} plugins")

        # Monitor for 60 seconds
        await asyncio.sleep(60)

        # Check health
        all_health = await checker.check_all_health()
        for name, health in all_health.items():
            print(f"{name}: healthy={health.is_healthy}, runs={health.total_runs}")

    finally:
        await scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

## Available Collectors

### Social Media
- **Reddit** (`reddit`) - r/all top posts
- **Hacker News** (`hackernews`) - Top stories

### News Sources
- **BBC** (`bbc`) - BBC News RSS
- **The Guardian** (`guardian`) - World news
- **Reuters** (`reuters`) - International news
- **AP News** (`ap_news`) - Associated Press
- **Al Jazeera** (`al_jazeera`) - Middle East focus
- **Google News** (`google_news`) - Aggregated news

## Testing

### Unit Tests

```bash
# Run all ingestion plugin tests
pytest tests/test_ingestion_plugins.py -v

# Run specific test
pytest tests/test_ingestion_plugins.py::test_plugin_registration -v

# Run with coverage
pytest tests/test_ingestion_plugins.py --cov=trend_agent.ingestion
```

### Integration Tests

```bash
# Run demo script
python examples/plugin_system_demo.py
```

## Configuration

### Environment Variables

```bash
# Redis (for distributed rate limiting)
REDIS_HOST=localhost
REDIS_PORT=6379

# Plugin settings
PLUGIN_DIR=/app/trend_agent/collectors
PLUGIN_AUTO_DISCOVER=true

# Rate limiting
DEFAULT_RATE_LIMIT=100
RATE_LIMIT_WINDOW=3600

# Health checking
HEALTH_FAILURE_THRESHOLD=3
HEALTH_CHECK_INTERVAL=60
```

### Config File (config.yaml)

```yaml
ingestion:
  plugins:
    auto_discover: true
    directory: /app/trend_agent/collectors

  health:
    failure_threshold: 3
    check_interval_seconds: 60
    history_size: 1000

  rate_limiting:
    enabled: true
    default_limit: 100
    window_seconds: 3600
    backend: redis  # or "memory"

  scheduling:
    enabled: true
    timezone: UTC
```

## Best Practices

### 1. Error Handling

Always handle errors gracefully in collectors:

```python
async def collect(self) -> List[RawItem]:
    try:
        # Collection logic
        items = await self._fetch_data()
        return items
    except aiohttp.ClientError as e:
        logger.error(f"Network error: {e}")
        raise CollectionError(f"Failed to fetch data: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise
```

### 2. Timeout Handling

Use timeouts to prevent hanging:

```python
async def collect(self) -> List[RawItem]:
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Fetch data
        ...
```

### 3. Validation

Implement proper validation:

```python
async def validate(self, item: RawItem) -> bool:
    # Check required fields
    if not item.title or not item.url:
        return False

    # Check content quality
    if len(item.title) < 10:
        return False

    # Filter unwanted content
    if any(spam_word in item.title.lower() for spam_word in ["spam", "ads"]):
        return False

    return True
```

### 4. Logging

Use structured logging:

```python
import logging

logger = logging.getLogger(__name__)

async def collect(self) -> List[RawItem]:
    logger.info(f"Starting collection from {self.metadata.name}")

    items = await self._fetch_data()

    logger.info(
        f"Collection complete",
        extra={
            "plugin": self.metadata.name,
            "item_count": len(items),
            "duration_ms": elapsed_ms
        }
    )

    return items
```

### 5. Resource Cleanup

Always clean up resources:

```python
async def collect(self) -> List[RawItem]:
    session = aiohttp.ClientSession()
    try:
        # Use session
        ...
    finally:
        await session.close()
```

## Troubleshooting

### Plugin Not Discovered

- Check plugin file is in `trend_agent/collectors/` directory
- Ensure class inherits from `CollectorPlugin`
- Verify `@register_collector` decorator is used
- Check plugin has valid `metadata` attribute

### Rate Limit Errors

- Check plugin's `rate_limit` in metadata
- Verify rate limiter is configured correctly
- Use `get_remaining_quota()` to debug
- Consider increasing limits or window size

### Health Check Failures

- Check `failure_threshold` setting
- Review plugin logs for errors
- Use `get_health_history()` to analyze patterns
- Reset health after fixing issues: `checker.reset_health(name)`

### Scheduler Issues

- Verify cron expression is valid
- Check scheduler is started: `await scheduler.start()`
- Use `get_next_run()` to verify schedule
- Check logs for execution errors

## Performance Tips

1. **Concurrent Collection**: Use `asyncio.gather()` for parallel requests
2. **Connection Pooling**: Reuse aiohttp sessions
3. **Caching**: Cache API responses when appropriate
4. **Batch Processing**: Collect multiple items per request
5. **Exponential Backoff**: Implement retry logic with delays

## Contributing

To add a new collector:

1. Create plugin class in `trend_agent/collectors/`
2. Add tests in `tests/test_collectors/`
3. Update this documentation
4. Submit PR with example usage

## License

MIT License - see LICENSE file
```
