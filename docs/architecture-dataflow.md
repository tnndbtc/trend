# AI Trend Intelligence Platform - Data Flow Pipeline

## Overview

This document describes the complete data flow through the AI Trend Intelligence Platform, from raw data collection to final consumption by dashboards and AI agents.

---

## Complete Pipeline Flow

```
┌─────────────┐
│  EXTERNAL   │
│  SOURCES    │  (YouTube, Twitter, Reddit, News, etc.)
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: COLLECTION                                         │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│ │ YouTube  │  │ Twitter  │  │  Reddit  │  │   News   │    │
│ │  Plugin  │  │  Plugin  │  │  Plugin  │  │  Plugin  │    │
│ └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│      │             │              │             │          │
│      └─────────────┴──────────────┴─────────────┘          │
│                          │                                  │
│                          ▼                                  │
│              ┌──────────────────────┐                       │
│              │  Raw Items Queue     │                       │
│              │  (RabbitMQ)          │                       │
│              └──────────┬───────────┘                       │
└───────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2: NORMALIZATION                                      │
│ ┌────────────────────────────────────────────────┐          │
│ │ - Clean text (HTML, special chars)             │          │
│ │ - Extract entities (URLs, mentions, hashtags)  │          │
│ │ - Normalize timestamps (UTC ISO-8601)          │          │
│ │ - Map source-specific metrics to unified score │          │
│ └──────────────────────┬─────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 3: LANGUAGE DETECTION                                 │
│ ┌────────────────────────────────────────────────┐          │
│ │ - Detect language (fasttext lid.176.bin)       │          │
│ │ - Store language code + confidence             │          │
│ │ - Flag for translation if non-English          │          │
│ └──────────────────────┬─────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 4: EMBEDDING GENERATION                               │
│ ┌────────────────────────────────────────────────┐          │
│ │ - Batch items (100-500 at a time)              │          │
│ │ - Generate embeddings (OpenAI/Cohere/Local)    │          │
│ │ - Cache embeddings by content hash             │          │
│ │ - Store in vector DB (Qdrant)                  │          │
│ └──────────────────────┬─────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 5: DEDUPLICATION                                      │
│ ┌────────────────────────────────────────────────┐          │
│ │ Level 1: Exact URL matching (SHA-256 hash)     │          │
│ │ Level 2: Embedding similarity (threshold 0.92) │          │
│ │ Level 3: Cross-source (merge related items)    │          │
│ │ - Keep highest engagement or earliest          │          │
│ └──────────────────────┬─────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 6: CLUSTERING                                         │
│ ┌────────────────────────────────────────────────┐          │
│ │ Sub-stage 6a: Topic Clustering (HDBSCAN)       │          │
│ │ - Create micro-clusters (50-200)               │          │
│ │ - Identify outliers (noise points)             │          │
│ │                                                 │          │
│ │ Sub-stage 6b: Trend Clustering (Agglomerative) │          │
│ │ - Merge micro-clusters into macro-trends       │          │
│ │ - Dynamic K (elbow method / silhouette)        │          │
│ │ - Result: 10-30 macro-trends                   │          │
│ │                                                 │          │
│ │ Sub-stage 6c: Category Assignment              │          │
│ │ - Map trends to categories (supervised)        │          │
│ │ - Categories: Tech, Politics, Sports, etc.     │          │
│ └──────────────────────┬─────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 7: RANKING                                            │
│ ┌────────────────────────────────────────────────┐          │
│ │ - Calculate composite score per topic          │          │
│ │   (engagement 40% + recency 30% +              │          │
│ │    velocity 20% + source authority 10%)        │          │
│ │ - Rank topics within each trend                │          │
│ │ - Rank trends globally                         │          │
│ │ - Apply source diversity filter                │          │
│ └──────────────────────┬─────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 8: CONTENT ENRICHMENT                                 │
│ ┌────────────────────────────────────────────────┐          │
│ │ - Fetch full article content (trafilatura)     │          │
│ │ - Extract metadata (author, publish date)      │          │
│ │ - Download thumbnails/images (optional)        │          │
│ └──────────────────────┬─────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 9: LLM PROCESSING                                     │
│ ┌────────────────────────────────────────────────┐          │
│ │ Sub-stage 9a: Summarization                    │          │
│ │ - Batch topics (50 at a time)                  │          │
│ │ - Generate title_summary (15 words)            │          │
│ │ - Generate full_summary (50-200 words)         │          │
│ │ - Generate trend summary (per trend)           │          │
│ │                                                 │          │
│ │ Sub-stage 9b: Tagging                          │          │
│ │ - Extract keywords/entities                    │          │
│ │ - Assign sentiment (positive/neutral/negative) │          │
│ │                                                 │          │
│ │ Sub-stage 9c: Translation (on-demand)          │          │
│ │ - Translate non-English content to English     │          │
│ │ - Cache translations in Redis                  │          │
│ └──────────────────────┬─────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 10: TREND DETECTION                                   │
│ ┌────────────────────────────────────────────────┐          │
│ │ - Compare current clusters to historical       │          │
│ │ - Identify EMERGING trends (new clusters)      │          │
│ │ - Identify VIRAL trends (exponential growth)   │          │
│ │ - Identify SUSTAINED trends (steady growth)    │          │
│ │ - Identify DECLINING trends (shrinking)        │          │
│ │ - Store trend state in time-series DB          │          │
│ └──────────────────────┬─────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 11: STORAGE                                           │
│ ┌────────────────────────────────────────────────┐          │
│ │ Atomic transaction:                             │          │
│ │ 1. Save metadata → PostgreSQL                   │          │
│ │ 2. Save embeddings → Qdrant                     │          │
│ │ 3. Save raw content → MinIO/FS                  │          │
│ │ 4. Save metrics → InfluxDB/Timescale            │          │
│ │ 5. Invalidate caches → Redis                    │          │
│ └──────────────────────┬─────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 12: NOTIFICATION                                      │
│ ┌────────────────────────────────────────────────┐          │
│ │ - Publish "new_trends" event (WebSocket)       │          │
│ │ - Send alerts to subscribers (email/webhook)   │          │
│ │ - Update dashboards (real-time push)           │          │
│ └────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │  CONSUMERS    │
                  │ - Dashboards  │
                  │ - AI Agents   │
                  │ - API Clients │
                  └───────────────┘
```

---

## Detailed Stage Specifications

### STAGE 1: COLLECTION

**Input:** External APIs (YouTube, Twitter, Reddit, etc.)
**Output:** `RawItem` objects published to message queue

**Process:**
1. **Scheduler** triggers collection job (e.g., "collect_youtube" at 6 AM)
2. **Task queue** routes job to ingestion worker
3. **Ingestion worker** loads YouTube plugin
4. **YouTube plugin** authenticates with API, fetches trending videos
5. **Plugin** yields `RawItem` objects:
   ```python
   RawItem(
       id="youtube:dQw4w9WgXcQ",
       title="Never Gonna Give You Up",
       description="Official music video...",
       url="https://youtube.com/watch?v=dQw4w9WgXcQ",
       timestamp="2024-01-15T10:30:00Z",
       source="youtube",
       metadata={"view_count": 1000000, "like_count": 50000, ...},
       raw_data={"snippet": {...}, "statistics": {...}}
   )
   ```
6. **Ingestion worker** publishes items to `raw_items` queue (RabbitMQ)
7. **Metrics**: Record `ingestion_items_collected_total{source="youtube"}` = 50

**Error Handling:**
- API errors (rate limit, timeout): Retry with exponential backoff (60s, 120s, 240s)
- Network errors: Retry up to 3 times, then mark job as failed
- Invalid data: Log warning, skip item, continue processing

**Parallelization:**
- Multiple sources collect concurrently (asyncio.gather)
- Each source runs in separate task (isolated failures)

---

### STAGE 2: NORMALIZATION

**Input:** `RawItem` from queue
**Output:** `NormalizedItem`

**Process:**
1. **Worker** consumes `RawItem` from queue
2. **Text cleaning:**
   - Remove HTML tags: `BeautifulSoup(text, "html.parser").get_text()`
   - Remove excessive whitespace: `re.sub(r'\s+', ' ', text).strip()`
   - Decode HTML entities: `html.unescape(text)`
   - Normalize Unicode: `unicodedata.normalize('NFKC', text)`
3. **Entity extraction:**
   - URLs: `re.findall(r'https?://[^\s]+', text)`
   - Mentions: `re.findall(r'@\w+', text)` (Twitter)
   - Hashtags: `re.findall(r'#\w+', text)`
4. **Timestamp normalization:**
   - Parse various formats: `dateutil.parser.parse(timestamp)`
   - Convert to UTC: `dt.astimezone(timezone.utc)`
   - Format: `dt.isoformat()` → "2024-01-15T10:30:00+00:00"
5. **Metric normalization:**
   - Map source-specific metrics to unified engagement score
   - Example:
     ```python
     engagement = (
         metrics.get("view_count", 0) * 1.0 +
         metrics.get("like_count", 0) * 10.0 +
         metrics.get("comment_count", 0) * 5.0
     )
     ```
6. **Output:**
   ```python
   NormalizedItem(
       id="youtube:dQw4w9WgXcQ",
       title="Never Gonna Give You Up",
       description="Official music video for Never Gonna Give You Up...",
       url="https://youtube.com/watch?v=dQw4w9WgXcQ",
       timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
       source="youtube",
       engagement_score=1055000.0,
       entities={"urls": [...], "mentions": [], "hashtags": []},
       language=None,  # To be set in next stage
       embedding=None  # To be set in stage 4
   )
   ```

**Batch Size:** 100 items per batch (amortize overhead)

---

### STAGE 3: LANGUAGE DETECTION

**Input:** `NormalizedItem` (batch of 100)
**Output:** `NormalizedItem` with `language` and `language_confidence` set

**Process:**
1. **Load model:** `fasttext.load_model("lid.176.bin")` (one-time, cached)
2. **Prepare text:** Concatenate title + description
3. **Detect language:**
   ```python
   predictions = model.predict([item.title + " " + item.description for item in batch])
   # predictions = [("__label__en", 0.95), ("__label__es", 0.87), ...]
   ```
4. **Parse results:**
   - Language code: `predictions[0][0].replace("__label__", "")` → "en"
   - Confidence: `predictions[1][0]` → 0.95
5. **Set fields:**
   ```python
   item.language = lang_code if confidence > 0.7 else "unknown"
   item.language_confidence = confidence
   ```
6. **Flag for translation:**
   - If `language != "en"` and `confidence > 0.7`: Set `needs_translation = True`

**Performance:** ~1000 items/second (batched)

---

### STAGE 4: EMBEDDING GENERATION

**Input:** `NormalizedItem` (batch of 100-500)
**Output:** `NormalizedItem` with `embedding` set + saved to Qdrant

**Process:**
1. **Check cache:** Query Redis for cached embeddings (key = SHA-256 of text)
   - Cache hit: Load embedding from Redis, skip API call
   - Cache miss: Continue to step 2
2. **Prepare text:** Combine title + description
   ```python
   text = f"{item.title}. {item.description}"
   ```
3. **Call embedding API:**
   ```python
   response = await openai_client.embeddings.create(
       model="text-embedding-3-small",
       input=[text for item in batch]
   )
   embeddings = [e.embedding for e in response.data]
   ```
