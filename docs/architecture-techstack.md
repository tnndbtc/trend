# AI Trend Intelligence Platform - Tech Stack Recommendations

## Overview

This document provides specific technology recommendations for each component of the AI Trend Intelligence Platform, with rationale and alternatives.

**Design Principles:**
- **Open source first** - Avoid vendor lock-in, enable self-hosting
- **Battle-tested** - Prefer mature technologies with large communities
- **Python ecosystem** - Leverage rich ML/AI libraries
- **Cloud-agnostic** - Run anywhere (local, VM, Kubernetes, cloud)
- **Cost-effective** - Minimize operational costs while maintaining performance
- **Security-first** - Build security into every layer from the start

---

## Core Technology Stack

| Component | Technology | Rationale | Alternatives |
|-----------|-----------|-----------|--------------|
| **Primary Language** | Python 3.12+ | Rich ML ecosystem, async support | TypeScript/Node.js, Go |
| **API Framework** | FastAPI | High performance, auto-docs, async | Django REST, Flask, Starlette |
| **Web UI Framework** | Django | Admin panel, ORM, mature ecosystem | React + Next.js, Vue.js |
| **Task Queue** | Celery | Python-native, flexible, scalable | Temporal, Prefect, Dramatiq |
| **Message Broker** | RabbitMQ | Reliable, feature-rich, AMQP standard | Redis, Apache Kafka, NATS |
| **Primary Database** | PostgreSQL 16 | ACID, JSON support, full-text search | MySQL, CockroachDB |
| **Connection Pooler** | PgBouncer | Lightweight, battle-tested | Pgpool-II, built-in pooling |
| **Vector Database** | Qdrant | Fast, Rust-based, great Python SDK | Milvus, Weaviate, pgvector |
| **Cache** | Redis 7 | Fast, versatile, proven | Memcached, Valkey |
| **Object Storage** | MinIO | S3-compatible, self-hosted | Local FS, AWS S3, GCS |
| **Time-Series DB** | TimescaleDB | PostgreSQL extension, familiar SQL | InfluxDB, Prometheus TSDB |
| **Scheduler** | APScheduler | Python-native, simple | Airflow, Dagster, Cron |
| **Metrics** | Prometheus + Grafana | Industry standard, rich ecosystem | Datadog, New Relic, VictoriaMetrics |
| **Logging** | Loki + Promtail | Log aggregation, Grafana integration | ELK Stack, Fluentd |
| **Tracing** | Jaeger / Tempo | Distributed tracing, troubleshooting | Zipkin, OpenTelemetry Collector |
| **Secrets Management** | HashiCorp Vault | Secure, auditable, dynamic secrets | AWS Secrets Manager, Doppler |
| **Container** | Docker + Docker Compose | Simple dev, Kubernetes compat | Podman, containerd |
| **Orchestration** | Kubernetes (Phase 3+) | Industry standard, cloud-agnostic | Docker Swarm, Nomad |

---

## Detailed Recommendations

### 1. Programming Language

#### **Choice: Python 3.12+**

**Rationale:**
- **ML/AI libraries:** PyTorch, scikit-learn, sentence-transformers, LangChain
- **Async support:** asyncio, aiohttp, async/await syntax
- **Data processing:** pandas, numpy, polars
- **Type safety:** Type hints + mypy for production quality
- **Community:** Largest ML/AI community, abundant resources

**Why not alternatives:**

| Language | Pros | Cons | Verdict |
|----------|------|------|---------|
| TypeScript | Fast, good async, type-safe | Weaker ML ecosystem, fewer embeddings libraries | Good for API layer only |
| Go | High performance, simple concurrency | No ML libraries, FFI overhead for Python models | Good for infrastructure, not ML |
| Rust | Fastest, memory-safe, zero-cost abstractions | Steep learning curve, small ML ecosystem | Good for performance-critical modules (e.g., custom vector DB) |
| Java/Kotlin | Enterprise-ready, JVM ecosystem | Verbose, slower dev cycle, fewer ML libs | Not ideal for rapid AI experimentation |

**Recommended Setup:**
```toml
# pyproject.toml
[project]
name = "trend-intelligence"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = [
    # API & Web Framework
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",

    # Database & ORM
    "sqlalchemy>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",  # Database migrations
    "psycopg[binary]>=3.2.0",  # PostgreSQL adapter

    # Task Queue & Messaging
    "celery>=5.4.0",
    "kombu>=5.4.0",  # Celery messaging library
    "redis>=5.2.0",

    # Vector Database & Embeddings
    "qdrant-client>=1.12.0",
    "sentence-transformers>=3.3.0",
    "torch>=2.5.0",  # Required for embeddings

    # LLM Integration
    "openai>=1.58.0",
    "anthropic>=0.40.0",  # Claude API support
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",

    # Data Processing
    "pandas>=2.2.3",
    "numpy>=2.1.0",
    "polars>=1.15.0",  # Fast alternative to pandas
    "scikit-learn>=1.6.0",
    "hdbscan>=0.8.40",  # Clustering

    # Web Scraping & Parsing
    "trafilatura>=1.14.0",
    "beautifulsoup4>=4.12.3",
    "lxml>=5.3.0",
    "aiohttp>=3.11.0",
    "httpx>=0.28.0",  # Modern HTTP client

    # Utilities
    "langdetect>=1.0.9",
    "python-dotenv>=1.0.1",
    "tenacity>=9.0.0",  # Retry logic
    "arrow>=1.3.0",  # Better datetime handling

    # Monitoring & Logging
    "prometheus-client>=0.21.0",
    "structlog>=24.4.0",
    "opentelemetry-api>=1.28.0",
    "opentelemetry-sdk>=1.28.0",
    "opentelemetry-instrumentation-fastapi>=0.49b0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "pytest-mock>=3.14.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "pre-commit>=4.0.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "N", "UP", "B", "A", "C4", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

### 2. API Framework

#### **Choice: FastAPI**

**Rationale:**
- **Performance:** Based on Starlette (async, Uvicorn)
- **Developer Experience:** Auto-generated OpenAPI docs, Pydantic validation
- **Type Safety:** Leverages Python type hints for request/response validation
- **Async-first:** Native async/await support
- **Modern:** Dependency injection, WebSocket support, background tasks

**Example:**
```python
from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="Trend Intelligence API", version="1.0.0")

