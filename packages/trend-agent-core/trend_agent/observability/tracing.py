"""
Distributed Tracing with OpenTelemetry.

Provides end-to-end request tracing across services, tasks, and external calls.
"""

import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable for current span
current_span_context: ContextVar[Optional[Any]] = ContextVar("current_span", default=None)


class TracingManager:
    """
    Manages OpenTelemetry tracing configuration and instrumentation.

    Provides automatic instrumentation for:
    - HTTP requests (FastAPI, aiohttp)
    - Database queries (asyncpg, PostgreSQL)
    - Redis operations
    - Celery tasks
    - Custom spans
    """

    def __init__(
        self,
        service_name: str = "trend-intelligence-platform",
        endpoint: str = "http://localhost:4318/v1/traces",
        enable_auto_instrumentation: bool = True,
    ):
        """
        Initialize tracing manager.

        Args:
            service_name: Name of the service
            endpoint: OpenTelemetry collector endpoint (OTLP)
            enable_auto_instrumentation: Enable automatic instrumentation
        """
        self.service_name = service_name
        self.endpoint = endpoint
        self.enable_auto_instrumentation = enable_auto_instrumentation
        self._tracer = None
        self._tracer_provider = None

    def setup(self) -> None:
        """Setup OpenTelemetry tracing."""
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource, SERVICE_NAME
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
            from opentelemetry.instrumentation.redis import RedisInstrumentor
            from opentelemetry.instrumentation.celery import CeleryInstrumentor

            # Create resource with service name
            resource = Resource(attributes={
                SERVICE_NAME: self.service_name
            })

            # Create tracer provider
            self._tracer_provider = TracerProvider(resource=resource)

            # Create OTLP exporter
            otlp_exporter = OTLPSpanExporter(endpoint=self.endpoint)

            # Add span processor
            span_processor = BatchSpanProcessor(otlp_exporter)
            self._tracer_provider.add_span_processor(span_processor)

            # Set as global tracer provider
            trace.set_tracer_provider(self._tracer_provider)

            # Get tracer
            self._tracer = trace.get_tracer(__name__)

            # Enable automatic instrumentation
            if self.enable_auto_instrumentation:
                try:
                    FastAPIInstrumentor().instrument()
                    logger.info("FastAPI instrumentation enabled")
                except Exception as e:
                    logger.warning(f"Failed to instrument FastAPI: {e}")

                try:
                    AioHttpClientInstrumentor().instrument()
                    logger.info("AioHTTP instrumentation enabled")
                except Exception as e:
                    logger.warning(f"Failed to instrument AioHTTP: {e}")

                try:
                    RedisInstrumentor().instrument()
                    logger.info("Redis instrumentation enabled")
                except Exception as e:
                    logger.warning(f"Failed to instrument Redis: {e}")

                try:
                    CeleryInstrumentor().instrument()
                    logger.info("Celery instrumentation enabled")
                except Exception as e:
                    logger.warning(f"Failed to instrument Celery: {e}")

            logger.info(f"OpenTelemetry tracing initialized for {self.service_name}")

        except ImportError as e:
            logger.warning(f"OpenTelemetry not installed: {e}")
            logger.warning("Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http")
            logger.warning("Install instrumentations: pip install opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-aiohttp-client opentelemetry-instrumentation-redis opentelemetry-instrumentation-celery")

        except Exception as e:
            logger.error(f"Failed to setup tracing: {e}")

    def shutdown(self) -> None:
        """Shutdown tracing and flush remaining spans."""
        if self._tracer_provider:
            self._tracer_provider.shutdown()
            logger.info("Tracing shutdown complete")

    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Start a new span.

        Args:
            name: Span name
            attributes: Optional span attributes

        Returns:
            Span object (context manager)

        Example:
            with tracer.start_span("process_items", {"item_count": 10}):
                # Do work
                pass
        """
        if not self._tracer:
            # Return no-op context manager if tracing not initialized
            return NoOpSpan()

        from opentelemetry import trace

        span = self._tracer.start_as_current_span(name)

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        return span

    def trace_function(
        self,
        name: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Decorator to trace a function.

        Args:
            name: Optional span name (defaults to function name)
            attributes: Optional span attributes

        Example:
            @tracer.trace_function(attributes={"category": "data_processing"})
            async def process_data():
                pass
        """
        def decorator(func: Callable):
            span_name = name or f"{func.__module__}.{func.__name__}"

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.start_span(span_name, attributes):
                    return await func(*args, **kwargs)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.start_span(span_name, attributes):
                    return func(*args, **kwargs)

            # Return appropriate wrapper
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Add an event to the current span.

        Args:
            name: Event name
            attributes: Optional event attributes

        Example:
            tracer.add_event("item_processed", {"item_id": "123"})
        """
        if not self._tracer:
            return

        from opentelemetry import trace

        span = trace.get_current_span()
        if span:
            span.add_event(name, attributes=attributes or {})

    def set_attribute(self, key: str, value: Any):
        """
        Set an attribute on the current span.

        Args:
            key: Attribute key
            value: Attribute value

        Example:
            tracer.set_attribute("user_id", "123")
        """
        if not self._tracer:
            return

        from opentelemetry import trace

        span = trace.get_current_span()
        if span:
            span.set_attribute(key, value)

    def record_exception(self, exception: Exception):
        """
        Record an exception in the current span.

        Args:
            exception: Exception object

        Example:
            try:
                # Some operation
                pass
            except Exception as e:
                tracer.record_exception(e)
                raise
        """
        if not self._tracer:
            return

        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode

        span = trace.get_current_span()
        if span:
            span.record_exception(exception)
            span.set_status(Status(StatusCode.ERROR, str(exception)))


class NoOpSpan:
    """No-op span for when tracing is not initialized."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# ============================================================================
