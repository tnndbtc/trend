# Platform Services Documentation

Complete reference for all services in the AI Trend Intelligence Platform.

---

## Service Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                           │
├─────────────────────────────────────────────────────────────────┤
│  Django Web (11800)  │  FastAPI REST (8000)  │  Grafana (3000) │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                           │
├─────────────────────────────────────────────────────────────────┤
│   Celery Workers   │   Celery Beat   │   Trend Agents          │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL  │  Qdrant  │  Redis  │  RabbitMQ  │  InfluxDB     │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Observability Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  Prometheus  │  Jaeger  │  Loki  │  OpenTelemetry Collector    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Services

### 1. Django Web Interface

**Port**: 11800
**Profile**: Default (always runs)
**Container**: `trend-web`

**Purpose**: Primary web interface for managing the platform.

**Features**:
- Trend browsing and filtering
- Category management
- Admin panel (`/admin`)
- Data visualization
- Manual trend collection triggers

**URLs**:
- Web Interface: http://localhost:11800
- Admin Panel: http://localhost:11800/admin

**Default Credentials**:
- Username: `admin`
- Password: `changeme123`

**Dependencies**: PostgreSQL, Redis, Qdrant

**Configuration**:
```bash
DJANGO_DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
SECRET_KEY=change-this-to-a-random-secret-key-in-production
```

**Common Commands**:
```bash
# Create superuser
docker compose exec web python manage.py createsuperuser

# Run migrations
docker compose exec web python manage.py migrate

# Collect static files
docker compose exec web python manage.py collectstatic

# Django shell
docker compose exec web python manage.py shell
```

---

### 2. FastAPI REST API

**Port**: 8000
**Profile**: `api`
**Container**: `trend-api`

**Purpose**: High-performance REST API with automatic OpenAPI documentation.

**Features**:
- RESTful endpoints for all platform operations
- API key authentication
- Rate limiting
- WebSocket support
- Automatic OpenAPI/Swagger docs
- CORS configuration

**URLs**:
- API Base: http://localhost:8000
- OpenAPI Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/api/v1/health

**Authentication**:
```bash
# Request with API key
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:8000/api/v1/trends
```

**Dependencies**: PostgreSQL, Redis, Qdrant, RabbitMQ

**Configuration**:
```bash
API_KEYS=dev_key_placeholder,test_key_placeholder
ADMIN_API_KEYS=admin_key_placeholder
ENABLE_RATE_LIMITING=true
RATE_LIMIT_DEFAULT=100/minute
CORS_ORIGINS=http://localhost:3000,http://localhost:11800
```

**Key Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/trends` | GET | List trends with filters |
| `/api/v1/trends/{id}` | GET | Get single trend |
| `/api/v1/search/semantic` | POST | Semantic search |
| `/api/v1/admin/collect` | POST | Trigger collection |
| `/api/v1/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |

**Starting**:
```bash
# Via setup.sh
./setup.sh → 3) Start/Stop Services → 1) Start FastAPI

# Via docker compose
docker compose --profile api up -d
```

---

### 3. PostgreSQL Database

**Port**: 5432 (internal)
**Profile**: Default (always runs)
**Container**: `trend-postgres`

**Purpose**: Primary relational database for structured data.

**Stores**:
- Trends and articles
- Categories and sources
- User accounts
- API keys
- Audit logs
- Task history

**Configuration**:
```bash
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=trends
POSTGRES_USER=trend_user
POSTGRES_PASSWORD=trend_password
```

**Accessing**:
```bash
# Via setup.sh
./setup.sh → 8) Database Operations → 4) PostgreSQL Shell

# Via docker compose
docker compose exec postgres psql -U trend_user -d trends

# From host (requires psql installed)
PGPASSWORD=trend_password psql -h localhost -p 5432 -U trend_user -d trends
```

**Common Queries**:
```sql
-- Show all tables
\dt

-- Count trends
SELECT COUNT(*) FROM trends_trend;

-- Recent trends
SELECT title, source, collected_at
FROM trends_trend
ORDER BY collected_at DESC
LIMIT 10;

-- Category statistics
SELECT c.name, COUNT(t.id) as trend_count
FROM trends_category c
LEFT JOIN trends_trend t ON t.category_id = c.id
GROUP BY c.name;
```

