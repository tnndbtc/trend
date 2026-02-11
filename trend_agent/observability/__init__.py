"""
Observability module for monitoring, metrics, and logging.

This module provides comprehensive observability for the Trend Intelligence Platform:
- Prometheus metrics exporters
- Structured logging
- Distributed tracing (OpenTelemetry)
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
    get_metrics,
    update_system_metrics,
)

from trend_agent.observability.logging import (
    setup_logging,
    get_logger,
    log_context,
    audit_logger,
)

from trend_agent.observability.tracing import (
    setup_tracing,
    get_tracer,
    shutdown_tracing,
    trace,
    add_trace_event,
    set_trace_attribute,
    record_trace_exception,
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
    "get_metrics",
    "update_system_metrics",
    # Logging
    "setup_logging",
    "get_logger",
    "log_context",
    "audit_logger",
    # Tracing
    "setup_tracing",
    "get_tracer",
    "shutdown_tracing",
    "trace",
    "add_trace_event",
    "set_trace_attribute",
    "record_trace_exception",
]
