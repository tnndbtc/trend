# API Usage Guide

Complete reference for the FastAPI REST API.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Base URL & Versioning](#base-url--versioning)
3. [Rate Limiting](#rate-limiting)
4. [Response Formats](#response-formats)
5. [Error Handling](#error-handling)
6. [Pagination](#pagination)
7. [Filtering & Sorting](#filtering--sorting)
8. [Endpoints](#endpoints)
9. [WebSocket Support](#websocket-support)
10. [Batch Operations](#batch-operations)
11. [Code Examples](#code-examples)

---

## Authentication

The API uses API key authentication via the `X-API-Key` header.

### Generating API Keys

```bash
# Via setup.sh
./setup.sh → 10) Generate API Keys

# Manual generation
openssl rand -hex 32
```

### Using API Keys

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:8000/api/v1/trends
```

### Key Types

**Regular API Keys** (`API_KEYS`):
- Read access to trends and search
- Limited rate: 100 requests/minute
- Cannot trigger collections or modify data

**Admin API Keys** (`ADMIN_API_KEYS`):
- Full access including admin endpoints
- Higher rate limit: 1000 requests/hour
- Can trigger collections and modify configuration

### Configuration

In `.env.docker`:
```bash
API_KEYS=key1,key2,key3
ADMIN_API_KEYS=admin_key1,admin_key2
```

---

## Base URL & Versioning

**Base URL**: `http://localhost:8000`

**API Version**: `v1` (current)

**Full API Base**: `http://localhost:8000/api/v1`

**Interactive Documentation**:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Rate Limiting

Rate limits prevent API abuse and ensure fair usage.

### Default Limits

| Key Type | Endpoint Type | Limit |
|----------|---------------|-------|
| Regular | General | 100 requests/minute |
| Regular | Search | 30 requests/minute |
| Admin | All | 1000 requests/hour |

### Configuration

In `.env.docker`:
```bash
ENABLE_RATE_LIMITING=true
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_SEARCH=30/minute
RATE_LIMIT_ADMIN=1000/hour
```

### Rate Limit Headers

Response includes rate limit information:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

### Rate Limit Exceeded

```json
{
  "detail": "Rate limit exceeded. Try again in 45 seconds.",
  "status_code": 429,
  "retry_after": 45
}
```

---

## Response Formats

All responses are JSON with consistent structure.

### Success Response

```json
{
  "success": true,
  "data": {
    "id": "123",
    "title": "AI Trend Example"
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "v1"
  }
}
```

### List Response

```json
{
  "success": true,
  "data": [
    {"id": "1", "title": "Trend 1"},
    {"id": "2", "title": "Trend 2"}
  ],
  "meta": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid parameter: limit must be between 1 and 100",
    "details": {
      "field": "limit",
      "value": 200
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "abc123"
  }
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing/invalid API key |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily down |

### Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Invalid request parameters |
| `AUTHENTICATION_ERROR` | Invalid API key |
| `AUTHORIZATION_ERROR` | Insufficient permissions |
| `NOT_FOUND` | Resource not found |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `INTERNAL_ERROR` | Server error |
| `SERVICE_UNAVAILABLE` | Service down |

### Example Error Handling

```python
import requests

response = requests.get(
    "http://localhost:8000/api/v1/trends",
    headers={"X-API-Key": "YOUR_KEY"}
)

if response.status_code == 200:
    data = response.json()["data"]
    print(f"Found {len(data)} trends")
elif response.status_code == 429:
    retry_after = response.json()["error"]["details"]["retry_after"]
    print(f"Rate limited. Retry after {retry_after} seconds")
else:
    error = response.json()["error"]
    print(f"Error: {error['message']}")
```

---

## Pagination

List endpoints support pagination using offset/limit or cursor-based pagination.

### Offset/Limit Pagination

**Parameters**:
- `limit`: Number of items per page (default: 20, max: 100)
- `offset`: Number of items to skip (default: 0)

**Example**:
```bash
# First page
curl "http://localhost:8000/api/v1/trends?limit=20&offset=0"

# Second page
curl "http://localhost:8000/api/v1/trends?limit=20&offset=20"
```

**Response**:
```json
{
  "data": [...],
  "meta": {
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

### Cursor-Based Pagination

For large datasets or real-time updates:

**Parameters**:
- `cursor`: Opaque cursor token
- `limit`: Items per page

**Example**:
```bash
# First page
curl "http://localhost:8000/api/v1/trends?limit=20"

# Next page (use cursor from response)
curl "http://localhost:8000/api/v1/trends?limit=20&cursor=eyJpZCI6MTIzfQ"
```

**Response**:
```json
{
  "data": [...],
  "meta": {
    "next_cursor": "eyJpZCI6MTQzfQ",
    "prev_cursor": "eyJpZCI6MTAzfQ",
    "has_next": true
  }
}
```

---

## Filtering & Sorting

### Filtering

Filter results using query parameters:

```bash
# Single filter
curl "http://localhost:8000/api/v1/trends?category=technology"

# Multiple filters
curl "http://localhost:8000/api/v1/trends?category=technology&source=github"

# Date range
curl "http://localhost:8000/api/v1/trends?start_date=2024-01-01&end_date=2024-01-31"

# Search in title
curl "http://localhost:8000/api/v1/trends?q=artificial+intelligence"
```

### Supported Filters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `q` | string | Search query | `q=AI` |
| `category` | string | Category slug | `category=technology` |
| `source` | string | Source name | `source=github` |
| `start_date` | date | From date | `start_date=2024-01-01` |
| `end_date` | date | To date | `end_date=2024-01-31` |
| `min_score` | float | Minimum score | `min_score=0.8` |
| `language` | string | Language code | `language=en` |

### Sorting

Sort results using `sort_by` and `order`:

```bash
# Sort by date (newest first)
curl "http://localhost:8000/api/v1/trends?sort_by=collected_at&order=desc"

# Sort by score (highest first)
curl "http://localhost:8000/api/v1/trends?sort_by=score&order=desc"

# Sort by title (A-Z)
curl "http://localhost:8000/api/v1/trends?sort_by=title&order=asc"
```

### Supported Sort Fields

| Field | Description |
|-------|-------------|
| `collected_at` | Collection timestamp |
| `score` | Trend score |
| `title` | Alphabetical |
| `engagement` | Social engagement |

---

## Endpoints

### Health Check

**GET** `/api/v1/health`

Check API health status.

**No authentication required**

```bash
curl http://localhost:8000/api/v1/health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "cache": "healthy",
    "queue": "healthy",
    "vector_db": "healthy"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### List Trends

**GET** `/api/v1/trends`

Get paginated list of trends with optional filters.

**Authentication**: Required (regular or admin key)

**Parameters**:
- `limit` (optional): Items per page (1-100, default: 20)
- `offset` (optional): Skip items (default: 0)
- `category` (optional): Filter by category slug
- `source` (optional): Filter by source name
- `q` (optional): Search query
- `start_date` (optional): From date (YYYY-MM-DD)
- `end_date` (optional): To date (YYYY-MM-DD)
- `sort_by` (optional): Sort field (default: collected_at)
- `order` (optional): asc/desc (default: desc)

**Example**:
```bash
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:8000/api/v1/trends?limit=10&category=technology&sort_by=score&order=desc"
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "trend_123",
      "title": "GPT-4 Vision Released",
      "description": "OpenAI announces multimodal AI model...",
      "url": "https://example.com/article",
      "source": "techcrunch",
      "category": "technology",
      "score": 0.95,
      "collected_at": "2024-01-15T10:00:00Z",
      "engagement": {
        "views": 50000,
        "comments": 234,
        "shares": 1200
      },
      "metadata": {
        "language": "en",
        "author": "John Doe",
        "tags": ["AI", "OpenAI", "GPT-4"]
      }
    }
  ],
  "meta": {
    "total": 150,
    "page": 1,
    "page_size": 10,
    "total_pages": 15,
    "has_next": true,
    "has_prev": false
  }
}
```

---

### Get Single Trend

**GET** `/api/v1/trends/{trend_id}`

Get detailed information about a specific trend.

**Authentication**: Required

**Parameters**:
- `trend_id` (path): Trend ID

**Example**:
```bash
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:8000/api/v1/trends/trend_123
```

**Response**:
```json
{
  "success": true,
  "data": {
    "id": "trend_123",
    "title": "GPT-4 Vision Released",
    "description": "OpenAI announces multimodal AI model...",
    "url": "https://example.com/article",
    "source": "techcrunch",
    "category": "technology",
    "score": 0.95,
    "collected_at": "2024-01-15T10:00:00Z",
    "embedding": [0.1, 0.2, ...],  // 768-dimensional vector
    "related_trends": ["trend_124", "trend_125"],
    "translations": {
      "zh": "GPT-4视觉版本发布",
      "ja": "GPT-4ビジョンリリース"
    }
  }
}
```

**Error (404)**:
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Trend not found",
    "details": {"trend_id": "trend_999"}
  }
}
```

---

### Semantic Search

**POST** `/api/v1/search/semantic`

Search trends using natural language queries (vector similarity).

**Authentication**: Required
**Rate Limit**: 30/minute

**Request Body**:
```json
{
  "query": "latest advancements in artificial intelligence",
  "limit": 10,
  "min_score": 0.7,
  "filters": {
    "category": "technology",
    "start_date": "2024-01-01"
  }
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/search/semantic \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI breakthrough in healthcare",
    "limit": 5,
    "min_score": 0.75
  }'
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "trend_456",
      "title": "AI Detects Cancer with 99% Accuracy",
      "description": "New AI model outperforms doctors...",
      "score": 0.92,
      "similarity": 0.87,
      "url": "https://example.com/article"
    }
  ],
  "meta": {
    "query": "AI breakthrough in healthcare",
    "total_results": 15,
    "search_time_ms": 45
  }
}
```

---

### Keyword Search

**GET** `/api/v1/search/keyword`

Traditional keyword search across titles and descriptions.

**Authentication**: Required

**Parameters**:
- `q`: Search query (required)
- `limit`: Results per page (default: 20)
- `offset`: Skip results (default: 0)
- `category` (optional): Filter by category
- `fuzzy` (optional): Enable fuzzy matching (default: false)

**Example**:
```bash
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:8000/api/v1/search/keyword?q=machine+learning&limit=10"
```

**Response**: Same format as List Trends

---

### Get Categories

**GET** `/api/v1/categories`

List all available trend categories.

**Authentication**: Required

**Example**:
```bash
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:8000/api/v1/categories
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "cat_1",
      "name": "Technology",
      "slug": "technology",
      "description": "Tech trends and innovations",
      "trend_count": 1234,
      "enabled": true,
      "priority": 1
    },
    {
      "id": "cat_2",
      "name": "Business",
      "slug": "business",
      "description": "Business and startup trends",
      "trend_count": 567,
      "enabled": true,
      "priority": 2
    }
  ]
}
```

---

### Get Sources

**GET** `/api/v1/sources`

List all configured trend sources.

**Authentication**: Required

**Example**:
```bash
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:8000/api/v1/sources
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "src_1",
      "name": "GitHub Trending",
      "slug": "github",
      "type": "web_scraper",
      "enabled": true,
      "last_collected": "2024-01-15T10:00:00Z",
      "success_rate": 0.98
    },
    {
      "id": "src_2",
      "name": "Hacker News",
      "slug": "hackernews",
      "type": "api",
      "enabled": true,
      "last_collected": "2024-01-15T10:15:00Z",
      "success_rate": 1.0
    }
  ]
}
```

---

### Get Statistics

**GET** `/api/v1/stats`

Platform statistics and metrics.

**Authentication**: Required

**Parameters**:
- `period` (optional): day/week/month/year (default: day)

**Example**:
```bash
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:8000/api/v1/stats?period=week"
```

**Response**:
```json
{
  "success": true,
  "data": {
    "period": "week",
    "trends": {
      "total": 5432,
      "new": 1234,
      "categories": {
        "technology": 2345,
        "business": 1234,
        "science": 890
      }
    },
    "sources": {
      "github": 2000,
      "hackernews": 1500,
      "reddit": 1932
    },
    "engagement": {
      "total_views": 500000,
      "total_shares": 12345,
      "avg_score": 0.78
    },
    "collection": {
      "successful_runs": 168,
      "failed_runs": 2,
      "avg_duration_seconds": 45
    }
  }
}
```

---

### Trigger Collection (Admin)

**POST** `/api/v1/admin/collect`

Manually trigger trend collection.

**Authentication**: Admin key required

**Request Body**:
```json
{
  "category": "technology",
  "max_items": 10,
  "sources": ["github", "hackernews"]
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/admin/collect \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "max_items": 5
  }'
```

**Response**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_abc123",
    "status": "queued",
    "estimated_duration_seconds": 120,
    "message": "Collection task queued successfully"
  }
}
```

---

### Get Task Status (Admin)

**GET** `/api/v1/admin/tasks/{task_id}`

Check status of a background task.

**Authentication**: Admin key required

**Example**:
```bash
curl -H "X-API-Key: YOUR_ADMIN_KEY" \
  http://localhost:8000/api/v1/admin/tasks/task_abc123
```

**Response (Running)**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_abc123",
    "status": "running",
    "progress": 45,
    "message": "Collecting from GitHub Trending...",
    "started_at": "2024-01-15T10:00:00Z",
    "items_collected": 23
  }
}
```

**Response (Completed)**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_abc123",
    "status": "completed",
    "progress": 100,
    "message": "Collection completed successfully",
    "started_at": "2024-01-15T10:00:00Z",
    "completed_at": "2024-01-15T10:02:15Z",
    "duration_seconds": 135,
    "items_collected": 50,
    "items_deduplicated": 3,
    "errors": []
  }
}
```

---

### Export Trends (Admin)

**GET** `/api/v1/admin/export`

Export trends in various formats.

**Authentication**: Admin key required

**Parameters**:
- `format`: json/csv/excel (default: json)
- `start_date` (optional): From date
- `end_date` (optional): To date
- `category` (optional): Filter by category

**Example**:
```bash
# JSON export
curl -H "X-API-Key: YOUR_ADMIN_KEY" \
  "http://localhost:8000/api/v1/admin/export?format=json&start_date=2024-01-01" \
  -o trends.json

# CSV export
curl -H "X-API-Key: YOUR_ADMIN_KEY" \
  "http://localhost:8000/api/v1/admin/export?format=csv" \
  -o trends.csv

# Excel export
curl -H "X-API-Key: YOUR_ADMIN_KEY" \
  "http://localhost:8000/api/v1/admin/export?format=excel" \
  -o trends.xlsx
```

---

### Batch Operations (Admin)

**POST** `/api/v1/admin/batch/delete`

Delete multiple trends.

**Authentication**: Admin key required

**Request Body**:
```json
{
  "trend_ids": ["trend_1", "trend_2", "trend_3"]
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/admin/batch/delete \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "trend_ids": ["trend_123", "trend_456"]
  }'
```

**Response**:
```json
{
  "success": true,
  "data": {
    "deleted": 2,
    "failed": 0,
    "errors": []
  }
}
```

---

### Metrics

**GET** `/metrics`

Prometheus metrics endpoint.

**No authentication required**

```bash
curl http://localhost:8000/metrics
```

**Response** (Prometheus format):
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/trends",status="200"} 1234

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1"} 1000
http_request_duration_seconds_bucket{le="0.5"} 1200
http_request_duration_seconds_sum 567.8
http_request_duration_seconds_count 1234

# HELP celery_tasks_total Total Celery tasks
# TYPE celery_tasks_total counter
celery_tasks_total{task="collect_trends",status="success"} 450

# HELP agent_tasks_total Agent control plane tasks
# TYPE agent_tasks_total counter
agent_tasks_total{agent="researcher",status="success"} 123
agent_budget_usage_usd{agent="researcher"} 45.67
agent_trust_level{agent="researcher"} 2
```

---

## WebSocket Support

Real-time updates via WebSocket.

### Connect

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/trends?api_key=YOUR_KEY');

ws.onopen = () => {
  console.log('Connected to trend updates');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('New trend:', data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected');
};
```

### Subscribe to Events

```javascript
// Subscribe to specific category
ws.send(JSON.stringify({
  action: 'subscribe',
  channel: 'category:technology'
}));

// Subscribe to all new trends
ws.send(JSON.stringify({
  action: 'subscribe',
  channel: 'trends:new'
}));

// Unsubscribe
ws.send(JSON.stringify({
  action: 'unsubscribe',
  channel: 'category:technology'
}));
```

### Message Format

```json
{
  "event": "trend.created",
  "channel": "category:technology",
  "data": {
    "id": "trend_123",
    "title": "New AI Breakthrough",
    "category": "technology",
    "score": 0.95
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Batch Operations

### Batch Get Trends

**POST** `/api/v1/trends/batch`

Retrieve multiple trends by ID.

**Request**:
```json
{
  "trend_ids": ["trend_1", "trend_2", "trend_3"]
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/trends/batch \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "trend_ids": ["trend_123", "trend_456"]
  }'
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "trend_123",
      "title": "AI Advancement",
      ...
    },
    {
      "id": "trend_456",
      "title": "Tech Innovation",
      ...
    }
  ],
  "meta": {
    "requested": 2,
    "found": 2,
    "not_found": []
  }
}
```

---

## Code Examples

### Python (requests)

```python
import requests
from typing import List, Dict

class TrendAPIClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}

    def get_trends(self, category: str = None, limit: int = 20) -> List[Dict]:
        """Get trends with optional category filter."""
        params = {"limit": limit}
        if category:
            params["category"] = category

        response = requests.get(
            f"{self.base_url}/api/v1/trends",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()["data"]

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search trends using natural language."""
        response = requests.post(
            f"{self.base_url}/api/v1/search/semantic",
            headers=self.headers,
            json={"query": query, "limit": limit}
        )
        response.raise_for_status()
        return response.json()["data"]

    def trigger_collection(self, max_items: int = 5) -> str:
        """Trigger trend collection (admin only)."""
        response = requests.post(
            f"{self.base_url}/api/v1/admin/collect",
            headers=self.headers,
            json={"max_items": max_items}
        )
        response.raise_for_status()
        return response.json()["data"]["task_id"]

# Usage
client = TrendAPIClient("http://localhost:8000", "YOUR_API_KEY")

# Get trends
trends = client.get_trends(category="technology", limit=10)
for trend in trends:
    print(f"{trend['title']} - Score: {trend['score']}")

# Semantic search
results = client.semantic_search("AI breakthroughs in medicine")
for result in results:
    print(f"{result['title']} - Similarity: {result['similarity']}")
```

### JavaScript (fetch)

```javascript
class TrendAPIClient {
  constructor(baseURL, apiKey) {
    this.baseURL = baseURL;
    this.apiKey = apiKey;
  }

  async getTrends(options = {}) {
    const params = new URLSearchParams({
      limit: options.limit || 20,
      ...(options.category && { category: options.category }),
      ...(options.sort_by && { sort_by: options.sort_by })
    });

    const response = await fetch(
      `${this.baseURL}/api/v1/trends?${params}`,
      {
        headers: { 'X-API-Key': this.apiKey }
      }
    );

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    const json = await response.json();
    return json.data;
  }

  async semanticSearch(query, limit = 10) {
    const response = await fetch(
      `${this.baseURL}/api/v1/search/semantic`,
      {
        method: 'POST',
        headers: {
          'X-API-Key': this.apiKey,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query, limit })
      }
    );

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    const json = await response.json();
    return json.data;
  }

  async getStats(period = 'day') {
    const response = await fetch(
      `${this.baseURL}/api/v1/stats?period=${period}`,
      {
        headers: { 'X-API-Key': this.apiKey }
      }
    );

    const json = await response.json();
    return json.data;
  }
}

// Usage
const client = new TrendAPIClient('http://localhost:8000', 'YOUR_API_KEY');

// Get trends
const trends = await client.getTrends({
  category: 'technology',
  limit: 10,
  sort_by: 'score'
});

trends.forEach(trend => {
  console.log(`${trend.title} - ${trend.score}`);
});

// Search
const results = await client.semanticSearch('quantum computing breakthroughs');
console.log(`Found ${results.length} similar trends`);

// Stats
const stats = await client.getStats('week');
console.log(`Total trends this week: ${stats.trends.total}`);
```

### cURL Examples

```bash
# Get trends
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:8000/api/v1/trends?limit=5&category=technology"

# Single trend
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:8000/api/v1/trends/trend_123

# Semantic search
curl -X POST http://localhost:8000/api/v1/search/semantic \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI in healthcare", "limit": 5}'

# Keyword search
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:8000/api/v1/search/keyword?q=machine+learning&limit=10"

# Get categories
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:8000/api/v1/categories

# Get statistics
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:8000/api/v1/stats?period=week"

# Trigger collection (admin)
curl -X POST http://localhost:8000/api/v1/admin/collect \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"max_items": 5}'

# Check task status (admin)
curl -H "X-API-Key: YOUR_ADMIN_KEY" \
  http://localhost:8000/api/v1/admin/tasks/task_abc123

# Export to CSV (admin)
curl -H "X-API-Key: YOUR_ADMIN_KEY" \
  "http://localhost:8000/api/v1/admin/export?format=csv" \
  -o trends.csv

# Health check (no auth)
curl http://localhost:8000/api/v1/health

# Metrics (no auth)
curl http://localhost:8000/metrics
```

---

## Best Practices

### 1. Use Appropriate Keys

- Use **regular keys** for read-only operations
- Reserve **admin keys** for write operations and collection triggers
- Rotate keys periodically

### 2. Handle Rate Limits

```python
import time

def api_call_with_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After', 60))
                print(f"Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
            else:
                raise
    raise Exception("Max retries exceeded")
```

### 3. Use Pagination

```python
def get_all_trends(client):
    all_trends = []
    offset = 0
    limit = 100

    while True:
        trends = client.get_trends(offset=offset, limit=limit)
        all_trends.extend(trends)

        if len(trends) < limit:
            break

        offset += limit

    return all_trends
```

### 4. Cache Results

```python
import redis
import json

cache = redis.Redis(host='localhost', port=6379, db=0)

def get_trends_cached(category, ttl=300):
    cache_key = f"trends:{category}"
    cached = cache.get(cache_key)

    if cached:
        return json.loads(cached)

    trends = client.get_trends(category=category)
    cache.setex(cache_key, ttl, json.dumps(trends))

    return trends
```

### 5. Error Handling

```python
try:
    trends = client.get_trends()
except requests.HTTPError as e:
    if e.response.status_code == 401:
        print("Invalid API key")
    elif e.response.status_code == 429:
        print("Rate limit exceeded")
    elif e.response.status_code == 500:
        print("Server error, try again later")
    else:
        print(f"Unexpected error: {e}")
```

---

## See Also

- **QUICKSTART.md** - Getting started guide
- **SERVICES.md** - Service documentation
- **docs/TROUBLESHOOTING.md** - Common issues
- **Interactive Docs** - http://localhost:8000/docs