class TrendSearchRequest(BaseModel):
    query: str
    category: str | None = None
    limit: int = 10

@app.post("/api/v1/search")
async def search_trends(request: TrendSearchRequest):
    trends = await trend_service.search(
        query=request.query,
        category=request.category,
        limit=request.limit
    )
    return {"data": trends, "meta": {"total": len(trends)}}
```

**Why not Django REST Framework:**
- DRF is sync-first (blocking I/O) - not ideal for high concurrency
- Heavier framework (more batteries, slower startup)
- Good for admin panel, not ideal for high-performance API

**Hybrid Approach (Recommended):**

For maximum productivity and performance, use both frameworks:

| Component | Framework | Rationale |
|-----------|-----------|-----------|
| **Public API** | FastAPI | High performance, async I/O, auto-docs, type validation |
| **Admin Panel** | Django Admin | Rapid CRUD interfaces, built-in auth, mature ecosystem |
| **Database Migrations** | Alembic (SQLAlchemy) | Works with both frameworks, version control for schema |
| **Background Tasks** | Celery | Framework-agnostic, works with both |

**Implementation Strategy:**
```python
# Shared database models (SQLAlchemy) - used by both FastAPI and Django
# trend_intelligence/models/trend.py
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Trend(Base):
    __tablename__ = "trends"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
```

**Note:** If this dual-framework approach adds too much complexity for your team, start with **FastAPI only** and use third-party admin libraries like SQLAdmin or FastAPI-Admin.

---

### 3. Task Queue & Scheduler

#### **Choice: Celery + RabbitMQ**

**Rationale:**
- **Celery:** Most mature Python task queue (12+ years)
- **RabbitMQ:** Reliable message broker, AMQP standard
- **Flexibility:** Supports multiple brokers (Redis, RabbitMQ, SQS)
- **Features:** Retries, routing, prioritization, scheduled tasks

**Setup:**
```python
# tasks.py
from celery import Celery

app = Celery('trend_intelligence', broker='amqp://rabbitmq:5672')

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_backend='redis://redis:6379/0',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'tasks.collect_from_source': {'queue': 'ingestion'},
        'tasks.process_pipeline': {'queue': 'processing'},
        'tasks.summarize_batch': {'queue': 'llm'},
    }
)

@app.task(bind=True, max_retries=3, autoretry_for=(Exception,))
def collect_from_source(self, source: str):
    # ... collection logic
    pass
```

**Alternative: Temporal**

**Pros:**
- Workflow orchestration (not just tasks)
- Durable execution (survives crashes)
- Built-in UI for monitoring

**Cons:**
- Heavier infrastructure (requires Temporal server)
- Steeper learning curve
- Less Python-native

**Verdict:** Use **Celery for Phase 1-2**, consider **Temporal for Phase 3+** if complex workflows emerge.

---

### 4. Databases

#### **4.1 Primary Database: PostgreSQL 16**

**Rationale:**
- **ACID compliance:** Critical for data integrity
- **JSON support:** `JSONB` for flexible schemas (metadata, config)
- **Full-text search:** Built-in (no need for Elasticsearch for simple cases)
- **Partitioning:** Time-based partitioning for scaling
- **Extensions:** PostGIS (geospatial), pg_trgm (fuzzy search), TimescaleDB

**Configuration:**
```sql
-- postgresql.conf (optimized for 64 GB RAM, SSD)
shared_buffers = 16GB
effective_cache_size = 48GB
maintenance_work_mem = 2GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1  -- SSD
effective_io_concurrency = 200
work_mem = 64MB
min_wal_size = 2GB
max_wal_size = 8GB
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
```

**Alternative: CockroachDB**

**When to consider:** Phase 4+ (global scale, multi-region)
**Pros:** Distributed, automatic replication, PostgreSQL-compatible
**Cons:** Higher latency, more complex, not needed for Phase 1-3

---

#### **4.1.1 Connection Pooling: PgBouncer**

**Rationale:**
- **Efficiency:** Reduces connection overhead (PostgreSQL connections are expensive)
- **Scalability:** Support thousands of client connections with ~100 database connections
- **Protection:** Prevents connection exhaustion under load
- **Transaction pooling:** Fast connection reuse between transactions

**Configuration:**
```ini
# pgbouncer.ini
[databases]
trend_intelligence = host=postgres port=5432 dbname=trend_intelligence

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# Pool settings
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
reserve_pool_size = 5
reserve_pool_timeout = 3

# Performance tuning
server_idle_timeout = 600
server_lifetime = 3600
server_connect_timeout = 15
query_timeout = 0
```

**Docker Compose:**
```yaml
pgbouncer:
  image: edoburu/pgbouncer:latest
  environment:
    - DATABASE_URL=postgres://postgres:password@postgres:5432/trend_intelligence
    - POOL_MODE=transaction
    - MAX_CLIENT_CONN=1000
    - DEFAULT_POOL_SIZE=25
  ports:
    - "6432:6432"
  depends_on:
    - postgres
