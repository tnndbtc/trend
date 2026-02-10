# AI Trend Intelligence Platform - Module Breakdown

## Overview

This document provides detailed specifications for each architectural layer of the AI Trend Intelligence Platform.

Each layer is designed as a **replaceable module** with well-defined interfaces, enabling:
- Independent scaling
- Technology swaps without system-wide changes
- Parallel development by different teams
- Isolated testing and deployment

---

## 1. INGESTION LAYER

### Purpose
Collect raw trending data from diverse sources (YouTube, Twitter, Reddit, News, RSS, Google Trends, etc.) using a pluggable architecture.

### Design Pattern: Plugin Registry + Abstract Factory

```
┌─────────────────────────────────────────────────────────┐
│              Ingestion Orchestrator                     │
│  - Plugin discovery and registration                    │
│  - Scheduler integration (which plugins, when)          │
│  - Rate limiting and quota management                   │
│  - Error handling and retry logic                       │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│              Plugin Registry                            │
│  - Loaded plugins: {name → instance}                    │
│  - Plugin metadata: {name → config, enabled, priority}  │
│  - Health checks: monitor plugin status                 │
└────────────┬────────────────────────────────────────────┘
             │
             ├─────────────────┬─────────────────┬──────────────────┐
             ▼                 ▼                 ▼                  ▼
       ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
       │ YouTube  │      │ Twitter  │      │  Reddit  │      │  News    │
       │ Plugin   │      │ Plugin   │      │  Plugin  │      │  RSS     │
       └──────────┘      └──────────┘      └──────────┘      └──────────┘
```

### Core Interface: `CollectorPlugin`

```python
class CollectorPlugin(ABC):
    """Base interface for all data source collectors"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this collector"""
        pass

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Plugin configuration and capabilities"""
        pass

    @abstractmethod
    async def collect(self, config: CollectionConfig) -> AsyncIterator[RawItem]:
        """
        Collect items from this source.

        Yields:
            RawItem: Normalized data structure containing:
                - id: unique identifier (source-specific)
                - title: headline/title
                - description: snippet/preview
                - url: source URL
                - timestamp: when item was created
                - source: collector name
                - metadata: source-specific fields (views, likes, etc.)
                - raw_data: original API response (for debugging)
        """
        pass

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check if this collector is functional"""
        pass
```

### Plugin Specifications

#### 1.1 YouTube Plugin

**Data Source:** YouTube Data API v3 + fallback scraping
**Quota:** 10,000 units/day (API), unlimited (scraping)
**Collection Strategy:**
- Trending videos (regionCode=US, chart=mostPopular)
- Search results for tracked keywords
- Channel uploads for monitored creators

**Configuration:**
```yaml
youtube:
  enabled: true
  api_key: ${YOUTUBE_API_KEY}
  fallback_to_scraping: true
  max_results_per_query: 50
  regions: [US, GB, IN, JP]
  categories: [Technology, Science, News]
  collection_frequency: "0 */6 * * *"  # Every 6 hours
```

**Output Fields:**
- title, description, channel_name, view_count, like_count, comment_count
- published_at, video_id, thumbnail_url, duration, tags

#### 1.2 Twitter/X Plugin

**Data Source:** Twitter API v2 (requires elevated access)
**Quota:** Varies by tier (Essential: 500K tweets/month, Basic: 10M/month)
**Collection Strategy:**
- Trending topics (GET /2/trends/place)
- Search recent tweets (GET /2/tweets/search/recent)
- Stream filtered tweets (GET /2/tweets/search/stream)

**Configuration:**
```yaml
twitter:
  enabled: true
  api_key: ${TWITTER_API_KEY}
  api_secret: ${TWITTER_API_SECRET}
  bearer_token: ${TWITTER_BEARER_TOKEN}
  mode: search  # or 'stream'
  keywords: ["AI", "technology", "breaking news"]
  min_retweets: 10
  collection_frequency: "*/15 * * * *"  # Every 15 minutes
```

**Output Fields:**
- text, author_username, retweet_count, like_count, reply_count
- created_at, tweet_id, entities (hashtags, mentions, urls)

#### 1.3 Reddit Plugin

**Data Source:** Reddit API (OAuth2)
**Quota:** 60 requests/minute
**Collection Strategy:**
- Subreddit hot/top posts (r/all, r/popular, r/worldnews, etc.)
- Cross-post detection and merging
- Comment sentiment analysis (optional)