# Global Tracer Instance
# ============================================================================

# Global tracing manager
_tracing_manager: Optional[TracingManager] = None


def setup_tracing(
    service_name: str = "trend-intelligence-platform",
    endpoint: str = "http://localhost:4318/v1/traces",
    enable_auto_instrumentation: bool = True,
) -> TracingManager:
    """
    Setup global tracing.

    Args:
        service_name: Name of the service
        endpoint: OpenTelemetry collector endpoint
        enable_auto_instrumentation: Enable automatic instrumentation

    Returns:
        TracingManager instance

    Example:
        tracer = setup_tracing(
            service_name="trends-api",
            endpoint="http://otel-collector:4318/v1/traces"
        )
    """
    global _tracing_manager

    _tracing_manager = TracingManager(
        service_name=service_name,
        endpoint=endpoint,
        enable_auto_instrumentation=enable_auto_instrumentation,
    )

    _tracing_manager.setup()

    return _tracing_manager


def get_tracer() -> Optional[TracingManager]:
    """
    Get global tracing manager.

    Returns:
        TracingManager instance or None if not initialized
    """
    return _tracing_manager


def shutdown_tracing():
    """Shutdown global tracing."""
    global _tracing_manager

    if _tracing_manager:
        _tracing_manager.shutdown()
        _tracing_manager = None


# ============================================================================
# Convenience Decorators
# ============================================================================

def trace(name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator to trace a function.

    Args:
        name: Optional span name (defaults to function name)
        attributes: Optional span attributes

    Example:
        @trace(attributes={"category": "api"})
        async def get_trends():
            pass
    """
    tracer = get_tracer()
    if tracer:
        return tracer.trace_function(name, attributes)
    else:
        # Return no-op decorator if tracing not initialized
        def decorator(func):
            return func
        return decorator


def add_trace_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Add an event to the current span.

    Args:
        name: Event name
        attributes: Optional event attributes
    """
    tracer = get_tracer()
    if tracer:
        tracer.add_event(name, attributes)


def set_trace_attribute(key: str, value: Any):
    """
    Set an attribute on the current span.

    Args:
        key: Attribute key
        value: Attribute value
    """
    tracer = get_tracer()
    if tracer:
        tracer.set_attribute(key, value)


def record_trace_exception(exception: Exception):
    """
    Record an exception in the current span.

    Args:
        exception: Exception object
    """
    tracer = get_tracer()
    if tracer:
        tracer.record_exception(exception)