```

**Application Connection String:**
```python
# Use PgBouncer instead of direct PostgreSQL connection
DATABASE_URL = "postgresql+asyncpg://user:pass@pgbouncer:6432/trend_intelligence"
```

**When to add:** Phase 2+ (when you have >50 concurrent connections)

---

#### **4.2 Vector Database: Qdrant**

**Rationale:**
- **Performance:** Written in Rust, highly optimized
- **Python SDK:** Excellent, idiomatic Python API
- **Filtering:** Combine vector search + metadata filters efficiently
- **Sharding:** Built-in horizontal scaling
- **Open source:** Self-hosted, no vendor lock-in

**Setup:**
```yaml
# docker-compose.yml
qdrant:
  image: qdrant/qdrant:v1.7.0
  ports:
    - "6333:6333"
  volumes:
    - qdrant-storage:/qdrant/storage
  environment:
    - QDRANT__SERVICE__GRPC_PORT=6334
```

**Alternatives:**

| Vector DB | Pros | Cons | Verdict |
|-----------|------|------|---------|
| **pgvector** | PostgreSQL extension, simple, ACID guarantees | Slower at scale (>5M vectors), limited HNSW tuning | **Valid for Phase 1-2** if simplicity is priority |
| **Milvus** | Very mature, GPU support, large-scale | Complex setup, heavier infrastructure | Good for Phase 4+ |
| **Weaviate** | GraphQL API, schema-based, good ecosystem | Less flexible filtering, heavier | Good if GraphQL is priority |
| **Chroma** | Simple, SQLite-based, great for prototyping | Not production-ready for scale | Dev/testing only |
| **Pinecone** | Managed, easy, good performance | Vendor lock-in, costly | Avoid (not self-hosted) |

**Verdict:**
- **Phase 1 (MVP):** Consider **pgvector** if you want simplicity and have <1M vectors
- **Phase 2-3 (Production):** Use **Qdrant** for better performance and filtering
- **Phase 4 (Global Scale):** Consider **Milvus** if GPU acceleration needed

**pgvector Note:** Recent improvements (HNSW index, quantization) make pgvector viable for smaller datasets (<5M vectors). If you're already using PostgreSQL and want to minimize infrastructure, start with pgvector and migrate to Qdrant when you hit performance limits.

---

#### **4.3 Time-Series Database: TimescaleDB**

**Rationale:**
- **PostgreSQL extension:** Familiar SQL, easy migration
- **Compression:** Automatic compression (10x storage reduction)
- **Continuous aggregates:** Pre-compute rollups (hourly, daily)
- **No new infrastructure:** Runs alongside PostgreSQL

**Setup:**
```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Convert table to hypertable (time-series)
SELECT create_hypertable('trend_metrics', 'timestamp');

-- Add compression policy (compress data older than 7 days)
ALTER TABLE trend_metrics SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'trend_id'
);

SELECT add_compression_policy('trend_metrics', INTERVAL '7 days');

-- Create continuous aggregate (hourly rollups)
CREATE MATERIALIZED VIEW trend_metrics_hourly
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 hour', timestamp) AS hour,
  trend_id,
  AVG(engagement) AS avg_engagement,
  MAX(item_count) AS max_item_count
FROM trend_metrics
GROUP BY hour, trend_id;
```

**Alternative: InfluxDB**

**Pros:** Purpose-built for time-series, Flux query language
**Cons:** Separate infrastructure, different query language
**Verdict:** Use **TimescaleDB for simplicity**, **InfluxDB if need** specialized time-series features (e.g., anomaly detection, forecasting)

---

### 5. Caching

#### **Choice: Redis 7**

**Rationale:**
- **Speed:** In-memory, sub-millisecond latency
- **Versatility:** Strings, hashes, lists, sets, sorted sets, streams
- **Persistence:** RDB snapshots + AOF for durability
- **Clustering:** Redis Cluster for horizontal scaling

**Use Cases:**
1. Embedding cache (reduce OpenAI API costs)
2. Translation cache (reduce translation API costs)
3. API response cache (reduce database load)
4. Rate limiting (track API usage)
5. Session storage (user sessions)

**Configuration:**
```conf
# redis.conf
maxmemory 8gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

**Alternative: Valkey**

**What is it:** Redis fork (after Redis license change)
**Verdict:** Watch closely, switch if Redis becomes non-OSS

---

### 6. Object Storage

#### **Choice: MinIO**

**Rationale:**
- **S3-compatible:** Standard API, easy to migrate to/from cloud
- **Self-hosted:** Zero cloud costs
- **High performance:** Written in Go, optimized for throughput
- **Erasure coding:** Data redundancy without full replication overhead

**Setup:**
```yaml
# docker-compose.yml
minio:
  image: minio/minio:latest
  command: server /data --console-address ":9001"
  ports:
    - "9000:9000"
    - "9001:9001"
  environment:
    - MINIO_ROOT_USER=admin
    - MINIO_ROOT_PASSWORD=${MINIO_PASSWORD}
  volumes:
    - minio-data:/data
```

**Alternative: Local Filesystem**

**When to use:** Phase 1 only (simple, no dependencies)
**Cons:** No redundancy, harder to scale, no S3-compatible API
**Verdict:** Use **MinIO from the start** for future-proofing

---

### 7. Message Broker

#### **Choice: RabbitMQ**