**Configuration:**
```yaml
reddit:
  enabled: true
  client_id: ${REDDIT_CLIENT_ID}
  client_secret: ${REDDIT_CLIENT_SECRET}
  user_agent: "TrendIntelligence/1.0"
  subreddits: [all, popular, worldnews, technology, science]
  time_filter: day  # hour, day, week, month, year, all
  limit: 100
  collection_frequency: "0 */3 * * *"  # Every 3 hours
```

**Output Fields:**
- title, selftext, author, score, num_comments, upvote_ratio
- created_utc, permalink, subreddit, url, is_self

#### 1.4 Google Trends Plugin

**Data Source:** Google Trends (unofficial API via pytrends)
**Quota:** No official limit (use rate limiting)
**Collection Strategy:**
- Real-time trending searches (trending_searches)
- Interest over time for tracked keywords
- Related queries and topics

**Configuration:**
```yaml
google_trends:
  enabled: true
  regions: [US, GB, IN, JP, worldwide]
  timeframe: "now 1-d"  # Last 24 hours
  categories: [0]  # 0 = all categories
  collection_frequency: "0 */2 * * *"  # Every 2 hours
```

**Output Fields:**
- query, related_queries, traffic (number representation of search interest)
- region, timestamp, category

#### 1.5 News RSS Plugin

**Data Source:** RSS feeds from major news outlets
**Quota:** Unlimited (public feeds)
**Collection Strategy:**
- Poll RSS feeds from configured sources
- Detect duplicates via URL/title hashing
- Extract article content via web scraping (trafilatura)

**Configuration:**
```yaml
news_rss:
  enabled: true
  feeds:
    - url: https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml
      name: New York Times
      category: News
    - url: https://feeds.bbci.co.uk/news/rss.xml
      name: BBC News
      category: World News
    # ... more feeds
  fetch_full_content: true
  max_age_hours: 24
  collection_frequency: "0 * * * *"  # Hourly
```

**Output Fields:**
- title, summary, link, published, author, source_name
- full_content (if scraped), categories

#### 1.6 Generic RSS Plugin

**Purpose:** Allow users to add custom RSS feeds
**Dynamic configuration:** Load feeds from database, not just static config

### Plugin Manager

**Responsibilities:**
1. **Discovery:** Auto-load plugins from `plugins/` directory
2. **Registration:** Validate and register plugins in registry
3. **Scheduling:** Coordinate collection frequency (some hourly, some daily)
4. **Quota Management:** Track API usage, pause when limits approached
5. **Error Handling:** Retry failed collections with exponential backoff
6. **Health Monitoring:** Periodic health checks, disable failing plugins

**State Management:**
- Store last collection timestamp per plugin
- Track success/failure rates
- Log quota consumption

---

## 2. PROCESSING LAYER

### Purpose
Transform raw collected items into clean, normalized, deduplicated, and clustered data ready for intelligence analysis.

### Pipeline Stages

```
Raw Items → Normalize → Language Detect → Deduplicate → Cluster → Rank → Processed Items
```

### 2.1 Normalization Module

**Input:** `RawItem` (heterogeneous structure from different sources)
**Output:** `NormalizedItem` (unified schema)

**Operations:**
- **Text cleaning:** Remove HTML tags, URLs (optionally preserve in metadata), emoji standardization
- **Entity extraction:** Extract URLs, mentions, hashtags
- **Timestamp normalization:** Convert all to UTC ISO-8601
- **Metric normalization:** Map source-specific metrics (likes, retweets) to unified engagement score

**Example Mapping:**
```python
# YouTube video
RawItem(view_count=10000, like_count=500, comment_count=50)
→ NormalizedItem(engagement_score=10000 + 500*10 + 50*5 = 15250)

# Reddit post
RawItem(score=1000, num_comments=200)
→ NormalizedItem(engagement_score=1000 + 200*5 = 2000)
```

### 2.2 Language Detection Module

**Library:** `fasttext` (faster and more accurate than langdetect)
**Model:** `lid.176.bin` (supports 176 languages)

**Operations:**
- Detect language from title + description
- Confidence threshold: 0.7 (below this, mark as "unknown")
- Store: `language_code` (ISO 639-1), `language_confidence`

