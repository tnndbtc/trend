"""
Shared type definitions for the Trend Intelligence Platform.

This module contains type definitions used across all layers of the application.
These types serve as the contract between different components and enable
type-safe development across parallel work streams.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


# ============================================================================
# Enums
# ============================================================================


class TrendState(str, Enum):
    """Lifecycle state of a trend."""

    EMERGING = "emerging"  # New trend just detected
    VIRAL = "viral"  # Rapidly growing engagement
    SUSTAINED = "sustained"  # Stable high engagement
    DECLINING = "declining"  # Decreasing engagement
    DEAD = "dead"  # No longer active


class SourceType(str, Enum):
    """Type of data source."""

    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    GOOGLE_NEWS = "google_news"
    BBC = "bbc"
    REUTERS = "reuters"
    AP_NEWS = "ap_news"
    AL_JAZEERA = "al_jazeera"
    GUARDIAN = "guardian"
    RSS = "rss"
    CUSTOM = "custom"


class Category(str, Enum):
    """Content category classification."""

    TECHNOLOGY = "Technology"
    POLITICS = "Politics"
    ENTERTAINMENT = "Entertainment"
    SPORTS = "Sports"
    SCIENCE = "Science"
    BUSINESS = "Business"
    HEALTH = "Health"
    WORLD_NEWS = "World News"
    ENVIRONMENT = "Environment"
    EDUCATION = "Education"
    OTHER = "Other"


class ProcessingStatus(str, Enum):
    """Status of processing pipeline."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============================================================================
# Core Data Models
# ============================================================================


class Metrics(BaseModel):
    """Engagement metrics for content."""

    upvotes: int = 0
    downvotes: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0
    score: float = 0.0  # Composite engagement score

    class Config:
        frozen = True


class RawItem(BaseModel):
    """Raw item from a data source before processing."""

    source: SourceType
    source_id: str  # ID from the source system
    url: HttpUrl
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    published_at: datetime
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    metrics: Metrics = Field(default_factory=Metrics)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = False


class ProcessedItem(BaseModel):
    """Item after normalization and initial processing."""

    id: Optional[UUID] = None
    source: SourceType
    source_id: str
    url: HttpUrl
    title: str
    title_normalized: str  # Cleaned title
    description: Optional[str] = None
    content: Optional[str] = None
    content_normalized: Optional[str] = None  # Cleaned content
    language: str = "en"  # ISO 639-1 code
    author: Optional[str] = None
    published_at: datetime
    collected_at: datetime
    metrics: Metrics
    category: Optional[Category] = None
    embedding: Optional[List[float]] = None  # Vector embedding
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = False


class Topic(BaseModel):
    """A topic is a cluster of related items."""

    id: Optional[UUID] = None
    title: str
    summary: str
    category: Category
    sources: List[SourceType]
    item_count: int
    total_engagement: Metrics
    first_seen: datetime
    last_updated: datetime
    language: str = "en"
    keywords: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = False


class Trend(BaseModel):
    """A trend is a ranked, analyzed topic with state tracking."""

    id: Optional[UUID] = None
    topic_id: UUID
    rank: int
    title: str
    summary: str
    key_points: List[str] = Field(default_factory=list)
    category: Category
    state: TrendState = TrendState.EMERGING
    score: float  # Composite ranking score
    sources: List[SourceType]
    item_count: int
    total_engagement: Metrics
    velocity: float = 0.0  # Rate of engagement growth
    first_seen: datetime
    last_updated: datetime
    peak_engagement_at: Optional[datetime] = None
    language: str = "en"
    keywords: List[str] = Field(default_factory=list)
    related_trend_ids: List[UUID] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = False


# ============================================================================
# Search and Filter Models
# ============================================================================


class TrendFilter(BaseModel):
    """Filter criteria for trend search."""

    category: Optional[Category] = None
    sources: Optional[List[SourceType]] = None
    state: Optional[TrendState] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    language: Optional[str] = None
    keywords: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = 100
    offset: int = 0

    class Config:
        frozen = True


class VectorMatch(BaseModel):
    """Result from vector similarity search."""

    id: str
    score: float  # Similarity score (0-1)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class SemanticSearchRequest(BaseModel):
    """Request for semantic search."""

    query: str
    filters: Optional[TrendFilter] = None
    limit: int = 20
    min_similarity: float = 0.7

    class Config:
        frozen = True


# ============================================================================
# Pipeline Models
# ============================================================================


class PipelineConfig(BaseModel):
    """Configuration for processing pipeline."""

    deduplication_threshold: float = 0.92
    clustering_distance_threshold: float = 0.3
    min_cluster_size: int = 2
    max_trends_per_category: int = 10
    source_diversity_enabled: bool = True
    max_percentage_per_source: float = 0.20

    class Config:
        frozen = True


class PipelineResult(BaseModel):
    """Result of pipeline execution."""

    status: ProcessingStatus
    items_collected: int
    items_processed: int
    items_deduplicated: int
    topics_created: int
    trends_created: int
    duration_seconds: float
    errors: List[str] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = False


# ============================================================================
# Plugin Models
# ============================================================================


class PluginMetadata(BaseModel):
    """Metadata for a collector plugin."""

    name: str
    version: str
    author: str
    description: str
    source_type: SourceType
    schedule: str  # Cron expression
    enabled: bool = True
    rate_limit: Optional[int] = None  # Max requests per hour
    timeout_seconds: int = 30
    retry_count: int = 3

    class Config:
        frozen = True


class PluginHealth(BaseModel):
    """Health status of a plugin."""

    name: str
    is_healthy: bool
    last_run_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    total_runs: int = 0
    success_rate: float = 0.0

    class Config:
        frozen = False


# ============================================================================
# API Models
# ============================================================================


class APIResponse(BaseModel):
    """Standard API response wrapper."""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class PaginatedResponse(BaseModel):
    """Paginated API response."""

    items: List[Any]
    total: int
    limit: int
    offset: int
    has_more: bool

    class Config:
        frozen = True


# ============================================================================
# Configuration Models
# ============================================================================


class DatabaseConfig(BaseModel):
    """Database configuration."""

    host: str = "localhost"
    port: int = 5432
    database: str = "trends"
    username: str
    password: str
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

    class Config:
        frozen = True


class VectorDBConfig(BaseModel):
    """Vector database configuration."""

    host: str = "localhost"
    port: int = 6333
    collection_name: str = "trend_embeddings"
    vector_size: int = 1536
    distance_metric: str = "cosine"

    class Config:
        frozen = True


class CacheConfig(BaseModel):
    """Cache configuration."""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ttl_seconds: int = 3600

    class Config:
        frozen = True


class MessageQueueConfig(BaseModel):
    """Message queue configuration."""

    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    vhost: str = "/"

    class Config:
        frozen = True
