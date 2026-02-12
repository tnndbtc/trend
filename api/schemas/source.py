"""
Pydantic schemas for Crawler Source management API.

These schemas define the request/response formats for the source management endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator
from enum import Enum


class SourceTypeEnum(str, Enum):
    """Available source types."""
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
    DEMO = "demo"


class HealthStatusEnum(str, Enum):
    """Health status options."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"


# ============================================================================
# Request Schemas (for creating/updating sources)
# ============================================================================

class CrawlerSourceCreate(BaseModel):
    """Schema for creating a new crawler source."""

    # Basic Information
    name: str = Field(..., min_length=1, max_length=100, description="Unique name for this source")
    source_type: SourceTypeEnum = Field(..., description="Type of data source")
    description: Optional[str] = Field(None, description="Description of what this source collects")
    url: Optional[str] = Field(None, description="Source URL (for RSS, API endpoints, etc.)")
    enabled: bool = Field(True, description="Enable/disable collection from this source")

    # Scheduling Configuration
    schedule: str = Field(
        "0 */4 * * *",
        description="Cron expression for collection schedule"
    )
    collection_interval_hours: int = Field(
        4,
        ge=1,
        le=168,
        description="Collection interval in hours (1-168)"
    )

    # Rate Limiting & Timeouts
    rate_limit: Optional[int] = Field(
        None,
        ge=1,
        description="Maximum requests per hour (null = unlimited)"
    )
    timeout_seconds: int = Field(
        30,
        ge=1,
        le=300,
        description="Timeout for requests in seconds"
    )
    retry_count: int = Field(
        3,
        ge=0,
        le=10,
        description="Number of retries on failure"
    )
    backoff_multiplier: float = Field(
        2.0,
        ge=1.0,
        le=10.0,
        description="Exponential backoff multiplier for retries"
    )

    # Authentication
    api_key: Optional[str] = Field(
        None,
        description="API key for authenticated sources (will be encrypted)"
    )
    oauth_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="OAuth configuration (client_id, client_secret, tokens, etc.)"
    )
    custom_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom HTTP headers for requests"
    )

    # Content Filtering
    category_filters: List[str] = Field(
        default_factory=list,
        description="List of allowed categories (empty = all categories)"
    )
    keyword_filters: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Keyword filters: {'include': ['keyword1'], 'exclude': ['keyword2']}"
    )
    language: str = Field(
        "en",
        min_length=2,
        max_length=10,
        description="Target language code (ISO 639-1)"
    )
    content_filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Advanced content filters (min_length, max_length, etc.)"
    )

    # Custom Plugin Code
    plugin_code: Optional[str] = Field(
        None,
        description="Python code for custom collector plugin"
    )

    # Additional Configuration
    config_json: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional source-specific configuration"
    )

    # Metadata
    created_by: Optional[str] = Field(
        None,
        description="User who created this source"
    )

    @field_validator('schedule')
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Basic cron expression validation."""
        parts = v.split()
        if len(parts) not in [5, 6]:
            raise ValueError('Invalid cron expression. Expected 5 or 6 parts.')
        return v

    @field_validator('url')
    @classmethod
    def validate_url_for_source_type(cls, v: Optional[str], info) -> Optional[str]:
        """Validate URL is provided for certain source types."""
        # Note: We can't access source_type here directly in v2
        # This validation will be done in the endpoint
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "TechCrunch RSS",
                "source_type": "rss",
                "description": "TechCrunch technology news feed",
                "url": "https://techcrunch.com/feed/",
                "enabled": True,
                "schedule": "0 */2 * * *",
                "collection_interval_hours": 2,
                "rate_limit": 60,
                "timeout_seconds": 30,
                "language": "en",
                "category_filters": ["Technology", "Business"],
            }
        }


class CrawlerSourceUpdate(BaseModel):
    """Schema for updating an existing crawler source."""

    # All fields are optional for partial updates
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    source_type: Optional[SourceTypeEnum] = None
    description: Optional[str] = None
    url: Optional[str] = None
    enabled: Optional[bool] = None
    schedule: Optional[str] = None
    collection_interval_hours: Optional[int] = Field(None, ge=1, le=168)
    rate_limit: Optional[int] = Field(None, ge=1)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    retry_count: Optional[int] = Field(None, ge=0, le=10)
    backoff_multiplier: Optional[float] = Field(None, ge=1.0, le=10.0)
    api_key: Optional[str] = None
    oauth_config: Optional[Dict[str, Any]] = None
    custom_headers: Optional[Dict[str, str]] = None
    category_filters: Optional[List[str]] = None
    keyword_filters: Optional[Dict[str, List[str]]] = None
    language: Optional[str] = Field(None, min_length=2, max_length=10)
    content_filters: Optional[Dict[str, Any]] = None
    plugin_code: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": False,
                "schedule": "0 */6 * * *",
                "description": "Updated description",
            }
        }


# ============================================================================
# Response Schemas (for returning source data)
# ============================================================================

class CrawlerSourceResponse(BaseModel):
    """Schema for crawler source response."""

    id: int = Field(..., description="Source ID")
    name: str
    source_type: str
    description: str
    url: str
    enabled: bool

    # Scheduling
    schedule: str
    collection_interval_hours: int

    # Rate Limiting & Timeouts
    rate_limit: Optional[int]
    timeout_seconds: int
    retry_count: int
    backoff_multiplier: float

    # Authentication (API key is masked)
    api_key_set: bool = Field(..., description="Whether API key is configured")
    oauth_config: Dict[str, Any]
    custom_headers: Dict[str, str]

    # Content Filtering
    category_filters: List[str]
    keyword_filters: Dict[str, List[str]]
    language: str
    content_filters: Dict[str, Any]

    # Custom Plugin
    has_custom_code: bool = Field(..., description="Whether custom plugin code is provided")

    # Configuration
    config_json: Dict[str, Any]

    # Health & Monitoring
    health_status: str
    last_collection: Optional[datetime]
    last_error: str
    consecutive_failures: int
    total_collections: int
    successful_collections: int
    total_items_collected: int
    success_rate: float = Field(..., description="Success rate as percentage")

    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: str

    class Config:
        from_attributes = True  # Pydantic v2
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "TechCrunch RSS",
                "source_type": "rss",
                "description": "TechCrunch technology news feed",
                "url": "https://techcrunch.com/feed/",
                "enabled": True,
                "schedule": "0 */2 * * *",
                "collection_interval_hours": 2,
                "rate_limit": 60,
                "timeout_seconds": 30,
                "retry_count": 3,
                "backoff_multiplier": 2.0,
                "api_key_set": False,
                "oauth_config": {},
                "custom_headers": {},
                "category_filters": ["Technology"],
                "keyword_filters": {},
                "language": "en",
                "content_filters": {},
                "has_custom_code": False,
                "config_json": {},
                "health_status": "healthy",
                "last_collection": "2024-02-12T10:30:00Z",
                "last_error": "",
                "consecutive_failures": 0,
                "total_collections": 100,
                "successful_collections": 98,
                "total_items_collected": 5000,
                "success_rate": 98.0,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-02-12T10:30:00Z",
                "created_by": "admin",
            }
        }


class CrawlerSourceList(BaseModel):
    """Schema for paginated list of crawler sources."""

    sources: List[CrawlerSourceResponse]
    total: int = Field(..., description="Total number of sources")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        json_schema_extra = {
            "example": {
                "sources": [],
                "total": 15,
                "page": 1,
                "page_size": 10,
                "total_pages": 2,
            }
        }


# ============================================================================
# Action Schemas (for testing, triggering collection, etc.)
# ============================================================================

class SourceTestRequest(BaseModel):
    """Schema for source connection test request."""

    source_id: int = Field(..., description="ID of source to test")


class SourceTestResponse(BaseModel):
    """Schema for source connection test response."""

    success: bool = Field(..., description="Whether test was successful")
    message: str = Field(..., description="Test result message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully connected to RSS feed",
                "timestamp": "2024-02-12T10:30:00Z",
            }
        }


class CollectionTriggerRequest(BaseModel):
    """Schema for triggering manual collection."""

    source_ids: List[int] = Field(..., description="List of source IDs to collect from")
    force: bool = Field(False, description="Force collection even if recently collected")


class CollectionTriggerResponse(BaseModel):
    """Schema for collection trigger response."""

    triggered: List[int] = Field(..., description="Source IDs that were triggered")
    skipped: List[int] = Field(..., description="Source IDs that were skipped")
    errors: Dict[int, str] = Field(..., description="Errors by source ID")
    message: str = Field(..., description="Overall status message")

    class Config:
        json_schema_extra = {
            "example": {
                "triggered": [1, 2, 3],
                "skipped": [],
                "errors": {},
                "message": "Successfully triggered collection for 3 sources",
            }
        }


class SourceValidationRequest(BaseModel):
    """Schema for validating source configuration without saving."""

    source_data: CrawlerSourceCreate


class SourceValidationResponse(BaseModel):
    """Schema for source validation response."""

    valid: bool = Field(..., description="Whether configuration is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "errors": [],
                "warnings": ["Rate limit not set - unlimited requests allowed"],
            }
        }


# ============================================================================
# Health & Metrics Schemas
# ============================================================================

class SourceHealthMetrics(BaseModel):
    """Schema for detailed source health metrics."""

    source_id: int
    source_name: str
    health_status: HealthStatusEnum
    uptime_percentage: float = Field(..., description="Uptime percentage over last 30 days")
    avg_collection_time_seconds: float = Field(..., description="Average collection duration")
    items_per_collection: float = Field(..., description="Average items collected per run")
    last_24h_collections: int = Field(..., description="Collections in last 24 hours")
    error_rate_24h: float = Field(..., description="Error rate in last 24 hours")
    current_health_score: float = Field(..., ge=0, le=100, description="Overall health score (0-100)")

    class Config:
        json_schema_extra = {
            "example": {
                "source_id": 1,
                "source_name": "TechCrunch RSS",
                "health_status": "healthy",
                "uptime_percentage": 98.5,
                "avg_collection_time_seconds": 3.2,
                "items_per_collection": 15.5,
                "last_24h_collections": 12,
                "error_rate_24h": 0.0,
                "current_health_score": 95.0,
            }
        }


# ============================================================================
# Filter Schemas
# ============================================================================

class SourceFilter(BaseModel):
    """Schema for filtering sources in list queries."""

    enabled: Optional[bool] = None
    source_type: Optional[SourceTypeEnum] = None
    health_status: Optional[HealthStatusEnum] = None
    min_success_rate: Optional[float] = Field(None, ge=0, le=100)
    search: Optional[str] = Field(None, description="Search in name and description")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")
    sort_by: str = Field("name", description="Field to sort by")
    sort_order: str = Field("asc", description="Sort order (asc/desc)")

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "source_type": "rss",
                "health_status": "healthy",
                "min_success_rate": 90.0,
                "search": "tech",
                "page": 1,
                "page_size": 10,
                "sort_by": "name",
                "sort_order": "asc",
            }
        }
