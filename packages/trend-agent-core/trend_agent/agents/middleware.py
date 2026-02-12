"""
Middleware for Agent Control Plane.

Provides request-level correlation tracking and governance enforcement.
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from trend_agent.agents.correlation import CorrelationContext

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for correlation ID propagation.

    Behavior:
    - Extracts correlation ID from X-Correlation-ID header
    - Generates new correlation ID if not present
    - Adds correlation ID to response headers
    - Sets correlation ID in context for logging and tracing
    """

    HEADER_NAME = "X-Correlation-ID"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process request with correlation ID tracking.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response with correlation ID header
        """
        # Extract or generate correlation ID
        correlation_id = request.headers.get(self.HEADER_NAME)
        if correlation_id:
            logger.debug(f"Using correlation ID from header: {correlation_id}")
            CorrelationContext.set(correlation_id)
        else:
            correlation_id = CorrelationContext.generate()
            logger.debug(f"Generated new correlation ID: {correlation_id}")

        try:
            # Process request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers[self.HEADER_NAME] = correlation_id

            return response

        finally:
            # Clean up context
            CorrelationContext.clear()


class GovernanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware for agent governance enforcement.

    Future: Integrate with Budget Engine, Rate Limiting, Risk Scoring
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Enforce governance policies.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response
        """
        # TODO: Add budget checks
        # TODO: Add rate limiting
        # TODO: Add risk scoring

        response = await call_next(request)
        return response