**Rationale:**
- **Reliability:** Persistent queues, acknowledgments, dead-letter exchanges
- **Routing:** Complex routing patterns (topic, fanout, headers)
- **Management UI:** Built-in web UI for monitoring
- **Community:** Large community, many integrations

**Setup:**
```yaml
# docker-compose.yml
rabbitmq:
  image: rabbitmq:3-management
  ports:
    - "5672:5672"   # AMQP
    - "15672:15672" # Management UI
  environment:
    - RABBITMQ_DEFAULT_USER=admin
    - RABBITMQ_DEFAULT_PASS=${RABBITMQ_PASSWORD}
  volumes:
    - rabbitmq-data:/var/lib/rabbitmq
```

**Alternative: Apache Kafka**

**When to consider:** Phase 4+ (need event streaming, millions of messages/second)
**Pros:** Higher throughput, log-based architecture, event sourcing
**Cons:** Complex setup, heavier infrastructure, overkill for Phase 1-3
**Verdict:** **RabbitMQ for Phase 1-3**, **Kafka for Phase 4** if streaming workloads emerge

---

### 8. Observability

#### **8.1 Metrics: Prometheus**

**Rationale:**
- **Industry standard:** Most popular metrics system
- **Pull-based:** No agent installation needed
- **PromQL:** Powerful query language
- **Alerting:** Integrated with Alertmanager

**Setup:**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'api'
    static_configs:
      - targets: ['api:8000']
  - job_name: 'celery'
    static_configs:
      - targets: ['celery-exporter:9808']
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

**In-app instrumentation:**
```python
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

# Instrument FastAPI
@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    api_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    api_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response

# Expose /metrics endpoint
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

#### **8.2 Visualization: Grafana**

**Rationale:**
- **De facto standard:** Most popular dashboarding tool
- **Data sources:** Prometheus, Loki, Tempo, PostgreSQL, etc.
- **Alerting:** Visual alert configuration
- **Community dashboards:** Reusable dashboards for common services

**Setup:**
```yaml
# docker-compose.yml
grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
  volumes:
    - grafana-data:/var/lib/grafana
    - ./grafana/provisioning:/etc/grafana/provisioning
```

**Pre-built Dashboards:**
- **Node Exporter:** System metrics (CPU, RAM, disk)
- **PostgreSQL Exporter:** Database metrics
- **Redis Exporter:** Cache metrics
- **RabbitMQ:** Queue metrics

---

#### **8.3 Logging: Structured JSON + Loki**

**Rationale:**
- **Structured logging:** Machine-parseable (JSON)
- **Loki:** Like Prometheus, but for logs (low cost, high performance)
- **Correlation:** Trace IDs link logs to metrics to traces

**Setup:**
```python
import structlog

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Usage
logger.info(
    "trend_collected",
    trend_id="trend-123",
    source="youtube",
    item_count=50,
    duration_seconds=12.3
)

# Output:
# {"event": "trend_collected", "trend_id": "trend-123", "source": "youtube", "item_count": 50, "duration_seconds": 12.3, "timestamp": "2024-01-15T10:30:00Z", "level": "info"}
```

**Loki Setup:**
```yaml
# docker-compose.yml
loki:
  image: grafana/loki:latest
  ports:
    - "3100:3100"
  volumes:
    - loki-data:/loki
  command: -config.file=/etc/loki/local-config.yaml
```

---

### 9. Security & Authentication

#### **9.1 Authentication: JWT + OAuth 2.0**

**Rationale:**
- **JWT (JSON Web Tokens):** Stateless authentication, works across services
- **OAuth 2.0:** Industry standard for API authorization
- **FastAPI-Users:** Comprehensive auth solution for FastAPI

**Setup:**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": user_id}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Protect endpoints
@app.get("/api/v1/trends")
async def get_trends(user: dict = Depends(get_current_user)):
    # Only authenticated users can access
    return {"trends": [...]}
```

**API Key Authentication (for service-to-service):**
```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
```

**Recommended Libraries:**
- `python-jose[cryptography]`: JWT encoding/decoding
- `passlib[bcrypt]`: Password hashing
- `fastapi-users`: Complete auth solution with user management

---

#### **9.2 Secrets Management: HashiCorp Vault (Phase 3+)**

**Rationale:**
- **Dynamic secrets:** Generate credentials on-demand
- **Audit trail:** Track who accessed what secrets
- **Encryption as a service:** Centralized encryption/decryption
- **Lease management:** Automatic secret rotation

**Setup (Docker Compose):**
```yaml
vault:
  image: hashicorp/vault:latest
  ports:
    - "8200:8200"
  environment:
    - VAULT_DEV_ROOT_TOKEN_ID=${VAULT_ROOT_TOKEN}
    - VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200
  cap_add:
    - IPC_LOCK
  volumes:
    - vault-data:/vault/file
```

**Python Integration:**
```python
import hvac

# Initialize Vault client
client = hvac.Client(url="http://vault:8200", token=os.getenv("VAULT_TOKEN"))

# Read database credentials
db_creds = client.secrets.database.generate_credentials(name="postgres-role")
# Returns: {"username": "v-root-abc123", "password": "xyz789"}

# Store/retrieve secrets
client.secrets.kv.v2.create_or_update_secret(
    path="openai",
    secret={"api_key": "sk-..."}
)
```

**For Phase 1-2:** Use environment variables + `.env` files (with proper `.gitignore`)

**For Phase 3+:** Migrate to Vault for production secrets management

---

#### **9.3 Rate Limiting & API Protection**

