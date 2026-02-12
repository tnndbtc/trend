# Trend Intelligence Platform - Crawler Service

Automated data collection service for gathering trends from multiple sources.

## Overview

The Crawler Service is responsible for:

- **Multi-source data collection** - Reddit, HackerNews, Google News, BBC, Reuters, AP, Al Jazeera, Guardian
- **Scheduled crawling** - Automatic collection based on configurable cron schedules
- **Plugin-based architecture** - Easy to add new data sources
- **Data normalization** - Standardizes data from different sources
- **Language detection** - Identifies content language for multi-language support
- **CJK support** - Handles Chinese, Japanese, Korean text with proper segmentation
- **Robust error handling** - Continues operating even if individual collectors fail

## Architecture

```
services/crawler/
├── src/
│   └── main.py          # Main crawler service
├── tests/               # Unit tests
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container image
└── README.md           # This file
```

## How It Works

```
┌─────────────┐
│  Scheduler  │ (APScheduler with cron triggers)
└──────┬──────┘
       │
       ├─> Reddit Collector (every 30 min)
       ├─> HackerNews Collector (every 20 min)
       ├─> Google News Collector (every 1 hour)
       ├─> News RSS Collectors (every 2-3 hours)
       │
       v
┌─────────────────┐
│ Plugin Manager  │ (Loads and manages collector plugins)
└────────┬────────┘
         │
         v
┌─────────────────┐
│   Collectors    │ (Extract data from sources)
└────────┬────────┘
         │
         v
┌─────────────────┐
│   Processing    │ (Normalize, detect language, clean)
└────────┬────────┘
         │
         v
┌─────────────────┐
│    Storage      │ (PostgreSQL + Redis cache)
└─────────────────┘
```

## Dependencies

The crawler service depends on:

1. **Infrastructure**:
   - PostgreSQL (port 5433) - store collected trends
   - Redis (port 6380) - caching

2. **Shared Libraries**:
   - `trend-agent-core` - storage, observability
   - `trend-agent-collectors` - collector plugins

3. **External APIs**:
   - Reddit API
   - HackerNews API
   - Google News RSS
   - News outlet RSS feeds

## Collectors

### Active Collectors

| Source | Type | Schedule | Items/Run |
|--------|------|----------|-----------|
| Reddit | API | Every 30 min | 100+ |
| HackerNews | API | Every 20 min | 30+ |
| Google News | RSS | Every 1 hour | 50+ |
| Guardian | RSS | Every 2 hours | 20+ |
| BBC | RSS | Every 2 hours | 20+ |
| Reuters | RSS | Every 2 hours | 20+ |
| AP News | RSS | Every 3 hours | 15+ |
| Al Jazeera | RSS | Every 3 hours | 15+ |

### Adding New Collectors

1. Create a new collector plugin in `packages/trend-agent-collectors/`:

```python
# packages/trend-agent-collectors/trend_agent/collectors/my_source.py
from trend_agent.collectors.base import BaseCollector

class MySourceCollector(BaseCollector):
    def __init__(self):
        super().__init__(name="my_source", description="My data source")

    async def collect_async(self) -> List[Dict]:
        # Implement collection logic
        return [{"title": "...", "url": "...", "content": "..."}]
```

2. Register in `__init__.py`:

```python
# packages/trend-agent-collectors/trend_agent/collectors/__init__.py
from .my_source import MySourceCollector

COLLECTORS = {
    "my_source": MySourceCollector,
    # ... other collectors
}
```

3. Add schedule in `main.py`:

```python
schedules = {
    "my_source": "0 * * * *",  # Every hour
}
```

## Development

### Local Setup

1. **Install dependencies**:
   ```bash
   # From repo root
   pip install -e packages/trend-agent-core
   pip install -e packages/trend-agent-collectors
   pip install -r services/crawler/requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5433
   export POSTGRES_DB=trends
   export POSTGRES_USER=trend_user
   export POSTGRES_PASSWORD=trend_password
   export REDIS_HOST=localhost
   export REDIS_PORT=6380
   export RUN_ON_STARTUP=true  # Run initial collection
   ```

3. **Configure API keys** (if needed):
   ```bash
   export REDDIT_CLIENT_ID=your_client_id
   export REDDIT_CLIENT_SECRET=your_secret
   export GOOGLE_NEWS_API_KEY=your_api_key  # Optional
   ```

4. **Run the crawler**:
   ```bash
   cd services/crawler
   python -m src.main
   ```

### Docker Development

```bash
# Build the crawler service
docker build -f services/crawler/Dockerfile -t trend-crawler:latest .

# Run the container
docker run \
  -e POSTGRES_HOST=host.docker.internal \
  -e REDIS_HOST=host.docker.internal \
  trend-crawler:latest
```

### Testing

```bash
# Run tests
pytest services/crawler/tests/

# Run specific collector tests
pytest services/crawler/tests/test_collectors.py

# Run with coverage
pytest services/crawler/tests/ --cov=crawler --cov-report=html
```

## Configuration

Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | localhost | PostgreSQL host |
| `POSTGRES_PORT` | 5433 | PostgreSQL port |
| `REDIS_HOST` | localhost | Redis host |
| `REDIS_PORT` | 6380 | Redis port |
| `RUN_ON_STARTUP` | true | Run collection on startup |
| `LOG_LEVEL` | INFO | Logging level |

### Collector-Specific Configuration

#### Reddit
- `REDDIT_CLIENT_ID` - Reddit API client ID
- `REDDIT_CLIENT_SECRET` - Reddit API secret
- `REDDIT_SUBREDDITS` - Comma-separated subreddits (default: "technology,programming,worldnews")

#### HackerNews
- `HACKERNEWS_TOP_STORIES` - Number of top stories to fetch (default: 30)