4. **Store in cache:**
   ```python
   for item, embedding in zip(batch, embeddings):
       cache_key = hashlib.sha256(text.encode()).hexdigest()
       redis.setex(f"embedding:{cache_key}", 86400, embedding)  # 24h TTL
   ```
5. **Save to vector DB:**
   ```python
   qdrant_client.upsert(
       collection_name="topics",
       points=[
           PointStruct(
               id=item.id,
               vector=embedding,
               payload={"title": item.title, "source": item.source, ...}
           )
           for item, embedding in zip(batch, embeddings)
       ]
   )
   ```
6. **Set embedding field:**
   ```python
   item.embedding = np.array(embedding)
   ```

**Cost Optimization:**
- Cache hit rate: 30-50% (popular topics re-appear)
- Batch API calls: 500 items per call (reduce overhead)

---

### STAGE 5: DEDUPLICATION

**Input:** `NormalizedItem` with embeddings
**Output:** Deduplicated list of items

**Process:**

#### Level 1: Exact Duplicate (URL-based)
```python
seen_urls = set()
unique_items = []

for item in items:
    url_hash = hashlib.sha256(item.url.encode()).hexdigest()
    if url_hash not in seen_urls:
        seen_urls.add(url_hash)
        unique_items.append(item)
    else:
        # Merge engagement scores (keep highest)
        existing = next(i for i in unique_items if sha256(i.url) == url_hash)
        if item.engagement_score > existing.engagement_score:
            unique_items.remove(existing)
            unique_items.append(item)
```

#### Level 2: Near-Duplicate (Embedding-based)
```python
threshold = 0.92
deduped = []

for item in unique_items:
    # Search for similar items in Qdrant
    results = qdrant_client.search(
        collection_name="topics",
        query_vector=item.embedding,
        limit=5,
        score_threshold=threshold
    )

    # If similar item exists, merge
    if len(results) > 1:  # First result is self
        similar_item_id = results[1].id
        # Keep item with higher engagement
        if item.engagement_score > get_item(similar_item_id).engagement_score:
            # Mark similar item as duplicate
            mark_duplicate(similar_item_id, item.id)
        else:
            # Skip current item
            continue

    deduped.append(item)
```

#### Level 3: Cross-Source Deduplication
- Detect same story from multiple sources
- Strategy: High embedding similarity (0.85+) + overlapping named entities
- Action: Create "story cluster", link all sources

**Output:** ~30-50% reduction in items (typical)

---

### STAGE 6: CLUSTERING

**Input:** Deduplicated items with embeddings
**Output:** Items assigned to topics/trends/categories

#### Sub-stage 6a: Topic Clustering (HDBSCAN)

**Why HDBSCAN:** Finds clusters of varying density, doesn't require K, handles outliers

```python
from hdbscan import HDBSCAN

embeddings_matrix = np.vstack([item.embedding for item in items])

clusterer = HDBSCAN(
    min_cluster_size=5,  # Minimum 5 items per cluster
    metric='cosine',
    cluster_selection_method='eom'  # Excess of mass
)

cluster_labels = clusterer.fit_predict(embeddings_matrix)

# cluster_labels = [0, 0, 1, 2, -1, 2, ...]
# -1 = outlier (doesn't fit any cluster)

for item, label in zip(items, cluster_labels):
    item.topic_cluster_id = label if label != -1 else None
```

**Result:** 50-200 micro-clusters (topics)

#### Sub-stage 6b: Trend Clustering (Agglomerative)

**Purpose:** Merge similar topics into macro-trends

```python
from sklearn.cluster import AgglomerativeClustering

# Get cluster centroids (mean embedding of each topic)
topic_clusters = defaultdict(list)
for item in items:
    if item.topic_cluster_id is not None:
        topic_clusters[item.topic_cluster_id].append(item.embedding)

centroids = {
    cluster_id: np.mean(embeddings, axis=0)
    for cluster_id, embeddings in topic_clusters.items()
}

# Cluster centroids into macro-trends
centroid_matrix = np.vstack(list(centroids.values()))

# Determine optimal K using elbow method
from sklearn.metrics import silhouette_score

silhouette_scores = []
for k in range(5, 31):
    clusterer = AgglomerativeClustering(n_clusters=k, linkage='average')
    labels = clusterer.fit_predict(centroid_matrix)
    score = silhouette_score(centroid_matrix, labels)
    silhouette_scores.append(score)

optimal_k = silhouette_scores.index(max(silhouette_scores)) + 5

# Cluster with optimal K
clusterer = AgglomerativeClustering(n_clusters=optimal_k, linkage='average')
macro_labels = clusterer.fit_predict(centroid_matrix)

# Assign items to macro-trends
for item in items:
    if item.topic_cluster_id is not None:
        topic_idx = list(centroids.keys()).index(item.topic_cluster_id)
        item.trend_cluster_id = int(macro_labels[topic_idx])
```

**Result:** 10-30 macro-trends

#### Sub-stage 6c: Category Assignment

**Two approaches:**

**Approach 1: Keyword Matching**
```python
CATEGORY_KEYWORDS = {
    "Technology": ["AI", "software", "hardware", "tech", "app", "code", ...],
    "Politics": ["election", "president", "congress", "vote", ...],
    "Sports": ["game", "team", "player", "score", "league", ...],
    # ...
}

for trend in trends:
    # Get all text from trend items
    trend_text = " ".join(item.title + " " + item.description for item in trend.items)

    # Count keyword matches per category
    scores = {
        category: sum(1 for keyword in keywords if keyword.lower() in trend_text.lower())
        for category, keywords in CATEGORY_KEYWORDS.items()
    }

    # Assign category with highest score
    trend.category = max(scores, key=scores.get)
```

**Approach 2: LLM Classification** (more accurate but costly)
```python
prompt = f"""
Classify this trend into ONE of these categories:
Technology, Politics, Entertainment, Sports, Science, Business, World News, Health, Other

Trend title: {trend.title}
Sample topics:
{"\n".join([f"- {item.title}" for item in trend.items[:5]])}

Category:"""

category = await llm_client.complete(prompt, max_tokens=10)
trend.category = category.strip()
```

---

### STAGE 7: RANKING

**Input:** Clustered items
**Output:** Ranked items + ranked trends

**Scoring Function:**
```python
def calculate_trend_score(item: NormalizedItem) -> float:
    """Composite score for ranking"""

    # 1. Engagement (40% weight)
    engagement = item.engagement_score
    max_engagement = max(i.engagement_score for i in all_items)
    engagement_normalized = engagement / max_engagement

    # 2. Recency (30% weight)
    hours_old = (now - item.timestamp).total_seconds() / 3600
    recency_score = math.exp(-hours_old / 24.0)  # Exponential decay

    # 3. Velocity (20% weight)
    velocity = engagement / max(hours_old, 1)
    max_velocity = max(i.engagement / max((now - i.timestamp).total_seconds() / 3600, 1) for i in all_items)
    velocity_normalized = velocity / max_velocity

    # 4. Source authority (10% weight)
    SOURCE_AUTHORITY = {
        "nytimes": 1.5,
        "bbc": 1.5,
        "reuters": 1.5,
        "youtube": 1.0,
        "reddit": 0.8,
        "twitter": 0.7
    }
    source_weight = SOURCE_AUTHORITY.get(item.source, 1.0)

    return (
        engagement_normalized * 0.4 +
        recency_score * 0.3 +
        velocity_normalized * 0.2 +
        source_weight * 0.1
    )
```

**Source Diversity Filter:**
```python
def apply_source_diversity(trend_items, max_percentage=0.4):
    """Limit each source to max_percentage of trend items"""

    source_counts = Counter(item.source for item in trend_items)
    total_items = len(trend_items)
    max_per_source = int(total_items * max_percentage)

    filtered_items = []
    source_used = defaultdict(int)

    # Sort by score (highest first)
    sorted_items = sorted(trend_items, key=lambda i: i.score, reverse=True)

    for item in sorted_items:
        if source_used[item.source] < max_per_source:
            filtered_items.append(item)
            source_used[item.source] += 1

    return filtered_items
```

---

### STAGE 8: CONTENT ENRICHMENT

**Input:** Ranked items
**Output:** Items with full content + metadata

**Process:**
```python
async def enrich_content(item: NormalizedItem):
    """Fetch full article content"""

    # Skip if URL is a platform (not article)
    if any(domain in item.url for domain in ["reddit.com", "twitter.com", "youtube.com"]):
        return item

    try:
        # Fetch webpage
        async with aiohttp.ClientSession() as session:
            async with session.get(item.url, timeout=10) as response:
                html = await response.text()

        # Extract content
        from trafilatura import extract

        content = extract(
            html,
            include_comments=False,
            include_tables=False,
            no_fallback=False
        )

        if content:
            item.full_content = content[:5000]  # Limit to 5000 chars
            item.content_fetched = True
        else:
            item.full_content = item.description
            item.content_fetched = False

    except Exception as e:
        logger.warning(f"Failed to fetch content for {item.url}: {e}")
        item.full_content = item.description
        item.content_fetched = False

    return item
```

**Parallelization:** 10 concurrent requests (avoid overwhelming servers)

---

### STAGE 9: LLM PROCESSING

**Input:** Enriched items
**Output:** Items with summaries, tags, sentiment

#### Sub-stage 9a: Summarization

**Batch processing:**
```python
async def summarize_batch(items: List[NormalizedItem], max_words=15):
    """Summarize multiple items in one API call"""

    prompt = f"""
Summarize each of the following articles in exactly {max_words} words.
Format: One summary per line, separated by "---"

{"\n\n---\n\n".join([f"Title: {item.title}\nContent: {item.full_content[:500]}" for item in items])}

Summaries:
"""

    response = await llm_client.complete(prompt, max_tokens=max_words * len(items) * 2)

    summaries = response.split("---")

    for item, summary in zip(items, summaries):
        item.title_summary = summary.strip()

    return items
```

**Batch size:** 50 items per call (balance cost vs latency)

#### Sub-stage 9b: Tagging

```python
async def extract_tags(item: NormalizedItem):
    """Extract keywords and sentiment"""

    prompt = f"""
Extract 5-10 relevant keywords/tags and sentiment from this article.

Title: {item.title}
Content: {item.full_content[:500]}

Output JSON:
{{"tags": ["tag1", "tag2", ...], "sentiment": "positive|neutral|negative"}}
"""

    response = await llm_client.complete(prompt, max_tokens=100)
    data = json.loads(response)

    item.tags = data["tags"]
    item.sentiment = data["sentiment"]

    return item
```

---

### STAGE 10: TREND DETECTION

**Input:** Current trends + historical trend data
**Output:** Trend state (EMERGING, VIRAL, SUSTAINED, DECLINING)