**Optimization:** Batch detection (1000 items at once)

### 2.3 Deduplication Module

**Strategy:** Multi-level deduplication

#### Level 1: Exact Duplicate (URL-based)
- Hash: SHA-256 of normalized URL
- Collision handling: Keep item with highest engagement score

#### Level 2: Near-Duplicate (Embedding-based)
- Algorithm: Cosine similarity on embeddings
- Threshold: 0.92 (92% similarity = duplicate)
- Keep: Item with highest engagement or earliest timestamp

#### Level 3: Cross-Source Deduplication
- Same story from multiple sources (e.g., Reuters article shared on Reddit)
- Detect: High embedding similarity (0.85+) + overlapping entities
- Strategy: Merge into single item, link sources

**Performance:**
- Use FAISS or Qdrant's built-in ANN search for fast similarity lookup
- Batch processing: Compute embeddings in batches of 100-500

### 2.4 Clustering Module

**Redesign:** Move from fixed-K to **hierarchical dynamic clustering**

#### Stage 1: Topic Clustering (Micro-Trends)
**Algorithm:** HDBSCAN (density-based, finds clusters of arbitrary shape)
**Parameters:**
- `min_cluster_size=5` (minimum 5 items per cluster)
- `metric='cosine'` (on embeddings)
- Outliers: Items that don't fit any cluster (noise points)

**Output:** 50-200 micro-clusters (topics like "OpenAI GPT-5 release", "SpaceX Starship launch")

#### Stage 2: Trend Clustering (Macro-Trends)
**Algorithm:** Agglomerative Clustering
**Parameters:**
- `n_clusters=dynamic` (use elbow method or silhouette score)
- `linkage='average'`
- Merge micro-clusters based on embedding similarity

**Output:** 10-30 macro-clusters (trends like "AI advancements", "Space exploration")

#### Stage 3: Category Assignment
**Algorithm:** Supervised classification or keyword matching
**Categories:** Technology, Politics, Entertainment, Sports, Science, Business, World News, Health, etc.

**Dynamic:** Categories can be user-defined and extended

### 2.5 Ranking Module

**Multi-Factor Scoring:**

```python
def calculate_trend_score(item: NormalizedItem) -> float:
    """
    Composite score based on:
    1. Engagement (40%): likes, comments, shares
    2. Recency (30%): time decay (newer = higher score)
    3. Velocity (20%): engagement growth rate (if available)
    4. Source authority (10%): trusted sources weighted higher
    """

    engagement_score = (
        item.likes * 1.0 +
        item.comments * 5.0 +  # Comments weighted higher (more engagement)
        item.shares * 10.0  # Shares weighted highest (viral potential)
    )

    recency_score = exp(-hours_since_published / 24.0)  # Decay over 24 hours

    velocity_score = engagement_score / max(hours_since_published, 1)

    source_weight = SOURCE_AUTHORITY.get(item.source, 1.0)

    return (
        engagement_score * 0.4 +
        recency_score * 100 * 0.3 +
        velocity_score * 0.2 +
        source_weight * 0.1
    )
```

**Source Diversity Filter:**
- Limit each source to X% of items per cluster (configurable, default 40%)
- Round-robin selection when multiple sources have high-scoring items
- Prevents source monopolization (e.g., all items from Reddit)

---

## 3. INTELLIGENCE LAYER

### Purpose
Apply AI/ML models to extract insights, generate summaries, translate content, and enable semantic search.

### 3.1 Embedding Service

**Provider:** Pluggable (OpenAI, Cohere, Local)
**Models:**
- OpenAI: `text-embedding-3-small` (1536 dims, $0.02/1M tokens)
- OpenAI: `text-embedding-3-large` (3072 dims, $0.13/1M tokens)
- Local: `all-MiniLM-L6-v2` (384 dims, free, faster)

**Interface:**
```python
class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts"""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimension (e.g., 1536)"""
        pass
```

**Optimization:**
- Batch size: 100-500 texts per API call
- Caching: Cache embeddings by content hash (avoid re-computing)
- Compression: Use dimensionality reduction (PCA) for storage (optional)

### 3.2 LLM Service

