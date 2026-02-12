
# Dynamic Crawler Source Management System

## Complete Guide: Setup, Configuration, and Usage

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup & Installation](#setup--installation)
4. [Usage Guide](#usage-guide)
5. [API Reference](#api-reference)
6. [Examples](#examples)
7. [Security](#security)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The Dynamic Crawler Source Management System allows you to add, configure, and manage data collection sources without code changes or application restarts. The system provides:

### Key Features

✅ **Web UI & REST API** - Manage sources via Django Admin or API endpoints
✅ **Hot Reload** - Changes take effect immediately without restart
✅ **Multi-Source Support** - RSS feeds, Twitter, Reddit, YouTube, custom plugins
✅ **Sandboxed Execution** - Secure custom plugin code execution
✅ **Authentication** - API keys, OAuth 2.0, custom headers
✅ **Content Filtering** - Keywords, categories, language, date ranges
✅ **Health Monitoring** - Track success rates, failures, performance
✅ **Rate Limiting** - Per-source request limits
✅ **Encrypted Storage** - API keys encrypted at rest

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Admin Interfaces                          │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Django Admin    │         │   FastAPI REST   │         │
│  │   /admin/        │         │  /admin/sources  │         │
│  └────────┬─────────┘         └────────┬─────────┘         │
│           │                            │                     │
│           └────────────┬───────────────┘                     │
└────────────────────────┼─────────────────────────────────────┘
                         │
            ┌────────────▼────────────┐
            │   CrawlerSource Model   │
            │     (PostgreSQL)        │
            └────────────┬────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐   ┌─────▼──────┐  ┌────▼────┐
    │ Dynamic │   │ Hot Reload │  │  Auth   │
    │ Loader  │   │  Monitor   │  │ Handler │
    └────┬────┘   └─────┬──────┘  └────┬────┘
         │              │              │
         │     ┌────────▼────────┐     │
         │     │   Sandbox       │     │
         │     │  (Custom Code)  │     │
         │     └─────────────────┘     │
         │                             │
    ┌────▼─────────────────────────────▼────┐
    │        Collector Plugins               │
    │  RSS │ Twitter │ Reddit │ Custom      │
    └────┬─────────────────────────────┬────┘
         │                             │
    ┌────▼─────────────────────────────▼────┐
    │         Content Filters                │
    │  Keywords │ Language │ Categories      │
    └────┬─────────────────────────────┬────┘
         │                             │
    ┌────▼─────────────────────────────▼────┐
    │      Data Processing Pipeline          │
    └───────────────────────────────────────┘
```

### Key Modules

- **`/web_interface/trends_viewer/models.py`** - CrawlerSource Django model
- **`/web_interface/trends_viewer/admin.py`** - Django admin interface
- **`/api/routers/admin.py`** - FastAPI REST endpoints
- **`/api/schemas/source.py`** - Pydantic schemas
- **`/trend_agent/ingestion/dynamic_loader.py`** - Dynamic plugin factory
- **`/trend_agent/ingestion/hot_reload.py`** - Hot reload system
- **`/trend_agent/ingestion/sandbox.py`** - Secure code execution
- **`/trend_agent/ingestion/auth.py`** - Authentication handlers
- **`/trend_agent/ingestion/filters.py`** - Content filtering

---

## Setup & Installation

### 1. Install Dependencies

```bash
pip install cryptography feedparser httpx
```

### 2. Configure Django Settings

Add encryption key to `/web_interface/web_interface/settings.py`:

```python
from cryptography.fernet import Fernet

# Generate key (do this once, then store securely)
# key = Fernet.generate_key()

CRAWLER_SOURCE_ENCRYPTION_KEY = "your-secret-encryption-key-here"
```

### 3. Run Migrations

```bash
cd /home/tnnd/data/code/trend/web_interface
python manage.py migrate
```

### 4. Initialize System

In your main application startup:

```python
from trend_agent.ingestion.dynamic_loader import get_dynamic_loader
from trend_agent.ingestion.hot_reload import initialize_hot_reload

async def startup():
    # Load dynamic sources from database
    loader = get_dynamic_loader()
    await loader.load_from_database()

    # Start hot reload system
    await initialize_hot_reload(loader, enable_signals=True)
```

---

## Usage Guide

### Web UI (Django Admin)

#### Access Admin Interface

1. Navigate to `http://localhost:8000/admin/`
2. Log in with admin credentials
3. Go to **Crawler Sources** section

#### Add New Source

1. Click **Add Crawler Source**
2. Fill in required fields:
   - **Name**: Unique identifier (e.g., "TechCrunch RSS")
   - **Source Type**: Select from dropdown
   - **URL**: Feed/API URL
   - **Schedule**: Cron expression (e.g., `0 */2 * * *`)
3. Configure optional settings:
   - Rate limiting
   - Authentication (API keys, OAuth)
   - Content filters
4. Click **Save**

#### Monitor Source Health

1. View **Crawler Sources** list
2. Check health badges:
   - 🟢 **Healthy** - Success rate ≥ 95%
   - 🟠 **Warning** - Success rate 80-94%
   - 🔴 **Unhealthy** - Success rate < 80%
3. View detailed metrics in source detail page

---

### REST API

#### Authentication

All admin endpoints require authentication:

```bash
export ADMIN_API_KEY="your-admin-api-key"

curl -H "X-API-Key: $ADMIN_API_KEY" \
  http://localhost:8000/admin/sources
```

#### Create RSS Source

```bash
curl -X POST "http://localhost:8000/admin/sources" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TechCrunch",
    "source_type": "rss",
    "url": "https://techcrunch.com/feed/",
    "description": "TechCrunch technology news",
    "enabled": true,
    "schedule": "0 */2 * * *",
    "rate_limit": 60,
    "timeout_seconds": 30,
    "language": "en",
    "category_filters": ["Technology", "Business"]
  }'
```

#### List All Sources

```bash
curl "http://localhost:8000/admin/sources?enabled=true&page=1&page_size=10" \
  -H "X-API-Key: $ADMIN_API_KEY"
```

#### Update Source

```bash
curl -X PUT "http://localhost:8000/admin/sources/1" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false,
    "schedule": "0 */6 * * *"
  }'
```

#### Delete Source

```bash
curl -X DELETE "http://localhost:8000/admin/sources/1" \
  -H "X-API-Key: $ADMIN_API_KEY"
```

#### Test Connection

```bash
curl -X POST "http://localhost:8000/admin/sources/1/test" \
  -H "X-API-Key: $ADMIN_API_KEY"
```

#### Trigger Manual Collection

```bash
curl -X POST "http://localhost:8000/admin/sources/trigger" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "source_ids": [1, 2, 3],
    "force": false
  }'
```

---

## Examples

### Example 1: Add Twitter Source

```json
{
  "name": "Twitter Trending",
  "source_type": "twitter",
  "description": "Twitter trending topics",
  "enabled": true,
  "schedule": "0 * * * *",
  "rate_limit": 180,
  "api_key": "your-twitter-bearer-token",
  "custom_headers": {
    "User-Agent": "TrendBot/1.0"
  },
  "category_filters": ["Technology", "Politics"],
  "language": "en"
}
```

### Example 2: Add RSS with Keyword Filtering

```json
{
  "name": "Tech News Filtered",
  "source_type": "rss",
  "url": "https://example.com/feed.rss",
  "enabled": true,
  "schedule": "0 */4 * * *",
  "keyword_filters": {
    "include": ["AI", "machine learning", "technology"],
    "exclude": ["advertisement", "sponsored"]
  },
  "content_filters": {
    "min_length": 100,
    "max_age_hours": 48
  }
}
```

### Example 3: Custom Plugin

```json
{
  "name": "Custom API Source",
  "source_type": "custom",
  "description": "Custom data source",
  "enabled": true,
  "schedule": "0 */3 * * *",
  "plugin_code": "from datetime import datetime\n\nasync def collect(config):\n    # Your collection logic\n    return []\n"
}
```

---

## Security

### API Key Encryption

API keys are encrypted using Fernet (symmetric encryption):

- Keys encrypted before storage
- Decrypted only when needed
- Never exposed in API responses
- Displayed masked in admin UI

### Custom Plugin Sandbox

Custom plugins run in a restricted environment:

✅ **Allowed:**
- Safe built-in functions (len, range, str, etc.)
- Datetime, JSON, regex modules
- HTTP requests (via approved client)

❌ **Blocked:**
- File system access (open, read, write)
- Process execution (subprocess, os.system)
- Dangerous functions (eval, exec, compile)
- Arbitrary imports

### Resource Limits

- **CPU Time**: 30 seconds default
- **Memory**: 100MB default
- **Timeout**: Enforced per request
- **Rate Limiting**: Configurable per source

---

## API Reference

### Source Endpoints

#### `GET /admin/sources`
List all sources with filtering and pagination.

**Query Parameters:**
- `enabled` (boolean) - Filter by status
- `source_type` (string) - Filter by type
- `health_status` (string) - Filter by health
- `search` (string) - Search query
- `page` (int) - Page number
- `page_size` (int) - Items per page

**Response:** `CrawlerSourceList`

---

#### `POST /admin/sources`
Create a new source.

**Body:** `CrawlerSourceCreate`

**Response:** `CrawlerSourceResponse` (201 Created)

---

#### `GET /admin/sources/{id}`
Get source details.

**Response:** `CrawlerSourceResponse`

---

#### `PUT /admin/sources/{id}`
Update source (partial updates supported).

**Body:** `CrawlerSourceUpdate`

**Response:** `CrawlerSourceResponse`

---

#### `DELETE /admin/sources/{id}`
Delete a source.

**Response:** Success message

---

#### `POST /admin/sources/{id}/test`
Test source connection.

**Response:** `SourceTestResponse`

---

#### `POST /admin/sources/trigger`
Trigger manual collection.

**Body:** `CollectionTriggerRequest`
```json
{
  "source_ids": [1, 2, 3],
  "force": false
}
```

**Response:** `CollectionTriggerResponse`

---

#### `POST /admin/sources/validate`
Validate source configuration before creating.

**Body:** `SourceValidationRequest`

**Response:** `SourceValidationResponse`

---

#### `GET /admin/sources/{id}/health`
Get detailed health metrics.

**Response:** `SourceHealthMetrics`

---

## Troubleshooting

### Issue: Migration Not Applied

**Symptom:** Django error about missing `crawlersource` table

**Solution:**
```bash
cd web_interface
python manage.py migrate trends_viewer
```

---

### Issue: Hot Reload Not Working

**Symptom:** Source changes don't take effect

**Solution:**
1. Check hot reload manager is started:
   ```python
   from trend_agent.ingestion.hot_reload import get_hot_reload_manager
   manager = get_hot_reload_manager(loader)
   assert manager.is_running()
   ```
2. Check Django signals are connected
3. Manually trigger reload:
   ```python
   await manager.trigger_manual_reload()
   ```

---

### Issue: Custom Plugin Fails

**Symptom:** `SandboxSecurityError`

**Solution:**
1. Validate plugin code:
   ```python
   from trend_agent.ingestion.sandbox import get_sandbox
   sandbox = get_sandbox()
   result = sandbox.validate_and_test(plugin_code)
   print(result['errors'])
   ```
2. Check for blacklisted functions
3. Use only allowed imports

---

### Issue: Authentication Fails

**Symptom:** 401 Unauthorized

**Solution:**
1. Check API key is set correctly:
   ```bash
   curl -H "X-API-Key: your-key" http://localhost:8000/admin/sources
   ```
2. Verify admin API key in settings
3. Check OAuth tokens are not expired

---

### Issue: Collection Not Running

**Symptom:** Source enabled but not collecting

**Solution:**
1. Check source health status in admin
2. View error messages in source detail
3. Test connection:
   ```bash
   curl -X POST "http://localhost:8000/admin/sources/1/test" \
     -H "X-API-Key: $ADMIN_API_KEY"
   ```
4. Check scheduler is running
5. View logs for errors

---

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_dynamic_loader.py

# Run with coverage
pytest --cov=trend_agent.ingestion tests/
```

---

## Best Practices

### Source Configuration

1. **Use Descriptive Names** - Make source names clear and unique
2. **Set Appropriate Schedules** - Don't over-poll sources
3. **Configure Rate Limits** - Respect API limits
4. **Enable Filtering** - Reduce noise with keyword/category filters
5. **Monitor Health** - Check success rates regularly

### Security

1. **Rotate API Keys** - Update keys periodically
2. **Use HTTPS** - Always use secure URLs
3. **Validate Custom Code** - Test plugins in sandbox before deploying
4. **Limit Permissions** - Use least-privilege API keys

### Performance

1. **Batch Operations** - Use bulk actions when possible
2. **Optimize Schedules** - Stagger collection times
3. **Cache Responses** - Implement caching where appropriate
4. **Monitor Resources** - Track memory and CPU usage

---

## Support & Documentation

- **API Docs**: `/docs` (Swagger UI)
- **Architecture**: `/docs/architecture-admin-interface.md`
- **Code**: `/trend_agent/ingestion/`
- **Tests**: `/tests/`

---

## Version History

### v1.0.0 (Current)
- ✅ Dynamic source management
- ✅ Hot reload system
- ✅ Sandboxed custom plugins
- ✅ Multi-source authentication
- ✅ Content filtering
- ✅ Health monitoring
- ✅ Django Admin UI
- ✅ REST API

---

**Last Updated**: 2024-02-12
**Status**: Production Ready ✅