**Rationale:**
- **Prevent abuse:** Protect against DDoS and scraping
- **Cost control:** Limit expensive operations (LLM calls)
- **Fair usage:** Ensure equitable resource distribution

**Implementation (Redis-based):**
```python
from fastapi import Request, HTTPException
from redis import Redis
import time

redis_client = Redis(host="redis", port=6379, decode_responses=True)

async def rate_limit(request: Request, calls: int = 100, period: int = 60):
    """Allow 'calls' requests per 'period' seconds"""
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"

    current = redis_client.get(key)
    if current is None:
        redis_client.setex(key, period, 1)
        return

    if int(current) >= calls:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    redis_client.incr(key)

# Apply to endpoints
@app.get("/api/v1/search")
async def search(
    request: Request,
    _: None = Depends(lambda r: rate_limit(r, calls=10, period=60))
):
    # Limited to 10 requests per minute per IP
    return {"results": [...]}
```

**Alternative Libraries:**
- `slowapi`: Rate limiting library for FastAPI
- `fastapi-limiter`: Redis-based rate limiting

---

#### **9.4 Input Validation & Sanitization**

**Use Pydantic for all inputs:**
```python
from pydantic import BaseModel, Field, validator
from typing import Literal

class TrendSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    category: Literal["tech", "business", "health"] | None = None
    limit: int = Field(default=10, ge=1, le=100)

    @validator("query")
    def sanitize_query(cls, v):
        # Remove SQL injection attempts, XSS, etc.
        dangerous_chars = ["<", ">", "script", "--", ";"]
        for char in dangerous_chars:
            if char.lower() in v.lower():
                raise ValueError("Invalid characters in query")
        return v.strip()
```

**SQL Injection Prevention:**
- **Always use SQLAlchemy ORM** (automatic parameterization)
- **Never** use raw SQL with string interpolation
- Use parameterized queries for raw SQL

**XSS Prevention:**
- Sanitize all user inputs before storing
- Use Content Security Policy (CSP) headers
- Escape HTML in responses

---

### 10. Machine Learning Libraries

#### **Embeddings: sentence-transformers**

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(["Text 1", "Text 2"], batch_size=512)
```

**Models:**
- `all-MiniLM-L6-v2`: 384 dims, fast, good quality (recommended for Phase 1-2)
- `all-mpnet-base-v2`: 768 dims, slower, higher quality
- `multilingual-e5-base`: Multilingual support

#### **Clustering: scikit-learn + HDBSCAN**

```python
from sklearn.cluster import AgglomerativeClustering
import hdbscan

# HDBSCAN for dynamic clustering
clusterer = hdbscan.HDBSCAN(min_cluster_size=5, metric='cosine')
labels = clusterer.fit_predict(embeddings)

# Agglomerative for hierarchical clustering
agg = AgglomerativeClustering(n_clusters=None, distance_threshold=0.3, linkage='average')
labels = agg.fit_predict(embeddings)
```

#### **LLM Integration: OpenAI SDK + LangChain**

```python
from openai import AsyncOpenAI
from langchain.prompts import PromptTemplate

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Direct API call
response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Summarize this trend: ..."}]
)

# LangChain for complex chains
template = PromptTemplate(
    input_variables=["trend_title", "topics"],
    template="Summarize this trend: {trend_title}\n\nTopics:\n{topics}"
)
```

---

#### **ML Model Management & Versioning**

**Challenges:**
- Track which embedding model version generated which vectors
- Version LLM prompts and compare performance
- Reproduce results from weeks/months ago
- A/B test different models

**Solution: MLflow (Lightweight)**

```python
import mlflow
from sentence_transformers import SentenceTransformer

# Track embedding model
with mlflow.start_run(run_name="embedding_model_v1"):
    mlflow.log_param("model_name", "all-MiniLM-L6-v2")
    mlflow.log_param("dimension", 384)
    mlflow.log_param("use_case", "trend_clustering")

    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Log model
    mlflow.pyfunc.log_model(
        artifact_path="embedding_model",
        python_model=model
    )

# Track LLM prompt versions
with mlflow.start_run(run_name="trend_summary_prompt_v2"):
    mlflow.log_param("model", "gpt-4o-mini")
    mlflow.log_param("temperature", 0.7)
    mlflow.log_text(prompt_template, "prompt.txt")

    # Log metrics after evaluation
    mlflow.log_metric("avg_summary_length", 150)
    mlflow.log_metric("user_satisfaction", 4.2)
```

**Docker Setup:**
```yaml
mlflow:
  image: ghcr.io/mlflow/mlflow:latest
  ports:
    - "5000:5000"
  command: mlflow server --host 0.0.0.0 --backend-store-uri postgresql://user:pass@postgres/mlflow --default-artifact-root s3://mlflow-artifacts
  environment:
    - AWS_ACCESS_KEY_ID=${MINIO_ACCESS_KEY}
    - AWS_SECRET_ACCESS_KEY=${MINIO_SECRET_KEY}
    - MLFLOW_S3_ENDPOINT_URL=http://minio:9000
```

**When to add:** Phase 2+ (when you start experimenting with multiple models)

**Alternatives:**
- **DVC (Data Version Control):** Git-like versioning for data/models
- **Weights & Biases:** Feature-rich, managed or self-hosted
- **Simple approach:** Git tags + model naming convention (e.g., `model_v1_20240115.pt`)

---

### 10. Containerization & Orchestration

#### **Phase 1-2: Docker + Docker Compose**

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    command: uvicorn main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/trend_intelligence
    depends_on:
      - postgres
      - redis
      - rabbitmq

  celery-worker:
    build: .
    command: celery -A tasks worker -Q ingestion,processing,llm --concurrency=4
    depends_on:
      - rabbitmq
      - redis

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: trend_intelligence
      POSTGRES_PASSWORD: password
    volumes:
      - postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redis-data:/data

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "15672:15672"

volumes:
  postgres-data:
  redis-data:
```