**Backup & Restore**:
```bash
# Create backup (via setup.sh)
./setup.sh → 8) Database Operations → 2) Create Backup

# Manual backup
docker compose exec postgres pg_dump -U trend_user trends > backup.sql

# Restore
docker compose exec -T postgres psql -U trend_user -d trends < backup.sql
```

**Performance Tuning**:
```bash
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
```

---

### 4. Qdrant Vector Database

**Port**: 6333 (internal), 6334 (gRPC)
**Profile**: Default (always runs)
**Container**: `trend-qdrant`

**Purpose**: Vector database for semantic search and similarity matching.

**Features**:
- Embedding storage (768-dimensional vectors)
- Similarity search
- Deduplication via vector similarity
- Trend clustering

**Configuration**:
```bash
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=trends
EMBED_MODEL=text-embedding-3-small
```

**Collections**:
- `trends`: Trend embeddings for semantic search

**Accessing Web UI**:
- URL: http://localhost:6333/dashboard
- No authentication required in development

**API Examples**:
```bash
# Collection info
curl http://localhost:6333/collections/trends

# Search similar vectors (from within container)
curl -X POST http://localhost:6333/collections/trends/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, ...],
    "limit": 10
  }'
```

**Performance**:
- In-memory index for fast retrieval
- Persistent storage in `/qdrant/storage`
- Optimized for 100K+ vectors

---

### 5. Redis Cache

**Port**: 6379 (internal)
**Profile**: Default (always runs)
**Container**: `trend-redis`

**Purpose**: High-speed cache and session storage.

**Use Cases**:
- API response caching
- Session storage
- Rate limiting counters
- Celery task results
- Real-time metrics

**Configuration**:
```bash
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
CACHE_TTL_DEFAULT=300
CACHE_TTL_TRENDS=60
CACHE_TTL_SEARCH=120
```

**Accessing**:
```bash
# Redis CLI
docker compose exec redis redis-cli

# Common commands
redis-cli KEYS '*'
redis-cli GET cache_key
redis-cli FLUSHALL  # Clear all caches
redis-cli INFO stats
```

**Cache Keys**:
- `trends:list:*`: Cached trend lists
- `search:*`: Cached search results
- `rate_limit:*`: Rate limiting counters
- `celery-task-meta-*`: Celery task results

**Monitoring**:
```bash
# Memory usage
docker compose exec redis redis-cli INFO memory

# Hit/miss ratio
docker compose exec redis redis-cli INFO stats | grep keyspace
```

---

### 6. RabbitMQ Message Queue

**Port**: 5672 (AMQP), 15672 (Management UI)
**Profile**: `celery`
**Container**: `trend-rabbitmq`

**Purpose**: Message broker for asynchronous task queue.

**Features**:
- Task queue for Celery workers
- Message persistence
- Dead letter queues
- Management UI

**Configuration**:
```bash
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=trend_user
RABBITMQ_PASSWORD=trend_password
RABBITMQ_VHOST=/
```

**Management UI**:
- URL: http://localhost:15672
- Username: `trend_user`
- Password: `trend_password`

**Queues**:
- `celery`: Default task queue
- `celery.priority.high`: High-priority tasks
- `celery.priority.low`: Low-priority tasks

**Monitoring**:
```bash
# List queues
docker compose exec rabbitmq rabbitmqctl list_queues

# List connections
docker compose exec rabbitmq rabbitmqctl list_connections

# Purge queue
docker compose exec rabbitmq rabbitmqctl purge_queue celery
```

---

### 7. Celery Workers

**Profile**: `celery`
**Container**: `trend-celery-worker`

**Purpose**: Background task processing.

**Tasks**:
- Trend collection from sources
- Embedding generation
- Data cleanup
- Email/Slack alerts
- Batch processing

**Configuration**:
```bash
CELERY_BROKER_URL=amqp://trend_user:trend_password@rabbitmq:5672/
CELERY_RESULT_BACKEND=redis://redis:6379/1
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=100
CELERY_WORKER_PREFETCH_MULTIPLIER=4
```

**Starting**:
```bash
# Via setup.sh
./setup.sh → 3) Start/Stop Services → 2) Start Celery

# Via docker compose
docker compose --profile celery up -d
```

