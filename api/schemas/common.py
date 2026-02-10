"""
Common API schemas used across endpoints.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field


T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: str = Field(..., description="Error code")
    timestamp: str = Field(..., description="ISO 8601 timestamp")

    class Config:
        schema_extra = {
            "example": {
                "error": "Resource not found",
                "detail": "Trend with ID abc123 does not exist",
                "code": "NOT_FOUND",
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }


class SuccessResponse(BaseModel):
    """Standard success response."""

    success: bool = Field(True, description="Operation success status")
    message: Optional[str] = Field(None, description="Success message")
    data: Optional[Any] = Field(None, description="Response data")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"id": "abc123"},
            }
        }


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    limit: int = Field(20, ge=1, le=100, description="Number of items per page")
    offset: int = Field(0, ge=0, description="Number of items to skip")

    class Config:
        schema_extra = {"example": {"limit": 20, "offset": 0}}


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., ge=0, description="Total number of items")
    limit: int = Field(..., ge=1, description="Items per page")
    offset: int = Field(..., ge=0, description="Offset from start")
    has_more: bool = Field(..., description="Whether more items are available")

    class Config:
        schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "limit": 20,
                "offset": 0,
                "has_more": True,
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    services: Dict[str, bool] = Field(
        ..., description="Status of dependent services"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "services": {
                    "database": True,
                    "vector_db": True,
                    "cache": True,
                    "message_queue": True,
                },
            }
        }


class FilterParams(BaseModel):
    """Common filter parameters."""

    category: Optional[str] = Field(None, description="Filter by category")
    source: Optional[str] = Field(None, description="Filter by source")
    language: Optional[str] = Field(None, description="Filter by language (ISO 639-1)")
    date_from: Optional[str] = Field(None, description="Filter from date (ISO 8601)")
    date_to: Optional[str] = Field(None, description="Filter to date (ISO 8601)")
    keywords: Optional[List[str]] = Field(None, description="Filter by keywords")

    class Config:
        schema_extra = {
            "example": {
                "category": "Technology",
                "source": "reddit",
                "language": "en",
                "date_from": "2024-01-01T00:00:00Z",
                "date_to": "2024-01-15T23:59:59Z",
                "keywords": ["AI", "machine learning"],
            }
        }