#### **Phase 3+: Kubernetes**

**Why Kubernetes:**
- **Auto-scaling:** HPA, VPA, cluster autoscaler
- **Self-healing:** Automatic restarts, health checks
- **Rolling updates:** Zero-downtime deployments
- **Resource management:** CPU/memory limits, quotas

**Example Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 5
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: trend-intelligence-api:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: 2
            memory: 4Gi
          limits:
            cpu: 4
            memory: 8Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

---

### 11. CI/CD & Deployment

#### **11.1 Continuous Integration: GitHub Actions**

**Rationale:**
- **Native GitHub integration:** No external service needed
- **Free for public repos:** Generous free tier for private repos
- **Matrix builds:** Test across multiple Python versions
- **Caching:** Speed up builds with dependency caching

**Workflow Example:**
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Lint with Ruff
        run: ruff check .

      - name: Type check with mypy
        run: mypy src/

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest --cov=src --cov-report=xml --cov-report=term-missing

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: true

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: trend-intelligence:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**Alternative:** GitLab CI, Jenkins, CircleCI

---

#### **11.2 Continuous Deployment**

**Deployment Strategies:**

| Strategy | Description | Use Case |
|----------|-------------|----------|
| **Blue-Green** | Two identical environments, switch traffic | Zero-downtime, easy rollback |
| **Canary** | Gradual rollout to subset of users | Risk mitigation, A/B testing |
| **Rolling** | Replace instances one by one | Kubernetes default, gradual |

**Kubernetes Deployment (Rolling Update):**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Zero downtime
  template:
    metadata:
      labels:
        app: api
        version: v1.2.3
    spec:
      containers:
      - name: api
        image: trend-intelligence:v1.2.3
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**GitHub Actions CD Workflow:**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: |
            myregistry/trend-intelligence:${{ github.ref_name }}
            myregistry/trend-intelligence:latest

      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/api \
            api=myregistry/trend-intelligence:${{ github.ref_name }}
          kubectl rollout status deployment/api
```

---

#### **11.3 Database Migrations**

**Use Alembic for schema versioning:**

```python
# alembic/versions/001_create_trends_table.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'trends',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
    )
    op.create_index('idx_trends_created_at', 'trends', ['created_at'])

def downgrade():
    op.drop_index('idx_trends_created_at')
    op.drop_table('trends')
```

**Migration Strategy:**
1. **Development:** Run migrations locally
2. **CI:** Run migrations in test database, validate
3. **Production:** Run migrations before deploying new code
   - Use `alembic upgrade head` in init container
   - Or run manually before deployment

**Best Practices:**
- ✅ Always write reversible migrations (downgrade function)
- ✅ Test migrations on production-like data
- ✅ Avoid long-running migrations during peak hours
- ✅ Use separate migration for data changes
- ⚠️ Never delete columns directly - deprecate first

---

#### **11.4 Feature Flags**

**Rationale:**
- **Gradual rollout:** Enable features for subset of users
- **Kill switch:** Disable problematic features instantly
- **A/B testing:** Test multiple versions simultaneously

**Simple Implementation (Redis-based):**
```python
from redis import Redis
from typing import Dict
import json

redis_client = Redis(host="redis", decode_responses=True)

class FeatureFlags:
    @staticmethod
    def is_enabled(feature: str, user_id: str | None = None) -> bool:
        # Check if feature is globally enabled
        global_config = redis_client.get(f"feature:{feature}")
        if not global_config:
            return False

        config = json.loads(global_config)

        # Global toggle
        if not config.get("enabled", False):
            return False

        # Percentage rollout
        if "percentage" in config:
            # Consistent hash-based rollout
            if user_id:
                hash_val = hash(f"{feature}:{user_id}") % 100
                if hash_val >= config["percentage"]:
                    return False

        # Whitelist
        if "whitelist" in config and user_id:
            if user_id not in config["whitelist"]:
                return False

        return True

# Usage
if FeatureFlags.is_enabled("new_clustering_algorithm", user_id=user.id):
    # Use new algorithm
    result = new_clustering(data)
else:
    # Use old algorithm
    result = old_clustering(data)
```

**Set feature flags:**
```python
# Enable for 10% of users
redis_client.set(
    "feature:new_clustering_algorithm",
    json.dumps({"enabled": True, "percentage": 10})
)

# Enable for specific users
redis_client.set(
    "feature:premium_features",
    json.dumps({
        "enabled": True,
        "whitelist": ["user-123", "user-456"]
    })
)
```

**Production-Grade Solutions:**
- **LaunchDarkly:** Managed feature flag service
- **Unleash:** Self-hosted, open-source
- **Flagsmith:** Open-source, cloud or self-hosted

---

#### **11.5 Backup & Disaster Recovery**

**Database Backups:**

```bash
# Automated PostgreSQL backup script
#!/bin/bash
# backup-postgres.sh

BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup
pg_dump -h postgres -U postgres trend_intelligence | gzip > \
  "$BACKUP_DIR/backup_$TIMESTAMP.sql.gz"

# Upload to S3-compatible storage (MinIO, AWS S3)
aws s3 cp "$BACKUP_DIR/backup_$TIMESTAMP.sql.gz" \
  "s3://backups/postgres/backup_$TIMESTAMP.sql.gz"