**Monitoring**:
```bash
# View logs
docker compose logs -f celery-worker

# Inspect active tasks
docker compose exec celery-worker celery -A trend_project inspect active

# Worker stats
docker compose exec celery-worker celery -A trend_project inspect stats
```

**Task Examples**:
```python
# Trigger collection task
from trends.tasks import collect_trends_task
collect_trends_task.delay(max_posts_per_category=5)

# Check task status
from celery.result import AsyncResult
result = AsyncResult(task_id)
print(result.status, result.result)
```

---

### 8. Celery Beat (Scheduler)

**Profile**: `celery`
**Container**: `trend-celery-beat`

**Purpose**: Periodic task scheduler (like cron).

**Schedules**:
```python
# Every hour: Full collection
collect_trends_task: crontab(minute=0)

# Every 15 minutes: High-frequency sources
collect_high_frequency: crontab(minute='*/15')

# Daily at 3 AM: Cleanup old data
cleanup_old_data: crontab(hour=3, minute=0)

# Daily at 2 AM: Generate embeddings
generate_embeddings: crontab(hour=2, minute=0)
```

**Configuration**:
```bash
CELERY_BEAT_ENABLED=true
CELERY_TIMEZONE=UTC
```

**Managing**:
```bash
# View schedule
docker compose exec celery-beat celery -A trend_project inspect scheduled

# View logs
docker compose logs -f celery-beat
```

---

## Observability Services

### 9. Grafana

**Port**: 3000
**Profile**: `observability`
**Container**: `trend-grafana`

**Purpose**: Metrics visualization and dashboards.

**Access**:
- URL: http://localhost:3000
- Username: `admin`
- Password: `admin`

**Dashboards**:
- Platform Overview
- API Performance
- Celery Task Metrics
- Database Performance
- Cache Hit Rates
- Error Rates

**Data Sources**:
- Prometheus (metrics)
- Loki (logs)
- Jaeger (traces)
- InfluxDB (time series)

**Starting**:
```bash
# Via setup.sh
./setup.sh → 3) Start/Stop Services → 3) Start Monitoring

# Via docker compose
docker compose --profile observability up -d
```

---

### 10. Prometheus

**Port**: 9090
**Profile**: `observability`
**Container**: `trend-prometheus`

**Purpose**: Metrics collection and alerting.

**Metrics Collected**:
- HTTP request rates/latency
- Celery task counts/duration
- Database connection pool usage
- Cache hit/miss rates
- Agent control plane metrics

**Configuration**:
```bash
PROMETHEUS_PORT=9090
PROMETHEUS_RETENTION_DAYS=30
```

**Access**:
- URL: http://localhost:9090
- Query UI: http://localhost:9090/graph

**Example Queries**:
```promql
# Request rate
rate(http_requests_total[5m])

# Task duration
histogram_quantile(0.95, celery_task_duration_seconds_bucket)

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

**Scrape Targets**:
- FastAPI: http://api:8000/metrics
- Django: http://web:11800/metrics
- Celery: (via Prometheus exporter)

---

### 11. Jaeger

**Port**: 16686 (UI), 6831 (agent)
**Profile**: `observability`
**Container**: `trend-jaeger`

**Purpose**: Distributed tracing for request flows.

**Features**:
- End-to-end request tracing
- Service dependency mapping
- Latency analysis
- Error tracking

**Configuration**:
```bash
JAEGER_ENABLED=true
JAEGER_AGENT_HOST=jaeger
JAEGER_AGENT_PORT=6831
```

**Access**:
- URL: http://localhost:16686

**Use Cases**:
- Trace API request → Celery task → Database query
- Identify slow operations
- Analyze service dependencies

---

### 12. Loki

**Port**: 3100 (internal)
**Profile**: `observability`
**Container**: `trend-loki`

**Purpose**: Log aggregation and querying.

**Features**:
- Centralized log storage
- Label-based indexing
- Integration with Grafana
- Long-term retention

**Configuration**:
```bash
LOKI_ENABLED=true
LOKI_URL=http://loki:3100
```

**Querying** (via Grafana):
```logql
# All logs from API service
{service="api"}

# Error logs
{service="api"} |= "ERROR"

