"""
Ingestion layer for the Trend Intelligence Platform.

This package provides plugin-based data collection from various sources.
Collectors are auto-discovered and registered at runtime.
"""

# Base classes and registry
from trend_agent.ingestion.base import (
    CollectorPlugin,
    PluginRegistry,
    register_collector,
    CollectionError,
    ValidationError,
)

# Interface contracts (Protocols)
from trend_agent.ingestion.interfaces import (
    PluginManager,
    HealthChecker,
    RateLimiter,
    Scheduler,
)

# Concrete implementations
from trend_agent.ingestion.manager import DefaultPluginManager
from trend_agent.ingestion.health import DefaultHealthChecker
from trend_agent.ingestion.rate_limiter import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    create_rate_limiter,
)
from trend_agent.ingestion.scheduler import DefaultScheduler

__all__ = [
    # Base classes
    "CollectorPlugin",
    "PluginRegistry",
    "register_collector",
    "CollectionError",
    "ValidationError",
    # Interface contracts
    "PluginManager",
    "HealthChecker",
    "RateLimiter",
    "Scheduler",
    # Implementations
    "DefaultPluginManager",
    "DefaultHealthChecker",
    "InMemoryRateLimiter",
    "RedisRateLimiter",
    "create_rate_limiter",
    "DefaultScheduler",
]