**Provider:** Pluggable (OpenAI, Anthropic Claude, Local LLaMA)
**Use Cases:**
1. **Summarization:** Generate concise summaries (15 words, 50 words, 200 words)
2. **Tagging:** Extract keywords, entities, sentiment
3. **Translation:** Translate to canonical language (English) or user language
4. **Trend Analysis:** Identify why this is trending, key narratives

**Interface:**
```python
class LLMProvider(ABC):
    @abstractmethod
    async def summarize(self, text: str, max_words: int) -> str:
        """Summarize text to max_words"""
        pass

    @abstractmethod
    async def translate(self, text: str, target_lang: str) -> str:
        """Translate text to target language"""
        pass

    @abstractmethod
    async def extract_tags(self, text: str) -> List[str]:
        """Extract relevant keywords/tags"""
        pass
```

**Prompt Engineering:**
- **Summarization prompt:** "Summarize the following article in exactly {max_words} words, preserving key facts and neutrality: {text}"
- **Translation prompt:** "Translate the following text to {target_lang}, preserving meaning and tone: {text}"
- **Tagging prompt:** "Extract 5-10 relevant keywords or tags from this text: {text}"

**Batching:**
- Batch multiple summarization requests in single API call
- Current: 15 items per call → Increase to 50 items with better prompting

### 3.3 Trend Detection Engine

**Purpose:** Identify emerging, growing, and declining trends

**Metrics:**
1. **Emergence:** New clusters appearing in recent data (not in historical clusters)
2. **Growth:** Cluster size increasing over time (compare hourly/daily snapshots)
3. **Virality:** Rapid engagement growth (exponential curve fitting)
4. **Persistence:** Trend lasting multiple collection cycles (not a flash in the pan)

**Algorithm:**
```python
def detect_trend_state(cluster_history: List[ClusterSnapshot]) -> TrendState:
    """
    Analyze cluster over time to determine trend state.

    States:
    - EMERGING: New cluster, growing rapidly
    - VIRAL: Exponential growth in engagement
    - SUSTAINED: Steady growth over multiple days
    - DECLINING: Decreasing engagement/size
    - DEAD: No new items, low engagement
    """

    if len(cluster_history) == 1:
        return TrendState.EMERGING

    sizes = [c.item_count for c in cluster_history]
    engagement = [c.total_engagement for c in cluster_history]

    # Fit growth curve
    growth_rate = np.polyfit(range(len(sizes)), sizes, deg=1)[0]

    if growth_rate > 10:  # Growing by 10+ items per cycle
        return TrendState.VIRAL
    elif growth_rate > 0:
        return TrendState.SUSTAINED
    elif growth_rate < -5:
        return TrendState.DECLINING
    else:
        return TrendState.DEAD
```

**Temporal Storage:**
- Store cluster snapshots every collection cycle
- Time-series DB (InfluxDB or Timescale) for fast queries
- Metrics: cluster_id, timestamp, item_count, total_engagement, avg_engagement

### 3.4 Semantic Search Engine

**Purpose:** Enable similarity-based search ("find trends similar to X")

**Implementation:**
- Vector DB: Qdrant or Milvus
- Query: User provides text → embed → search top-K similar trends
- Filters: Date range, category, source, language
- Hybrid search: Combine vector similarity + keyword matching

**API:**
```python
async def search_trends(
    query: str,
    limit: int = 10,
    filters: Optional[SearchFilters] = None
) -> List[Trend]:
    """
    Search for trends similar to query.

    Args:
        query: Search text
        limit: Max results
        filters: Optional filters (date range, category, etc.)

    Returns:
        List of trends sorted by relevance
    """
    query_embedding = await embedding_service.embed(query)
    results = await vector_db.search(
        embedding=query_embedding,
        limit=limit,
        filters=filters
    )
    return results
```

---

## 4. STORAGE LAYER

See [architecture-storage.md](./architecture-storage.md) for full details.

**Summary:**
- **PostgreSQL:** Metadata, relationships, user data
- **Qdrant/Milvus:** Embeddings, vector search
- **Redis:** Cache (hot trends, API responses, translations)
- **MinIO/Local FS:** Raw content, media files, backups
- **InfluxDB/Timescale:** Time-series metrics (trend growth, engagement)
- **RabbitMQ/Kafka:** Message queue for async processing

---

## 5. API LAYER

### Purpose
Expose platform capabilities via REST, GraphQL, and WebSocket APIs for dashboards, AI agents, and third-party integrations.

### 5.1 REST API (FastAPI)

