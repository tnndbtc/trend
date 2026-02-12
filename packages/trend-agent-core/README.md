# Trend Agent Core

Shared core library for the Trend Intelligence Platform.

## Overview

`trend-agent-core` is the foundational library used by all services in the Trend Intelligence Platform. It provides:

- **Storage abstractions** - PostgreSQL, Redis, Qdrant repositories
- **LLM integration** - OpenAI API client with retry logic
- **Intelligence modules** - Embeddings, clustering, deduplication
- **Workflow engine** - DAG-based workflow orchestration
- **Agent control plane** - Budget management, circuit breaker, governance
- **Observability** - Metrics, tracing, structured logging

## Installation

### Development (Editable Install)

From the repository root:

```bash
pip install -e packages/trend-agent-core
```

### Production

```bash
pip install trend-agent-core
```

### With Optional Dependencies

```bash
# Storage backends
pip install "trend-agent-core[storage]"

# Full instrumentation
pip install "trend-agent-core[instrumentation]"

# Development tools
pip install "trend-agent-core[dev]"

# Everything
pip install "trend-agent-core[storage,instrumentation,dev]"
```

## Modules

### Storage Layer (`trend_agent.storage`)

#### PostgreSQL Repository

```python
from trend_agent.storage.postgres import PostgreSQLTrendRepository

repo = PostgreSQLTrendRepository(
    host="localhost",
    port=5433,
    database="trends",
    user="trend_user",
    password="trend_password",
)

await repo.connect()

# Create trend
trend_id = await repo.create({
    "title": "AI Breakthrough",
    "url": "https://example.com",
    "source": "reddit",
    "content": "...",
})

# Query trends
trends = await repo.find_by_source("reddit", limit=10)

# Update trend
await repo.update(trend_id, {"views": 100})

# Delete trend
await repo.delete(trend_id)

await repo.close()
```

#### Redis Cache

```python
from trend_agent.storage.redis import RedisCacheRepository

cache = RedisCacheRepository(
    host="localhost",
    port=6380,
    default_ttl=3600,  # 1 hour
)

await cache.connect()

# Set value
await cache.set("key", {"data": "value"}, ttl=300)

# Get value
value = await cache.get("key")

# Delete
await cache.delete("key")

# Pattern matching
keys = await cache.keys("prefix:*")

await cache.close()
```

#### Qdrant Vector Store

```python
from trend_agent.storage.qdrant import QdrantVectorRepository

vector_repo = QdrantVectorRepository(
    host="localhost",
    port=6333,
    collection_name="trend_embeddings",
    vector_size=1536,
)

# Store embedding
await vector_repo.upsert(
    id="trend_123",
    vector=[0.1, 0.2, ...],  # 1536-dim embedding
    metadata={"title": "...", "source": "reddit"},
)

# Semantic search
results = await vector_repo.search(
    query_vector=[0.1, 0.2, ...],
    limit=10,
    score_threshold=0.7,
)

# Batch operations
await vector_repo.upsert_batch(vectors_batch)
```

### LLM Integration (`trend_agent.llm`)

```python
from trend_agent.llm.openai_client import OpenAIClient

llm = OpenAIClient(api_key="your-api-key")

# Generate completion
response = await llm.complete(
    prompt="Summarize this trend: ...",
    model="gpt-4",
    max_tokens=200,
)

# Generate embedding
embedding = await llm.embed("Your text here")
# Returns: [0.1, 0.2, ..., 0.9]  # 1536-dim vector

# Batch embeddings
embeddings = await llm.embed_batch(["text1", "text2", "text3"])

# With retry logic
response = await llm.complete_with_retry(
    prompt="...",
    max_retries=3,
    backoff_factor=2,
)
```

### Intelligence Modules (`trend_agent.intelligence`)

#### Embeddings

```python
from trend_agent.intelligence.embeddings import EmbeddingGenerator

generator = EmbeddingGenerator(llm_client=llm)

# Generate embedding for text
embedding = await generator.generate("AI trends in 2024")

# Batch generation
embeddings = await generator.generate_batch([
    "Trend 1",
    "Trend 2",
    "Trend 3",
])
```