# Delete old backups
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
```

**Kubernetes CronJob for backups:**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:16
            command: ["/bin/bash", "/scripts/backup-postgres.sh"]
            volumeMounts:
            - name: backup-scripts
              mountPath: /scripts
            - name: backup-storage
              mountPath: /backups
          restartPolicy: OnFailure
```

**Disaster Recovery Plan:**

1. **RTO (Recovery Time Objective):** 1 hour
2. **RPO (Recovery Point Objective):** 24 hours (daily backups)

**Recovery Steps:**
```bash
# 1. Restore database from backup
gunzip < backup_20240115_020000.sql.gz | \
  psql -h postgres -U postgres trend_intelligence

# 2. Restore vector database (Qdrant)
# Qdrant supports snapshots
curl -X POST 'http://qdrant:6333/collections/trends/snapshots/upload' \
  -H 'Content-Type: multipart/form-data' \
  -F 'snapshot=@trends_snapshot.tar.gz'

# 3. Verify data integrity
python scripts/verify_data_integrity.py

# 4. Resume services
kubectl scale deployment/api --replicas=5
```

**What to back up:**
- ✅ PostgreSQL database (daily, WAL archiving for PITR)
- ✅ Qdrant vector database (snapshots)
- ✅ MinIO object storage (replication or S3 sync)
- ✅ Configuration files & secrets (encrypted)
- ✅ Redis (if persistence enabled, backup RDB files)

---

## Development Tools

### Code Quality

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "N", "UP", "B", "A", "C4", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
addopts = "--cov=src --cov-report=html --cov-report=term-missing"
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.2.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]
```

---

## Summary Matrix

### By Scale Phase

| Component | Phase 1 (MVP) | Phase 2 (Growth) | Phase 3 (Production) | Phase 4 (Global Scale) |
|-----------|---------------|------------------|----------------------|------------------------|
| **API** | FastAPI (1 instance) | FastAPI (2-3 instances) | FastAPI (5-10 pods) + LB | FastAPI (50+ pods, multi-region) |
| **Database** | PostgreSQL (single) | PostgreSQL + PgBouncer | PostgreSQL HA + replicas | CockroachDB (distributed) |
| **Vector DB** | pgvector or Qdrant | Qdrant (single) | Qdrant cluster (4 shards) | Milvus cluster (GPU) |
| **Cache** | Redis (single) | Redis (single, larger) | Redis cluster (3 nodes) | Redis cluster (10+ nodes) |
| **Queue** | RabbitMQ (single) | RabbitMQ (single) | RabbitMQ cluster (3 nodes) | Kafka cluster |
| **Workers** | 2-4 workers | 10-20 workers | 50-100 workers | 500+ workers (auto-scaled) |
| **Object Storage** | MinIO (single) | MinIO (single) | MinIO cluster (erasure coding) | Multi-region S3/MinIO |
| **Observability** | Prometheus + Grafana | + Loki (logs) | + Tempo (tracing) | Full stack + alerting |
| **Security** | Env vars, basic auth | + Rate limiting, JWT | + Vault, mTLS | Full security suite |
| **CI/CD** | Manual deployment | GitHub Actions | Automated + staging env | Multi-env + canary |
| **Backups** | Manual/daily | Automated daily | Daily + WAL archiving | PITR, geo-redundant |
| **ML Versioning** | Git commits | MLflow basic | MLflow + experiments | Full ML platform |
| **Deployment** | Docker Compose | Docker Compose / VM | Kubernetes (single cluster) | Kubernetes (multi-region) |
| **Team Size** | 1-2 developers | 2-5 developers | 5-15 developers | 15+ developers |
| **Expected Load** | <10 req/s | 10-100 req/s | 100-1000 req/s | >1000 req/s |

---

## Final Recommendations

### Phase 1 (MVP) - Weeks 1-4

**Goal:** Get to market quickly with minimal infrastructure

✅ **Core Stack:**
- **Language:** Python 3.12+
- **API:** FastAPI only (skip Django initially)
- **Database:** PostgreSQL 16 with pgvector
- **Cache:** Redis 7
- **Queue:** RabbitMQ + Celery
- **Storage:** MinIO
- **Deployment:** Docker Compose
- **Monitoring:** Prometheus + Grafana (basic)

✅ **Security Basics:**
- Environment variables for secrets (`.env` + `.gitignore`)
- Basic API key authentication
- Input validation with Pydantic

⚠️ **Explicitly Avoid:**
- Kubernetes (premature optimization)
- Kafka (too complex for initial scale)
- Separate vector database (use pgvector)
- Vault (use .env files)
- Django (adds complexity, use FastAPI admin libraries)
- Managed cloud services (unnecessary costs)

**Estimated Infrastructure Cost:** $50-100/month (single VM/VPS)

---

### Phase 2 (Growth) - Months 2-6

**Goal:** Handle increased traffic, improve developer productivity

✅ **Add:**
- **PgBouncer:** Connection pooling for PostgreSQL
- **Qdrant:** Migrate from pgvector when >1M vectors
- **Loki:** Centralized logging
- **MLflow:** Track model experiments
- **GitHub Actions:** Automated CI/CD
- **Rate limiting:** Protect APIs from abuse
- **JWT authentication:** Replace API keys
- **Automated backups:** Daily PostgreSQL dumps to S3

✅ **Scale existing:**
- 2-3 API instances (load balanced)
- 10-20 Celery workers
- Increase PostgreSQL resources

**Estimated Infrastructure Cost:** $200-500/month (2-3 VMs or small k8s cluster)

---

### Phase 3 (Production Scale) - Months 6-12

**Goal:** Production-grade reliability, security, and observability

✅ **Add:**
- **Kubernetes:** Container orchestration with auto-scaling
- **Vault:** Secrets management
- **Tempo/Jaeger:** Distributed tracing
- **PostgreSQL HA:** Primary + 2 replicas with automatic failover
- **Qdrant cluster:** 4+ shards for performance
- **Redis cluster:** 3+ nodes for high availability
- **RabbitMQ cluster:** 3 nodes for reliability
- **TimescaleDB:** Time-series analytics
- **Comprehensive monitoring:** Full observability stack with alerting
- **Staging environment:** Separate env for testing

✅ **Security:**
- mTLS between services
- Regular security audits
- Automated dependency scanning
- SOC 2 compliance prep (if needed)

⚠️ **Consider (but not required):**
- Temporal (only if complex multi-step workflows emerge)
- Self-hosted LLM with vLLM (if API costs too high)

**Estimated Infrastructure Cost:** $1,000-3,000/month (Kubernetes cluster)

---

### Phase 4 (Global Scale) - Year 2+

**Goal:** Multi-region deployment, extreme scale

✅ **Migrate to:**
- **CockroachDB:** Multi-region PostgreSQL replacement
- **Milvus:** GPU-accelerated vector search (if needed)
- **Kafka:** Replace RabbitMQ for event streaming
- **Multi-region Kubernetes:** Deploy to multiple geographic regions
- **CDN:** CloudFlare or similar for static assets
- **API Gateway:** Kong or similar for advanced routing

✅ **Advanced Features:**
- Canary deployments
- Chaos engineering (test resilience)
- Advanced ML platform (Kubeflow, etc.)
- Real-time analytics
- Global load balancing

**Estimated Infrastructure Cost:** $5,000-20,000+/month (multi-region)

---

## Decision Tree

**Start here:** Which phase are you in?

```
Are you pre-launch or have <100 users?
├─ YES → Phase 1 (MVP)
│  └─ Use: Docker Compose, pgvector, single instances
│
└─ NO → Do you have >10,000 daily active users?
   ├─ YES → Do you need multi-region deployment?
   │  ├─ YES → Phase 4 (Global Scale)
   │  └─ NO → Phase 3 (Production Scale)
   │
   └─ NO → Phase 2 (Growth)
      └─ Use: Multiple instances, Qdrant, basic automation
