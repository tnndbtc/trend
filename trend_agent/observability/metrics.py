"""
Prometheus metrics exporters for the Trend Intelligence Platform.

This module defines and exports Prometheus metrics for monitoring:
- API request rates and latencies
- Celery task execution metrics
- Database query performance
- Business metrics (items collected, trends created)
- System resource utilization
"""

import time
import psutil
from typing import Callable, Optional
from functools import wraps

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


# Create a custom registry for this application
metrics_registry = CollectorRegistry()


# ============================================================================
# API Metrics
# ============================================================================

api_request_counter = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status_code"],
    registry=metrics_registry,
)

api_request_duration = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=metrics_registry,
)

api_active_requests = Gauge(
    "api_active_requests",
    "Number of active API requests",
    ["endpoint"],
    registry=metrics_registry,
)

# ============================================================================
# Celery Task Metrics
# ============================================================================

celery_task_counter = Counter(
    "celery_tasks_total",
    "Total number of Celery tasks executed",
    ["task_name", "status"],  # status: success, failure, retry
    registry=metrics_registry,
)

celery_task_duration = Histogram(
    "celery_task_duration_seconds",
    "Celery task execution duration in seconds",
    ["task_name"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800],  # 1s to 30min
    registry=metrics_registry,
)

celery_task_retry_counter = Counter(
    "celery_task_retries_total",
    "Total number of task retries",
    ["task_name"],
    registry=metrics_registry,
)

celery_active_tasks = Gauge(
    "celery_active_tasks",
    "Number of currently executing tasks",
    ["task_name"],
    registry=metrics_registry,
)

celery_queue_length = Gauge(
    "celery_queue_length",
    "Number of tasks waiting in queue",
    ["queue_name"],
    registry=metrics_registry,
)

# ============================================================================
# Database Metrics
# ============================================================================

db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=metrics_registry,
)

db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Current database connection pool size",
    registry=metrics_registry,
)

db_connection_pool_available = Gauge(
    "db_connection_pool_available",
    "Number of available connections in pool",
    registry=metrics_registry,
)

# ============================================================================
# Business Metrics
# ============================================================================

items_collected_counter = Counter(
    "items_collected_total",
    "Total number of items collected from sources",
    ["source"],
    registry=metrics_registry,
)

trends_created_counter = Counter(
    "trends_created_total",
    "Total number of trends created",
    ["category"],
    registry=metrics_registry,
)

topics_created_counter = Counter(
    "topics_created_total",
    "Total number of topics created",
    ["category"],
    registry=metrics_registry,
)

active_trends_gauge = Gauge(
    "active_trends",
    "Number of currently active trends",
    ["state"],  # emerging, viral, sustained, declining
    registry=metrics_registry,
)

# ============================================================================
# System Metrics
# ============================================================================

system_cpu_usage = Gauge(
    "system_cpu_usage_percent",
    "System CPU usage percentage",
    registry=metrics_registry,
)

system_memory_usage = Gauge(
    "system_memory_usage_percent",
    "System memory usage percentage",
    registry=metrics_registry,
)

system_disk_usage = Gauge(
    "system_disk_usage_percent",
    "System disk usage percentage",
    registry=metrics_registry,
)

# ============================================================================
# Application Info
# ============================================================================

app_info = Info(
    "app",
    "Application information",
    registry=metrics_registry,
)

app_info.info({
    "name": "Trend Intelligence Platform",
    "version": "1.0.0",
    "python_version": "3.10+",
})


# ============================================================================
# Decorator Functions for Auto-Instrumentation
# ============================================================================

