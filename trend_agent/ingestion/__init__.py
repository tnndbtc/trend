"""
Ingestion layer for the Trend Intelligence Platform.

This package provides plugin-based data collection from various sources.
Collectors are auto-discovered and registered at runtime.
"""

from trend_agent.ingestion.base import CollectorPlugin, PluginRegistry
from trend_agent.ingestion.interfaces import PluginManager, HealthChecker

__all__ = [
    "CollectorPlugin",
    "PluginRegistry",
    "PluginManager",
    "HealthChecker",
]
