# API Router Contracts

This directory contains FastAPI router implementations for the Trend Intelligence Platform API.

## Router Structure

Each router should follow this structure:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from api.schemas import TrendResponse, TrendListResponse
from trend_agent.storage.interfaces import TrendRepository

router = APIRouter(prefix="/api/v1/trends", tags=["trends"])

@router.get("/", response_model=TrendListResponse)
async def get_trends(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    trend_repo: TrendRepository = Depends(get_trend_repository)
):
    """Get list of trends with pagination."""
    pass
```

## Required Routers

### 1. trends.py - Trend Endpoints

- `GET /api/v1/trends` - List trends with pagination
- `GET /api/v1/trends/{trend_id}` - Get single trend
- `POST /api/v1/trends/search` - Semantic search for trends
- `GET /api/v1/trends/{trend_id}/similar` - Find similar trends
- `GET /api/v1/trends/stats` - Get trend statistics
- `GET /api/v1/trends/top` - Get top-ranked trends

### 2. topics.py - Topic Endpoints

- `GET /api/v1/topics` - List topics with pagination
- `GET /api/v1/topics/{topic_id}` - Get single topic
- `GET /api/v1/topics/{topic_id}/items` - Get items in topic
- `POST /api/v1/topics/search` - Search topics

### 3. search.py - Search Endpoints

- `POST /api/v1/search/semantic` - Semantic search across all content
- `POST /api/v1/search/keyword` - Keyword-based search
- `GET /api/v1/search/suggestions` - Get search suggestions

### 4. health.py - Health Check Endpoints

- `GET /api/v1/health` - Health check
- `GET /api/v1/health/detailed` - Detailed health status
- `GET /api/v1/version` - API version info

### 5. admin.py - Admin Endpoints (Protected)

- `POST /api/v1/admin/collect` - Trigger manual collection
- `GET /api/v1/admin/plugins` - List collector plugins
- `POST /api/v1/admin/plugins/{name}/enable` - Enable plugin
- `POST /api/v1/admin/plugins/{name}/disable` - Disable plugin
- `GET /api/v1/admin/metrics` - Get system metrics

## WebSocket Endpoints

### ws.py - Real-time Updates

- `WS /ws/trends` - Real-time trend updates
- `WS /ws/topics` - Real-time topic updates

## Authentication

All endpoints should support:
- API Key authentication (via header)
- JWT token authentication (optional)
- Rate limiting per API key

## Error Handling

Use standard HTTP status codes:
- 200 OK - Success
- 201 Created - Resource created
- 400 Bad Request - Invalid input
- 401 Unauthorized - Missing/invalid auth
- 403 Forbidden - Insufficient permissions
- 404 Not Found - Resource not found
- 429 Too Many Requests - Rate limit exceeded
- 500 Internal Server Error - Server error

## Dependencies

Routers should inject dependencies using FastAPI's dependency injection:
- `TrendRepository` - For trend data access
- `TopicRepository` - For topic data access
- `VectorRepository` - For semantic search
- `CacheRepository` - For caching
- `CurrentUser` - For authentication

## Testing

Each router should have corresponding tests in `tests/api/routers/test_{router_name}.py`
