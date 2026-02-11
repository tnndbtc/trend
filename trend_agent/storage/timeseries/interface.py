"""
TimeSeries Database Interface.

For storing historical trend metrics, analytics, and time-series data.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID


class TimeSeriesPoint:
    """Single time series data point."""

    def __init__(
        self,
        timestamp: datetime,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        fields: Optional[Dict[str, Any]] = None,
    ):
        self.timestamp = timestamp
        self.value = value
        self.tags = tags or {}
        self.fields = fields or {}


class TimeSeriesRepository(ABC):
    """Abstract interface for time series storage."""

    @abstractmethod
    async def write_point(
        self,
        measurement: str,
        point: TimeSeriesPoint,
    ) -> None:
        """Write a single data point."""
        pass

    @abstractmethod
    async def write_points(
        self,
        measurement: str,
        points: List[TimeSeriesPoint],
    ) -> None:
        """Write multiple data points."""
        pass

    @abstractmethod
    async def query(
        self,
        measurement: str,
        start_time: datetime,
        end_time: datetime,
        tags: Optional[Dict[str, str]] = None,
    ) -> List[TimeSeriesPoint]:
        """Query time series data."""
        pass