**Endpoints:**

```
# Trends
GET    /api/v1/trends                    # List trends (paginated, filterable)
GET    /api/v1/trends/{id}               # Get trend details
GET    /api/v1/trends/{id}/topics        # Get topics in trend
GET    /api/v1/trends/search             # Search trends (query param)

# Topics
GET    /api/v1/topics                    # List topics
GET    /api/v1/topics/{id}               # Get topic details

# Collections
GET    /api/v1/collections               # List collection runs
GET    /api/v1/collections/{id}          # Get collection run details

# Search
POST   /api/v1/search                    # Semantic search (body: query, filters)
GET    /api/v1/search/similar/{id}       # Find similar trends

# Analytics
GET    /api/v1/analytics/trending        # Currently trending topics
GET    /api/v1/analytics/emerging        # Emerging trends
GET    /api/v1/analytics/timeline        # Trend timeline (growth over time)

# Admin
POST   /api/v1/admin/collect             # Trigger collection (auth required)
DELETE /api/v1/admin/trends/{id}         # Delete trend (auth required)
```

**Authentication:**
- API keys (for programmatic access)
- OAuth2 (for user authentication)
- Rate limiting: 1000 req/hour (free), 10000 req/hour (paid)

**Response Format:**
```json
{
  "data": { ... },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  },
  "links": {
    "self": "/api/v1/trends?page=1",
    "next": "/api/v1/trends?page=2",
    "prev": null
  }
}
```

### 5.2 GraphQL API (Strawberry)

**Schema:**
```graphql
type Trend {
  id: ID!
  title: String!
  summary: String!
  category: Category!
  score: Float!
  state: TrendState!
  language: String!
  createdAt: DateTime!
  updatedAt: DateTime!
  topics: [Topic!]!
  metrics: TrendMetrics!
}

type Topic {
  id: ID!
  title: String!
  description: String
  url: String!
  source: String!
  timestamp: DateTime!
  engagement: EngagementMetrics!
  cluster: Trend
}

type Query {
  trends(
    limit: Int = 10
    offset: Int = 0
    category: Category
    state: TrendState
    language: String
    dateRange: DateRange
  ): [Trend!]!

  trend(id: ID!): Trend

  searchTrends(query: String!, limit: Int = 10): [Trend!]!

  similarTrends(id: ID!, limit: Int = 10): [Trend!]!
}

type Subscription {
  newTrend: Trend!
  trendUpdated(id: ID!): Trend!
}
```

**Use Cases:**
- Complex queries (nested data fetching)
- Real-time subscriptions (via WebSocket)
- Flexible client-driven data fetching (avoid over-fetching)

### 5.3 WebSocket API

**Purpose:** Real-time updates for dashboards

**Events:**
- `new_trend`: New trend detected
- `trend_updated`: Trend metrics updated
- `collection_started`: Collection job started
- `collection_completed`: Collection job completed

**Protocol:**
```json
// Client subscribes
{"type": "subscribe", "channel": "trends", "filters": {"category": "Technology"}}

// Server pushes updates
{"type": "new_trend", "data": {"id": "123", "title": "...", ...}}
```

---

## 6. ORCHESTRATION LAYER

### Purpose
Coordinate collection jobs, processing pipelines, and system-wide workflows.

### 6.1 Scheduler (APScheduler or Airflow)

**Jobs:**
- `collect_youtube`: Every 6 hours
- `collect_twitter`: Every 15 minutes
- `collect_reddit`: Every 3 hours
- `collect_news_rss`: Hourly
- `process_pipeline`: Triggered after each collection
- `cleanup_old_data`: Daily at 2 AM

**Configuration:**
```yaml
jobs:
  - name: collect_youtube
    schedule: "0 */6 * * *"  # Cron expression
    task: ingestion.tasks.collect
    args: {source: youtube}
    retries: 3
    timeout: 1800  # 30 minutes
```

### 6.2 Task Queue (Celery)

**Workers:**
- `ingestion_worker`: Runs collection tasks
- `processing_worker`: Runs processing pipeline
- `llm_worker`: Runs LLM tasks (summarization, translation)

**Queues:**
- `high_priority`: Real-time tasks (WebSocket updates, user-triggered collections)
- `default`: Regular tasks (scheduled collections)
- `low_priority`: Batch tasks (cleanup, analytics)

