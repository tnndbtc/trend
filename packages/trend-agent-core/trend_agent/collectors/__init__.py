"""
Collector Registry - Auto-discovery and management of all news source collectors.

This module provides a centralized registry for all collector modules. Collectors
are automatically discovered and registered, eliminating the need for hardcoded
imports in main.py and collect_trends.py.

Usage:
    from collectors import get_all_collectors, get_collector

    # Get all collectors
    all_collectors = get_all_collectors()

    # Get specific collector
    reddit_collector = get_collector('reddit')
"""

from typing import Dict, Callable, List, Optional
import importlib
import pkgutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Global registry of collectors
_COLLECTOR_REGISTRY: Dict[str, Callable] = {}


def register_collector(name: str, fetch_func: Callable):
    """
    Register a collector function.

    Args:
        name: Unique identifier for the collector (e.g., 'reddit', 'bbc')
        fetch_func: Async function that returns List[Topic]
    """
    if name in _COLLECTOR_REGISTRY:
        logger.warning(f"Collector '{name}' is already registered. Overwriting.")

    _COLLECTOR_REGISTRY[name] = fetch_func
    logger.debug(f"Registered collector: {name}")


def get_collector(name: str) -> Optional[Callable]:
    """
    Get a specific collector by name.

    Args:
        name: Collector name

    Returns:
        Collector fetch function or None if not found
    """
    return _COLLECTOR_REGISTRY.get(name)


def get_all_collectors() -> Dict[str, Callable]:
    """
    Get all registered collectors.

    Returns:
        Dictionary of collector_name -> fetch_function
    """
    return _COLLECTOR_REGISTRY.copy()


def list_collector_names() -> List[str]:
    """
    Get list of all registered collector names.

    Returns:
        List of collector names
    """
    return list(_COLLECTOR_REGISTRY.keys())


def auto_discover_collectors():
    """
    Automatically discover and import all collector modules in this package.

    This scans the collectors/ directory and imports any .py files that aren't
    __init__, utils, or in subdirectories. Each collector module should call
    register_collector() at module level.

    After importing, this also bridges class-based plugins from PluginRegistry
    into the function-based _COLLECTOR_REGISTRY for backward compatibility.
    """
    collectors_dir = Path(__file__).parent

    # Get all .py files in collectors/ directory
    for file_path in collectors_dir.glob('*.py'):
        module_name = file_path.stem

        # Skip __init__, utils, and base modules
        if module_name in ['__init__', 'utils', 'base', 'base_rss']:
            continue

        try:
            # Import the module (this triggers register_collector() calls)
            importlib.import_module(f'.{module_name}', package='trend_agent.collectors')
            logger.info(f"Loaded collector module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to load collector '{module_name}': {e}", exc_info=True)

    # Bridge class-based plugins from PluginRegistry into function-based registry
    try:
        from trend_agent.ingestion.base import PluginRegistry

        for plugin_instance in PluginRegistry.get_all_plugins():
            plugin_name = plugin_instance.metadata.name

            # Create a wrapper function that calls the plugin's collect() method
            async def collector_wrapper(plugin=plugin_instance):
                return await plugin.collect()

            # Register in function-based registry
            if plugin_name not in _COLLECTOR_REGISTRY:
                _COLLECTOR_REGISTRY[plugin_name] = collector_wrapper
                logger.info(f"Bridged class-based collector '{plugin_name}' to function registry")

    except Exception as e:
        logger.warning(f"Failed to bridge class-based collectors: {e}")


# Auto-discover collectors when this module is imported
auto_discover_collectors()

# Note: Explicit imports removed to avoid double-registration
# All collectors are auto-discovered and registered by auto_discover_collectors()


# ============================================================================
# Demo Collector (for testing)
# ============================================================================

async def demo_collector():
    """
    Demo collector that returns sample trending topics for testing.

    This demonstrates the trend collection pipeline with sample data.
    """
    from datetime import datetime, timezone as dt_timezone
    from trend_agent.schemas import RawItem, Metrics, SourceType

    # Sample trending topics
    items = [
        RawItem(
            source=SourceType.DEMO,
            source_id="demo-1",
            url="https://example.com/ai-breakthrough",
            title="AI Breakthrough: New Language Model Achieves Human-Level Performance",
            description="Researchers announce a new AI model that achieves human-level performance on complex reasoning tasks",
            published_at=datetime.now(dt_timezone.utc),
            metrics=Metrics(upvotes=1250, comments=340, score=1590),
        ),
        RawItem(
            source=SourceType.DEMO,
            source_id="demo-2",
            url="https://example.com/opensource-ai",
            title="Tech Giant Releases Open Source AI Framework",
            description="Major technology company open-sources their internal AI development framework",
            published_at=datetime.now(dt_timezone.utc),
            metrics=Metrics(upvotes=980, comments=215, score=1195),
        ),
        RawItem(
            source=SourceType.DEMO,
            source_id="demo-3",
            url="https://example.com/new-language",
            title="New Programming Language Gains Popularity Among Developers",
            description="A new systems programming language is rapidly gaining adoption in the developer community",
            published_at=datetime.now(dt_timezone.utc),
            metrics=Metrics(upvotes=750, comments=180, score=930),
        ),
        RawItem(
            source=SourceType.DEMO,
            source_id="demo-4",
            url="https://example.com/quantum-breakthrough",
            title="Scientists Discover New Method for Quantum Computing",
            description="Research team announces breakthrough in quantum computing stability",
            published_at=datetime.now(dt_timezone.utc),
            metrics=Metrics(upvotes=1100, comments=290, score=1390),
        ),
        RawItem(
            source=SourceType.DEMO,
            source_id="demo-5",
            url="https://example.com/election-results",
            title="Major Election Results Announced in European Country",
            description="Historic election results reshape political landscape",
            published_at=datetime.now(dt_timezone.utc),
            metrics=Metrics(upvotes=2100, comments=520, score=2620),
        ),
    ]

    return items


# Register demo collector
register_collector('demo', demo_collector)
logger.info("Registered demo collector")
