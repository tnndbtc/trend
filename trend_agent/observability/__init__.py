"""
Observability module for monitoring, metrics, and logging.

This module provides comprehensive observability for the Trend Intelligence Platform:
- Prometheus metrics exporters
- Structured logging
- Health checks
- Performance monitoring
"""

from trend_agent.observability.metrics import (
    metrics_registry,
    api_request_counter,
    api_request_duration,
    celery_task_counter,
    celery_task_duration,
    db_query_duration,
    items_collected_counter,
    trends_created_counter,
)

from trend_agent.observability.logging import (
    setup_logging,
    get_logger,
    log_context,
)

__all__ = [
    # Metrics
    "metrics_registry",
    "api_request_counter",
    "api_request_duration",
    "celery_task_counter",
    "celery_task_duration",
    "db_query_duration",
    "items_collected_counter",
    "trends_created_counter",
    # Logging
    "setup_logging",
    "get_logger",
    "log_context",
]