def track_api_request(endpoint: str):
    """
    Decorator to track API request metrics.

    Args:
        endpoint: API endpoint path

    Example:
        @track_api_request("/api/v1/trends")
        async def get_trends():
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            method = "GET"  # Default, should be extracted from request
            start_time = time.time()

            # Track active requests
            api_active_requests.labels(endpoint=endpoint).inc()

            try:
                result = await func(*args, **kwargs)
                status_code = 200
                return result

            except Exception as e:
                status_code = 500
                raise

            finally:
                # Record duration
                duration = time.time() - start_time
                api_request_duration.labels(
                    method=method,
                    endpoint=endpoint,
                ).observe(duration)

                # Increment counter
                api_request_counter.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                ).inc()

                # Decrement active requests
                api_active_requests.labels(endpoint=endpoint).dec()

        return wrapper
    return decorator


def track_celery_task(task_name: str):
    """
    Decorator to track Celery task metrics.

    Args:
        task_name: Name of the Celery task

    Example:
        @track_celery_task("collect_from_plugin")
        def my_task():
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            # Track active tasks
            celery_active_tasks.labels(task_name=task_name).inc()

            try:
                result = func(*args, **kwargs)
                status = "success"
                return result

            except Exception as e:
                status = "failure"
                raise

            finally:
                # Record duration
                duration = time.time() - start_time
                celery_task_duration.labels(task_name=task_name).observe(duration)

                # Increment counter
                celery_task_counter.labels(
                    task_name=task_name,
                    status=status,
                ).inc()

                # Decrement active tasks
                celery_active_tasks.labels(task_name=task_name).dec()

        return wrapper
    return decorator


def track_db_query(operation: str, table: str):
    """
    Decorator to track database query metrics.

    Args:
        operation: Type of operation (SELECT, INSERT, UPDATE, DELETE)
        table: Table name

    Example:
        @track_db_query("SELECT", "trends")
        async def get_trend():
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                return result

            finally:
                duration = time.time() - start_time
                db_query_duration.labels(
                    operation=operation,
                    table=table,
                ).observe(duration)

        return wrapper
    return decorator


# ============================================================================
# System Metrics Collection
# ============================================================================

def update_system_metrics():
    """
    Update system resource metrics.

    Should be called periodically (e.g., every 15 seconds).
    """
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        system_cpu_usage.set(cpu_percent)

        # Memory usage
        memory = psutil.virtual_memory()
        system_memory_usage.set(memory.percent)

        # Disk usage
        disk = psutil.disk_usage('/')
        system_disk_usage.set(disk.percent)

    except Exception as e:
        # Log error but don't crash
        import logging
        logging.error(f"Error updating system metrics: {e}")


# ============================================================================
# Metrics Endpoint Handler
# ============================================================================

def get_metrics() -> bytes:
    """
    Get Prometheus metrics in text format.

    Returns:
        Metrics data in Prometheus text format

    Example:
        metrics_data = get_metrics()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
    """
    # Update system metrics before exporting
    update_system_metrics()

    return generate_latest(metrics_registry)


# ============================================================================
# Helper Functions
# ============================================================================

def record_item_collected(source: str, count: int = 1):
    """
    Record items collected from a source.

    Args:
        source: Source name (reddit, hackernews, etc.)
        count: Number of items collected
    """
    items_collected_counter.labels(source=source).inc(count)


def record_trend_created(category: str, count: int = 1):
    """
    Record trends created.

    Args:
        category: Trend category
        count: Number of trends created
    """
    trends_created_counter.labels(category=category).inc(count)


def record_topic_created(category: str, count: int = 1):
    """
    Record topics created.

    Args:
        category: Topic category
        count: Number of topics created
    """
    topics_created_counter.labels(category=category).inc(count)


def update_active_trends(state: str, count: int):
    """
    Update active trends gauge.

    Args:
        state: Trend state (emerging, viral, sustained, declining)
        count: Number of trends in this state
    """
    active_trends_gauge.labels(state=state).set(count)


def update_db_pool_metrics(size: int, available: int):
    """
    Update database connection pool metrics.

    Args:
        size: Total pool size
        available: Number of available connections
    """
    db_connection_pool_size.set(size)
    db_connection_pool_available.set(available)


def update_queue_length(queue_name: str, length: int):
    """
    Update Celery queue length.

    Args:
        queue_name: Name of the queue
        length: Number of tasks in queue
    """
    celery_queue_length.labels(queue_name=queue_name).set(length)
