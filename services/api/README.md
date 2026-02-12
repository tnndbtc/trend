# Trend Intelligence Platform - REST API Service

FastAPI-based REST API for the Trend Intelligence Platform.

## Overview

This service provides a RESTful API for accessing trend data, performing semantic search, and managing the platform. It includes:

- **RESTful endpoints** for trends, topics, and search
- **GraphQL support** for flexible queries
- **WebSocket support** for real-time updates
- **Rate limiting** to prevent abuse
- **API key authentication** for secure access
- **OpenTelemetry tracing** for observability
- **Prometheus metrics** for monitoring

## Architecture

```
services/api/
├── routers/           # API endpoint routers
│   ├── admin.py      # Admin operations
│   ├── health.py     # Health checks
│   ├── metrics.py    # Prometheus metrics
│   ├── search.py     # Semantic search
│   ├── topics.py     # Topic management
│   ├── translation.py # Translation endpoints
│   ├── trends.py     # Trend data access
│   ├── workflows.py  # Workflow management
│   └── ws.py         # WebSocket connections
├── schemas/          # Pydantic data models
├── graphql/          # GraphQL schema
├── main.py           # FastAPI application
├── dependencies.py   # Dependency injection
└── cache_helpers.py  # Caching utilities
```

## Dependencies

The API service depends on:

1. **Infrastructure**:
   - PostgreSQL (port 5433) - relational data
   - Redis (port 6380) - caching and rate limiting
   - Qdrant (port 6333) - vector search

2. **Shared Library**:
   - `trend-agent-core` - storage, LLM, and observability modules

## Development

### Local Setup

1. **Install dependencies**:
   ```bash
   # From repo root
   pip install -e packages/trend-agent-core
   pip install -r services/api/requirements.txt
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
   export QDRANT_HOST=localhost
   export QDRANT_PORT=6333
   ```

3. **Run the API**:
   ```bash
   cd services/api
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the API**:
   - Swagger docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - GraphQL: http://localhost:8000/graphql

### Docker Development

```bash
# Build the API service
docker build -f services/api/Dockerfile -t trend-api:latest .

# Run the API container
docker run -p 8000:8000 \
  -e POSTGRES_HOST=host.docker.internal \
  -e REDIS_HOST=host.docker.internal \
  -e QDRANT_HOST=host.docker.internal \
  trend-api:latest
```

### Testing

```bash
# Run tests
pytest services/api/tests/

# Run with coverage
pytest services/api/tests/ --cov=api --cov-report=html
```

## API Endpoints

### Core Endpoints

- `GET /` - API root information
- `GET /api/v1/health` - Health check
- `GET /metrics` - Prometheus metrics

### Data Access

- `GET /api/v1/trends` - List trending topics
- `GET /api/v1/trends/{trend_id}` - Get specific trend
- `GET /api/v1/topics` - List all topics
- `GET /api/v1/search` - Semantic search

### Translation

- `POST /api/v1/translation/translate` - Translate text
- `GET /api/v1/translation/languages` - Supported languages
- `GET /api/v1/translation/detect` - Detect language

### Admin

- `GET /api/v1/admin/stats` - Platform statistics
- `GET /api/v1/admin/collectors` - Collector status
- `POST /api/v1/admin/collectors/{name}/trigger` - Trigger collection

### WebSocket

- `WS /ws` - Real-time trend updates

### GraphQL

- `POST /graphql` - GraphQL endpoint

## Configuration

The API can be configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | localhost | PostgreSQL host |
| `POSTGRES_PORT` | 5433 | PostgreSQL port |
| `REDIS_HOST` | localhost | Redis host |
| `REDIS_PORT` | 6380 | Redis port |
| `QDRANT_HOST` | localhost | Qdrant host |
| `QDRANT_PORT` | 6333 | Qdrant port |
| `ENABLE_RATE_LIMITING` | true | Enable rate limiting |
| `RATE_LIMIT_DEFAULT` | 100/minute | Default rate limit |
| `CORS_ORIGINS` | * | Allowed CORS origins |

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Default**: 100 requests/minute per IP
- **Hourly**: 1000 requests/hour per IP
- **Storage**: Redis-backed rate limiting

Override defaults with environment variables:
```bash
export RATE_LIMIT_DEFAULT="200/minute"
export RATE_LIMIT_DEFAULT_HOUR="2000/hour"
```

## Authentication

Most endpoints require API key authentication:

```bash
curl -H "X-API-Key: your-api-key-here" http://localhost:8000/api/v1/trends
```

## Observability

### Metrics

Prometheus metrics are exposed at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

Metrics include:
- Request count and latency
- Database connection pool stats
- Cache hit/miss rates
- Custom business metrics

### Tracing

OpenTelemetry traces are exported to the OTLP collector:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

Traces include:
- HTTP request spans
- Database query spans
- Cache operation spans
- External API call spans

### Logging

Structured JSON logging to stdout:

```python
import logging
logger = logging.getLogger(__name__)
logger.info("API request", extra={"user_id": 123, "endpoint": "/trends"})
```

## Deployment

### Docker Compose

```bash
cd infrastructure/docker
docker-compose up api
```

### Kubernetes

```bash
kubectl apply -k k8s/overlays/production
```

## Troubleshooting

### Database Connection Failed

```
⚠️  Database connection failed: connection refused
```

**Solution**: Ensure PostgreSQL is running and accessible:
```bash
docker-compose up postgres
```

### Redis Connection Failed

```
⚠️  Redis connection failed: connection refused
```

**Solution**: Start Redis:
```bash
docker-compose up redis
```

### Import Errors

```
ModuleNotFoundError: No module named 'trend_agent'
```

**Solution**: Install the core library:
```bash
pip install -e packages/trend-agent-core
```

## Performance

### Optimization Tips

1. **Connection Pooling**: Configure pool size based on load
   ```python
   app_state.db_pool = PostgreSQLConnectionPool(
       min_size=10,  # Increase for high traffic
       max_size=50,
   )
   ```

2. **Caching**: Enable Redis caching for expensive queries
   ```python
   @cache_with_ttl(ttl=300)  # Cache for 5 minutes
   async def get_trends():
       ...
   ```

3. **Workers**: Scale uvicorn workers
   ```bash
   uvicorn api.main:app --workers 8
   ```

4. **Database Indexes**: Ensure proper indexing on frequently queried columns

## Related Services

- **Web Interface**: `services/web-interface/` - Django-based UI
- **Celery Worker**: `services/celery-worker/` - Background tasks
- **Crawler**: `services/crawler/` - Data collection
- **Translation**: `services/translation-service/` - Translation pipeline

## Contributing

See the root `README.md` for contribution guidelines.

## License

See `LICENSE` in the root directory.