**Process:**
```python
async def detect_trend_state(current_trend, trend_history):
    """Compare current trend to historical data"""

    # Query time-series DB for trend history
    history = await influxdb.query(f"""
        SELECT item_count, total_engagement
        FROM trend_metrics
        WHERE trend_id = '{current_trend.id}'
        AND time > now() - 7d
        ORDER BY time
    """)

    if len(history) == 0:
        return TrendState.EMERGING  # New trend

    # Analyze growth
    sizes = [h.item_count for h in history]
    engagements = [h.total_engagement for h in history]

    # Fit growth curve
    from scipy.optimize import curve_fit

    def exponential(x, a, b):
        return a * np.exp(b * x)

    try:
        params, _ = curve_fit(exponential, range(len(sizes)), sizes)
        growth_rate = params[1]  # Exponential growth rate

        if growth_rate > 0.5:  # 50%+ growth per period
            return TrendState.VIRAL
        elif growth_rate > 0.1:
            return TrendState.SUSTAINED
        elif growth_rate < -0.1:
            return TrendState.DECLINING
        else:
            return TrendState.STABLE
    except:
        # Fallback: simple linear regression
        slope = np.polyfit(range(len(sizes)), sizes, 1)[0]
        if slope > 10:
            return TrendState.GROWING
        elif slope < -5:
            return TrendState.DECLINING
        else:
            return TrendState.STABLE
```

---

### STAGE 11: STORAGE

**Atomic Transaction:**
```python
async def save_trends(trends: List[Trend]):
    """Save trends to multiple storage backends atomically"""

    async with db_transaction():  # PostgreSQL transaction
        try:
            # 1. Save metadata to PostgreSQL
            await pg_repo.save_trends(trends)

            # 2. Save embeddings to Qdrant
            await qdrant_client.upsert(
                collection_name="trends",
                points=[
                    PointStruct(
                        id=trend.id,
                        vector=trend.embedding,
                        payload={"title": trend.title, "category": trend.category}
                    )
                    for trend in trends
                ]
            )

            # 3. Save full content to MinIO
            for trend in trends:
                await minio_client.put_object(
                    bucket="trend-content",
                    key=f"{trend.id}.json",
                    data=json.dumps(trend.to_dict())
                )

            # 4. Save metrics to InfluxDB
            await influxdb.write(
                measurement="trend_metrics",
                tags={"trend_id": trend.id, "category": trend.category},
                fields={"item_count": len(trend.items), "total_engagement": trend.score},
                time=datetime.utcnow()
            )

            # 5. Invalidate caches
            await redis.delete(f"trend:{trend.id}")
            await redis.delete("trending_topics")

            # Commit transaction
            await db_transaction.commit()

        except Exception as e:
            await db_transaction.rollback()
            raise e
```

---

### STAGE 12: NOTIFICATION

**WebSocket Push:**
```python
async def notify_new_trends(trends: List[Trend]):
    """Push new trends to connected clients"""

    # Broadcast to all WebSocket connections
    message = {
        "type": "new_trends",
        "count": len(trends),
        "trends": [
            {"id": t.id, "title": t.title, "category": t.category, "score": t.score}
            for t in trends
        ]
    }

    await websocket_manager.broadcast(message)
```

**Alert Webhooks:**
```python
async def send_alerts(trends: List[Trend]):
    """Send alerts for high-priority trends"""

    # Get users with alert subscriptions
    subscribers = await db.query("SELECT * FROM alert_subscriptions WHERE enabled = true")

    for subscriber in subscribers:
        # Filter trends by user preferences
        relevant_trends = [
            t for t in trends
            if t.category in subscriber.categories and t.score > subscriber.min_score
        ]

        if relevant_trends:
            await send_webhook(subscriber.webhook_url, relevant_trends)
```

---

## Pipeline Metrics & Monitoring

### Key Metrics to Track

**Ingestion:**
- `ingestion_items_collected_total{source}` - Total items collected per source
- `ingestion_duration_seconds{source}` - Time to collect from each source
- `ingestion_errors_total{source, error_type}` - Collection failures

**Processing:**
- `processing_items_processed_total{stage}` - Items processed per stage
- `processing_duration_seconds{stage}` - Time per processing stage
- `deduplication_removed_total` - Items removed as duplicates
- `clustering_clusters_created` - Number of clusters created

**Intelligence:**
- `embedding_generation_duration_seconds` - Embedding API latency
- `llm_api_calls_total{provider, operation}` - LLM API usage
- `llm_cost_dollars{provider}` - LLM costs
- `cache_hit_rate{type}` - Embedding/translation cache hit rate

**Storage:**
- `storage_writes_total{backend}` - Writes to each storage backend
- `storage_size_bytes{backend}` - Storage usage
- `transaction_duration_seconds` - Time to complete atomic save

**End-to-End:**
- `pipeline_duration_seconds` - Total time from collection to storage
- `pipeline_items_output` - Final number of trends/topics saved
- `pipeline_success_rate` - Percentage of successful pipeline runs

### Alerting Rules

```yaml
alerts:
  - name: IngestionFailure
    condition: ingestion_errors_total > 10 (in 5 minutes)
    severity: high
    action: Page on-call engineer

  - name: PipelineStalled
    condition: pipeline_duration_seconds > 3600 (1 hour)
    severity: medium
    action: Send Slack notification

  - name: LLMCostSpike
    condition: llm_cost_dollars > 100 (per day)
    severity: low
    action: Send email to admin

  - name: StorageFull
    condition: storage_size_bytes{backend="postgres"} > 0.9 * max_size
    severity: critical
    action: Auto-trigger cleanup job + page admin
```

---

---

## Pipeline Improvements & Resilience Strategy

This section provides **actionable recommendations** for enhancing the pipeline's resilience, efficiency, consistency, multilingual handling, and edge-case management.

---

## 1. RESILIENCE & FAULT TOLERANCE

### 1.1 Retry Strategies with Exponential Backoff

**Affected Stages:** 1 (Collection), 4 (Embedding), 8 (Content Enrichment), 9 (LLM Processing)

**Problem:** API failures (rate limits, timeouts, transient errors) cause data loss or pipeline stalls.

**Recommendation:** Implement tiered retry with exponential backoff + jitter

**Implementation:**

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class RetryableAPIError(Exception):
    """Errors that should trigger retry"""
    pass

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60) + wait_random(0, 3),  # jitter
    retry=retry_if_exception_type((RetryableAPIError, aiohttp.ClientError)),
    before_sleep=log_retry_attempt
)
async def call_external_api(url: str, payload: dict):
    """API call with retry logic"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=30) as response:
                if response.status == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', 60))
                    raise RetryableAPIError(f"Rate limited, retry after {retry_after}s")
                elif response.status >= 500:  # Server error
                    raise RetryableAPIError(f"Server error: {response.status}")
                elif response.status >= 400:  # Client error (don't retry)
                    raise ValueError(f"Client error: {response.status}")

                return await response.json()
    except asyncio.TimeoutError:
        raise RetryableAPIError("Request timeout")
```

**Per-Stage Configuration:**

| Stage | Max Retries | Initial Delay | Max Delay | Timeout |
|-------|-------------|---------------|-----------|---------|
| Collection (YouTube API) | 5 | 4s | 60s | 30s |
| Embedding (OpenAI) | 3 | 2s | 30s | 60s |
| Content Fetch (Web scraping) | 3 | 1s | 10s | 10s |
| LLM Summarization | 3 | 5s | 60s | 120s |

**Trade-offs:**
- ✅ Handles transient failures gracefully
- ⚠️ Increases latency for failed requests
- ⚠️ May amplify load during outages (use circuit breaker)

---

### 1.2 Circuit Breaker Pattern

**Affected Stages:** All stages with external dependencies (1, 4, 8, 9)

**Problem:** Cascading failures when external services are down; retry storms worsen outages.

**Recommendation:** Implement circuit breaker to fail fast and prevent retry storms

**Implementation:**

```python
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"    # Normal operation
    OPEN = "open"        # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60, half_open_max_calls=3):
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # seconds before trying again
        self.half_open_max_calls = half_open_max_calls

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker"""

        # Check if circuit should transition from OPEN to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
            else:
                raise CircuitBreakerOpenError("Circuit is open, failing fast")

        # Limit calls in HALF_OPEN state
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpenError("Circuit is half-open, limited calls")
            self.half_open_calls += 1

        try:
            result = await func(*args, **kwargs)

            # Success: reset or close circuit
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0

            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            # Open circuit if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")

            raise e

# Usage per service
openai_circuit = CircuitBreaker(failure_threshold=5, timeout=120)
youtube_circuit = CircuitBreaker(failure_threshold=10, timeout=60)

# In collection stage
async def collect_from_youtube():
    try:
        return await youtube_circuit.call(youtube_plugin.fetch)
    except CircuitBreakerOpenError:
        logger.warning("YouTube circuit is open, skipping collection")
        return []  # Skip gracefully, don't fail entire pipeline
```

**Benefits:**
- ✅ Prevents retry storms during outages
- ✅ Fails fast, reducing resource waste
- ✅ Automatic recovery testing (half-open state)

**Trade-offs:**
- ⚠️ May skip data collection during brief outages
- ⚠️ Requires careful threshold tuning

---

### 1.3 Dead Letter Queue (DLQ) for Unprocessable Items

**Affected Stages:** All processing stages (2-11)

**Problem:** Items that fail repeatedly block the queue and are eventually lost.

**Recommendation:** Route failed items to DLQ after max retries for manual inspection

**Implementation:**

```python
# RabbitMQ configuration
channel.queue_declare(
    queue='processing.normalized',
    durable=True,
    arguments={
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'dlq.failed_items'
    }
)

# Dead letter exchange
channel.exchange_declare(exchange='dlx', exchange_type='direct', durable=True)
channel.queue_declare(queue='dlq.failed_items', durable=True)
channel.queue_bind(exchange='dlx', queue='dlq.failed_items', routing_key='dlq.failed_items')

# Worker handling
@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,))
async def process_item(self, item: dict):
    try:
        # Processing logic
        normalized = await normalize_item(item)
        return normalized
    except Exception as e:
        if self.request.retries >= self.max_retries:
            # Log failure reason before sending to DLQ
            logger.error(
                "Item failed after max retries, sending to DLQ",
                extra={
                    "item_id": item.get("id"),
                    "error": str(e),
                    "retries": self.request.retries,
                    "stage": "normalization"
                }
            )
            # RabbitMQ will automatically route to DLQ via dead-letter-exchange
        raise
```

**DLQ Monitoring Dashboard:**

```python
# Prometheus metrics
dlq_items_total = Counter(
    'dlq_items_total',
    'Total items sent to DLQ',
    ['stage', 'error_type']
)

# Alert rule
alerts:
  - name: DLQBacklogHigh
    condition: dlq_items_total > 100 (in 1 hour)
    severity: high
    action: Page on-call engineer
```

**DLQ Processing Workflow:**

```python
# Admin tool to inspect DLQ
@app.get("/admin/dlq/items")
async def get_dlq_items(limit: int = 50):
    """View items in DLQ"""
    messages = rabbitmq_channel.basic_get(queue='dlq.failed_items', auto_ack=False)
    return [json.loads(msg.body) for msg in messages[:limit]]

@app.post("/admin/dlq/retry/{item_id}")
async def retry_dlq_item(item_id: str):
    """Manually retry a DLQ item (after fixing issue)"""
    # Requeue to original queue
    item = get_dlq_item(item_id)
    await rabbitmq_channel.basic_publish(
        exchange='',
        routing_key='processing.normalized',
        body=json.dumps(item)
    )