**Task Example:**
```python
@celery_app.task(bind=True, max_retries=3)
async def collect_from_source(self, source: str, config: dict):
    """
    Collect data from a specific source.

    Retries on failure with exponential backoff.
    """
    try:
        plugin = plugin_registry.get(source)
        items = []
        async for item in plugin.collect(config):
            items.append(item)
        return {"source": source, "count": len(items)}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

### 6.3 Workflow Engine (Optional: Temporal or Prefect)

**For complex multi-step workflows:**
```python
@workflow
async def collection_workflow(source: str):
    """
    Full collection workflow: collect → process → summarize → store → notify
    """
    # Step 1: Collect
    items = await collect_from_source(source)

    # Step 2: Process
    processed = await process_pipeline(items)

    # Step 3: Summarize (parallel)
    summaries = await asyncio.gather(*[
        summarize_item(item) for item in processed
    ])

    # Step 4: Store
    await store_trends(summaries)

    # Step 5: Notify
    await notify_subscribers(summaries)
```

**Benefits:**
- Durability: Workflow state persisted (survives crashes)
- Observability: Track workflow execution in UI
- Replay: Retry failed workflows from checkpoint

### 6.4 Observability (Prometheus + Grafana)

**Metrics:**
- `ingestion_items_collected_total{source}`: Counter
- `processing_duration_seconds{stage}`: Histogram
- `llm_api_calls_total{provider, operation}`: Counter
- `api_requests_total{endpoint, status}`: Counter
- `trend_count{category, state}`: Gauge

**Dashboards:**
- Ingestion: Items collected per source, API quota usage
- Processing: Pipeline throughput, stage durations
- Intelligence: LLM costs, embedding cache hit rate
- API: Request rate, latency, error rate
- System: CPU, memory, disk usage

---

## Module Communication Patterns

### 1. Ingestion → Processing
**Medium:** Message queue (RabbitMQ)
**Pattern:** Pub/Sub
**Flow:** Ingestion publishes `items_collected` event → Processing subscribes and processes

### 2. Processing → Intelligence
**Medium:** Task queue (Celery)
**Pattern:** Task delegation
**Flow:** Processing enqueues `generate_embeddings` task → LLM worker processes

### 3. Intelligence → Storage
**Medium:** Direct call (Repository pattern)
**Pattern:** ACID transaction
**Flow:** Intelligence calls `TrendRepository.save(trend)` → PostgreSQL + Qdrant atomic save

### 4. API → All Layers
**Medium:** Direct call (Service layer)
**Pattern:** Service orchestration
**Flow:** API calls `TrendService.search(query)` → Service coordinates Intelligence + Storage

### 5. Orchestration → All Layers
**Medium:** Task queue (Celery) + HTTP callbacks
**Pattern:** Command dispatch
**Flow:** Scheduler triggers `collect_task` → Task queue routes to worker → Worker executes

---

## Module Isolation & Testing

### Unit Testing
- Each module has isolated unit tests (mock dependencies)
- Example: Test `DeduplicationModule` with fake embeddings, no real LLM

### Integration Testing
- Test module pairs (e.g., Ingestion + Processing)
- Use testcontainers for real databases (PostgreSQL, Redis in Docker)

### End-to-End Testing
- Full pipeline test: Collect (mock source) → Process → Store → API query
- Verify data flows correctly through all layers

### Contract Testing
- Define interface contracts (e.g., `CollectorPlugin` interface)
- Test that all plugins implement contract correctly
- Use Pact or similar for consumer-driven contracts

---

## Module Deployment

### Single-Node Deployment
All modules run as separate processes on one machine:
- `docker-compose.yaml` defines services for each module
- Shared volumes for data persistence
- Internal Docker network for inter-module communication

### Distributed Deployment
Modules deployed as microservices on Kubernetes:
- Each module is a separate deployment
- Load balancers for API layer
- Shared services: PostgreSQL (RDS-like), Redis (ElastiCache-like), but self-hosted
- Message queue cluster (RabbitMQ or Kafka cluster)

---

## Next Steps

- [Data Flow Pipeline](./architecture-dataflow.md) - See how data flows through these modules
- [Storage Design](./architecture-storage.md) - Database schemas and storage strategy
- [Tech Stack](./architecture-techstack.md) - Specific technology choices for each module