```

**Migration triggers:**

| From | To | Trigger |
|------|-----|---------|
| Phase 1 → 2 | When you hit 1,000+ DAU or >1M vectors | Add PgBouncer, Qdrant, CI/CD |
| Phase 2 → 3 | When you need 99.9% uptime SLA | Add Kubernetes, HA, monitoring |
| Phase 3 → 4 | When you need <100ms latency globally | Multi-region deployment |

---

## Common Pitfalls to Avoid

❌ **Don't:**
1. **Over-engineer Phase 1** - No Kubernetes for MVP
2. **Under-invest in monitoring** - Add Prometheus from day 1
3. **Ignore security** - Use environment variables properly, validate inputs
4. **Skip backups** - Automate from Phase 1
5. **Use managed services prematurely** - Self-host until it becomes a burden
6. **Optimize prematurely** - Profile first, then optimize
7. **Ignore database indexes** - Add indexes for all query patterns
8. **Store secrets in git** - Use `.env` (gitignored) or Vault
9. **Skip CI/CD** - Automate testing from Phase 2 at latest
10. **Forget about costs** - Monitor LLM API usage, add caching aggressively

---

## Technology Substitution Guide

**If you prefer different tools:**

| Current Recommendation | Alternative | Trade-off |
|------------------------|-------------|-----------|
| FastAPI | Flask + extensions | Less features, more manual work |
| Celery | Dramatiq, Temporal | Dramatiq simpler, Temporal more powerful |
| RabbitMQ | Redis (as broker) | Redis faster but less durable |
| Qdrant | pgvector, Weaviate | pgvector simpler, Weaviate more features |
| PostgreSQL | MySQL, CockroachDB | MySQL less features, CockroachDB distributed |
| MinIO | Local filesystem, S3 | Filesystem not scalable, S3 costly |
| Prometheus | VictoriaMetrics, Datadog | VM better performance, Datadog managed |
| GitHub Actions | GitLab CI, Jenkins | GitLab integrated, Jenkins self-hosted |

**Principle:** The recommendations prioritize **open source, self-hosted, Python-friendly** solutions. If you have different constraints (e.g., existing Java infrastructure), adapt accordingly.

---

## Conclusion

This tech stack provides:

✅ **Zero vendor lock-in** - All open-source, self-hosted options
✅ **Cost-effective** - Start at $50/month, scale as you grow
✅ **Production-ready** - Battle-tested components used by major companies
✅ **Python-first** - Leverage the rich ML/AI ecosystem
✅ **Scalable** - Proven technologies that scale horizontally
✅ **Secure** - Security built-in from Phase 1
✅ **Observable** - Comprehensive monitoring and logging
✅ **Maintainable** - Clear migration path between phases

**Key Principle:** Start simple, add complexity only when needed. Don't build Phase 3 infrastructure for Phase 1 problems.

**Next Steps:**
1. Identify your current phase based on user count and requirements
2. Implement only the components needed for that phase
3. Set up monitoring to identify when to scale
4. Plan migration to next phase based on metrics, not timelines

**Questions or feedback?** Open an issue or contribute improvements to this document.