# Logs for specific request
{service="api", correlation_id="abc123"}
```

---

### 13. OpenTelemetry Collector

**Port**: 4317 (OTLP gRPC), 4318 (OTLP HTTP)
**Profile**: `observability`
**Container**: `trend-otel-collector`

**Purpose**: Unified observability data collection.

**Features**:
- Collects traces, metrics, logs
- Exports to Jaeger, Prometheus, Loki
- Protocol conversion
- Data enrichment

**Configuration**:
```bash
OTEL_ENABLED=true
OTEL_SERVICE_NAME=trend-platform
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

---

## Service Profiles

The platform uses Docker Compose profiles for optional service groups:

### Default Profile (no flag needed)
- Django Web
- PostgreSQL
- Qdrant
- Redis

**Start**: `docker compose up -d`

### API Profile
- FastAPI REST API

**Start**: `docker compose --profile api up -d`

### Celery Profile
- RabbitMQ
- Celery Workers
- Celery Beat

**Start**: `docker compose --profile celery up -d`

### Observability Profile
- Grafana
- Prometheus
- Jaeger
- Loki
- OpenTelemetry Collector

**Start**: `docker compose --profile observability up -d`

### All Services
**Start**: `docker compose --profile api --profile celery --profile observability up -d`

Or use: `./setup.sh → 1) Full Platform Setup`

---

## Service Dependencies

```
Django Web
  ├─ PostgreSQL (required)
  ├─ Redis (required)
  └─ Qdrant (required)

FastAPI
  ├─ PostgreSQL (required)
  ├─ Redis (required)
  ├─ Qdrant (required)
  └─ RabbitMQ (optional, for async tasks)

Celery Workers
  ├─ RabbitMQ (required)
  ├─ Redis (required)
  ├─ PostgreSQL (required)
  └─ Qdrant (required)

Celery Beat
  ├─ RabbitMQ (required)
  └─ PostgreSQL (required)

Grafana
  ├─ Prometheus (data source)
  ├─ Loki (data source)
  └─ Jaeger (data source)
```

---

## Resource Requirements

| Service | CPU (cores) | Memory (MB) | Disk (GB) |
|---------|-------------|-------------|-----------|
| Django Web | 0.5 | 512 | 0.1 |
| FastAPI | 0.5 | 512 | 0.1 |
| PostgreSQL | 1.0 | 1024 | 5.0 |
| Qdrant | 1.0 | 2048 | 10.0 |
| Redis | 0.5 | 512 | 1.0 |
| RabbitMQ | 0.5 | 512 | 2.0 |
| Celery Worker | 1.0 | 1024 | 0.1 |
| Celery Beat | 0.25 | 256 | 0.1 |
| Grafana | 0.5 | 512 | 1.0 |
| Prometheus | 0.5 | 1024 | 5.0 |
| Jaeger | 0.5 | 512 | 2.0 |
| Loki | 0.5 | 512 | 5.0 |
| **Total (Full)** | **7.75** | **9.5 GB** | **31.5 GB** |
| **Total (Basic)** | **3.0** | **4.1 GB** | **16.2 GB** |

---

## Health Checks

All services include health checks accessible via:

```bash
# Via setup.sh
./setup.sh → 6) Service Status & Health Check

# Manual checks
curl http://localhost:11800              # Django Web
curl http://localhost:8000/api/v1/health # FastAPI
curl http://localhost:6333/collections   # Qdrant
curl http://localhost:15672              # RabbitMQ
curl http://localhost:3000/api/health    # Grafana
curl http://localhost:9090/-/healthy     # Prometheus
```

**Docker Health Status**:
```bash
docker compose ps
# Shows health: healthy/unhealthy/starting
```

---

## Logs

View logs for any service:

```bash
# Via setup.sh
./setup.sh → 7) View Logs

# Via docker compose
docker compose logs -f <service_name>

# Examples
docker compose logs -f web
docker compose logs -f api
docker compose logs -f celery-worker
docker compose logs --tail=100 postgres
docker compose logs --since 1h rabbitmq
```

**Centralized Logs** (with observability):
- Access via Grafana → Explore → Loki
- Filter by service, log level, time range

---

## Troubleshooting

### Service Won't Start

