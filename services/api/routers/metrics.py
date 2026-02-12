"""
Prometheus metrics endpoint for the Trend Intelligence Platform API.

This module exposes Prometheus-compatible metrics for monitoring
API performance, system health, and business metrics.
"""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from trend_agent.observability.metrics import (
    update_system_metrics,
)

router = APIRouter(
    prefix="/metrics",
    tags=["Monitoring"],
)


@router.get("", response_class=Response)
async def prometheus_metrics():
    """
    Expose Prometheus metrics.

    This endpoint returns all collected metrics in Prometheus text format,
    which can be scraped by Prometheus server.

    Returns:
        Response: Metrics in Prometheus text format

    Example metrics exposed:
        - api_requests_total{method="GET",endpoint="/trends",status_code="200"} 42
        - api_request_duration_seconds_bucket{method="GET",endpoint="/trends",le="0.5"} 40
        - celery_tasks_total{task_name="collect_from_plugin_task",status="success"} 15
        - active_trends{state="viral"} 3
        - system_cpu_percent 45.2
        - db_connection_pool_size 10

    Usage:
        Configure Prometheus to scrape this endpoint:

        ```yaml
        scrape_configs:
          - job_name: 'trend-api'
            static_configs:
              - targets: ['api:8000']
            metrics_path: '/metrics'
        ```
    """
    # Update system metrics before returning (CPU, memory, disk)
    update_system_metrics()

    # Generate and return metrics in Prometheus format
    metrics_output = generate_latest()

    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST,
    )


@router.get("/health", response_class=Response)
async def metrics_health():
    """
    Simple health check for the metrics endpoint.

    Returns:
        Response: "OK" if metrics system is functioning
    """
    return Response(content="OK", media_type="text/plain")