#### Clustering

```python
from trend_agent.intelligence.clustering import TrendClusterer

clusterer = TrendClusterer(
    min_cluster_size=5,
    min_samples=3,
    metric="euclidean",
)

# Cluster trends by embeddings
clusters = await clusterer.cluster(embeddings)
# Returns: {0: [trend_1, trend_2], 1: [trend_3, trend_4], -1: [noise]}

# Get cluster statistics
stats = clusterer.get_cluster_stats()
# Returns: {"num_clusters": 5, "num_noise": 12, "sizes": [10, 8, 6, 5, 5]}
```

#### Deduplication

```python
from trend_agent.intelligence.deduplication import ContentDeduplicator

deduplicator = ContentDeduplicator(similarity_threshold=0.85)

# Find duplicates
duplicates = await deduplicator.find_duplicates([
    {"id": 1, "content": "AI breakthrough", "embedding": [...]},
    {"id": 2, "content": "Major AI advance", "embedding": [...]},
    {"id": 3, "content": "Unrelated news", "embedding": [...]},
])
# Returns: [(1, 2, 0.92)]  # IDs 1 and 2 are 92% similar

# Remove duplicates (keeps first occurrence)
unique_trends = await deduplicator.deduplicate(trends)
```

### Workflow Engine (`trend_agent.workflow`)

```python
from trend_agent.workflow.engine import WorkflowEngine
from trend_agent.workflow.dsl import WorkflowBuilder

# Build workflow
workflow = (
    WorkflowBuilder("trend_processing")
    .add_task("collect", collect_trends)
    .add_task("embed", generate_embeddings, depends_on=["collect"])
    .add_task("cluster", cluster_trends, depends_on=["embed"])
    .add_task("deduplicate", remove_duplicates, depends_on=["cluster"])
    .add_task("store", store_results, depends_on=["deduplicate"])
    .build()
)

# Execute workflow
engine = WorkflowEngine()
result = await engine.execute(workflow, input_data={"source": "reddit"})

# Monitor execution
status = engine.get_status(workflow.id)
# Returns: {"status": "running", "completed_tasks": 3, "total_tasks": 5}
```

### Agent Control Plane (`trend_agent.agents`)

#### Budget Manager

```python
from trend_agent.agents.budget import BudgetManager

budget_mgr = BudgetManager(
    daily_limit=1000.0,  # $1000/day
    cost_per_token=0.00002,  # GPT-4 pricing
)

# Check budget before API call
if await budget_mgr.can_afford(estimated_tokens=5000):
    response = await llm.complete(prompt)
    await budget_mgr.record_usage(
        tokens_used=len(response),
        cost=budget_mgr.calculate_cost(len(response)),
    )
else:
    logger.warning("Budget limit reached!")

# Get usage stats
stats = await budget_mgr.get_usage_stats()
# Returns: {"used": 750.0, "limit": 1000.0, "remaining": 250.0}
```

#### Circuit Breaker

```python
from trend_agent.agents.circuit_breaker import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,  # Open after 5 failures
    timeout=60,  # Try again after 60 seconds
    expected_exception=Exception,
)

# Protect external API call
@breaker
async def call_external_api():
    response = await client.get("https://api.example.com")
    return response

try:
    result = await call_external_api()
except CircuitBreakerOpenError:
    logger.error("Circuit breaker is open, using fallback")
    result = fallback_value
```

#### Governance

```python
from trend_agent.agents.governance import GovernancePolicy

policy = GovernancePolicy(
    max_api_calls_per_minute=100,
    allowed_models=["gpt-3.5-turbo", "gpt-4"],
    require_approval_for_cost_over=100.0,
)

# Check compliance
if policy.is_compliant(model="gpt-4", estimated_cost=50.0):
    response = await llm.complete(prompt, model="gpt-4")
else:
    logger.warning("Request violates governance policy")
```

