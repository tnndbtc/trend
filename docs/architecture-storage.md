# AI Trend Intelligence Platform - Storage Design

## Overview

The storage layer implements a **multi-tier architecture** optimized for different data types and access patterns:

- **Hot data** (last 7 days): Fast access, frequently queried
- **Warm data** (7-30 days): Moderate access, historical analysis
- **Cold data** (30-365 days): Archival, rarely queried
- **Frozen data** (>365 days): Compressed backups, compliance

---

## Storage Components

```
┌──────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                         │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Hot Tier (7 days)                              │    │
│  │  - Redis (cache)                                │    │
│  │  - PostgreSQL (metadata, indexed)               │    │
│  │  - Qdrant (embeddings, HNSW index)              │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Warm Tier (7-30 days)                          │    │
│  │  - PostgreSQL (metadata, less indexed)          │    │
│  │  - MinIO (full content, JSON)                   │    │
│  │  - InfluxDB/Timescale (time-series metrics)     │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Cold Tier (30-365 days)                        │    │
│  │  - MinIO (compressed JSON)                      │    │
│  │  - PostgreSQL (summary only, no full text)      │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Frozen Tier (>365 days)                        │    │
│  │  - MinIO (archived, compressed tar.gz)          │    │
│  │  - S3-compatible backup (optional)              │    │
│  └─────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

---

## 1. PostgreSQL - Primary Metadata Database

### Schema Design

#### Table: `trends`
```sql
CREATE TABLE trends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    category VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,  -- EMERGING, VIRAL, SUSTAINED, DECLINING
    score FLOAT NOT NULL,
    language VARCHAR(10) NOT NULL,

    -- Summaries
    title_summary VARCHAR(200),
    full_summary TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    first_seen_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Metrics
    item_count INT NOT NULL DEFAULT 0,
    total_engagement BIGINT NOT NULL DEFAULT 0,
    avg_engagement FLOAT NOT NULL DEFAULT 0,

    -- Metadata
    tags TEXT[],  -- Array of tags
    entities JSONB,  -- Named entities (people, places, orgs)

    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Indexes
    INDEX idx_trends_category (category),
    INDEX idx_trends_state (state),
    INDEX idx_trends_created (created_at DESC),
    INDEX idx_trends_score (score DESC),
    INDEX idx_trends_language (language),
    INDEX idx_trends_tags USING GIN (tags),

    -- Full-text search
    FULLTEXT INDEX idx_trends_fts (title, title_summary, full_summary)
);
```

#### Table: `topics`
```sql
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trend_id UUID REFERENCES trends(id) ON DELETE CASCADE,

    -- Content
    title VARCHAR(1000) NOT NULL,
    description TEXT,
    url TEXT NOT NULL UNIQUE,
    full_content_key VARCHAR(500),  -- MinIO object key

    -- Source
    source VARCHAR(100) NOT NULL,
    source_id VARCHAR(500) NOT NULL,  -- ID from source (e.g., YouTube video ID)
    author VARCHAR(500),

    -- Timestamps
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    collected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Metrics
    engagement_score FLOAT NOT NULL DEFAULT 0,
    views BIGINT,
    likes BIGINT,
    comments BIGINT,
    shares BIGINT,

    -- Classification
    language VARCHAR(10) NOT NULL,
    language_confidence FLOAT,
    sentiment VARCHAR(20),  -- positive, neutral, negative
    tags TEXT[],

    -- Processing flags
    content_fetched BOOLEAN DEFAULT FALSE,
    summarized BOOLEAN DEFAULT FALSE,
    translated BOOLEAN DEFAULT FALSE,

    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Indexes
    INDEX idx_topics_trend (trend_id),
    INDEX idx_topics_source (source),
    INDEX idx_topics_published (published_at DESC),
    INDEX idx_topics_engagement (engagement_score DESC),
    INDEX idx_topics_url_hash (MD5(url)),

    UNIQUE INDEX idx_topics_source_id (source, source_id)
);
```

#### Table: `collection_runs`
```sql
CREATE TABLE collection_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Status
    status VARCHAR(50) NOT NULL,  -- running, completed, failed
    error_message TEXT,

    -- Metrics
    items_collected INT DEFAULT 0,
    items_processed INT DEFAULT 0,
    trends_created INT DEFAULT 0,
    topics_created INT DEFAULT 0,
    duration_seconds FLOAT,

    -- Configuration
    sources TEXT[],  -- Which sources were collected
    config JSONB,  -- Collection configuration

    INDEX idx_runs_started (started_at DESC),
    INDEX idx_runs_status (status)
);
```

#### Table: `users` & `api_keys`
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    INDEX idx_users_email (email)
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),

    -- Rate limiting
    rate_limit_per_hour INT DEFAULT 1000,
    requests_today INT DEFAULT 0,
    last_reset_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Validity
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,

    INDEX idx_api_keys_user (user_id),
    INDEX idx_api_keys_hash (key_hash)
);
```

