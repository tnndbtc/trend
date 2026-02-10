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
    """
    collectors_dir = Path(__file__).parent

    # Get all .py files in collectors/ directory
    for file_path in collectors_dir.glob('*.py'):
        module_name = file_path.stem

        # Skip __init__, utils, and base modules
        if module_name in ['__init__', 'utils', 'base']:
            continue

        try:
            # Import the module (this triggers register_collector() calls)
            importlib.import_module(f'.{module_name}', package='collectors')
            logger.debug(f"Loaded collector module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to load collector '{module_name}': {e}")


# Auto-discover collectors when this module is imported
auto_discover_collectors()

# Import commonly used collectors for backward compatibility
# (These will be auto-registered by auto_discover_collectors)
try:
    from . import reddit, hackernews, google_news
except ImportError as e:
    logger.warning(f"Could not import legacy collectors: {e}")
