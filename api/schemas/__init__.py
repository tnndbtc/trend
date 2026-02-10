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

__all__ = [
    "TrendResponse",
    "TrendListResponse",
    "TrendSearchRequest",
    "TopicResponse",
    "TopicListResponse",
    "ErrorResponse",
    "SuccessResponse",
    "PaginationParams",
    "PaginatedResponse",
]