### Partitioning Strategy

**Partition `topics` by month** (reduce query time for recent data):

```sql
CREATE TABLE topics (
    -- ... columns ...
) PARTITION BY RANGE (published_at);

CREATE TABLE topics_2024_01 PARTITION OF topics
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE topics_2024_02 PARTITION OF topics
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Auto-create partitions via cron or pg_partman extension
```

### Indexing Strategy

**Compound indexes for common queries:**

```sql
-- Most common: filter by category + sort by score
CREATE INDEX idx_trends_category_score ON trends (category, score DESC);

-- Time-range queries
CREATE INDEX idx_topics_published_engagement ON topics (published_at DESC, engagement_score DESC);

-- Source-specific queries
CREATE INDEX idx_topics_source_published ON topics (source, published_at DESC);
```

---

## 2. Qdrant - Vector Database for Embeddings

### Collection Schema

**Collection: `topics`**
```python
from qdrant_client.models import Distance, VectorParams

client.create_collection(
    collection_name="topics",
    vectors_config=VectorParams(
        size=1536,  # text-embedding-3-small dimension
        distance=Distance.COSINE
    ),
    optimizers_config=OptimizersConfig(
        indexing_threshold=20000,  # Start indexing after 20k vectors
        default_segment_number=2
    ),
    hnsw_config=HnswConfig(
        m=16,  # Number of edges per node
        ef_construct=100,  # Construction time accuracy
        full_scan_threshold=10000  # Use brute force below this size
    )
)
```

**Payload Structure:**
```python
{
    "id": "uuid",
    "trend_id": "uuid",
    "title": "Article title",
    "source": "youtube",
    "published_at": "2024-01-15T10:30:00Z",
    "engagement_score": 15000.0,
    "category": "Technology",
    "language": "en",
    "tags": ["AI", "OpenAI", "GPT"]
}
```

**Collection: `trends`**
```python
client.create_collection(
    collection_name="trends",
    vectors_config=VectorParams(
        size=1536,
        distance=Distance.COSINE
    )
)
```

**Payload:**
```python
{
    "id": "uuid",
    "title": "Trend title",
    "category": "Technology",
    "state": "VIRAL",
    "score": 100000.0,
    "item_count": 150
}
```

### Search Patterns

**Similarity search with filters:**
```python
results = client.search(
    collection_name="topics",
    query_vector=embedding,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="category",
                match=MatchValue(value="Technology")
            ),
            FieldCondition(
                key="published_at",
                range=DatetimeRange(
                    gte="2024-01-01T00:00:00Z",
                    lte="2024-01-31T23:59:59Z"
                )
            )
        ]
    ),
    limit=10
)
```

### Sharding & Replication

**For clusters:**
```python
client.create_collection(
    collection_name="topics",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    shard_number=4,  # Split across 4 shards
    replication_factor=2  # 2 replicas per shard
)
```

---

## 3. Redis - Multi-Purpose Cache

### Cache Types

#### 3.1 Embedding Cache
**Purpose:** Avoid re-computing embeddings for duplicate content

```python
# Key: embedding:{content_hash}
# Value: embedding vector (serialized)
# TTL: 7 days

key = f"embedding:{hashlib.sha256(text.encode()).hexdigest()}"
redis.setex(key, 604800, pickle.dumps(embedding))
```

#### 3.2 Translation Cache
**Purpose:** Cache expensive translations

```python
# Key: translation:{source_lang}:{target_lang}:{text_hash}
# Value: translated text
# TTL: 30 days

key = f"translation:{source_lang}:{target_lang}:{hashlib.sha256(text.encode()).hexdigest()}"
redis.setex(key, 2592000, translated_text)
```

