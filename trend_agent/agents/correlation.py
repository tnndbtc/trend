"""
Correlation ID Tracking for Agent Control Plane.

Provides unified request tracing across all platform operations.
"""

from contextvars import ContextVar
from typing import Optional
from uuid import uuid4
import logging

# Context variable for correlation ID (thread-safe, async-safe)
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

logger = logging.getLogger(__name__)


class CorrelationContext:
    """
    Manages correlation ID lifecycle.

    Provides:
    - Automatic correlation ID generation
    - Context-aware propagation
    - Request chain tracking
    """

    @staticmethod
    def get() -> Optional[str]:
        """
        Get current correlation ID.

        Returns:
            Current correlation ID or None
        """
        return _correlation_id.get()

    @staticmethod
    def set(correlation_id: str) -> None:
        """
        Set correlation ID for current context.

        Args:
            correlation_id: Correlation ID to set
        """
        _correlation_id.set(correlation_id)
        logger.debug(f"Set correlation ID: {correlation_id}")

    @staticmethod
    def generate() -> str:
        """
        Generate and set a new correlation ID.

        Returns:
            Generated correlation ID
        """
        correlation_id = f"corr_{uuid4().hex[:16]}"
        CorrelationContext.set(correlation_id)
        return correlation_id

    @staticmethod
    def get_or_generate() -> str:
        """
        Get existing correlation ID or generate new one.

        Returns:
            Correlation ID
        """
        correlation_id = CorrelationContext.get()
        if not correlation_id:
            correlation_id = CorrelationContext.generate()
        return correlation_id

    @staticmethod
    def clear() -> None:
        """Clear correlation ID from context."""
        _correlation_id.set(None)


class CorrelationIDFilter(logging.Filter):
    """
    Logging filter that adds correlation ID to log records.

    Usage:
        handler.addFilter(CorrelationIDFilter())
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add correlation ID to log record.

        Args:
            record: Log record to enhance

        Returns:
            True (always include record)
        """
        record.correlation_id = CorrelationContext.get() or "no-correlation-id"
        return True


def get_correlation_id() -> str:
    """
    Convenience function to get or generate correlation ID.

    Returns:
        Correlation ID
    """
    return CorrelationContext.get_or_generate()