#### Google News
- `GOOGLE_NEWS_LANGUAGE` - Language code (default: "en")
- `GOOGLE_NEWS_COUNTRY` - Country code (default: "US")

## Scheduling

Collectors are scheduled using cron expressions:

```python
"*/30 * * * *"  # Every 30 minutes
"0 * * * *"     # Every hour at :00
"0 */2 * * *"   # Every 2 hours
"0 */6 * * *"   # Every 6 hours
```

### Custom Schedules

Override default schedules via environment:

```bash
export REDDIT_SCHEDULE="*/15 * * * *"  # Every 15 minutes instead of 30
export HACKERNEWS_SCHEDULE="*/10 * * * *"  # Every 10 minutes
```

## Data Flow

1. **Scheduler triggers** collector at scheduled time
2. **Collector fetches** data from external source
3. **Data is normalized**:
   - Extract title, URL, content, metadata
   - Detect language
   - Clean and validate data
4. **Data is stored**:
   - PostgreSQL (persistent storage)
   - Redis (cache for quick access)
5. **Metrics updated**:
   - Collection success/failure count
   - Items collected per source
   - Collection duration

## Error Handling

The crawler is designed to be resilient:

- **Individual collector failures** don't stop other collectors
- **Network errors** are retried with exponential backoff
- **API rate limits** are respected with automatic throttling
- **Invalid data** is logged but doesn't crash the service
- **Database connection errors** trigger reconnection attempts

### Error Recovery

```
Collector Error → Log Warning → Continue with Next Collector
                     ↓
              Update Error Metrics
                     ↓
           Retry on Next Schedule
```

## Monitoring

### Metrics

Prometheus metrics are exposed (when running with metrics endpoint):

```
# Collection metrics
trends_collected_total{source="reddit"}
trends_collection_errors_total{source="reddit"}
trends_collection_duration_seconds{source="reddit"}

# Scheduler metrics
scheduled_jobs_total
scheduled_jobs_running
scheduled_jobs_failed_total
```

### Logging

Structured logs are written to stdout:

```json
{
  "timestamp": "2024-02-12T10:30:00Z",
  "level": "INFO",
  "service": "crawler",
  "message": "Collected 127 items from reddit",
  "collector": "reddit",
  "items_count": 127,
  "duration_ms": 1234
}
```

### Health Checks

The crawler exposes health status:

- **Startup**: Service is initializing
- **Healthy**: Scheduler running, recent collections successful
- **Degraded**: Some collectors failing but service operational
- **Unhealthy**: Scheduler stopped or all collectors failing

## Language Support

The crawler handles multi-language content:

### Language Detection

Uses `langdetect` to identify content language:

```python
detected_language = detect(content)  # "en", "zh", "ja", "ko", etc.
```

### CJK Processing

For Chinese, Japanese, Korean text:

- **Chinese**: Jieba segmentation + Pinyin romanization
- **Japanese**: Kakasi romanization (Kanji → Romaji)
- **Korean**: Hangul romanization

### RTL Languages

Arabic, Hebrew, Persian text is handled correctly:

- Proper text direction
- RTL-aware truncation
- Unicode normalization

## Performance

### Optimization Tips

1. **Parallel collection**:
   ```python
   tasks = [run_collector(name) for name in collectors]
   await asyncio.gather(*tasks)
   ```

2. **Connection pooling**:
   - Reuse database connections
   - HTTP client session reuse

3. **Caching**:
   - Cache recently seen URLs to avoid duplicates
   - TTL-based cache invalidation

4. **Batch processing**:
   - Store results in batches instead of one-by-one
   - Use bulk insert queries

### Resource Usage

Typical resource consumption:

- **CPU**: 0.1-0.5 cores (spikes during collection)
- **Memory**: 200-500 MB
- **Network**: 10-100 KB/s (depends on sources)
- **Database**: ~100 writes/minute

## Deployment

### Docker Compose

```bash
cd infrastructure/docker
docker-compose up crawler
```

### Kubernetes

```bash
kubectl apply -k k8s/overlays/production
```

### Scaling

The crawler can be scaled horizontally with partitioning:

```yaml
# Instance 1: Social media
env:
  - name: ENABLED_COLLECTORS
    value: "reddit,hackernews"

# Instance 2: News outlets
env:
  - name: ENABLED_COLLECTORS
    value: "guardian,bbc,reuters,ap_news,al_jazeera"
```

## Troubleshooting

### No Data Being Collected

```
Running collector: reddit
Collected 0 items from reddit
```

**Solution**: Check API credentials and network connectivity:
```bash
export REDDIT_CLIENT_ID=...
export REDDIT_CLIENT_SECRET=...
curl https://www.reddit.com/r/technology.json  # Test accessibility
```

### Scheduler Not Running

```
Scheduler failed to start
```

**Solution**: Check for timezone issues:
```bash
export TZ=UTC
python -m src.main
```

### Database Connection Errors

```
Failed to connect to PostgreSQL
```

**Solution**: Verify database is accessible:
```bash
docker-compose up postgres
psql -h localhost -p 5433 -U trend_user -d trends
```

### Import Errors

```
ModuleNotFoundError: No module named 'trend_agent'
```

**Solution**: Install shared libraries:
```bash
pip install -e packages/trend-agent-core
pip install -e packages/trend-agent-collectors
```

## Related Services

- **API Service**: `services/api/` - Exposes collected data
- **Web Interface**: `services/web-interface/` - UI for browsing
- **Celery Worker**: `services/celery-worker/` - Background processing
- **Translation**: `services/translation-service/` - Translation pipeline

## Contributing

See the root `README.md` for contribution guidelines.

## License

See `LICENSE` in the root directory.