#### 3.3 API Response Cache
**Purpose:** Cache common API queries

```python
# Key: api:trends:{query_params_hash}
# Value: JSON response
# TTL: 5 minutes (short for real-time data)

key = f"api:trends:{hashlib.sha256(json.dumps(query_params).encode()).hexdigest()}"
redis.setex(key, 300, json.dumps(response))
```

#### 3.4 Hot Trends Cache
**Purpose:** Pre-compute trending topics

```python
# Key: hot_trends:{category}
# Value: List of trend IDs
# TTL: 10 minutes

key = f"hot_trends:{category}"
redis.setex(key, 600, json.dumps([t.id for t in top_trends]))
```

#### 3.5 Rate Limiting
**Purpose:** Track API usage

```python
# Key: ratelimit:{api_key}:{hour}
# Value: request count
# TTL: 1 hour

key = f"ratelimit:{api_key}:{datetime.utcnow().strftime('%Y%m%d%H')}"
redis.incr(key)
redis.expire(key, 3600)

if redis.get(key) > rate_limit:
    raise RateLimitExceeded()
```

### Redis Configuration

```yaml
# redis.conf
maxmemory 4gb
maxmemory-policy allkeys-lru  # Evict least recently used keys
save 900 1  # Snapshot every 15 minutes if 1+ keys changed
save 300 10
save 60 10000
appendonly yes  # AOF for durability
appendfsync everysec
```

---

## 4. MinIO - Object Storage for Content

### Bucket Structure

**Bucket: `trend-content`**
- **Purpose:** Store full article content, raw HTML
- **Key pattern:** `{date}/{trend_id}/{topic_id}.json`
- **Lifecycle:** Delete after 90 days

**Bucket: `trend-media`**
- **Purpose:** Store images, videos, thumbnails
- **Key pattern:** `{date}/{topic_id}/{filename}`
- **Lifecycle:** Delete after 30 days

**Bucket: `trend-backups`**
- **Purpose:** Compressed database backups
- **Key pattern:** `backups/{YYYY-MM-DD}/{database}_{timestamp}.tar.gz`
- **Lifecycle:** Keep 30 daily, 12 monthly, 7 yearly

### Object Format

**Content Object:**
```json
{
    "topic_id": "uuid",
    "url": "https://...",
    "fetched_at": "2024-01-15T10:30:00Z",
    "content_type": "text/html",
    "raw_html": "<!DOCTYPE html>...",
    "extracted_text": "Article content...",
    "metadata": {
        "author": "John Doe",
        "publish_date": "2024-01-14",
        "word_count": 1500
    }
}
```

### Lifecycle Policies

```xml
<LifecycleConfiguration>
    <Rule>
        <ID>expire-old-content</ID>
        <Status>Enabled</Status>
        <Prefix>content/</Prefix>
        <Expiration>
            <Days>90</Days>
        </Expiration>
    </Rule>
    <Rule>
        <ID>transition-warm-tier</ID>
        <Status>Enabled</Status>
        <Prefix>content/</Prefix>
        <Transition>
            <Days>30</Days>
            <StorageClass>STANDARD_IA</StorageClass>
        </Transition>
    </Rule>
</LifecycleConfiguration>
```

---

## 5. InfluxDB / TimescaleDB - Time-Series Metrics

### Schema (InfluxDB)

**Measurement: `trend_metrics`**
```
trend_metrics,trend_id=uuid123,category=Technology item_count=150,total_engagement=100000,avg_engagement=666.67 1642248000000000000
```

**Fields:**
- `item_count`: Number of topics in trend (int)
- `total_engagement`: Sum of all engagement scores (int)
- `avg_engagement`: Average engagement per topic (float)
- `new_items_1h`: Items added in last hour (int)
- `growth_rate`: Percentage growth (float)

**Tags:**
- `trend_id`: Trend UUID
- `category`: Category name
- `state`: EMERGING, VIRAL, etc.

### Queries

**Growth rate over time:**
```flux
from(bucket: "trends")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "trend_metrics" and r.trend_id == "uuid123")
  |> derivative(unit: 1h, nonNegative: true, columns: ["item_count"])
```

