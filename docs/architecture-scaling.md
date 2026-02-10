# AI Trend Intelligence Platform - Scaling Roadmap

## Executive Summary

This document provides a comprehensive scaling strategy for the AI Trend Intelligence Platform from local development to global scale. The platform progresses through five distinct phases (Phase 0–4), scaling from 1,000 trends to 10M+ trends while managing costs from $0 to ~$15,000/month. Key bottlenecks addressed include database write throughput, embedding generation costs, vector search latency, LLM summarization expenses, and collection concurrency. The strategy emphasizes horizontal scaling, self-hosted alternatives to reduce API costs (90% savings on LLM), and detailed migration paths with zero-downtime deployment options.

---

## Table of Contents

1. [Scaling Phases](#scaling-phases)
2. [Bottleneck Analysis & Solutions](#bottleneck-analysis--solutions)
3. [Horizontal Scaling Architecture](#horizontal-scaling-architecture)
4. [Cost & Performance Analysis](#cost--performance-analysis)
5. [Migration Guide](#migration-guide)
6. [Advanced Topics](#advanced-topics)

---

## Scaling Phases

This section outlines five distinct phases from local development to global scale. Each phase defines scale targets, throughput requirements, infrastructure needs, and monthly costs.

### Phase 0: Local Development (Current State)

**Purpose:** Development and testing environment

- **Scale:** 1,000 trends, 10,000 topics
- **Throughput:** 1,000 items/day
- **Infrastructure:** Docker Compose on single machine
- **Monthly Cost:** $0 (self-hosted)
- **Use Case:** Initial development, feature testing, small-scale proof of concept

### Phase 1: Single-Node Production

**Purpose:** Production deployment for early adopters

- **Scale:** 10,000 trends, 100,000 topics
- **Throughput:** 10,000 items/day
- **Infrastructure:** Single VM (16 CPU, 64 GB RAM, 500 GB SSD)
- **Monthly Cost:** ~$200
- **Upgrade Trigger:** Sustained throughput >8,000 items/day or storage >400 GB

### Phase 2: Vertical Scaling

**Purpose:** Scale-up before distributing workload

- **Scale:** 100,000 trends, 1M topics
- **Throughput:** 50,000 items/day
- **Infrastructure:** Larger VM (32 CPU, 128 GB RAM, 2 TB SSD)
- **Monthly Cost:** ~$800
- **Upgrade Trigger:** CPU utilization >80% sustained or latency degradation
- **Key Addition:** Read replicas for PostgreSQL

### Phase 3: Horizontal Scaling (Distributed)

**Purpose:** Distributed architecture for high availability and performance

- **Scale:** 1M+ trends, 10M+ topics
- **Throughput:** 500,000+ items/day
- **Infrastructure:** Kubernetes cluster (10 nodes)
- **Monthly Cost:** ~$3,000 (or ~$1,800 optimized)
- **Key Features:**
  - Multi-node database clusters with sharding
  - Dedicated worker pools per data source
  - Auto-scaling based on queue depth and CPU
  - GPU nodes for local embedding generation

### Phase 4: Global Scale

**Purpose:** Multi-region deployment for global reach

- **Scale:** 10M+ trends, 100M+ topics
- **Throughput:** 5M+ items/day
- **Infrastructure:** Multi-region Kubernetes (50+ nodes)
- **Monthly Cost:** ~$15,000
- **Key Features:**
  - Geo-distributed data centers
  - CDN for API responses
  - Cross-region replication
  - Advanced caching strategies

---

## Bottleneck Analysis & Solutions

This section identifies the five critical bottlenecks encountered during scaling and provides actionable solutions for each.

---

### Bottleneck 1: Database Write Throughput

**Symptom:** Slow database writes during peak collection periods, increasing insert latency.

**Current Limits (Phase 1):**
- PostgreSQL on single disk
- ~1,000 writes/second maximum

**Problem at Phase 3:**
- Required throughput: 10,000+ writes/second
- Single PostgreSQL instance cannot handle this load
- Write locks cause contention and delays

**Solution Overview:**

1. **Read Replicas** - Offload 80% of read traffic to dedicated replicas
2. **Write Sharding** - Partition data across multiple PostgreSQL instances using hash-based sharding
3. **Connection Pooling** - Deploy PgBouncer to reduce connection overhead and improve efficiency

**Implementation Steps:**

#### Step 1: Add Read Replicas (Phase 2)

Deploy PostgreSQL with streaming replication to offload read queries.

```yaml
# docker-compose.yml - Read replicas configuration
postgres-primary:
  image: postgres:16
  volumes:
    - pg-primary-data:/var/lib/postgresql/data
  environment:
    POSTGRES_DB: trend_intelligence
    POSTGRES_USER: admin
  command:
    - "postgres"
    - "-c"
    - "wal_level=replica"
    - "-c"
    - "max_wal_senders=5"

postgres-replica-1:
  image: postgres:16
  environment:
    PGUSER: replicator
    POSTGRES_REPLICATION_MODE: slave
    POSTGRES_MASTER_HOST: postgres-primary
```

**Application Code:**

```python
from sqlalchemy import create_engine
import random

# Primary for writes
write_engine = create_engine(os.getenv("POSTGRES_PRIMARY_URL"))

# Replicas for reads (round-robin load balancing)
read_engines = [
    create_engine(os.getenv("POSTGRES_REPLICA_1_URL")),
    create_engine(os.getenv("POSTGRES_REPLICA_2_URL"))
]

class DatabaseRouter:
    """Routes queries to primary (writes) or replicas (reads)"""

    def get_engine(self, operation: str):
        if operation == "write":
            return write_engine
        else:
            # Round-robin across read replicas
            return random.choice(read_engines)
```

#### Step 2: Implement Write Sharding (Phase 3)

Distribute writes across multiple PostgreSQL instances using hash-based sharding.

**Sharding Strategy:** Hash `trend_id` to determine target shard.

```python
# Shard configuration
shard_count = 4

def get_shard(trend_id: str) -> int:
    """Determine shard number based on trend_id hash"""
    return hash(trend_id) % shard_count

# Route writes to appropriate shard
async def save_trend(trend: Trend):
    shard_id = get_shard(trend.id)
    db = db_connections[shard_id]
    await db.execute(
        "INSERT INTO trends (id, title, content, published_at) VALUES ($1, $2, $3, $4)",
        trend.id, trend.title, trend.content, trend.published_at
    )
```

**Trade-offs:**
- ✅ **Pros:** Linear write scaling, isolated shard failures
- ⚠️ **Cons:** Cross-shard queries more complex, requires application-level routing

---

### Bottleneck 2: Embedding Generation

**Symptom:** Slow processing due to OpenAI API rate limits and high costs at scale.

**Current Limits (Phase 1):**
- OpenAI API: 3,000 requests/minute
- Batch size: ~50 items/request = 150,000 items/minute capacity
- Sufficient for 10,000 items/day

**Problem at Phase 3:**
- Required: 500,000 items/day = ~350 items/minute average
- Burst collection needs faster processing (10,000 items in 5 minutes)
- API costs become prohibitive: ~$200/month for embeddings alone

**Solution Overview:**

1. **Self-hosted Embedding Model** - Deploy sentence-transformers locally
2. **GPU Acceleration** - Use NVIDIA GPUs for 10x speed improvement
3. **Hybrid Approach** - Local for bulk processing, OpenAI for critical/high-quality needs

**Implementation Steps:**

#### Step 1: Deploy Local Embedding Model (Phase 2)

Use sentence-transformers with GPU acceleration for cost-effective bulk embedding generation.

```python
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

# Load model once at startup (use GPU if available)
local_model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensions
local_model.to('cuda')  # GPU acceleration

async def generate_embeddings_hybrid(texts: List[str], use_high_quality: bool = False):
    """
    Generate embeddings using hybrid approach:
    - Small batches (<100): Use OpenAI for higher quality (1536 dims)
    - Large batches (≥100): Use local model for speed and cost (384 dims)
    """

    if len(texts) < 100 or use_high_quality:
        # OpenAI for critical data (better semantic quality)
        return await openai_embedding_service.embed_batch(texts)
    else:
        # Local model for bulk processing (faster, free)
        embeddings = local_model.encode(
            texts,
            batch_size=512,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings
```

#### Step 2: Microservice Architecture (Phase 3)

Deploy embedding generation as a dedicated microservice with horizontal scaling.

```yaml
# Kubernetes deployment for embedding service
apiVersion: apps/v1
kind: Deployment
metadata:
  name: embedding-worker
spec:
  replicas: 3  # Scale based on queue depth
  selector:
    matchLabels:
      app: embedding-worker
  template:
    spec:
      nodeSelector:
        gpu: "true"  # Schedule on GPU nodes
      containers:
      - name: worker
        image: trend-intelligence-embedding:latest
        resources:
          limits:
            nvidia.com/gpu: 1  # 1 GPU per pod
            memory: 8Gi
          requests:
            memory: 4Gi
```

**Performance Comparison:**

| Method | Speed (items/sec) | Cost (per 1M items) | Embedding Quality |
|--------|-------------------|---------------------|-------------------|
| OpenAI API | 50 | $20 | High (1536 dims) |
| Local CPU | 100 | $0 | Medium (384 dims) |
| Local GPU (T4) | 1,000 | $0.50 (GPU rental) | Medium (384 dims) |

**Cost Savings:** 90-95% reduction for bulk processing

---

### Bottleneck 3: Vector Search Latency

**Symptom:** Slow similarity searches as the vector database grows.

**Current Performance (Phase 1):**
- Qdrant on single node
- ~10M embeddings stored
- P95 latency: ~50ms

**Problem at Phase 3:**
- 100M+ embeddings
- P95 latency degrades to 500ms+
- Single-node memory limitations (128 GB max)

**Solution Overview:**

1. **Qdrant Sharding** - Distribute vectors across multiple nodes
2. **HNSW Parameter Tuning** - Optimize the Hierarchical Navigable Small World graph for speed vs accuracy
3. **Pre-filtering** - Use metadata filters to reduce search space before vector comparison

**Implementation Steps:**

#### Step 1: Deploy Sharded Qdrant Cluster (Phase 3)

Distribute vectors across multiple nodes with replication for high availability.

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, ShardingMethod

client = QdrantClient(host="qdrant-cluster", port=6333)

# Create collection with sharding
client.create_collection(
    collection_name="topics",
    vectors_config=VectorParams(
        size=1536,  # OpenAI embedding dimension
        distance=Distance.COSINE
    ),
    shard_number=8,  # Distribute across 8 shards
    replication_factor=2,  # 2 replicas per shard for HA
    sharding_method=ShardingMethod.AUTO  # Automatic shard routing
)
```

**Cluster Benefits:**
- **Horizontal Scaling:** Add nodes to increase capacity linearly
- **High Availability:** 2x replication ensures fault tolerance
- **Load Distribution:** Queries distributed across shards

#### Step 2: Tune HNSW Parameters

**HNSW** (Hierarchical Navigable Small World) is the indexing algorithm used by Qdrant. Tuning its parameters trades accuracy for speed.

```python
from qdrant_client.models import HnswConfig

# Optimized for speed (slight accuracy trade-off)
hnsw_config = HnswConfig(
    m=16,  # Lower = faster search, less accurate (default: 16)
    ef_construct=100,  # Lower = faster indexing (default: 100)
    full_scan_threshold=20000  # Use brute-force below this size (default: 10k)
)

client.update_collection(
    collection_name="topics",
    hnsw_config=hnsw_config
)
```

**Parameter Guide:**
- **m:** Number of bi-directional links per node (16-64 typical)
- **ef_construct:** Size of dynamic candidate list during indexing (100-200 typical)
- **full_scan_threshold:** Switch to brute-force for small collections

#### Step 3: Implement Pre-filtering

Reduce search space using metadata filters before vector comparison.

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Search only within specific date range and category
search_result = client.search(
    collection_name="topics",
    query_vector=query_embedding,
    limit=10,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="published_at",
                range={
                    "gte": "2024-01-01",
                    "lte": "2024-12-31"
                }
            ),
            FieldCondition(
                key="category",
                match=MatchValue(value="technology")
            )
        ]
    )
)
```

**Performance Impact:**
- Pre-filtering reduces search space by 70-90%
- Latency improvement: 500ms → 80ms for filtered queries

---

### Bottleneck 4: LLM Summarization Cost

**Symptom:** High OpenAI API costs at scale make the platform economically unfeasible.

**Current Costs (Phase 1):**
- 10,000 items/day × 500 chars avg = 5M chars/day
- Cost: 5M chars ÷ 4 chars/token × $0.15/1M tokens = $1.88/day
- **Monthly:** ~$56

**Problem at Phase 3:**
- 500,000 items/day = 250M chars/day
- Cost: 250M ÷ 4 × $0.15/1M = $940/day
- **Monthly:** ~$28,000 (unsustainable)

**Solution Overview:**

1. **Self-hosted LLM** - Deploy LLaMA 3.1 70B or similar open-source model
2. **Summary Caching** - Aggressive deduplication before summarization
3. **Cluster Summarization** - Summarize topic clusters, not individual items (10x reduction)

**Implementation Steps:**

#### Step 1: Deploy Local LLM (Phase 2-3)

Use vLLM for efficient serving of open-source LLMs.

```python
from vllm import LLM, SamplingParams

# Load model (requires 4x A100 GPUs or 8x T4 GPUs)
llm = LLM(
    model="meta-llama/Meta-Llama-3.1-70B-Instruct",
    tensor_parallel_size=4,  # Distribute across 4 GPUs
    gpu_memory_utilization=0.9
)

async def summarize_local(text: str, max_words: int = 50) -> str:
    """Generate summary using local LLM"""

    prompt = f"""Summarize the following text in {max_words} words or less:

{text}

Summary:"""

    sampling_params = SamplingParams(
        temperature=0.3,  # Lower = more deterministic
        max_tokens=max_words * 2,  # Buffer for token-to-word ratio
        top_p=0.9
    )

    output = llm.generate([prompt], sampling_params)[0]
    return output.outputs[0].text.strip()
```

#### Step 2: Implement Aggressive Caching

Deduplicate similar content before summarization.

```python
import hashlib
from typing import Optional

class SummaryCache:
    """Cache summaries with content-based deduplication"""

    def __init__(self, redis_client):
        self.redis = redis_client

    def get_content_hash(self, text: str) -> str:
        """Generate hash for similarity detection"""
        # Normalize: lowercase, remove extra whitespace
        normalized = ' '.join(text.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def get_or_generate(self, text: str) -> str:
        """Check cache before generating new summary"""

        content_hash = self.get_content_hash(text)

        # Check cache
        cached = await self.redis.get(f"summary:{content_hash}")
        if cached:
            return cached

        # Generate new summary
        summary = await summarize_local(text)

        # Cache for 30 days
        await self.redis.setex(f"summary:{content_hash}", 2592000, summary)

        return summary
```

**Cost Comparison:**

| Method | Cost (500k items/day) | Monthly Cost | Notes |
|--------|----------------------|--------------|-------|
| OpenAI GPT-4o-mini | $940/day | $28,000 | High quality, API limits |
| OpenAI GPT-3.5 Turbo | $470/day | $14,000 | Lower quality |
| Self-hosted LLaMA 70B | $70/day GPU | $2,100 | One-time setup cost |
| Hybrid (cache + cluster) | $20/day GPU | $600 | 90% cache hit rate |

**Recommended:** Self-hosted with aggressive caching = **$26,000/month savings**

---

### Bottleneck 5: Collection Concurrency

**Symptom:** Sequential data collection from multiple sources creates delays and staleness.

**Current Performance (Phase 1):**
- 8 data sources
- ~5 seconds per source (serial)
- **Total collection time:** 40 seconds

**Problem at Phase 3:**
- 20+ data sources
- **Total collection time:** 100+ seconds (sequential)
- Real-time data becomes stale

**Solution Overview:**

1. **Parallel Collection** - Already implemented with `asyncio.gather()`
2. **Distributed Workers** - Dedicated worker pools per data source
3. **Priority Queues** - High-priority sources (Twitter, Reddit) processed first

**Implementation Steps:**

#### Step 1: Verify Parallel Collection (Phase 1)

Ensure asyncio parallel collection is working.

```python
import asyncio
from typing import List

async def collect_all_sources() -> List[dict]:
    """Collect from all sources in parallel"""

    sources = [
        collect_twitter(),
        collect_reddit(),
        collect_youtube(),
        collect_github(),
        collect_hackernews(),
        collect_producthunt(),
        collect_medium(),
        collect_devto()
    ]

    # Run all collectors concurrently
    results = await asyncio.gather(*sources, return_exceptions=True)

    # Filter out failures
    return [r for r in results if not isinstance(r, Exception)]
```

**Performance:** 40 seconds → 5 seconds (parallel)

#### Step 2: Deploy Dedicated Worker Pools (Phase 3)

Assign dedicated Celery workers per data source for isolation and scaling.

```yaml
# docker-compose.yml - Dedicated workers per source
services:
  # High-volume sources get more workers
  ingestion-worker-twitter:
    image: trend-intelligence
    command: celery -A tasks worker -Q twitter --concurrency=10
    deploy:
      replicas: 3

  ingestion-worker-reddit:
    image: trend-intelligence
    command: celery -A tasks worker -Q reddit --concurrency=8
    deploy:
      replicas: 2

  # Medium-volume sources
  ingestion-worker-youtube:
    image: trend-intelligence
    command: celery -A tasks worker -Q youtube --concurrency=5
    deploy:
      replicas: 2

  # Low-volume sources share a worker pool
  ingestion-worker-misc:
    image: trend-intelligence
    command: celery -A tasks worker -Q github,hackernews,medium --concurrency=5
```

**Benefits:**
- **Isolation:** One source failure doesn't affect others
- **Scaling:** Increase workers for high-volume sources independently
- **Monitoring:** Track performance per source

#### Step 3: Implement Priority Queues

```python
from celery import Celery

app = Celery('tasks', broker='amqp://rabbitmq')

# Define task priorities
@app.task(queue='twitter', priority=9)  # Highest priority
async def collect_twitter():
    ...

@app.task(queue='reddit', priority=8)
async def collect_reddit():
    ...

@app.task(queue='youtube', priority=5)  # Medium priority
async def collect_youtube():
    ...
```

**Performance at Phase 3:**
- Collection time: 2 minutes (down from 100+ seconds)
- High-priority sources processed first
- Better resource utilization

---

## Horizontal Scaling Architecture

This section describes the distributed architecture for Phase 3 and beyond.

### Phase 3: Distributed Cluster Architecture

The following diagram illustrates a multi-node cluster with load balancing, stateless API nodes, clustered databases, and distributed worker pools.

```
┌─────────────────────────────────────────────────────────────┐
│                    LOAD BALANCER                            │
│                  (NGINX / HAProxy)                          │
│  • Routes traffic to healthy API nodes                     │
│  • SSL termination                                          │
│  • Rate limiting                                            │
└────────────┬────────────────────────────────────────────────┘
             │
             ├────────────┬────────────┬────────────┐
             ▼            ▼            ▼            ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ...
│  API Node 1  │  │  API Node 2  │  │  API Node 3  │  (Stateless)
│  (FastAPI)   │  │  (FastAPI)   │  │  (FastAPI)   │
│  • REST API  │  │  • REST API  │  │  • REST API  │
│  • Stateless │  │  • Stateless │  │  • Stateless │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
┌────────────────┐                  ┌────────────────┐
│  PostgreSQL    │                  │  Qdrant        │
│  Cluster       │                  │  Cluster       │
│  • Primary     │                  │  • 4 shards    │
│  • 2 Replicas  │                  │  • 2 replicas  │
│  • Write shard │                  │  • Vector DB   │
└────────────────┘                  └────────────────┘

        ┌─────────────────┬─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Celery       │  │ Celery       │  │ Celery       │
│ Worker 1     │  │ Worker 2     │  │ Worker 3     │  ...
│ (Ingestion)  │  │ (Processing) │  │ (LLM)        │
│ • Twitter    │  │ • Embedding  │  │ • Summary    │
│ • Reddit     │  │ • Clustering │  │ • Analysis   │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │  RabbitMQ      │
                  │  Cluster       │
                  │  • 3 nodes     │
                  │  • HA queues   │
                  │  • Message bus │
                  └────────────────┘
```

**Component Roles:**

- **Load Balancer:** Distributes HTTP requests across API nodes, handles SSL, implements rate limiting
- **API Nodes:** Stateless FastAPI instances that scale horizontally based on CPU/memory
- **PostgreSQL Cluster:** Primary handles writes, replicas handle reads (80% of queries)
- **Qdrant Cluster:** Vector database sharded across nodes for parallel search
- **Celery Workers:** Specialized worker pools for different task types (ingestion, processing, LLM)
- **RabbitMQ Cluster:** High-availability message broker with mirrored queues

### Kubernetes Deployment

Deploy the platform on Kubernetes for orchestration, auto-scaling, and self-healing.

**Namespace:** `trend-intelligence`

#### API Deployment

```yaml
# api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: trend-intelligence
spec:
  replicas: 5  # Base replicas (HPA will adjust)
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
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: connection-string
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: redis-url
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
          initialDelaySeconds: 10
          periodSeconds: 5
---
# Service for API
apiVersion: v1
kind: Service
metadata:
  name: api-service
  namespace: trend-intelligence
spec:
  selector:
    app: api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

#### Ingestion Worker Deployment

```yaml
# ingestion-worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ingestion-worker
  namespace: trend-intelligence
spec:
  replicas: 10  # HPA will adjust based on queue depth
  selector:
    matchLabels:
      app: ingestion-worker
  template:
    metadata:
      labels:
        app: ingestion-worker
    spec:
      containers:
      - name: worker
        image: trend-intelligence-worker:latest
        command: ["celery", "-A", "tasks", "worker", "-Q", "ingestion", "--concurrency=4"]
        resources:
          requests:
            cpu: 1
            memory: 2Gi
          limits:
            cpu: 2
            memory: 4Gi
        env:
        - name: CELERY_BROKER_URL
          valueFrom:
            secretKeyRef:
              name: rabbitmq-secrets
              key: broker-url
```

#### Embedding Worker Deployment (GPU)

```yaml
# embedding-worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: embedding-worker
  namespace: trend-intelligence
spec:
  replicas: 3
  selector:
    matchLabels:
      app: embedding-worker
  template:
    metadata:
      labels:
        app: embedding-worker
    spec:
      nodeSelector:
        gpu: "true"  # Schedule on GPU-enabled nodes
      containers:
      - name: worker
        image: trend-intelligence-embedding:latest
        command: ["celery", "-A", "tasks", "worker", "-Q", "embedding"]
        resources:
          limits:
            nvidia.com/gpu: 1  # Request 1 GPU per pod
            memory: 16Gi
          requests:
            memory: 8Gi
        env:
        - name: CUDA_VISIBLE_DEVICES
          value: "0"
```

**Key Features:**
- **Auto-scaling:** HPA adjusts replicas based on CPU, memory, or queue depth
- **Health checks:** Liveness and readiness probes ensure pod health
- **Resource limits:** Prevents resource exhaustion and ensures fair scheduling
- **GPU scheduling:** Dedicated nodes for GPU workloads

---

## Cost & Performance Analysis

This section provides detailed cost breakdowns, performance benchmarks, and optimization strategies.

### Cost Breakdown by Phase

#### Phase 1: Single-Node Production (~$200/month)

| Component | Specification | Monthly Cost |
|-----------|--------------|--------------|
| VM (Compute) | 16 CPU, 64 GB RAM, 500 GB SSD | $180 |
| Bandwidth | 2 TB egress | $20 |
| **Total** | | **$200** |

**Cost Drivers:** Compute and storage

---

#### Phase 2: Vertical Scaling (~$800/month)

| Component | Specification | Monthly Cost |
|-----------|--------------|--------------|
| VM (Compute) | 32 CPU, 128 GB RAM, 2 TB SSD | $700 |
| PostgreSQL Replica | 16 CPU, 64 GB RAM, 1 TB SSD | $80 |
| Bandwidth | 5 TB egress | $20 |
| **Total** | | **$800** |

**Cost Drivers:** Larger VM, read replica

---

#### Phase 3: Horizontal Scaling (Unoptimized: ~$3,400/month)

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| Kubernetes Cluster | 10 nodes (4 CPU, 16 GB each) | $1,500 |
| PostgreSQL Cluster | Primary + 2 replicas (8 CPU, 32 GB each) | $600 |
| Qdrant Cluster | 4 nodes (4 CPU, 16 GB each) | $400 |
| Redis Cluster | 3 nodes (2 CPU, 8 GB each) | $150 |
| RabbitMQ Cluster | 3 nodes (2 CPU, 4 GB each) | $100 |
| GPU Nodes | 2× NVIDIA T4 (embedding generation) | $600 |
| Object Storage | 1 TB (backups, artifacts) | $50 |
| **Total** | | **$3,400** |

---

#### Phase 3: Optimized (~$1,800/month)

| Component | Configuration | Monthly Cost | Savings |
|-----------|--------------|--------------|---------|
| Kubernetes Cluster | 10 nodes (spot instances) | $750 | $750 |
| PostgreSQL Cluster | Primary + 2 replicas | $600 | $0 |
| Qdrant Cluster | 4 nodes | $400 | $0 |
| Redis Cluster | 3 nodes | $150 | $0 |
| RabbitMQ Cluster | 3 nodes | $100 | $0 |
| GPU Nodes | 2× NVIDIA T4 (spot) | $300 | $300 |
| Object Storage | 1 TB | $50 | $0 |
| Self-hosted LLM | Included in GPU nodes | $0 | $28,000* |
| **Total** | | **$1,800** | **$1,600 + $28k** |

*Savings from self-hosted LLM vs OpenAI API at 500k items/day

**Optimization Strategies:**

1. **Spot Instances for Workers:** 50-70% cost reduction for fault-tolerant workloads
2. **Self-hosted LLM:** 90% cost reduction vs OpenAI API ($28k → $2k/month)
3. **Aggressive Caching:** Reduces API calls by 70%, lowering embedding and LLM costs
4. **Auto-scaling:** Scale down during off-peak hours (30% reduction in compute costs)
5. **Reserved Instances:** 1-year commitment for databases (20% discount)

---

### Performance Benchmarks

#### Phase 1: Single-Node Production

| Metric | Value | Notes |
|--------|-------|-------|
| **Throughput** | 10,000 items/day | ~7 items/minute |
| **API Latency (P50)** | 80ms | Median response time |
| **API Latency (P95)** | 200ms | 95th percentile |
| **API Latency (P99)** | 350ms | 99th percentile |
| **Collection Time** | 5 minutes | All sources (parallel) |
| **Processing Time** | 15 minutes | 10,000 items (embedding + clustering) |
| **Vector Search (P95)** | 50ms | 10M embeddings |
| **Database Write Rate** | 800 writes/sec | PostgreSQL peak |

---

#### Phase 3: Distributed Cluster

| Metric | Value | Improvement | Notes |
|--------|-------|-------------|-------|
| **Throughput** | 500,000 items/day | 50x | ~350 items/minute |
| **API Latency (P50)** | 40ms | 2x faster | Better caching |
| **API Latency (P95)** | 150ms | 1.3x faster | Load balanced |
| **API Latency (P99)** | 280ms | 1.25x faster | Fewer outliers |
| **Collection Time** | 2 minutes | 2.5x faster | Distributed workers |
| **Processing Time** | 30 minutes | 10x faster per item | 500k items in 30 min vs 10k in 15 min |
| **Vector Search (P95)** | 80ms | 1.6x slower* | 100M embeddings, but sharded |
| **Database Write Rate** | 12,000 writes/sec | 15x | Sharded across 4 instances |

*Latency increases with dataset size, but sharding keeps it manageable

---

### Trade-off Analysis

#### Vertical vs Horizontal Scaling

| Aspect | Vertical Scaling (Phase 2) | Horizontal Scaling (Phase 3) |
|--------|----------------------------|------------------------------|
| **Complexity** | Low (single machine) | High (distributed systems) |
| **Max Scale** | Limited by hardware (128 CPU, 1 TB RAM) | Unlimited (add more nodes) |
| **Cost Efficiency** | Good up to $800/month | Better at >$1,500/month |
| **High Availability** | Single point of failure | Multi-node redundancy |
| **Deployment Time** | Minutes (restart VM) | Hours (cluster setup) |
| **When to Use** | <50k items/day, <1M topics | >100k items/day, >1M topics |

**Recommendation:** Start with vertical scaling (Phase 2) and migrate to horizontal (Phase 3) when you hit resource limits or need high availability.

---

#### Local vs Cloud Embeddings

| Aspect | OpenAI API | Local CPU | Local GPU (T4) |
|--------|-----------|-----------|----------------|
| **Quality** | High (1536 dims) | Medium (384 dims) | Medium (384 dims) |
| **Speed** | 50 items/sec | 100 items/sec | 1,000 items/sec |
| **Cost (1M items)** | $20 | $0 | $0.50 (GPU rental) |
| **Setup Complexity** | None (API key) | Low (pip install) | Medium (GPU drivers, CUDA) |
| **Rate Limits** | 3,000 req/min | Unlimited | Unlimited |
| **When to Use** | <10k items/day | 10-50k items/day | >50k items/day |

**Recommendation:** Use hybrid approach—OpenAI for critical data, local GPU for bulk processing.

---

#### Self-hosted vs API LLM

| Aspect | OpenAI GPT-4o-mini | Self-hosted LLaMA 70B |
|--------|-------------------|----------------------|
| **Quality** | Excellent | Very Good |
| **Cost (500k items/day)** | $28,000/month | $2,000/month (GPU) |
| **Latency** | 500ms (API call) | 200ms (local) |
| **Setup Complexity** | None | High (vLLM, 4x GPUs) |
| **Rate Limits** | Yes (10k req/min) | None |
| **When to Use** | <10k items/day | >50k items/day |

**Recommendation:** Self-host LLM at Phase 3 for 90% cost savings.

---

## Migration Guide

This section provides step-by-step migration paths between scaling phases.

### Migration Path 1: Phase 1 → Phase 2 (Vertical Scaling)

**Goal:** Upgrade to larger server and add read replicas.

**Prerequisites:**
- [ ] Current throughput consistently >8,000 items/day
- [ ] CPU utilization >70% sustained
- [ ] Storage usage >350 GB

**Estimated Downtime:** 15-30 minutes (can be zero with careful planning)

**Steps:**

#### 1. Preparation (Day 1)

- [ ] **Benchmark current performance**
  ```bash
  # Record baseline metrics
  docker stats --no-stream > phase1_baseline.txt
  psql -c "SELECT pg_database_size('trend_intelligence');" > db_size.txt
  ```

- [ ] **Provision new VM**
  - Specification: 32 CPU, 128 GB RAM, 2 TB SSD
  - OS: Ubuntu 22.04 LTS
  - Network: Same VPC as current VM

- [ ] **Install dependencies on new VM**
  ```bash
  # Docker, Docker Compose, monitoring tools
  curl -fsSL https://get.docker.com | sh
  apt-get install -y postgresql-client monitoring-tools
  ```

#### 2. Database Migration (Day 2)

- [ ] **Set up PostgreSQL read replica on new VM**
  ```bash
  # On primary (old VM), enable replication
  psql -c "ALTER SYSTEM SET wal_level = replica;"
  psql -c "ALTER SYSTEM SET max_wal_senders = 5;"
  systemctl restart postgresql

  # Create replication user
  psql -c "CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'secure_password';"
  ```

- [ ] **Initialize replica on new VM**
  ```bash
  # Base backup from primary
  pg_basebackup -h old-vm-ip -D /var/lib/postgresql/data -U replicator -P -v

  # Configure as standby
  echo "primary_conninfo = 'host=old-vm-ip port=5432 user=replicator password=secure_password'" >> /var/lib/postgresql/data/postgresql.auto.conf
  touch /var/lib/postgresql/data/standby.signal

  # Start replica
  systemctl start postgresql
  ```

- [ ] **Verify replication is working**
  ```bash
  # On primary
  psql -c "SELECT * FROM pg_stat_replication;"

  # Should show replica connected
  ```

#### 3. Application Migration (Day 3)

- [ ] **Deploy application on new VM**
  ```bash
  # Copy docker-compose.yml and .env
  scp docker-compose.yml new-vm:/app/
  scp .env new-vm:/app/

  # Start services (in testing mode)
  docker-compose up -d
  ```

- [ ] **Update application to use read replica**
  ```python
  # config.py - Add replica URL
  POSTGRES_PRIMARY_URL = os.getenv("POSTGRES_PRIMARY_URL")  # Old VM
  POSTGRES_REPLICA_URLS = [os.getenv("POSTGRES_REPLICA_1_URL")]  # New VM
  ```

- [ ] **Test read queries against replica**
  ```bash
  # Verify queries work
  curl http://new-vm:8000/api/trends?limit=10
  ```

#### 4. Cutover (Day 4)

- [ ] **Promote replica to primary (downtime starts)**
  ```bash
  # Stop writes on old VM
  docker-compose stop api worker

  # Wait for replication to catch up (check lag = 0)
  psql -h old-vm -c "SELECT pg_current_wal_lsn();"
  psql -h new-vm -c "SELECT pg_last_wal_receive_lsn();"

  # Promote replica to primary
  pg_ctl promote -D /var/lib/postgresql/data
  ```

- [ ] **Update DNS/load balancer**
  ```bash
  # Point app.example.com to new VM IP
  # Wait for DNS propagation (5 minutes)
  ```

- [ ] **Verify writes working on new VM**
  ```bash
  # Test write endpoint
  curl -X POST http://new-vm:8000/api/trends -d '{"title":"Test"}'

  # Check database
  psql -h new-vm -c "SELECT COUNT(*) FROM trends;"
  ```

- [ ] **Decommission old VM (downtime ends)**
  ```bash
  # Stop all services
  docker-compose down

  # Keep VM for 7 days as backup, then delete
  ```

#### 5. Tune PostgreSQL for New Hardware (Day 5)

- [ ] **Optimize PostgreSQL configuration**
  ```sql
  -- Increase shared buffers (25% of RAM)
  ALTER SYSTEM SET shared_buffers = '32GB';

  -- Increase work memory for complex queries
  ALTER SYSTEM SET work_mem = '256MB';

  -- Increase max connections
  ALTER SYSTEM SET max_connections = 500;

  -- Restart PostgreSQL
  ```

- [ ] **Create indexes for common queries**
  ```sql
  CREATE INDEX CONCURRENTLY idx_trends_published_at ON trends(published_at DESC);
  CREATE INDEX CONCURRENTLY idx_topics_trend_id ON topics(trend_id);
  ```

#### 6. Verification (Day 6-7)

- [ ] **Monitor performance for 48 hours**
  - CPU utilization <60%
  - Memory utilization <70%
  - Disk I/O <80%
  - API latency P95 <200ms

- [ ] **Load test**
  ```bash
  # Simulate 20k items/day
  locust -f load_test.py --host http://new-vm:8000 --users 100
  ```

- [ ] **Verify backups working**
  ```bash
  # Test restore from backup
  pg_restore --dbname=trend_intelligence backup.dump
  ```

**Rollback Plan:**
If issues arise, point DNS back to old VM (kept online for 7 days).

---

### Migration Path 2: Phase 2 → Phase 3 (Horizontal Scaling)

**Goal:** Migrate from single-node to Kubernetes cluster.

**Prerequisites:**
- [ ] Throughput consistently >40,000 items/day
- [ ] Need for high availability (>99.9% uptime)
- [ ] Database size >500 GB

**Estimated Downtime:** 0 (zero-downtime migration with replication)

**Timeline:** 2-3 weeks

#### Week 1: Cluster Setup

##### Day 1-2: Provision Kubernetes Cluster

- [ ] **Create Kubernetes cluster**
  ```bash
  # Using managed Kubernetes (GKE, EKS, AKS)
  gcloud container clusters create trend-intelligence \
    --num-nodes=10 \
    --machine-type=n1-standard-4 \
    --enable-autoscaling \
    --min-nodes=5 \
    --max-nodes=20
  ```

- [ ] **Configure kubectl**
  ```bash
  gcloud container clusters get-credentials trend-intelligence
  kubectl create namespace trend-intelligence
  ```

- [ ] **Set up persistent storage**
  ```bash
  kubectl apply -f storage-class.yaml
  ```

##### Day 3-4: Deploy Databases

- [ ] **Deploy PostgreSQL cluster (primary + 2 replicas)**
  ```bash
  # Using Helm chart for PostgreSQL HA
  helm install postgres bitnami/postgresql-ha \
    --namespace trend-intelligence \
    --set postgresql.replicaCount=2 \
    --set postgresql.resources.requests.memory=32Gi \
    --set postgresql.resources.requests.cpu=8
  ```

- [ ] **Set up replication from old DB to new cluster**
  ```bash
  # Configure logical replication
  psql -h old-vm -c "CREATE PUBLICATION migration FOR ALL TABLES;"
  psql -h postgres-primary-k8s -c "CREATE SUBSCRIPTION migration CONNECTION 'host=old-vm dbname=trend_intelligence' PUBLICATION migration;"
  ```

- [ ] **Verify replication lag < 1 second**
  ```bash
  psql -h postgres-primary-k8s -c "SELECT * FROM pg_stat_subscription;"
  ```

- [ ] **Deploy Qdrant cluster (4 shards)**
  ```bash
  kubectl apply -f qdrant-statefulset.yaml
  # Wait for all pods ready
  kubectl wait --for=condition=ready pod -l app=qdrant --timeout=600s
  ```

- [ ] **Migrate vector data to Qdrant cluster**
  ```python
  # Script to migrate vectors from old Qdrant to new cluster
  from qdrant_client import QdrantClient

  old_client = QdrantClient(host="old-vm", port=6333)
  new_client = QdrantClient(host="qdrant-cluster-k8s", port=6333)

  # Stream and migrate all vectors
  for batch in old_client.scroll("topics", limit=1000):
      new_client.upsert("topics", points=batch)
  ```

##### Day 5-7: Deploy Application Components

- [ ] **Build and push container images**
  ```bash
  # API
  docker build -t gcr.io/project/trend-api:v1.0 -f Dockerfile.api .
  docker push gcr.io/project/trend-api:v1.0

  # Workers
  docker build -t gcr.io/project/trend-worker:v1.0 -f Dockerfile.worker .
  docker push gcr.io/project/trend-worker:v1.0
  ```

- [ ] **Deploy API pods**
  ```bash
  kubectl apply -f api-deployment.yaml
  kubectl apply -f api-service.yaml
  ```

- [ ] **Deploy Celery workers**
  ```bash
  kubectl apply -f ingestion-worker-deployment.yaml
  kubectl apply -f processing-worker-deployment.yaml
  kubectl apply -f llm-worker-deployment.yaml
  ```

- [ ] **Deploy RabbitMQ cluster**
  ```bash
  helm install rabbitmq bitnami/rabbitmq \
    --namespace trend-intelligence \
    --set replicaCount=3 \
    --set auth.password=secure_password
  ```

#### Week 2: Testing & Validation

##### Day 8-10: Integration Testing

- [ ] **Test API endpoints**
  ```bash
  # Health check
  curl http://api-service.trend-intelligence/health

  # Read endpoint (from new cluster)
  curl http://api-service.trend-intelligence/api/trends?limit=10

  # Write endpoint (verify writes to old DB still)
  curl -X POST http://api-service.trend-intelligence/api/trends -d '{"title":"Test"}'
  ```

- [ ] **Test worker processing**
  ```bash
  # Trigger collection job
  kubectl exec -it ingestion-worker-0 -- celery -A tasks call collect_all_sources

  # Monitor queue depth
  kubectl exec -it rabbitmq-0 -- rabbitmqctl list_queues
  ```

- [ ] **Verify data consistency**
  ```bash
  # Compare record counts
  psql -h old-vm -c "SELECT COUNT(*) FROM trends;"
  psql -h postgres-primary-k8s -c "SELECT COUNT(*) FROM trends;"
  ```

##### Day 11-12: Load Testing

- [ ] **Run load test against new cluster**
  ```bash
  # Simulate 100k items/day load
  locust -f load_test.py --host http://api-service.trend-intelligence --users 500 --spawn-rate 10
  ```

- [ ] **Monitor resource usage**
  ```bash
  # Check pod resource utilization
  kubectl top pods -n trend-intelligence

  # Check node resource utilization
  kubectl top nodes
  ```

- [ ] **Verify auto-scaling working**
  ```bash
  # Check HPA status
  kubectl get hpa -n trend-intelligence

  # Should show scaling based on CPU/queue depth
  ```

##### Day 13-14: Shadow Traffic

- [ ] **Route 10% of read traffic to new cluster**
  ```nginx
  # Load balancer config - weighted routing
  upstream backend {
      server old-vm:8000 weight=9;
      server api-service.trend-intelligence weight=1;
  }
  ```

- [ ] **Monitor for errors**
  ```bash
  # Check error rates
  kubectl logs -l app=api -n trend-intelligence | grep ERROR
  ```

- [ ] **Gradually increase to 50% traffic**
  ```nginx
  upstream backend {
      server old-vm:8000 weight=5;
      server api-service.trend-intelligence weight=5;
  }
  ```

#### Week 3: Cutover

##### Day 15: Database Cutover

- [ ] **Stop replication from old to new**
  ```bash
  psql -h postgres-primary-k8s -c "ALTER SUBSCRIPTION migration DISABLE;"
  ```

- [ ] **Point all writes to new cluster**
  ```bash
  # Update application config
  kubectl set env deployment/api DATABASE_URL=postgresql://postgres-primary-k8s/trend_intelligence
  ```

- [ ] **Verify writes working on new cluster**
  ```bash
  psql -h postgres-primary-k8s -c "SELECT COUNT(*) FROM trends WHERE created_at > NOW() - INTERVAL '1 hour';"
  ```

##### Day 16: Full Traffic Cutover

- [ ] **Route 100% traffic to new cluster**
  ```nginx
  upstream backend {
      server api-service.trend-intelligence;
      # Remove old-vm from rotation
  }
  ```

- [ ] **Monitor for 24 hours**
  - API error rate <0.1%
  - Latency P95 <150ms
  - All workers processing successfully

##### Day 17-21: Monitoring & Optimization

- [ ] **Set up Prometheus & Grafana**
  ```bash
  helm install prometheus prometheus-community/kube-prometheus-stack \
    --namespace monitoring
  ```

- [ ] **Configure alerts**
  ```yaml
  # alerting-rules.yaml
  groups:
  - name: api
    rules:
    - alert: HighErrorRate
      expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
      annotations:
        summary: "High error rate detected"
  ```

- [ ] **Optimize resource limits based on actual usage**
  ```bash
  # Review actual usage
  kubectl top pods -n trend-intelligence --containers

  # Adjust resource requests/limits in deployments
  ```

- [ ] **Decommission old VM**
  ```bash
  # After 7 days of stable operation
  # Backup final state
  pg_dump -h old-vm trend_intelligence > final_backup.sql

  # Shut down and delete
  ```

**Rollback Plan:**

If critical issues occur during Days 15-16:

1. Re-enable replication: `ALTER SUBSCRIPTION migration ENABLE;`
2. Point traffic back to old VM
3. Investigate and fix issues
4. Retry cutover

**Success Criteria:**

- [ ] API uptime >99.9% for 7 days
- [ ] P95 latency <150ms
- [ ] No data loss (verified via checksums)
- [ ] Worker processing rate >50k items/day
- [ ] Cost within budget ($1,800-$3,400/month)

---

## Advanced Topics

### Auto-Scaling Strategies

#### Horizontal Pod Autoscaler (HPA) for API

Automatically adjust API pod count based on CPU and memory utilization.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: trend-intelligence
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3  # Minimum for HA
  maxReplicas: 20  # Cap to control costs
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70  # Scale up at 70% CPU
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80  # Scale up at 80% memory
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60  # Wait 60s before scaling up
      policies:
      - type: Percent
        value: 50  # Scale up by 50% at a time
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scaling down
      policies:
      - type: Pods
        value: 1  # Scale down 1 pod at a time
        periodSeconds: 60
```

#### Queue-Based Autoscaling for Workers

Scale workers based on RabbitMQ queue depth.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ingestion-worker-hpa
  namespace: trend-intelligence
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ingestion-worker
  minReplicas: 5  # Always have 5 workers
  maxReplicas: 50  # Cap at 50 workers
  metrics:
  - type: External
    external:
      metric:
        name: rabbitmq_queue_depth
        selector:
          matchLabels:
            queue: ingestion
      target:
        type: AverageValue
        averageValue: "100"  # 100 messages per worker
```

**How it works:**
- If queue has 1,000 messages and 5 workers → 200 msgs/worker → Scale up
- Target: 100 msgs/worker → Scale to 10 workers
- If queue drops to 300 messages → Scale down to 3 workers (but minimum is 5)

---

### Caching Strategies

#### Redis Cluster for Distributed Caching (Phase 3)

Deploy a 3-node Redis cluster with automatic sharding.

```yaml
# redis-cluster.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-cluster-config
data:
  redis.conf: |
    cluster-enabled yes
    cluster-config-file nodes.conf
    cluster-node-timeout 5000
    appendonly yes
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-cluster
spec:
  serviceName: redis-cluster
  replicas: 6  # 3 masters + 3 replicas
  selector:
    matchLabels:
      app: redis-cluster
  template:
    spec:
      containers:
      - name: redis
        image: redis:7
        ports:
        - containerPort: 6379
          name: client
        - containerPort: 16379
          name: gossip
        volumeMounts:
        - name: data
          mountPath: /data
        - name: config
          mountPath: /etc/redis
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi
```

**Client-side usage:**

```python
from redis.cluster import RedisCluster

redis_client = RedisCluster(
    host="redis-cluster",
    port=6379,
    decode_responses=True,
    skip_full_coverage_check=True
)

# Automatic sharding based on key
redis_client.set("embedding:abc123", embedding_vector)
redis_client.set("trend:xyz789", trend_data)

# Retrieval
embedding = redis_client.get("embedding:abc123")
```

**Cache Strategy:**

```python
class CacheManager:
    """Centralized caching with TTL management"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def get_or_compute(self, key: str, compute_fn, ttl: int = 3600):
        """Get from cache or compute and cache result"""

        # Try cache first
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)

        # Compute
        result = await compute_fn()

        # Cache with TTL
        await self.redis.setex(key, ttl, json.dumps(result))

        return result
```

---

### Monitoring & Observability

#### Prometheus Metrics

Expose custom metrics for business logic monitoring.

```python
from prometheus_client import Counter, Histogram, Gauge

# API request metrics
api_requests_total = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"]
)

api_latency_seconds = Histogram(
    "api_request_duration_seconds",
    "API request latency",
    ["endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Worker metrics
worker_queue_depth = Gauge(
    "worker_queue_depth",
    "Number of pending tasks",
    ["queue_name"]
)

worker_processing_time = Histogram(
    "worker_processing_seconds",
    "Worker task processing time",
    ["task_type"]
)

# Database metrics
db_connections_active = Gauge(
    "db_connections_active",
    "Active database connections",
    ["database"]
)

db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["query_type"]
)
```

**Grafana Dashboards:**

1. **System Health Dashboard**
   - API request rate (requests/sec)
   - API latency (P50, P95, P99)
   - Error rate (% of 5xx responses)
   - Worker queue depth by source

2. **Database Dashboard**
   - Write throughput (writes/sec)
   - Replication lag (seconds)
   - Connection pool usage (%)
   - Cache hit rate (%)

3. **Cost Dashboard**
   - LLM API costs (daily/monthly)
   - Embedding API costs (daily/monthly)
   - Infrastructure costs (monthly projection)
   - Cost per processed item

---

### Disaster Recovery

#### Backup Strategy (Phase 3+)

**PostgreSQL:**

- **Continuous WAL archiving** to S3/GCS
- **Daily full backups** to separate region
- **Retention policy:** 30 daily, 12 weekly, 5 yearly

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h postgres-primary -U admin trend_intelligence | gzip > /backups/trend_$DATE.sql.gz
aws s3 cp /backups/trend_$DATE.sql.gz s3://backups-us-west/postgres/
```

**Qdrant:**

- **Daily snapshots** via API
- **Export to object storage**
- **Retention:** 7 daily snapshots

```python
from qdrant_client import QdrantClient

client = QdrantClient(host="qdrant-cluster")

# Create snapshot
snapshot = client.create_snapshot(collection_name="topics")

# Upload to S3
upload_to_s3(snapshot.name, "s3://backups-us-west/qdrant/")
```

**RabbitMQ:**

- **Message persistence enabled** (all messages written to disk)
- **Mirrored queues** across 3 nodes

#### Failover Plan

**Scenario: Primary PostgreSQL node failure**

1. **Automatic detection** (30 seconds via Patroni health checks)
2. **Promote replica to primary** (automated via Patroni)
3. **Update DNS/service discovery** (automated)
4. **Verify writes working** (smoke test)
5. **Restore failed primary as new replica** (manual)

**Recovery Time Objective (RTO):** 5 minutes
**Recovery Point Objective (RPO):** 0 (synchronous replication)

---

## Summary

This scaling roadmap provides a comprehensive path from local development to global-scale deployment:

- **Phase 0-2:** Focus on vertical scaling and optimization (weeks to months)
- **Phase 3:** Transition to distributed architecture (2-3 week migration)
- **Phase 4:** Multi-region expansion (advanced topic)

**Key Takeaways:**

1. **Start simple:** Docker Compose is sufficient for <10k items/day
2. **Scale vertically first:** Easier than distributed systems, good up to 50k items/day
3. **Self-host expensive services:** 90% cost savings on LLM and embeddings at scale
4. **Monitor relentlessly:** Metrics drive scaling decisions
5. **Plan for failure:** High availability requires redundancy

**Cost Optimization Summary:**

- Phase 1: $200/month
- Phase 2: $800/month
- Phase 3 (unoptimized): $3,400/month
- Phase 3 (optimized): $1,800/month + $26k LLM savings

**Next Steps:**

- Review [Tech Stack](./architecture-techstack.md) for specific technology choices
- Implement monitoring before you need to scale
- Test migration procedures in staging environment
- Plan capacity 6 months ahead of actual need

---

*Last Updated: 2026-02-10*
