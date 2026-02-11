"""
InfluxDB TimeSeries Storage Implementation.

High-performance time series database for metrics and analytics.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from trend_agent.storage.timeseries.interface import (
    TimeSeriesRepository,
    TimeSeriesPoint,
)

logger = logging.getLogger(__name__)


class InfluxDBTimeSeriesRepository(TimeSeriesRepository):
    """InfluxDB implementation of time series storage."""

    def __init__(
        self,
        url: str = "http://localhost:8086",
        token: Optional[str] = None,
        org: str = "trend-intelligence",
        bucket: str = "trends",
    ):
        """
        Initialize InfluxDB repository.

        Args:
            url: InfluxDB URL
            token: Authentication token
            org: Organization name
            bucket: Bucket name for data storage
        """
        self._url = url
        self._token = token
        self._org = org
        self._bucket = bucket
        self._client = None
        self._write_api = None
        self._query_api = None

    async def connect(self) -> None:
        """Connect to InfluxDB."""
        try:
            from influxdb_client import InfluxDBClient
            from influxdb_client.client.write_api import SYNCHRONOUS

            self._client = InfluxDBClient(
                url=self._url,
                token=self._token,
                org=self._org,
            )

            self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
            self._query_api = self._client.query_api()

            logger.info(f"Connected to InfluxDB at {self._url}")

        except ImportError:
            logger.error("influxdb-client not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            raise

    async def write_point(
        self, measurement: str, point: TimeSeriesPoint
    ) -> None:
        """Write single data point to InfluxDB."""
        from influxdb_client import Point

        p = (
            Point(measurement)
            .time(point.timestamp)
            .field("value", point.value)
        )

        for key, value in point.tags.items():
            p = p.tag(key, value)

        for key, value in point.fields.items():
            p = p.field(key, value)

        self._write_api.write(bucket=self._bucket, org=self._org, record=p)

    async def write_points(
        self, measurement: str, points: List[TimeSeriesPoint]
    ) -> None:
        """Write multiple data points to InfluxDB."""
        from influxdb_client import Point

        records = []
        for point in points:
            p = (
                Point(measurement)
                .time(point.timestamp)
                .field("value", point.value)
            )

            for key, value in point.tags.items():
                p = p.tag(key, value)

            for key, value in point.fields.items():
                p = p.field(key, value)

            records.append(p)

        self._write_api.write(bucket=self._bucket, org=self._org, record=records)

    async def query(
        self,
        measurement: str,
        start_time: datetime,
        end_time: datetime,
        tags: Optional[Dict[str, str]] = None,
    ) -> List[TimeSeriesPoint]:
        """Query time series data from InfluxDB."""
        # Build Flux query
        tag_filter = ""
        if tags:
            tag_filters = [f'r["{k}"] == "{v}"' for k, v in tags.items()]
            tag_filter = " and " + " and ".join(tag_filters)

        query = f'''
        from(bucket: "{self._bucket}")
          |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "{measurement}"{tag_filter})
        '''

        tables = self._query_api.query(query, org=self._org)

        points = []
        for table in tables:
            for record in table.records:
                point = TimeSeriesPoint(
                    timestamp=record.get_time(),
                    value=record.get_value(),
                    tags={k: v for k, v in record.values.items() if k.startswith("tag_")},
                    fields={k: v for k, v in record.values.items() if k.startswith("field_")},
                )
                points.append(point)

        return points

    async def close(self) -> None:
        """Close InfluxDB connection."""
        if self._client:
            self._client.close()