**Top growing trends:**
```flux
from(bucket: "trends")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "trend_metrics")
  |> aggregateWindow(every: 1h, fn: last)
  |> difference(nonNegative: true, columns: ["item_count"])
  |> top(n: 10, columns: ["item_count"])
```

---

## 6. RabbitMQ / Kafka - Message Queue

### Queue Structure

**Exchange:** `trend-intelligence` (topic exchange)

**Queues:**
1. `ingestion.raw_items` - Raw items from collectors
2. `processing.normalized` - Normalized items
3. `processing.clustered` - Clustered items
4. `intelligence.summaries` - Items ready for summarization
5. `storage.persist` - Items ready to save
6. `notifications.new_trends` - New trends detected
7. `dlq.failed_items` - Dead letter queue for failures

**Routing Keys:**
- `ingestion.youtube` - Items from YouTube
- `ingestion.twitter` - Items from Twitter
- `processing.deduplicate` - Items for deduplication
- `intelligence.summarize` - Items for summarization
- `storage.save` - Items to persist

### Message Format

```json
{
    "message_id": "uuid",
    "timestamp": "2024-01-15T10:30:00Z",
    "routing_key": "ingestion.youtube",
    "payload": {
        "id": "youtube:abc123",
        "title": "Video title",
        ...
    },
    "metadata": {
        "source": "youtube",
        "collection_run_id": "uuid",
        "retry_count": 0
    }
}
```

### Dead Letter Queue (DLQ)

**Purpose:** Capture failed messages for manual inspection

**Configuration:**
```python
channel.queue_declare(
    queue='dlq.failed_items',
    durable=True,
    arguments={
        'x-message-ttl': 604800000,  # 7 days
        'x-max-length': 10000  # Max 10k messages
    }
)
```

---

## Data Retention Policies

### Tier-Based Retention

| Tier | Age | Storage | Access | Actions |
|------|-----|---------|--------|---------|
| Hot | 0-7 days | PostgreSQL (full), Redis, Qdrant | High (100-1000 QPS) | Full indexing, real-time search |
| Warm | 7-30 days | PostgreSQL (metadata), MinIO (content) | Medium (10-100 QPS) | Reduced indexing, batch queries |
| Cold | 30-365 days | MinIO (compressed), PostgreSQL (summary) | Low (1-10 QPS) | Archive search, analytics |
| Frozen | >365 days | MinIO (archived tar.gz) | Rare (backup/restore) | Compliance, legal hold |

### Automated Cleanup Jobs

**Daily Cleanup Job:**
```python
@scheduled_task(cron="0 2 * * *")  # 2 AM daily
async def cleanup_old_data():
    """Move data between tiers based on age"""

    # Hot → Warm (7 days)
    await move_to_warm(age_days=7)

    # Warm → Cold (30 days)
    await move_to_cold(age_days=30)

    # Cold → Frozen (365 days)
    await archive_to_frozen(age_days=365)

    # Delete frozen (>730 days, 2 years)
    await delete_frozen(age_days=730)
```

**Implementation:**
```python
async def move_to_warm(age_days=7):
    """Move old topics to warm tier"""

    cutoff = datetime.utcnow() - timedelta(days=age_days)

    # 1. Move full content to MinIO
    topics = await db.query(
        "SELECT id, full_content FROM topics WHERE published_at < $1 AND full_content_key IS NULL",
        cutoff
    )

    for topic in topics:
        # Save to MinIO
        key = f"content/{topic.published_at.strftime('%Y-%m')}/{topic.id}.json"
        await minio.put_object("trend-content", key, json.dumps(topic.full_content))

        # Update PostgreSQL (remove full_content, store key)
        await db.execute(
            "UPDATE topics SET full_content = NULL, full_content_key = $1 WHERE id = $2",
            key, topic.id
        )

    # 2. Remove from Redis cache
    await redis.delete_pattern(f"topic:*")

    # 3. Drop detailed indexes
    await db.execute("DROP INDEX IF EXISTS idx_topics_fulltext_hot")
```

---

## Backup & Disaster Recovery

### Backup Strategy

**PostgreSQL:**
- **Continuous archiving:** WAL archiving to MinIO
- **Daily snapshots:** `pg_dump` at 3 AM, compress, upload to MinIO
- **Retention:** 30 daily, 12 monthly, 7 yearly