### Observability (`trend_agent.observability`)

#### Metrics

```python
from trend_agent.observability.metrics import MetricsCollector

metrics = MetricsCollector()

# Counter
metrics.increment("trends_collected_total", labels={"source": "reddit"})

# Gauge
metrics.set("active_connections", 15)

# Histogram (for latency)
with metrics.timer("api_request_duration_seconds"):
    response = await api_call()

# Expose Prometheus metrics
from prometheus_client import generate_latest
metrics_output = generate_latest()
```

#### Tracing

```python
from trend_agent.observability.tracing import trace_async

@trace_async("collect_trends")
async def collect_trends(source: str):
    # Function is automatically traced
    with trace_span("fetch_data"):
        data = await fetch_from_source(source)

    with trace_span("process_data"):
        processed = process(data)

    return processed
```

## Configuration

### Environment Variables

```bash
# Database
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
export POSTGRES_DB=trends
export POSTGRES_USER=trend_user
export POSTGRES_PASSWORD=trend_password

# Cache
export REDIS_HOST=localhost
export REDIS_PORT=6380
export REDIS_PASSWORD=your_password  # Optional

# Vector Store
export QDRANT_HOST=localhost
export QDRANT_PORT=6333

# LLM
export OPENAI_API_KEY=your_api_key

# Observability
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export PROMETHEUS_PORT=9090
```

### Configuration File

```python
# config.py
from trend_agent.config import Config

config = Config.from_env()

# Or load from file
config = Config.from_file("config.json")

# Access configuration
db_host = config.get("postgres.host", "localhost")
redis_port = config.get("redis.port", 6380)
```

## Testing

```bash
# Run all tests
pytest packages/trend-agent-core/tests/

# Run specific module tests
pytest packages/trend-agent-core/tests/test_storage.py

# Run with coverage
pytest packages/trend-agent-core/tests/ --cov=trend_agent --cov-report=html
```

## Development

### Code Style

```bash
# Format code
black packages/trend-agent-core/trend_agent

# Lint code
ruff packages/trend-agent-core/trend_agent

# Type checking
mypy packages/trend-agent-core/trend_agent
```

### Adding New Modules

1. Create module in `trend_agent/your_module/`
2. Add `__init__.py` with public API
3. Add tests in `tests/test_your_module.py`
4. Update `setup.py` dependencies if needed
5. Document in this README

## Architecture

```
trend_agent/
├── storage/          # Data persistence layer
│   ├── postgres.py
│   ├── redis.py
│   └── qdrant.py
│
├── llm/             # LLM integration
│   ├── openai_client.py
│   └── retry.py
│
├── intelligence/    # AI/ML modules
│   ├── embeddings.py
│   ├── clustering.py
│   └── deduplication.py
│
├── workflow/        # Workflow engine
│   ├── engine.py
│   └── dsl.py
│
├── agents/          # Agent control plane
│   ├── budget.py
│   ├── circuit_breaker.py
│   └── governance.py
│
├── observability/   # Metrics and tracing
│   ├── metrics.py
│   ├── tracing.py
│   └── logging.py
│
├── ingestion/       # Data ingestion
│   └── manager.py
│
├── processing/      # Data processing
│   └── pipeline.py
│
└── config.py        # Configuration management
```

## Version Compatibility

| trend-agent-core | Python | PostgreSQL | Redis | Qdrant |
|-----------------|--------|------------|-------|--------|
| 1.0.x           | 3.11+  | 13+        | 6+    | 1.7+   |

## Changelog

### 1.0.0 (2024-02-12)

- Initial release
- Storage layer (PostgreSQL, Redis, Qdrant)
- LLM integration (OpenAI)
- Intelligence modules (embeddings, clustering, deduplication)
- Workflow engine with DAG support
- Agent control plane (budget, circuit breaker, governance)
- Observability (metrics, tracing, logging)

## License

See `LICENSE` in the root directory.
