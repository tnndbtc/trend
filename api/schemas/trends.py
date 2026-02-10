"""
API schemas for trends and topics.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


class MetricsResponse(BaseModel):
    """Engagement metrics response."""

    upvotes: int = Field(0, ge=0)
    downvotes: int = Field(0, ge=0)
    comments: int = Field(0, ge=0)
    shares: int = Field(0, ge=0)
    views: int = Field(0, ge=0)
    score: float = Field(0.0, ge=0.0)

    class Config:
        schema_extra = {
            "example": {
                "upvotes": 1500,
                "downvotes": 50,
                "comments": 300,
                "shares": 200,
                "views": 50000,
                "score": 1450.0,
            }
        }


class TopicResponse(BaseModel):
    """Topic response model."""

    id: UUID = Field(..., description="Topic ID")
    title: str = Field(..., description="Topic title")
    summary: str = Field(..., description="Topic summary")
    category: str = Field(..., description="Topic category")
    sources: List[str] = Field(..., description="Data sources")
    item_count: int = Field(..., ge=1, description="Number of items in topic")
    total_engagement: MetricsResponse = Field(..., description="Total engagement metrics")
    first_seen: datetime = Field(..., description="First seen timestamp")
    last_updated: datetime = Field(..., description="Last update timestamp")
    language: str = Field("en", description="Language code (ISO 639-1)")
    keywords: List[str] = Field(default_factory=list, description="Topic keywords")

    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "New AI Model Released",
                "summary": "A groundbreaking new AI model has been released...",
                "category": "Technology",
                "sources": ["reddit", "hackernews"],
                "item_count": 15,
                "total_engagement": {
                    "upvotes": 1500,
                    "comments": 300,
                    "score": 1450.0,
                },
                "first_seen": "2024-01-15T10:00:00Z",
                "last_updated": "2024-01-15T14:30:00Z",
                "language": "en",
                "keywords": ["AI", "machine learning", "model"],
            }
        }


class TrendResponse(BaseModel):
    """Trend response model."""

    id: UUID = Field(..., description="Trend ID")
    topic_id: UUID = Field(..., description="Associated topic ID")
    rank: int = Field(..., ge=1, description="Trend rank")
    title: str = Field(..., description="Trend title")
    summary: str = Field(..., description="Trend summary")
    key_points: List[str] = Field(default_factory=list, description="Key points")
    category: str = Field(..., description="Trend category")
    state: str = Field(..., description="Trend state (emerging, viral, sustained, declining)")
    score: float = Field(..., ge=0.0, description="Ranking score")
    sources: List[str] = Field(..., description="Data sources")
    item_count: int = Field(..., ge=1, description="Number of items")
    total_engagement: MetricsResponse = Field(..., description="Total engagement metrics")
    velocity: float = Field(0.0, description="Engagement velocity")
    first_seen: datetime = Field(..., description="First seen timestamp")
    last_updated: datetime = Field(..., description="Last update timestamp")
    peak_engagement_at: Optional[datetime] = Field(None, description="Peak engagement timestamp")
    language: str = Field("en", description="Language code (ISO 639-1)")
    keywords: List[str] = Field(default_factory=list, description="Trend keywords")
    related_trend_ids: List[UUID] = Field(default_factory=list, description="Related trend IDs")

    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "topic_id": "660e8400-e29b-41d4-a716-446655440000",
                "rank": 1,
                "title": "New AI Model Released",
                "summary": "A groundbreaking new AI model has been released...",
                "key_points": [
                    "Model shows 20% improvement",
                    "Open source release",
                    "Supports 100+ languages",
                ],
                "category": "Technology",
                "state": "viral",
                "score": 95.5,
                "sources": ["reddit", "hackernews", "twitter"],
                "item_count": 25,
                "total_engagement": {
                    "upvotes": 5000,
                    "comments": 1200,
                    "views": 150000,
                    "score": 4800.0,
                },
                "velocity": 12.5,
                "first_seen": "2024-01-15T10:00:00Z",
                "last_updated": "2024-01-15T14:30:00Z",
                "peak_engagement_at": "2024-01-15T12:00:00Z",
                "language": "en",
                "keywords": ["AI", "machine learning", "open source"],
                "related_trend_ids": [],
            }
        }


class TrendListResponse(BaseModel):
    """List of trends with pagination."""

    trends: List[TrendResponse] = Field(..., description="List of trends")
    total: int = Field(..., ge=0, description="Total number of trends")
    limit: int = Field(..., ge=1, description="Items per page")
    offset: int = Field(..., ge=0, description="Offset from start")
    has_more: bool = Field(..., description="Whether more trends available")


class TopicListResponse(BaseModel):
    """List of topics with pagination."""

    topics: List[TopicResponse] = Field(..., description="List of topics")
    total: int = Field(..., ge=0, description="Total number of topics")
    limit: int = Field(..., ge=1, description="Items per page")
    offset: int = Field(..., ge=0, description="Offset from start")
    has_more: bool = Field(..., description="Whether more topics available")


class TrendSearchRequest(BaseModel):
    """Trend search request."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    category: Optional[str] = Field(None, description="Filter by category")
    sources: Optional[List[str]] = Field(None, description="Filter by sources")
    state: Optional[str] = Field(None, description="Filter by trend state")
    language: Optional[str] = Field(None, description="Filter by language (ISO 639-1)")
    min_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Minimum score")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    limit: int = Field(20, ge=1, le=100, description="Number of results")
    min_similarity: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")

    class Config:
        schema_extra = {
            "example": {
                "query": "artificial intelligence breakthroughs",
                "category": "Technology",
                "sources": ["reddit", "hackernews"],
                "state": "viral",
                "language": "en",
                "min_score": 50.0,
                "limit": 20,
                "min_similarity": 0.7,
            }
        }


class SimilarTrendsRequest(BaseModel):
    """Request for finding similar trends."""

    trend_id: UUID = Field(..., description="Trend ID to find similar trends for")
    limit: int = Field(10, ge=1, le=50, description="Number of results")
    min_similarity: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")

    class Config:
        schema_extra = {
            "example": {
                "trend_id": "550e8400-e29b-41d4-a716-446655440000",
                "limit": 10,
                "min_similarity": 0.7,
            }
        }


class TrendStatsResponse(BaseModel):
    """Trend statistics response."""

    total_trends: int = Field(..., ge=0, description="Total number of trends")
    total_topics: int = Field(..., ge=0, description="Total number of topics")
    total_items: int = Field(..., ge=0, description="Total number of items")
    trends_by_category: dict = Field(..., description="Trends count by category")
    trends_by_state: dict = Field(..., description="Trends count by state")
    trends_by_source: dict = Field(..., description="Trends count by source")
    average_engagement: MetricsResponse = Field(..., description="Average engagement metrics")

    class Config:
        schema_extra = {
            "example": {
                "total_trends": 150,
                "total_topics": 300,
                "total_items": 5000,
                "trends_by_category": {
                    "Technology": 45,
                    "Politics": 30,
                    "Entertainment": 25,
                },
                "trends_by_state": {
                    "emerging": 50,
                    "viral": 30,
                    "sustained": 40,
                    "declining": 30,
                },
                "trends_by_source": {
                    "reddit": 60,
                    "hackernews": 40,
                    "twitter": 50,
                },
                "average_engagement": {
                    "upvotes": 500,
                    "comments": 100,
                    "views": 10000,
                    "score": 450.0,
                },
            }
        }