```

**Trade-offs:**
- ✅ Prevents data loss
- ✅ Enables manual intervention
- ⚠️ Requires DLQ monitoring and manual cleanup

---

### 1.4 Backpressure & Rate Limiting

**Affected Stages:** 1 (Collection), 4 (Embedding), 9 (LLM)

**Problem:** Overwhelming downstream systems (e.g., embedding API rate limits, database write bottlenecks).

**Recommendation:** Implement adaptive rate limiting and queue-based backpressure

**Implementation:**

```python
from asyncio import Semaphore
from collections import deque
import time

class AdaptiveRateLimiter:
    """Rate limiter that adjusts based on error rates"""

    def __init__(self, initial_rate=100, min_rate=10, max_rate=500):
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.semaphore = Semaphore(initial_rate)

        # Track success/failure
        self.window = deque(maxlen=100)  # Last 100 requests
        self.last_adjustment = time.time()

    async def acquire(self):
        """Acquire permit to make request"""
        await self.semaphore.acquire()

    def release(self, success: bool):
        """Release permit and adjust rate"""
        self.semaphore.release()
        self.window.append(success)

        # Adjust rate every 10 seconds
        if time.time() - self.last_adjustment > 10 and len(self.window) >= 50:
            success_rate = sum(self.window) / len(self.window)

            if success_rate > 0.95:  # High success, increase rate
                new_rate = min(int(self.current_rate * 1.2), self.max_rate)
            elif success_rate < 0.80:  # High failure, decrease rate
                new_rate = max(int(self.current_rate * 0.7), self.min_rate)
            else:
                new_rate = self.current_rate

            if new_rate != self.current_rate:
                logger.info(f"Adjusting rate limit: {self.current_rate} → {new_rate}")
                self.current_rate = new_rate
                # Recreate semaphore with new rate
                self.semaphore = Semaphore(new_rate)

            self.last_adjustment = time.time()

# Usage in embedding stage
embedding_rate_limiter = AdaptiveRateLimiter(initial_rate=60, max_rate=200)

async def generate_embeddings_batch(texts: List[str]):
    """Generate embeddings with adaptive rate limiting"""
    await embedding_rate_limiter.acquire()

    try:
        embeddings = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        embedding_rate_limiter.release(success=True)
        return embeddings
    except Exception as e:
        embedding_rate_limiter.release(success=False)
        raise
```

**Queue-Based Backpressure:**

```python
# Monitor queue depth
async def check_backpressure():
    """Pause collection if processing queue is too deep"""
    queue_depth = await rabbitmq_channel.queue_declare(
        queue='processing.normalized',
        passive=True
    ).method.message_count

    if queue_depth > 10000:  # Threshold
        logger.warning(f"Queue depth {queue_depth}, pausing collection")
        await pause_collection_workers()
        return True
    elif queue_depth < 1000:
        await resume_collection_workers()
        return False

    return False

# In scheduler
@scheduled_task(interval=30)  # Check every 30 seconds
async def manage_backpressure():
    backpressure_active = await check_backpressure()

    # Emit metric
    prometheus_client.gauge('pipeline_backpressure_active').set(int(backpressure_active))
```

**Trade-offs:**
- ✅ Prevents system overload
- ✅ Self-adjusting to changing conditions
- ⚠️ May slow down collection during high load

---

### 1.5 Graceful Degradation

**Affected Stages:** 4 (Embedding), 9 (LLM)

**Problem:** Complete pipeline failure when expensive external services (OpenAI) are unavailable.

**Recommendation:** Fallback to local models or cached results

**Implementation:**

```python
async def generate_embedding_with_fallback(text: str) -> np.ndarray:
    """Generate embedding with fallback chain"""

    # Try 1: Check cache
    cached = await embedding_cache.get(text)
    if cached:
        return cached

    # Try 2: OpenAI (high quality)
    try:
        embedding = await openai_circuit.call(
            openai_embedding_service.embed, text
        )
        await embedding_cache.set(text, embedding)
        return embedding
    except (CircuitBreakerOpenError, Exception) as e:
        logger.warning(f"OpenAI embedding failed: {e}, falling back to local model")

    # Try 3: Local model (lower quality, but always available)
    try:
        embedding = local_embedding_model.encode([text])[0]
        await embedding_cache.set(text, embedding, ttl=3600)  # Shorter TTL for fallback

        # Emit metric
        prometheus_client.counter('embedding_fallback_total', labels=['local_model']).inc()

        return embedding
    except Exception as e:
        logger.error(f"Local embedding also failed: {e}")
        raise

async def summarize_with_fallback(text: str) -> str:
    """Summarize with fallback to extractive summarization"""

    # Try 1: OpenAI LLM (best quality)
    try:
        return await openai_circuit.call(llm_service.summarize, text)
    except Exception as e:
        logger.warning(f"LLM summarization failed: {e}, using extractive fallback")

    # Try 2: Extractive summarization (rule-based, always works)
    sentences = text.split('. ')
    # Simple heuristic: first sentence + longest sentence
    if len(sentences) < 2:
        return sentences[0][:200]

    first = sentences[0]
    longest = max(sentences[1:], key=len)
    return f"{first}. {longest}."[:200]
```

**Benefits:**
- ✅ Pipeline continues during API outages
- ✅ Reduced dependency on external services

**Trade-offs:**
- ⚠️ Quality degradation with fallbacks
- ⚠️ Need to track which items used fallback (for re-processing later)

---

## 2. CACHING & EFFICIENCY

### 2.1 Multi-Layer Embedding Cache

**Affected Stages:** 4 (Embedding Generation)

**Problem:** Duplicate content generates same embeddings repeatedly, wasting API quota and time.

**Recommendation:** Implement L1 (in-memory) + L2 (Redis) + L3 (PostgreSQL) cache hierarchy

**Implementation:**

```python
from cachetools import LRUCache
import hashlib

class MultiLayerEmbeddingCache:
    """Three-tier embedding cache"""

    def __init__(self):
        # L1: In-memory LRU (fastest, limited size)
        self.l1_cache = LRUCache(maxsize=10000)

        # L2: Redis (fast, larger, shared across workers)
        self.l2_redis = redis_client

        # L3: PostgreSQL (permanent, for frequently accessed items)
        self.l3_db = db_connection

    def _hash(self, text: str) -> str:
        """Generate cache key from text"""
        return hashlib.sha256(text.encode()).hexdigest()

    async def get(self, text: str) -> Optional[np.ndarray]:
        """Get embedding from cache (L1 → L2 → L3)"""
        key = self._hash(text)

        # Try L1 (in-memory)
        if key in self.l1_cache:
            prometheus_client.counter('embedding_cache_hits', labels=['L1']).inc()
            return self.l1_cache[key]

        # Try L2 (Redis)
        l2_value = await self.l2_redis.get(f"embedding:{key}")
        if l2_value:
            embedding = np.frombuffer(l2_value, dtype=np.float32)
            # Promote to L1
            self.l1_cache[key] = embedding
            prometheus_client.counter('embedding_cache_hits', labels=['L2']).inc()
            return embedding

        # Try L3 (PostgreSQL - only for hot items)
        l3_value = await self.l3_db.fetchval(
            "SELECT embedding FROM embedding_cache WHERE text_hash = $1 AND access_count > 10",
            key
        )
        if l3_value:
            embedding = np.array(l3_value)
            # Promote to L2 and L1
            await self.l2_redis.setex(f"embedding:{key}", 86400, embedding.tobytes())
            self.l1_cache[key] = embedding
            prometheus_client.counter('embedding_cache_hits', labels=['L3']).inc()
            return embedding

        # Cache miss
        prometheus_client.counter('embedding_cache_misses').inc()
        return None

    async def set(self, text: str, embedding: np.ndarray):
        """Set embedding in cache (write-through to all layers)"""
        key = self._hash(text)

        # L1
        self.l1_cache[key] = embedding

        # L2 (24h TTL)
        await self.l2_redis.setex(f"embedding:{key}", 86400, embedding.tobytes())

        # L3 (only if accessed multiple times - tracked separately)
        await self.l3_db.execute(
            """
            INSERT INTO embedding_cache (text_hash, embedding, access_count, created_at)
            VALUES ($1, $2, 1, NOW())
            ON CONFLICT (text_hash) DO UPDATE
            SET access_count = embedding_cache.access_count + 1,
                last_accessed = NOW()
            """,
            key, embedding.tolist()
        )
```

**Cache Warming Strategy:**

```python
@scheduled_task(cron="0 3 * * *")  # 3 AM daily
async def warm_embedding_cache():
    """Pre-compute embeddings for frequently seen topics"""

    # Get top 1000 most common titles from last 30 days
    common_texts = await db.fetch(
        """
        SELECT title, COUNT(*) as frequency
        FROM topics
        WHERE published_at > NOW() - INTERVAL '30 days'
        GROUP BY title
        HAVING COUNT(*) > 5
        ORDER BY frequency DESC
        LIMIT 1000
        """
    )

    for row in common_texts:
        text = row['title']
        if await embedding_cache.get(text) is None:
            embedding = await embedding_service.embed(text)
            await embedding_cache.set(text, embedding)
            logger.info(f"Warmed cache for: {text[:50]}")
