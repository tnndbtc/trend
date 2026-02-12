"""
API schemas for request and response models.

This module defines Pydantic models used for API serialization.
"""

from api.schemas.trends import (
    TrendResponse,
    TrendListResponse,
    TrendSearchRequest,
    TopicResponse,
    TopicListResponse,
)
from api.schemas.common import (
    ErrorResponse,
    SuccessResponse,
    PaginationParams,
    PaginatedResponse,
)
from api.schemas.source import (
    SourceTypeEnum,
    HealthStatusEnum,
    CrawlerSourceCreate,
    CrawlerSourceUpdate,
    CrawlerSourceResponse,
    CrawlerSourceList,
    SourceTestRequest,
    SourceTestResponse,
    CollectionTriggerRequest,
    CollectionTriggerResponse,
    SourceValidationRequest,
    SourceValidationResponse,
    SourceHealthMetrics,
    SourceFilter,
)

__all__ = [
    # Trends
    "TrendResponse",
    "TrendListResponse",
    "TrendSearchRequest",
    "TopicResponse",
    "TopicListResponse",
    # Common
    "ErrorResponse",
    "SuccessResponse",
    "PaginationParams",
    "PaginatedResponse",
    # Sources
    "SourceTypeEnum",
    "HealthStatusEnum",
    "CrawlerSourceCreate",
    "CrawlerSourceUpdate",
    "CrawlerSourceResponse",
    "CrawlerSourceList",
    "SourceTestRequest",
    "SourceTestResponse",
    "CollectionTriggerRequest",
    "CollectionTriggerResponse",
    "SourceValidationRequest",
    "SourceValidationResponse",
    "SourceHealthMetrics",
    "SourceFilter",
]
