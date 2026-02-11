"""
Prometheus metrics HTTP server for Celery workers.

This module provides an HTTP server that exposes Prometheus metrics
from Celery workers on port 9091, allowing Prometheus to scrape
task execution metrics.
"""

import logging
import threading
import time
from prometheus_client import start_http_server

from trend_agent.observability.metrics import update_system_metrics

logger = logging.getLogger(__name__)

# Global flag to track if server has been started
_metrics_server_started = False
_metrics_lock = threading.Lock()


def start_metrics_exporter(port: int = 9091, update_interval: int = 15):
    """
    Start Prometheus metrics HTTP server for Celery worker.

    This function should be called when the Celery worker starts.
    It creates an HTTP server on the specified port that exposes
    all Prometheus metrics, including Celery task metrics and
    system metrics.

    Args:
        port: Port to expose metrics on (default: 9091)
        update_interval: How often to update system metrics in seconds (default: 15)

    Example:
        # In Celery worker startup (e.g., celery worker_init signal)
        from trend_agent.tasks.prometheus_exporter import start_metrics_exporter
        start_metrics_exporter(port=9091)
    """
    global _metrics_server_started

    with _metrics_lock:
        if _metrics_server_started:
            logger.warning(f"Metrics server already started on port {port}")
            return

        try:
            # Start Prometheus HTTP server
            start_http_server(port)
            logger.info(f"✅ Prometheus metrics server started on port {port}")
            _metrics_server_started = True

            # Start background thread to update system metrics
            _start_system_metrics_updater(update_interval)

        except OSError as e:
            if "Address already in use" in str(e):
                logger.warning(f"Port {port} already in use - metrics server may already be running")
                _metrics_server_started = True
            else:
                logger.error(f"Failed to start metrics server: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error starting metrics server: {e}")
            raise


def _start_system_metrics_updater(interval: int = 15):
    """
    Start background thread to periodically update system metrics.

    This thread updates CPU, memory, and disk usage metrics at regular intervals.

    Args:
        interval: Update interval in seconds
    """
    def updater():
        logger.info(f"Started system metrics updater (interval: {interval}s)")
        while True:
            try:
                update_system_metrics()
            except Exception as e:
                logger.error(f"Error updating system metrics: {e}")

            time.sleep(interval)

    thread = threading.Thread(target=updater, daemon=True, name="SystemMetricsUpdater")
    thread.start()
    logger.info("✅ System metrics updater thread started")


def stop_metrics_exporter():
    """
    Stop the metrics exporter.

    Note: prometheus_client doesn't provide a clean way to stop the HTTP server,
    so this is mainly for cleanup/documentation purposes.
    The daemon thread will be automatically stopped when the process exits.
    """
    global _metrics_server_started
    with _metrics_lock:
        if _metrics_server_started:
            logger.info("Metrics exporter shutting down")
            _metrics_server_started = False