```bash
#!/bin/bash
# Daily backup script

BACKUP_DATE=$(date +%Y-%m-%d)
BACKUP_FILE="postgres_${BACKUP_DATE}.sql.gz"

pg_dump -h localhost -U postgres trend_intelligence | gzip > /tmp/${BACKUP_FILE}

# Upload to MinIO
mc cp /tmp/${BACKUP_FILE} minio/trend-backups/postgres/${BACKUP_FILE}

# Cleanup local file
rm /tmp/${BACKUP_FILE}
```

**Qdrant:**
- **Snapshots:** API-triggered snapshots daily
- **Export:** Export collections to JSON weekly

```python
# Create snapshot
client.create_snapshot(collection_name="topics")

# List snapshots
snapshots = client.list_snapshots(collection_name="topics")

# Download snapshot
client.download_snapshot(collection_name="topics", snapshot_name=snapshots[0].name, output_path="/backups/")
```

**Redis:**
- **RDB snapshots:** Every 15 minutes (if changes)
- **AOF:** Every second (fsync)
- **Backup:** Copy RDB + AOF to MinIO daily

**MinIO:**
- **Replication:** Mirror to secondary MinIO instance (optional)
- **Versioning:** Enable object versioning for `trend-backups` bucket

### Disaster Recovery Plan

**RTO (Recovery Time Objective):** 1 hour
**RPO (Recovery Point Objective):** 5 minutes

**Scenario 1: PostgreSQL Failure**
1. Provision new PostgreSQL instance
2. Restore latest pg_dump backup (< 15 minutes)
3. Replay WAL logs from archive (5 minutes RPO)
4. Update application connection string
5. Restart services

**Scenario 2: Qdrant Data Loss**
1. Restore Qdrant snapshot from MinIO
2. If no recent snapshot, regenerate embeddings from PostgreSQL
3. Rebuild HNSW index (may take hours for large datasets)

**Scenario 3: Complete Data Center Loss**
1. Provision new infrastructure (Kubernetes cluster or VMs)
2. Deploy application from Git
3. Restore databases from MinIO backups
4. Restore MinIO data from replicated bucket (if enabled)
5. Run smoke tests, redirect traffic

---

## Storage Sizing Estimates

### Assumptions
- **Collection rate:** 10,000 items/day
- **Embedding size:** 1536 floats (6 KB per embedding)
- **Full content:** Average 10 KB per item
- **Metadata:** 2 KB per item (PostgreSQL row)

### Storage Growth (per month)

| Component | Size per Item | Items/Month | Monthly Growth | Annual Growth |
|-----------|---------------|-------------|----------------|---------------|
| PostgreSQL (metadata) | 2 KB | 300,000 | 600 MB | 7.2 GB |
| Qdrant (embeddings) | 6 KB | 300,000 | 1.8 GB | 21.6 GB |
| MinIO (content) | 10 KB | 300,000 | 3 GB | 36 GB |
| InfluxDB (metrics) | 100 B | 300,000 × 24 | 720 MB | 8.6 GB |
| Redis (cache) | - | - | ~1 GB (fixed) | ~1 GB |

**Total Annual Growth:** ~75 GB

### Cluster Sizing (for 1M active trends)

**PostgreSQL:**
- Disk: 100 GB (50 GB data + 50 GB indexes)
- RAM: 16 GB (shared_buffers=4GB, OS cache=12GB)
- CPU: 4 cores

**Qdrant:**
- Disk: 50 GB (embeddings + HNSW index)
- RAM: 32 GB (keep index in memory)
- CPU: 8 cores (indexing is CPU-intensive)

**Redis:**
- Disk: 10 GB (RDB + AOF)
- RAM: 8 GB (cache size)
- CPU: 2 cores

**MinIO:**
- Disk: 500 GB (content + backups)
- RAM: 4 GB
- CPU: 2 cores

**Total:** 660 GB disk, 60 GB RAM, 16 CPU cores

---

## Next Steps

- [Translation Pipeline](./architecture-translation.md) - Multi-language processing
- [AI Agent Integration](./architecture-ai-agents.md) - Agent consumption patterns
- [Scaling Roadmap](./architecture-scaling.md) - Horizontal scaling strategy
- [Tech Stack](./architecture-techstack.md) - Specific technology choices