```

**Benefits:**
- ✅ 70-90% cache hit rate (reduces API costs significantly)
- ✅ L1 cache provides sub-millisecond lookups
- ✅ L3 cache survives Redis restarts

**Trade-offs:**
- ⚠️ Memory overhead for L1 cache
- ⚠️ Cache invalidation complexity

---

### 2.2 Intelligent Translation Caching with Language Pairs

**Affected Stages:** 3 (Language Detection), 9 (LLM Processing)

**Problem:** Same content translated multiple times in different requests.

**Recommendation:** Cache translations with language-pair-aware keys and preemptive caching

**Implementation:**

```python
class SmartTranslationCache:
    """Translation cache with language pair optimization"""

    def __init__(self):
        self.redis = redis_client

    def _cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate cache key for translation"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"translation:{source_lang}:{target_lang}:{text_hash}"

    async def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Get cached translation"""
        key = self._cache_key(text, source_lang, target_lang)
        translation = await self.redis.get(key)

        if translation:
            # Update access count for popularity tracking
            await self.redis.incr(f"{key}:access_count")
            await self.redis.expire(f"{key}:access_count", 2592000)  # 30 days

            prometheus_client.counter('translation_cache_hits').inc()
            return translation.decode()

        prometheus_client.counter('translation_cache_misses').inc()
        return None

    async def set(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        translation: str,
        ttl: int = 2592000  # 30 days default
    ):
        """Cache translation with adaptive TTL"""
        key = self._cache_key(text, source_lang, target_lang)

        # Set translation
        await self.redis.setex(key, ttl, translation)

        # Track reverse translation (for efficiency)
        reverse_key = self._cache_key(translation, target_lang, source_lang)
        await self.redis.setex(reverse_key, ttl, text)

    async def get_popular_pairs(self) -> List[tuple]:
        """Identify popular language pairs for preemptive caching"""
        # Scan for translation keys and count pairs
        pairs = {}
        cursor = 0

        while True:
            cursor, keys = await self.redis.scan(
                cursor,
                match="translation:*:access_count",
                count=1000
            )

            for key in keys:
                # Parse: translation:en:es:abc123:access_count
                parts = key.decode().split(':')
                if len(parts) >= 4:
                    pair = (parts[1], parts[2])  # (source, target)
                    count = int(await self.redis.get(key) or 0)
                    pairs[pair] = pairs.get(pair, 0) + count

            if cursor == 0:
                break

        # Return top 10 pairs
        return sorted(pairs.items(), key=lambda x: x[1], reverse=True)[:10]

# Preemptive translation for popular content
@scheduled_task(cron="0 */6 * * *")  # Every 6 hours
async def preemptive_translate():
    """Translate popular content to common languages proactively"""

    # Get popular language pairs
    popular_pairs = await translation_cache.get_popular_pairs()

    # Get recent trending topics (likely to be requested)
    trending_topics = await db.fetch(
        """
        SELECT id, title, description, language
        FROM topics
        WHERE published_at > NOW() - INTERVAL '24 hours'
        AND engagement_score > 1000
        LIMIT 100
        """
    )

    for topic in trending_topics:
        source_lang = topic['language']

        for (src, tgt), count in popular_pairs:
            if src == source_lang and count > 50:  # Only popular pairs
                # Check if already cached
                cached = await translation_cache.get(topic['title'], src, tgt)
                if cached is None:
                    # Translate proactively
                    translation = await translation_service.translate(
                        topic['title'],
                        src,
                        tgt
                    )
                    await translation_cache.set(topic['title'], src, tgt, translation)
                    logger.info(f"Preemptively translated: {src} → {tgt}")
```

**Benefits:**
- ✅ 60-80% cache hit rate for translations
- ✅ Proactive caching reduces latency for popular content
- ✅ Reverse caching (source→target and target→source) doubles hit rate

**Trade-offs:**
- ⚠️ Preemptive translation costs (amortized by cache savings)
- ⚠️ Cache invalidation when translations improve

---

### 2.3 Cache Invalidation Strategy

**Affected Stages:** 4 (Embedding), 9 (LLM), 11 (Storage)

**Problem:** Stale cached data when source content or models change.

**Recommendation:** Implement time-based + event-based invalidation with versioning

**Implementation:**

```python
class VersionedCache:
    """Cache with version-aware invalidation"""

    def __init__(self, cache_name: str, version: str = "v1"):
        self.cache_name = cache_name
        self.version = version
        self.redis = redis_client

    def _versioned_key(self, key: str) -> str:
        """Add version prefix to cache key"""
        return f"{self.cache_name}:{self.version}:{key}"

    async def get(self, key: str):
        """Get from versioned cache"""
        return await self.redis.get(self._versioned_key(key))

    async def set(self, key: str, value: any, ttl: int):
        """Set in versioned cache"""
        await self.redis.setex(self._versioned_key(key), ttl, value)

    async def invalidate_all(self):
        """Invalidate all keys in this cache (by incrementing version)"""
        # Increment version
        new_version = f"v{int(self.version[1:]) + 1}"

        logger.info(f"Invalidating cache {self.cache_name}: {self.version} → {new_version}")

        # Update version in config
        await self.redis.set(f"cache_version:{self.cache_name}", new_version)

        # Schedule deletion of old version keys (async cleanup)
        await self.redis.zadd(
            "cache_cleanup_queue",
            {self._versioned_key("*"): time.time()}
        )

        return new_version

# Specific cache instances
embedding_cache_v = VersionedCache("embeddings", version=EMBEDDING_MODEL_VERSION)
translation_cache_v = VersionedCache("translations", version=TRANSLATION_MODEL_VERSION)

# Event-based invalidation
@app.post("/admin/models/update")
async def update_model(model_type: str):
    """Invalidate cache when model is updated"""

    if model_type == "embedding":
        await embedding_cache_v.invalidate_all()
        logger.info("Embedding cache invalidated due to model update")

    elif model_type == "translation":
        await translation_cache_v.invalidate_all()
        logger.info("Translation cache invalidated due to model update")

    return {"status": "cache_invalidated", "model": model_type}

# Time-based TTL strategy (different per cache type)
CACHE_TTL_CONFIG = {
    "embedding": {
        "popular": 2592000,  # 30 days (accessed > 10 times)
        "normal": 604800,    # 7 days
        "rare": 86400        # 1 day (accessed once)
    },
    "translation": {
        "popular": 2592000,  # 30 days
        "normal": 604800,    # 7 days
        "rare": 86400        # 1 day
    },
    "api_response": {
        "trending": 300,     # 5 minutes (real-time data)
        "search": 1800,      # 30 minutes
        "details": 3600      # 1 hour
    }
}

async def set_with_adaptive_ttl(cache_type: str, key: str, value: any):
    """Set cache with TTL based on access patterns"""

    # Get access count
    access_count = await redis_client.get(f"{key}:access_count") or 0
    access_count = int(access_count)

    # Determine popularity tier
    if access_count > 10:
        tier = "popular"
    elif access_count > 1:
        tier = "normal"
    else:
        tier = "rare"

    ttl = CACHE_TTL_CONFIG[cache_type][tier]

    await redis_client.setex(key, ttl, value)
    logger.debug(f"Cached {key} with TTL {ttl}s (tier: {tier})")
```

**Cache Cleanup Worker:**

```python
@scheduled_task(cron="0 4 * * *")  # 4 AM daily
async def cleanup_old_cache_versions():
    """Remove old cache versions asynchronously"""

    # Get old version patterns from cleanup queue
    old_patterns = await redis_client.zrangebyscore(
        "cache_cleanup_queue",
        0,
        time.time() - 86400  # Older than 1 day
    )

    for pattern in old_patterns:
        # Scan and delete matching keys
        deleted_count = 0
        cursor = 0

        while True:
            cursor, keys = await redis_client.scan(cursor, match=pattern, count=1000)

            if keys:
                await redis_client.delete(*keys)
                deleted_count += len(keys)

            if cursor == 0:
                break

        logger.info(f"Deleted {deleted_count} keys matching {pattern}")

        # Remove from cleanup queue
        await redis_client.zrem("cache_cleanup_queue", pattern)
```

**Benefits:**
- ✅ Automatic invalidation when models change
- ✅ Adaptive TTL based on access patterns
- ✅ Async cleanup prevents blocking

**Trade-offs:**
- ⚠️ Complexity in managing versions
- ⚠️ Temporary cache duplication during version transition

---

## 3. ATOMICITY & CONSISTENCY

### 3.1 Distributed Transactions with Saga Pattern

**Affected Stages:** 11 (Storage)

**Problem:** Multi-backend storage (PostgreSQL + Qdrant + MinIO + InfluxDB) can have partial failures, leaving inconsistent state.

**Recommendation:** Implement Saga pattern with compensation actions

**Implementation:**

```python
from enum import Enum
from dataclasses import dataclass
from typing import Callable, List

class SagaStepStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPENSATED = "compensated"
    FAILED = "failed"

@dataclass
class SagaStep:
    name: str
    action: Callable  # Forward action
    compensation: Callable  # Rollback action
    status: SagaStepStatus = SagaStepStatus.PENDING

class DistributedSaga:
    """Saga pattern for multi-backend transactions"""

    def __init__(self, saga_id: str):
        self.saga_id = saga_id
        self.steps: List[SagaStep] = []
        self.completed_steps: List[SagaStep] = []

    def add_step(self, name: str, action: Callable, compensation: Callable):
        """Add a step to the saga"""
        self.steps.append(SagaStep(name, action, compensation))

    async def execute(self):
        """Execute saga with automatic compensation on failure"""

        logger.info(f"Starting saga {self.saga_id}")

        try:
            # Execute steps sequentially
            for step in self.steps:
                logger.info(f"Executing step: {step.name}")

                try:
                    # Execute forward action
                    await step.action()
                    step.status = SagaStepStatus.COMPLETED
                    self.completed_steps.append(step)

                except Exception as e:
                    logger.error(f"Step {step.name} failed: {e}")
                    step.status = SagaStepStatus.FAILED

                    # Trigger compensation
                    await self._compensate()
                    raise SagaFailedException(f"Saga {self.saga_id} failed at step {step.name}")

            logger.info(f"Saga {self.saga_id} completed successfully")
            return True

        except Exception as e:
            logger.error(f"Saga {self.saga_id} failed: {e}")
            raise

    async def _compensate(self):
        """Rollback completed steps in reverse order"""

        logger.warning(f"Compensating saga {self.saga_id}")

        for step in reversed(self.completed_steps):
            try:
                logger.info(f"Compensating step: {step.name}")
                await step.compensation()
                step.status = SagaStepStatus.COMPENSATED

            except Exception as e:
                logger.error(f"Compensation failed for {step.name}: {e}")
                # Continue compensating other steps

        logger.info(f"Saga {self.saga_id} compensation completed")

# Usage in storage stage
async def save_trends_atomic(trends: List[Trend]):
    """Save trends to multiple backends with saga pattern"""

    saga_id = f"save_trends_{uuid.uuid4()}"
    saga = DistributedSaga(saga_id)

    # Store temporary state
    postgres_saved_ids = []
    qdrant_saved_ids = []
    minio_saved_keys = []
    influx_saved_points = []

    # Step 1: Save to PostgreSQL
    async def save_to_postgres():
        nonlocal postgres_saved_ids
        for trend in trends:
            result = await db.execute(
                "INSERT INTO trends (...) VALUES (...) RETURNING id",
                trend.to_dict()
            )
            postgres_saved_ids.append(result['id'])

    async def compensate_postgres():
        if postgres_saved_ids:
            await db.execute(
                "DELETE FROM trends WHERE id = ANY($1)",
                postgres_saved_ids
            )
            logger.info(f"Deleted {len(postgres_saved_ids)} trends from PostgreSQL")

    saga.add_step("postgres", save_to_postgres, compensate_postgres)

    # Step 2: Save to Qdrant
    async def save_to_qdrant():
        nonlocal qdrant_saved_ids
        points = [
            PointStruct(
                id=trend.id,
                vector=trend.embedding,
                payload={"title": trend.title, "category": trend.category}
            )
            for trend in trends
        ]
        await qdrant_client.upsert(collection_name="trends", points=points)
        qdrant_saved_ids = [p.id for p in points]

    async def compensate_qdrant():
        if qdrant_saved_ids:
            await qdrant_client.delete(
                collection_name="trends",
                points_selector=PointIdsList(points=qdrant_saved_ids)
            )
            logger.info(f"Deleted {len(qdrant_saved_ids)} vectors from Qdrant")

    saga.add_step("qdrant", save_to_qdrant, compensate_qdrant)

    # Step 3: Save to MinIO
    async def save_to_minio():
        nonlocal minio_saved_keys
        for trend in trends:
            key = f"trends/{trend.id}.json"
            await minio_client.put_object(
                bucket="trend-content",
                key=key,
                data=json.dumps(trend.to_dict())
            )
            minio_saved_keys.append(key)

    async def compensate_minio():
        if minio_saved_keys:
            for key in minio_saved_keys:
                await minio_client.delete_object(bucket="trend-content", key=key)
            logger.info(f"Deleted {len(minio_saved_keys)} objects from MinIO")

    saga.add_step("minio", save_to_minio, compensate_minio)

    # Step 4: Save to InfluxDB
    async def save_to_influxdb():
        nonlocal influx_saved_points
        points = []
        for trend in trends:
            point = Point("trend_metrics") \
                .tag("trend_id", trend.id) \
                .tag("category", trend.category) \
                .field("item_count", trend.item_count) \
                .field("total_engagement", trend.total_engagement) \
                .time(datetime.utcnow())
            points.append(point)

        await influxdb_client.write_api().write(bucket="trends", record=points)
        influx_saved_points = points

    async def compensate_influxdb():
        # InfluxDB doesn't support easy deletion, mark as deleted instead
        if influx_saved_points:
            delete_points = [
                Point("trend_metrics") \
                    .tag("trend_id", p.tags['trend_id']) \
                    .field("deleted", True) \
                    .time(datetime.utcnow())
                for p in influx_saved_points
            ]
            await influxdb_client.write_api().write(bucket="trends", record=delete_points)
            logger.info(f"Marked {len(delete_points)} points as deleted in InfluxDB")

    saga.add_step("influxdb", save_to_influxdb, compensate_influxdb)

    # Execute saga
    try:
        await saga.execute()
        logger.info(f"Successfully saved {len(trends)} trends to all backends")
        return True
    except SagaFailedException as e:
        logger.error(f"Failed to save trends: {e}")
        # Emit metric
        prometheus_client.counter('saga_failures_total', labels=['save_trends']).inc()
        return False
```

**Saga Monitoring:**

```python
# Track saga execution
saga_executions_total = Counter(
    'saga_executions_total',
    'Total saga executions',
    ['saga_type', 'status']  # status: success, failed, compensated
)

saga_duration_seconds = Histogram(
    'saga_duration_seconds',
    'Saga execution duration',
    ['saga_type']
)
```

**Benefits:**
- ✅ Eventual consistency across backends
- ✅ Automatic rollback on failure
- ✅ Better error visibility

**Trade-offs:**
- ⚠️ Increased complexity
- ⚠️ Not truly atomic (window of inconsistency during execution)
- ⚠️ Compensation may fail (need manual intervention)

---

### 3.2 Idempotency Keys for Retry Safety

**Affected Stages:** All stages with external writes (1, 4, 11)

**Problem:** Retries can cause duplicate writes (e.g., same trend inserted twice).

**Recommendation:** Use idempotency keys to make operations safe to retry

**Implementation:**

```python
from dataclasses import dataclass
import uuid

@dataclass
class IdempotentRequest:
    idempotency_key: str
    operation: str
    payload: dict
    created_at: datetime

class IdempotencyManager:
    """Manage idempotent operations"""

    def __init__(self):
        self.redis = redis_client
        self.ttl = 86400  # 24 hours

    async def execute_idempotent(
        self,
        idempotency_key: str,
        operation: Callable,
        *args,
        **kwargs
    ):
        """Execute operation with idempotency guarantee"""

        cache_key = f"idempotency:{idempotency_key}"

        # Check if already executed
        cached_result = await self.redis.get(cache_key)
        if cached_result:
            logger.info(f"Idempotent operation {idempotency_key} already executed, returning cached result")
            return json.loads(cached_result)

        # Execute operation
        result = await operation(*args, **kwargs)

        # Cache result
        await self.redis.setex(
            cache_key,
            self.ttl,
            json.dumps({
                "result": result,
                "executed_at": datetime.utcnow().isoformat()
            })
        )

        return result

idempotency_mgr = IdempotencyManager()

# Usage in collection stage
@celery_app.task(bind=True)
async def collect_from_source_idempotent(self, source: str, collection_run_id: str):
    """Collect from source with idempotency"""

    # Generate idempotency key from task ID or use collection_run_id
    idempotency_key = f"{source}:{collection_run_id}"

    async def _collect():
        plugin = plugin_registry.get(source)
        items = []
        async for item in plugin.collect():
            items.append(item)
        return {"source": source, "count": len(items), "items": items}

    return await idempotency_mgr.execute_idempotent(
        idempotency_key,
        _collect
    )

# Usage in storage stage
async def save_trend_idempotent(trend: Trend):
    """Save trend with idempotency"""

    # Use trend.id as idempotency key
    idempotency_key = f"save_trend:{trend.id}"

    async def _save():
        # Check if trend already exists
        existing = await db.fetchval("SELECT id FROM trends WHERE id = $1", trend.id)
        if existing:
            logger.info(f"Trend {trend.id} already exists, skipping")
            return {"status": "already_exists", "id": trend.id}

        # Save trend
        await db.execute("INSERT INTO trends (...) VALUES (...)", trend.to_dict())
        return {"status": "created", "id": trend.id}

    return await idempotency_mgr.execute_idempotent(idempotency_key, _save)
```

**Benefits:**
- ✅ Safe retries (no duplicate writes)
- ✅ Consistent results for duplicate requests

**Trade-offs:**
- ⚠️ Requires idempotency key generation/management
- ⚠️ Cache overhead

---

## 4. MULTILINGUAL CONSISTENCY

### 4.1 Translation-Before-Embedding Strategy

**Affected Stages:** 3 (Language Detection), 4 (Embedding), 5 (Deduplication)

**Problem:** Embeddings in different languages have different semantic spaces, breaking cross-language deduplication.

**Recommendation:** Translate to canonical language (English) before embedding

**Implementation:**

```python
async def generate_canonical_embedding(item: NormalizedItem) -> np.ndarray:
    """
    Generate embedding in canonical language space.

    Workflow:
    1. Detect language
    2. If non-English, translate to English
    3. Generate embedding from English text
    4. Cache both original and translated embeddings
    """

    # Step 1: Language detection (with validation)
    if not item.language or item.language_confidence < 0.7:
        item.language, item.language_confidence = await detect_language_robust(
            f"{item.title} {item.description}"
        )

    # Step 2: Prepare canonical text
    if item.language == "en":
        canonical_text = f"{item.title}. {item.description}"
        item.canonical_text = canonical_text
    else:
        # Translate to English for canonical embedding
        canonical_text = await translate_for_embedding(
            item.title,
            item.description,
            source_lang=item.language,
            target_lang="en"
        )
        item.canonical_text = canonical_text
        item.original_text = f"{item.title}. {item.description}"

    # Step 3: Generate embedding from canonical text
    embedding = await embedding_service.embed(canonical_text)
    item.embedding = embedding

    # Step 4: Store language metadata
    item.processing_metadata = {
        "original_language": item.language,
        "canonical_language": "en",
        "translation_performed": item.language != "en",
        "embedding_source": "canonical"
    }

    return embedding

async def translate_for_embedding(
    title: str,
    description: str,
    source_lang: str,
    target_lang: str = "en"
) -> str:
    """
    Translate specifically for embedding generation.

    Different from user-facing translation:
    - Optimized for semantic preservation
    - Cached aggressively
    - Uses best available model
    """

    combined_text = f"{title}. {description}"

    # Check cache (longer TTL for embedding translations)
    cache_key = f"embed_translation:{source_lang}:{target_lang}:{hash(combined_text)}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached.decode()

    # Translate with high-quality provider
    translation = await translation_service.translate(
        combined_text,
        source_lang=source_lang,
        target_lang=target_lang,
        quality="high"  # Use best model for embeddings
    )

    # Cache with long TTL (embedding translations don't change)
    await redis_client.setex(cache_key, 2592000, translation)  # 30 days

    return translation
```

**Language Detection with Validation:**

```python
async def detect_language_robust(text: str) -> tuple[str, float]:
    """
    Robust language detection with fallbacks.

    Returns:
        (language_code, confidence)
    """

    # Method 1: fastText (primary)
    try:
        lang, confidence = fasttext_model.predict(text.replace("\n", " "))
        lang = lang[0].replace("__label__", "")
        confidence = float(confidence[0])

        if confidence > 0.7:
            return (lang, confidence)
    except Exception as e:
        logger.warning(f"fastText detection failed: {e}")

    # Method 2: langdetect (fallback)
    try:
        from langdetect import detect_langs
        detections = detect_langs(text)
        if detections:
            lang = detections[0].lang
            confidence = detections[0].prob
            if confidence > 0.7:
                return (lang, confidence)
    except Exception as e:
        logger.warning(f"langdetect failed: {e}")

    # Method 3: Character set heuristics (last resort)
    if any(ord(c) >= 0x4E00 and ord(c) <= 0x9FFF for c in text):
        # CJK characters
        return ("zh", 0.6)  # Lower confidence
    elif any(ord(c) >= 0x0400 and ord(c) <= 0x04FF for c in text):
        # Cyrillic
        return ("ru", 0.6)
    elif any(ord(c) >= 0x0600 and ord(c) <= 0x06FF for c in text):
        # Arabic
        return ("ar", 0.6)

    # Default to English with low confidence
    return ("en", 0.3)
```

**Benefits:**
- ✅ Enables cross-language deduplication (same story in different languages detected)
- ✅ Unified semantic space for clustering
- ✅ More accurate similarity search

**Trade-offs:**
- ⚠️ Translation cost for all non-English content
- ⚠️ Translation quality affects embedding quality
- ⚠️ Increased latency for non-English items

---

### 4.2 Language-Aware Deduplication Thresholds

**Affected Stages:** 5 (Deduplication)

**Problem:** Fixed threshold (0.92) doesn't account for translation quality variance across language pairs.

**Recommendation:** Use language-pair-specific thresholds based on empirical data

**Implementation:**

```python
# Empirically determined thresholds (from back-translation evaluation)
DEDUPLICATION_THRESHOLDS = {
    # High-resource languages (good translation quality)
    ("en", "en"): 0.92,  # Same language, high threshold
    ("es", "en"): 0.88,  # Spanish ↔ English (excellent)
    ("fr", "en"): 0.88,  # French ↔ English (excellent)
    ("de", "en"): 0.87,  # German ↔ English (very good)
    ("pt", "en"): 0.87,  # Portuguese ↔ English (very good)
    ("it", "en"): 0.87,  # Italian ↔ English (very good)

    # Medium-resource languages
    ("ja", "en"): 0.85,  # Japanese ↔ English (good)
    ("ko", "en"): 0.85,  # Korean ↔ English (good)
    ("zh", "en"): 0.84,  # Chinese ↔ English (challenging)
    ("ar", "en"): 0.83,  # Arabic ↔ English (challenging)
    ("ru", "en"): 0.86,  # Russian ↔ English (good)

    # Low-resource languages (conservative threshold)
    ("default", "en"): 0.80  # Unknown languages
}

def get_dedup_threshold(lang1: str, lang2: str) -> float:
    """Get language-pair-specific deduplication threshold"""

    # Normalize to (lang, "en") format
    if lang1 == "en":
        pair = (lang2, "en")
    else:
        pair = (lang1, "en")

    return DEDUPLICATION_THRESHOLDS.get(pair, DEDUPLICATION_THRESHOLDS[("default", "en")])

async def deduplicate_cross_language(items: List[NormalizedItem]) -> List[NormalizedItem]:
    """
    Deduplicate items with language-aware thresholds.
    """

    deduped = []
    seen_embeddings = []  # List of (embedding, item, language)

    for item in items:
        is_duplicate = False

        # Compare with previously seen items
        for prev_embedding, prev_item, prev_lang in seen_embeddings:
            # Calculate similarity
            similarity = cosine_similarity(item.embedding, prev_embedding)

            # Get threshold for this language pair
            threshold = get_dedup_threshold(item.language, prev_lang)

            if similarity >= threshold:
                logger.info(
                    f"Duplicate detected: '{item.title[:50]}' ({item.language}) ≈ "
                    f"'{prev_item.title[:50]}' ({prev_lang}) "
                    f"[similarity={similarity:.3f}, threshold={threshold}]"
                )

                is_duplicate = True

                # Merge items (keep higher engagement)
                if item.engagement_score > prev_item.engagement_score:
                    # Replace previous item with this one
                    deduped.remove(prev_item)
                    deduped.append(item)
                    seen_embeddings.remove((prev_embedding, prev_item, prev_lang))
                    seen_embeddings.append((item.embedding, item, item.language))

                    # Link as cross-language duplicate
                    item.linked_duplicates = prev_item.linked_duplicates + [prev_item.id]

                break

        if not is_duplicate:
            deduped.append(item)
            seen_embeddings.append((item.embedding, item, item.language))

    logger.info(f"Deduplication: {len(items)} → {len(deduped)} items")

    return deduped
```

**Threshold Calibration Tool:**

```python
@app.post("/admin/calibrate-thresholds")
async def calibrate_dedup_thresholds(language_pair: str):
    """
    Calibrate deduplication threshold for a language pair.

    Method: Back-translation test
    1. Take sample of English content
    2. Translate to target language
    3. Translate back to English
    4. Compare embeddings and measure optimal threshold
    """

    source_lang, target_lang = language_pair.split("-")

    # Get sample English content
    sample_texts = await db.fetch(
        """
        SELECT title, description
        FROM topics
        WHERE language = 'en'
        AND LENGTH(title) > 20
        LIMIT 100
        """
    )

    similarities = []

    for row in sample_texts:
        text = f"{row['title']}. {row['description']}"

        # Generate original embedding
        original_embedding = await embedding_service.embed(text)

        # Translate to target language
        translated = await translation_service.translate(text, "en", target_lang)

        # Translate back to English
        back_translated = await translation_service.translate(translated, target_lang, "en")

        # Generate back-translated embedding
        back_embedding = await embedding_service.embed(back_translated)

        # Calculate similarity
        similarity = cosine_similarity(original_embedding, back_embedding)
        similarities.append(similarity)

    # Analyze distribution
    import numpy as np
    mean_sim = np.mean(similarities)
    std_sim = np.std(similarities)
    p5 = np.percentile(similarities, 5)  # 5th percentile (conservative threshold)

    recommended_threshold = p5 - 0.02  # Add small margin

    return {
        "language_pair": language_pair,
        "sample_size": len(similarities),
        "mean_similarity": mean_sim,
        "std_similarity": std_sim,
        "5th_percentile": p5,
        "recommended_threshold": recommended_threshold,
        "current_threshold": DEDUPLICATION_THRESHOLDS.get((source_lang, target_lang))
    }
```

**Benefits:**
- ✅ Reduces false positives (incorrectly marking non-duplicates as duplicates)
- ✅ Reduces false negatives (missing actual duplicates)
- ✅ Adapts to translation quality

**Trade-offs:**
- ⚠️ Requires calibration for each language pair
- ⚠️ Needs periodic re-calibration as translation models improve

---

## 5. EDGE-CASE HANDLING

### 5.1 Outlier Detection & Handling

**Affected Stages:** 6 (Clustering), 7 (Ranking)

**Problem:** HDBSCAN marks low-quality or spam content as outliers (noise), but these items are lost.

**Recommendation:** Create "Uncategorized" trend for outliers, apply quality filtering

**Implementation:**

```python
async def handle_clustering_outliers(
    items: List[NormalizedItem],
    cluster_labels: np.ndarray
) -> tuple[List[NormalizedItem], List[NormalizedItem]]:
    """
    Separate outliers from clustered items and apply quality filtering.

    Returns:
        (clustered_items, quality_outliers)
    """

    clustered_items = []
    outliers = []

    for item, label in zip(items, cluster_labels):
        if label == -1:  # Outlier
            outliers.append(item)
        else:
            item.cluster_label = label
            clustered_items.append(item)

    logger.info(f"Clustering: {len(clustered_items)} clustered, {len(outliers)} outliers")

    # Filter outliers by quality
    quality_outliers = []
    spam_outliers = []

    for item in outliers:
        quality_score = assess_content_quality(item)

        if quality_score > 0.5:  # High-quality outlier
            quality_outliers.append(item)
        else:
            spam_outliers.append(item)
            logger.debug(f"Filtered low-quality outlier: {item.title[:50]}")

    logger.info(f"Outliers: {len(quality_outliers)} quality, {len(spam_outliers)} spam")

    # Emit metrics
    prometheus_client.gauge('clustering_outliers_total').set(len(outliers))
    prometheus_client.gauge('clustering_quality_outliers').set(len(quality_outliers))
    prometheus_client.gauge('clustering_spam_outliers').set(len(spam_outliers))

    return clustered_items, quality_outliers

def assess_content_quality(item: NormalizedItem) -> float:
    """
    Assess content quality using heuristics.

    Returns:
        Quality score (0.0 - 1.0)
    """

    score = 1.0

    # Penalize very short titles
    if len(item.title) < 10:
        score -= 0.3

    # Penalize excessive capitalization (clickbait)
    if sum(1 for c in item.title if c.isupper()) / max(len(item.title), 1) > 0.5:
        score -= 0.2

    # Penalize excessive punctuation
    if sum(1 for c in item.title if c in "!?") > 3:
        score -= 0.2

    # Penalize low engagement
    if item.engagement_score < 10:
        score -= 0.2

    # Penalize common spam keywords
    spam_keywords = ["click here", "you won't believe", "one weird trick", "doctors hate"]
    if any(keyword in item.title.lower() for keyword in spam_keywords):
        score -= 0.5

    # Reward reputable sources
    trusted_sources = ["nytimes", "bbc", "reuters", "apnews", "theguardian"]
    if any(source in item.source for source in trusted_sources):
        score += 0.2

    return max(0.0, min(1.0, score))

# Create "Uncategorized" trend for quality outliers
async def create_uncategorized_trend(outliers: List[NormalizedItem]) -> Trend:
    """Group quality outliers into an 'Uncategorized' trend"""

    if not outliers:
        return None

    # Sort by engagement
    outliers.sort(key=lambda x: x.engagement_score, reverse=True)

    # Take top N outliers
    max_outliers = 20
    top_outliers = outliers[:max_outliers]

    # Create trend
    trend = Trend(
        id=str(uuid.uuid4()),
        title="Uncategorized Trends",
        category="Other",
        state=TrendState.EMERGING,
        topics=top_outliers,
        score=sum(t.engagement_score for t in top_outliers),
        summary="Trending topics that don't fit standard categories",
        metadata={
            "type": "outlier_collection",
            "outlier_count": len(outliers),
            "displayed_count": len(top_outliers)
        }
    )

    return trend
```

**Benefits:**
- ✅ Preserves valuable content that doesn't fit categories
- ✅ Filters spam/low-quality content
- ✅ Provides user visibility into uncategorized trends

**Trade-offs:**
- ⚠️ "Uncategorized" trend may be noisy
- ⚠️ Quality heuristics need tuning

---

### 5.2 PII Detection & Filtering

**Affected Stages:** 2 (Normalization), 11 (Storage)

**Problem:** User-generated content (Reddit, Twitter) may contain personal information (emails, phone numbers, addresses).

**Recommendation:** Detect and redact PII before storage

**Implementation:**

```python
import re
from dataclasses import dataclass

@dataclass
class PIIMatch:
    type: str  # email, phone, ssn, credit_card, ip_address
    value: str
    start: int
    end: int

class PIIDetector:
    """Detect personally identifiable information"""

    # Regex patterns
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    PHONE_PATTERN = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
    SSN_PATTERN = r'\b\d{3}-\d{2}-\d{4}\b'
    CREDIT_CARD_PATTERN = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
    IP_ADDRESS_PATTERN = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'

    def detect(self, text: str) -> List[PIIMatch]:
        """Detect all PII in text"""

        matches = []

        # Email
        for match in re.finditer(self.EMAIL_PATTERN, text):
            matches.append(PIIMatch("email", match.group(), match.start(), match.end()))

        # Phone
        for match in re.finditer(self.PHONE_PATTERN, text):
            matches.append(PIIMatch("phone", match.group(), match.start(), match.end()))

        # SSN
        for match in re.finditer(self.SSN_PATTERN, text):
            matches.append(PIIMatch("ssn", match.group(), match.start(), match.end()))

        # Credit Card
        for match in re.finditer(self.CREDIT_CARD_PATTERN, text):
            matches.append(PIIMatch("credit_card", match.group(), match.start(), match.end()))

        # IP Address
        for match in re.finditer(self.IP_ADDRESS_PATTERN, text):
            # Validate it's actually an IP (not a version number like 1.2.3.4)
            parts = match.group().split('.')
            if all(0 <= int(p) <= 255 for p in parts):
                matches.append(PIIMatch("ip_address", match.group(), match.start(), match.end()))

        return matches

    def redact(self, text: str, replacement: str = "[REDACTED]") -> tuple[str, List[PIIMatch]]:
        """Redact PII from text"""

        matches = self.detect(text)

        if not matches:
            return text, []

        # Sort by position (reverse order to maintain indices)
        matches.sort(key=lambda m: m.start, reverse=True)

        # Redact
        redacted_text = text
        for match in matches:
            redacted_text = (
                redacted_text[:match.start] +
                f"[REDACTED_{match.type.upper()}]" +
                redacted_text[match.end:]
            )

        return redacted_text, matches

pii_detector = PIIDetector()

# Apply in normalization stage
async def normalize_item_with_pii_filter(item: RawItem) -> NormalizedItem:
    """Normalize item and filter PII"""

    # Standard normalization
    normalized = await normalize_item(item)

    # PII detection
    title_redacted, title_pii = pii_detector.redact(normalized.title)
    desc_redacted, desc_pii = pii_detector.redact(normalized.description)

    all_pii = title_pii + desc_pii

    if all_pii:
        logger.warning(
            f"PII detected in item {item.id}: {[m.type for m in all_pii]}",
            extra={"item_id": item.id, "pii_types": [m.type for m in all_pii]}
        )

        # Update text
        normalized.title = title_redacted
        normalized.description = desc_redacted

        # Flag item
        normalized.metadata["pii_detected"] = True
        normalized.metadata["pii_types"] = [m.type for m in all_pii]

        # Emit metric
        prometheus_client.counter('pii_detections_total', labels=[','.join(m.type for m in all_pii)]).inc()

    return normalized
```

**PII Monitoring Dashboard:**

```python
# Track PII detections
pii_detections_total = Counter(
    'pii_detections_total',
    'Total PII detections',
    ['pii_types']  # e.g., "email,phone"
)

# Alert on high PII rate
alerts:
  - name: HighPIIRate
    condition: rate(pii_detections_total[5m]) > 10
    severity: medium
    action: Notify security team
```

**Benefits:**
- ✅ Protects user privacy
- ✅ Reduces legal/compliance risk
- ✅ Prevents accidental PII leakage

**Trade-offs:**
- ⚠️ May redact false positives (e.g., version numbers mistaken for IPs)
- ⚠️ Regex-based detection not 100% accurate

---

### 5.3 Anomaly Detection in Trend Growth

**Affected Stages:** 10 (Trend Detection)

**Problem:** Sudden spikes may indicate bot activity, spam campaigns, or data quality issues.

**Recommendation:** Statistical anomaly detection with alerting

**Implementation:**

```python
from scipy import stats

class TrendAnomalyDetector:
    """Detect anomalous trend growth patterns"""

    async def detect_anomalies(self, trend: Trend, history: List[TrendSnapshot]) -> dict:
        """
        Detect anomalies in trend growth.

        Returns:
            {
                "is_anomaly": bool,
                "anomaly_type": str,  # spike, drop, sudden_viral, bot_pattern
                "confidence": float,
                "explanation": str
            }
        """

        if len(history) < 5:
            return {"is_anomaly": False, "confidence": 0.0}

        # Extract time series
        item_counts = np.array([h.item_count for h in history])
        engagement_rates = np.array([h.total_engagement / max(h.item_count, 1) for h in history])
        timestamps = [h.timestamp for h in history]

        # Test 1: Z-score spike detection
        mean_count = np.mean(item_counts[:-1])  # Exclude current
        std_count = np.std(item_counts[:-1])
        current_count = item_counts[-1]

        if std_count > 0:
            z_score = (current_count - mean_count) / std_count

            if z_score > 3:  # More than 3 std deviations
                return {
                    "is_anomaly": True,
                    "anomaly_type": "spike",
                    "confidence": min(z_score / 5, 1.0),
                    "explanation": f"Item count spike: {current_count} vs avg {mean_count:.1f} (z={z_score:.2f})"
                }

        # Test 2: Engagement rate anomaly
        mean_engagement = np.mean(engagement_rates[:-1])
        current_engagement = engagement_rates[-1]

        if current_engagement < mean_engagement * 0.3:  # Dropped to 30% of avg
            return {
                "is_anomaly": True,
                "anomaly_type": "engagement_drop",
                "confidence": 0.8,
                "explanation": f"Engagement drop: {current_engagement:.1f} vs avg {mean_engagement:.1f}"
            }

        # Test 3: Bot pattern (uniform posting intervals)
        if len(history) >= 10:
            intervals = np.diff([h.timestamp.timestamp() for h in history[-10:]])
            interval_std = np.std(intervals)

            if interval_std < 60:  # Less than 1 minute variation
                return {
                    "is_anomaly": True,
                    "anomaly_type": "bot_pattern",
                    "confidence": 0.9,
                    "explanation": f"Suspicious uniform intervals (std={interval_std:.1f}s)"
                }

        # Test 4: Sudden viral (exponential growth)
        if len(history) >= 5:
            growth_rates = np.diff(item_counts) / item_counts[:-1]
            recent_growth = growth_rates[-1]

            if recent_growth > 2.0:  # 200%+ growth
                return {
                    "is_anomaly": True,
                    "anomaly_type": "sudden_viral",
                    "confidence": 0.7,
                    "explanation": f"Sudden viral growth: {recent_growth*100:.0f}%"
                }

        return {"is_anomaly": False, "confidence": 0.0}

anomaly_detector = TrendAnomalyDetector()

# Apply in trend detection stage
async def detect_trend_state_with_anomaly_check(trend: Trend, history: List[TrendSnapshot]):
    """Detect trend state and check for anomalies"""

    # Standard trend state detection
    state = await detect_trend_state(trend, history)

    # Anomaly detection
    anomaly_result = await anomaly_detector.detect_anomalies(trend, history)

    if anomaly_result["is_anomaly"]:
        logger.warning(
            f"Anomaly detected in trend {trend.id}: {anomaly_result['anomaly_type']}",
            extra={
                "trend_id": trend.id,
                "anomaly": anomaly_result
            }
        )

        # Flag trend
        trend.metadata["anomaly_detected"] = True
        trend.metadata["anomaly_type"] = anomaly_result["anomaly_type"]
        trend.metadata["anomaly_confidence"] = anomaly_result["confidence"]

        # Emit alert for high-confidence anomalies
        if anomaly_result["confidence"] > 0.8:
            await send_anomaly_alert(trend, anomaly_result)

        # Quarantine if suspected bot activity
        if anomaly_result["anomaly_type"] == "bot_pattern":
            trend.state = TrendState.QUARANTINED
            logger.warning(f"Trend {trend.id} quarantined due to bot pattern")

    return state

async def send_anomaly_alert(trend: Trend, anomaly: dict):
    """Send alert for trend anomaly"""

    message = f"""
    🚨 Trend Anomaly Detected

    Trend: {trend.title}
    Type: {anomaly['anomaly_type']}
    Confidence: {anomaly['confidence']:.0%}

    {anomaly['explanation']}

    Review: /admin/trends/{trend.id}
    """

    # Send to monitoring channel (Slack, email, etc.)
    await notification_service.send(
        channel="security",
        message=message,
        severity="warning"
    )
```

**Benefits:**
- ✅ Early detection of spam/bot campaigns
- ✅ Data quality monitoring
- ✅ Reduces false trending topics

**Trade-offs:**
- ⚠️ May flag legitimate viral content
- ⚠️ Requires threshold tuning

---

### 5.4 Partial Failure Recovery

**Affected Stages:** All stages

**Problem:** If 1 out of 8 collection sources fails, should the entire pipeline fail?

**Recommendation:** Graceful degradation with partial success tracking

**Implementation:**

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class PartialResult:
    """Result of a stage that may partially succeed"""

    succeeded: List[any]
    failed: List[tuple[any, Exception]]
    total: int

    @property
    def success_rate(self) -> float:
        return len(self.succeeded) / max(self.total, 1)

    @property
    def is_acceptable(self) -> bool:
        """Check if partial success is acceptable"""
        return self.success_rate >= 0.5  # At least 50% success

async def collect_from_all_sources_partial() -> PartialResult:
    """Collect from all sources, allowing partial failures"""

    sources = plugin_registry.list_sources()
    succeeded = []
    failed = []

    # Collect from all sources concurrently
    tasks = [collect_from_source_safe(source) for source in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for source, result in zip(sources, results):
        if isinstance(result, Exception):
            failed.append((source, result))
            logger.error(f"Collection failed for {source}: {result}")
        else:
            succeeded.append((source, result))
            logger.info(f"Collection succeeded for {source}: {len(result)} items")

    partial_result = PartialResult(
        succeeded=[items for _, items in succeeded],
        failed=failed,
        total=len(sources)
    )

    # Emit metrics
    prometheus_client.gauge('collection_sources_total').set(len(sources))
    prometheus_client.gauge('collection_sources_succeeded').set(len(succeeded))
    prometheus_client.gauge('collection_sources_failed').set(len(failed))

    # Check if acceptable
    if not partial_result.is_acceptable:
        logger.error(
            f"Collection partial failure rate too high: {len(failed)}/{len(sources)} failed"
        )
        # Alert but don't fail entire pipeline
        await send_alert(
            f"Collection degraded: {partial_result.success_rate:.0%} sources succeeded"
        )

    return partial_result

async def collect_from_source_safe(source: str):
    """Collect from source with error handling"""
    try:
        return await collect_from_source(source)
    except Exception as e:
        logger.error(f"Collection error for {source}: {e}")
        # Return empty result instead of propagating exception
        return []

# Pipeline orchestrator with partial failure handling
async def run_pipeline_resilient():
    """Run pipeline with partial failure tolerance"""

    # Stage 1: Collection (allow partial failures)
    collection_result = await collect_from_all_sources_partial()

    if not collection_result.is_acceptable:
        logger.error("Collection stage failed acceptability threshold")
        # Continue anyway with available data

    # Flatten succeeded results
    all_items = [item for items in collection_result.succeeded for item in items]

    logger.info(f"Pipeline starting with {len(all_items)} items from {len(collection_result.succeeded)} sources")

    # Stage 2-11: Continue with available data
    try:
        normalized = await normalize_batch(all_items)
        # ... rest of pipeline

    except Exception as e:
        logger.error(f"Pipeline failed at later stage: {e}")
        # Save partial results before failing
        await save_partial_results(all_items, stage="normalization")
        raise

async def save_partial_results(items: List[any], stage: str):
    """Save partial results for manual recovery"""

    # Save to special "partial_results" table
    await db.execute(
        """
        INSERT INTO partial_results (stage, item_count, items, created_at)
        VALUES ($1, $2, $3, NOW())
        """,
        stage,
        len(items),
        json.dumps([item.to_dict() for item in items])
    )

    logger.info(f"Saved {len(items)} partial results from stage: {stage}")
```

**Admin Recovery Tool:**

```python
@app.get("/admin/partial-results")
async def list_partial_results():
    """View partial results from failed pipelines"""

    results = await db.fetch(
        """
        SELECT id, stage, item_count, created_at
        FROM partial_results
        WHERE created_at > NOW() - INTERVAL '7 days'
        ORDER BY created_at DESC
        """
    )

    return [dict(r) for r in results]

@app.post("/admin/partial-results/{id}/retry")
async def retry_partial_result(id: int):
    """Retry processing from partial result"""

    partial = await db.fetchrow(
        "SELECT stage, items FROM partial_results WHERE id = $1",
        id
    )

    items = json.loads(partial['items'])
    stage = partial['stage']

    # Resume pipeline from failed stage
    if stage == "normalization":
        return await run_pipeline_from_normalization(items)
    elif stage == "embedding":
        return await run_pipeline_from_embedding(items)
    # ... other stages
```

**Benefits:**
- ✅ Pipeline continues with available data
- ✅ Visibility into partial failures
- ✅ Manual recovery options

**Trade-offs:**
- ⚠️ Reduced data completeness
- ⚠️ Complexity in tracking partial states

---

## Summary: Implementation Priority

### P0 (Critical - Implement First)
1. **Retry with exponential backoff** (1.1)
2. **Dead letter queue** (1.3)
3. **Multi-layer embedding cache** (2.1)
4. **Translation-before-embedding** (4.1)
5. **PII detection** (5.2)

### P1 (High - Implement Soon)
1. **Circuit breaker** (1.2)
2. **Idempotency keys** (3.2)
3. **Intelligent translation caching** (2.2)
4. **Language-aware dedup thresholds** (4.2)
5. **Partial failure recovery** (5.4)

### P2 (Medium - Implement Later)
1. **Backpressure management** (1.4)
2. **Graceful degradation** (1.5)
3. **Cache invalidation** (2.3)
4. **Outlier handling** (5.1)
5. **Anomaly detection** (5.3)

### P3 (Nice to Have)
1. **Distributed saga** (3.1) - Only if multi-backend consistency is critical

---

## Next Steps

- [Storage Design](./architecture-storage.md) - Database schemas and retention policies
- [Translation Pipeline](./architecture-translation.md) - Multi-language processing
- [AI Agent Integration](./architecture-ai-agents.md) - Agent interaction patterns
- [Scaling Roadmap](./architecture-scaling.md) - Performance optimization and horizontal scaling