1. **Check logs**: `docker compose logs <service>`
2. **Check dependencies**: Ensure dependent services are running
3. **Check ports**: `sudo lsof -i :<port>`
4. **Check resources**: `docker stats`

### Database Connection Errors

```bash
# Verify PostgreSQL is running
docker compose ps postgres

# Check connection
docker compose exec postgres pg_isready -U trend_user

# Reset database
docker compose down -v
docker compose up -d
```

### RabbitMQ Connection Errors

```bash
# Check RabbitMQ status
docker compose exec rabbitmq rabbitmqctl status

# Check connections
docker compose exec rabbitmq rabbitmqctl list_connections

# Restart RabbitMQ
docker compose restart rabbitmq
```

### High Memory Usage

```bash
# Check container stats
docker stats

# Reduce worker concurrency
# In .env.docker:
CELERY_WORKER_CONCURRENCY=2  # Reduce from 4
```

### Slow Performance

1. **Check resource usage**: `docker stats`
2. **Verify cache hit rate**: Check Redis metrics in Grafana
3. **Check database queries**: Enable SQL logging
4. **Review Prometheus metrics**: Identify bottlenecks

---

## Security Considerations

### Production Checklist

- [ ] Change all default passwords
- [ ] Generate secure API keys: `./setup.sh → 10)`
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Enable HTTPS (update `*_COOKIE_SECURE=true`)
- [ ] Configure firewall rules
- [ ] Enable authentication on Redis
- [ ] Restrict database access
- [ ] Configure CORS properly
- [ ] Enable rate limiting
- [ ] Set up backup schedules
- [ ] Configure alert endpoints

### Network Isolation

```yaml
# docker-compose.yml networks
networks:
  frontend:   # Public-facing services
  backend:    # Internal services
  monitoring: # Observability stack
```

---

## Backup Strategy

### What to Backup

1. **PostgreSQL Database**: All structured data
2. **Qdrant Collections**: Vector embeddings
3. **Environment Config**: `.env.docker`
4. **Docker Volumes**: Persistent data

### Backup Commands

```bash
# Via setup.sh
./setup.sh → 8) Database Operations → 2) Create Backup

# Manual PostgreSQL backup
docker compose exec postgres pg_dump -U trend_user trends > backup_$(date +%Y%m%d).sql

# Manual Qdrant backup
docker compose exec qdrant tar czf /qdrant/backup.tar.gz /qdrant/storage

# Full volume backup
docker run --rm -v trend_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_volumes.tar.gz /data
```

### Restore

```bash
# Restore PostgreSQL
docker compose exec -T postgres psql -U trend_user -d trends < backup.sql

# Restore Qdrant
docker compose exec qdrant tar xzf /qdrant/backup.tar.gz -C /
docker compose restart qdrant
```

---

## Scaling Considerations

### Horizontal Scaling

**Celery Workers**:
```bash
# Scale to 3 workers
docker compose up -d --scale celery-worker=3
```

**FastAPI**:
```yaml
# Add load balancer (nginx/traefik)
# Run multiple API instances
docker compose up -d --scale api=3
```

### Vertical Scaling

```yaml
# docker-compose.yml
services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
```

### Database Optimization

- Enable query caching
- Add database indexes
- Configure connection pooling
- Use read replicas

---

## Monitoring & Alerts

### Key Metrics to Monitor

1. **API Performance**: Response time, error rate
2. **Task Queue**: Queue length, processing time
3. **Database**: Connection pool, query performance
4. **Cache**: Hit rate, eviction rate
5. **Resource Usage**: CPU, memory, disk

### Alert Rules

Configure in Prometheus/Grafana:

- High error rate (>5%)
- Slow response time (>2s p95)
- Task queue backlog (>100 tasks)
- High memory usage (>80%)
- Database connection pool exhaustion

### Alert Channels

```bash
# In .env.docker
ENABLE_EMAIL_ALERTS=true
SMTP_HOST=smtp.gmail.com
ALERT_EMAILS=admin@example.com

ENABLE_SLACK_ALERTS=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

---

## See Also

- **QUICKSTART.md** - Getting started guide
- **API_GUIDE.md** - Complete API reference
- **docs/TROUBLESHOOTING.md** - Common issues
- **README.md** - Project overview
