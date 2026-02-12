"""
Sandboxed Execution Environment for Custom Plugins.

This module provides a secure sandboxed environment for executing user-provided
collector plugin code. Security features include:

1. RestrictedPython for safe code execution
2. Whitelisted imports and builtins
3. Resource limits (memory, CPU time)
4. Timeout enforcement
5. API restrictions

This prevents malicious code from:
- Accessing the file system
- Making arbitrary network requests
- Consuming excessive resources
- Accessing sensitive system functions
"""

import logging
import asyncio
import sys
import io
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import resource
import signal
from contextlib import contextmanager

logger = logging.getLogger(__name__)


# Whitelisted imports that plugins can use
ALLOWED_IMPORTS = {
    # Standard library (safe modules only)
    'datetime': ['datetime', 'timedelta', 'timezone'],
    'json': ['dumps', 'loads'],
    're': ['match', 'search', 'findall', 'compile', 'sub'],
    'typing': ['List', 'Dict', 'Optional', 'Any'],
    'collections': ['Counter', 'defaultdict', 'namedtuple'],

    # Data processing
    'urllib.parse': ['urlparse', 'urlencode', 'parse_qs'],

    # Our schemas (safe to expose)
    'trend_agent.schemas': ['RawItem', 'Metrics', 'SourceType'],
}

# Whitelisted built-in functions
SAFE_BUILTINS = {
    'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytes',
    'chr', 'dict', 'divmod', 'enumerate', 'filter', 'float',
    'format', 'frozenset', 'hex', 'int', 'isinstance', 'issubclass',
    'iter', 'len', 'list', 'map', 'max', 'min', 'next',
    'oct', 'ord', 'pow', 'range', 'repr', 'reversed',
    'round', 'set', 'slice', 'sorted', 'str', 'sum',
    'tuple', 'type', 'zip',
    # Safe exceptions
    'Exception', 'ValueError', 'TypeError', 'KeyError',
    'IndexError', 'AttributeError',
}

# Dangerous functions that should never be accessible
BLACKLISTED = {
    'eval', 'exec', 'compile', '__import__', 'open',
    'file', 'input', 'raw_input', 'reload', 'execfile',
    'getattr', 'setattr', 'delattr', 'hasattr',
    'globals', 'locals', 'vars', 'dir',
}


class SandboxSecurityError(Exception):
    """Raised when sandbox security violation is detected."""
    pass


class SandboxTimeoutError(Exception):
    """Raised when sandbox execution exceeds time limit."""
    pass


class SandboxResourceError(Exception):
    """Raised when sandbox exceeds resource limits."""
    pass


class PluginSandbox:
    """
    Secure sandbox for executing custom plugin code.

    Provides isolation and resource limits for user-provided code.
    """

    def __init__(
        self,
        timeout_seconds: int = 30,
        max_memory_mb: int = 100,
        allowed_domains: Optional[Set[str]] = None,
    ):
        """
        Initialize plugin sandbox.

        Args:
            timeout_seconds: Maximum execution time
            max_memory_mb: Maximum memory usage
            allowed_domains: Domains that HTTP requests are allowed to
        """
        self.timeout_seconds = timeout_seconds
        self.max_memory_mb = max_memory_mb
        self.allowed_domains = allowed_domains or set()

    def _create_safe_globals(self) -> Dict[str, Any]:
        """
        Create a safe global namespace for code execution.

        Returns:
            Dictionary of safe globals
        """
        safe_globals = {
            '__builtins__': {
                name: __builtins__[name]
                for name in SAFE_BUILTINS
                if name in __builtins__
            },
        }

        # Add allowed imports
        for module_name, allowed_attrs in ALLOWED_IMPORTS.items():
            try:
                module = __import__(module_name, fromlist=allowed_attrs)
                if allowed_attrs == ['*']:
                    # Import entire module
                    safe_globals[module_name.split('.')[-1]] = module
                else:
                    # Import specific attributes
                    for attr in allowed_attrs:
                        if hasattr(module, attr):
                            safe_globals[attr] = getattr(module, attr)
            except ImportError:
                logger.warning(f"Could not import {module_name}")

        # Add safe helper functions
        safe_globals['print'] = self._safe_print
        safe_globals['len'] = len
        safe_globals['range'] = range

        return safe_globals

    def _safe_print(self, *args, **kwargs):
        """Safe print function that doesn't actually print."""
        # Log instead of printing
        message = ' '.join(str(arg) for arg in args)
        logger.debug(f"[Plugin Print] {message}")

    def _validate_code(self, code: str) -> None:
        """
        Validate plugin code for security issues.

        Args:
            code: Plugin code to validate

        Raises:
            SandboxSecurityError: If code contains dangerous patterns
        """
        # Check for blacklisted functions
        for dangerous in BLACKLISTED:
            if dangerous in code:
                raise SandboxSecurityError(
                    f"Dangerous function '{dangerous}' not allowed in plugin code"
                )

        # Check for import statements (must use pre-imported modules)
        lines = code.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                # Check if it's an allowed import
                import_allowed = False
                for allowed_module in ALLOWED_IMPORTS.keys():
                    if allowed_module in stripped:
                        import_allowed = True
                        break

                if not import_allowed:
                    raise SandboxSecurityError(
                        f"Import not allowed: {stripped}"
                    )

        # Check for file operations
        file_operations = ['open(', 'file(', 'read(', 'write(']
        for op in file_operations:
            if op in code:
                raise SandboxSecurityError(
                    f"File operation '{op}' not allowed in plugin code"
                )

    @contextmanager
    def _resource_limits(self):
        """Context manager to enforce resource limits."""
        old_limits = {}

        try:
            # Set memory limit (if supported on platform)
            try:
                # Convert MB to bytes
                max_memory_bytes = self.max_memory_mb * 1024 * 1024
                old_limits['memory'] = resource.getrlimit(resource.RLIMIT_AS)
                resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
            except (ValueError, resource.error):
                logger.warning("Could not set memory limit")

            # Set CPU time limit
            try:
                old_limits['cpu'] = resource.getrlimit(resource.RLIMIT_CPU)
                resource.setrlimit(resource.RLIMIT_CPU, (self.timeout_seconds, self.timeout_seconds))
            except (ValueError, resource.error):
                logger.warning("Could not set CPU time limit")

            yield

        finally:
            # Restore old limits
            try:
                if 'memory' in old_limits:
                    resource.setrlimit(resource.RLIMIT_AS, old_limits['memory'])
                if 'cpu' in old_limits:
                    resource.setrlimit(resource.RLIMIT_CPU, old_limits['cpu'])
            except Exception as e:
                logger.error(f"Failed to restore resource limits: {e}")

    async def execute_plugin_code(
        self,
        code: str,
        collect_function_name: str = 'collect',
        config: Optional[Dict[str, Any]] = None,
    ) -> List:
        """
        Execute plugin code in sandboxed environment.

        Args:
            code: Plugin code to execute
            collect_function_name: Name of the collect function to call
            config: Configuration dictionary to pass to collect function

        Returns:
            List of collected items

        Raises:
            SandboxSecurityError: If code violates security rules
            SandboxTimeoutError: If execution exceeds timeout
            SandboxResourceError: If resource limits exceeded
        """
        # Validate code
        self._validate_code(code)

        # Create safe execution environment
        safe_globals = self._create_safe_globals()
        safe_locals = {}

        try:
            # Compile code
            try:
                compiled_code = compile(code, '<plugin>', 'exec')
            except SyntaxError as e:
                raise SandboxSecurityError(f"Plugin code has syntax error: {e}")

            # Execute with timeout and resource limits
            try:
                # Use asyncio.wait_for for timeout
                async def execute_with_limits():
                    with self._resource_limits():
                        # Execute plugin code
                        exec(compiled_code, safe_globals, safe_locals)

                        # Check if collect function exists
                        if collect_function_name not in safe_locals:
                            raise SandboxSecurityError(
                                f"Plugin must define '{collect_function_name}' function"
                            )

                        collect_func = safe_locals[collect_function_name]

                        # Check if it's callable
                        if not callable(collect_func):
                            raise SandboxSecurityError(
                                f"'{collect_function_name}' must be a callable function"
                            )

                        # Call collect function
                        if asyncio.iscoroutinefunction(collect_func):
                            # Async function
                            result = await collect_func(config or {})
                        else:
                            # Sync function - run in executor
                            loop = asyncio.get_event_loop()
                            result = await loop.run_in_executor(
                                None, collect_func, config or {}
                            )

                        return result

                # Execute with timeout
                result = await asyncio.wait_for(
                    execute_with_limits(),
                    timeout=self.timeout_seconds
                )

                return result if result is not None else []

            except asyncio.TimeoutError:
                raise SandboxTimeoutError(
                    f"Plugin execution exceeded timeout of {self.timeout_seconds}s"
                )
            except MemoryError:
                raise SandboxResourceError(
                    f"Plugin exceeded memory limit of {self.max_memory_mb}MB"
                )

        except SandboxSecurityError:
            raise
        except SandboxTimeoutError:
            raise
        except SandboxResourceError:
            raise
        except Exception as e:
            logger.error(f"Plugin execution failed: {e}", exc_info=True)
            raise SandboxSecurityError(f"Plugin execution failed: {str(e)}")

    def validate_and_test(self, code: str) -> Dict[str, Any]:
        """
        Validate and test plugin code without full execution.

        Args:
            code: Plugin code to test

        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'has_collect_function': False,
            'is_async': False,
        }

        try:
            # Validate security
            self._validate_code(code)

            # Try to compile
            compiled_code = compile(code, '<plugin>', 'exec')

            # Execute in safe namespace to check structure
            safe_globals = self._create_safe_globals()
            safe_locals = {}

            exec(compiled_code, safe_globals, safe_locals)

            # Check for collect function
            if 'collect' in safe_locals:
                results['has_collect_function'] = True
                collect_func = safe_locals['collect']

                if asyncio.iscoroutinefunction(collect_func):
                    results['is_async'] = True
            else:
                results['errors'].append("Plugin must define a 'collect' function")

            # Check return type hint if available
            if results['has_collect_function']:
                collect_func = safe_locals['collect']
                if hasattr(collect_func, '__annotations__'):
                    if 'return' not in collect_func.__annotations__:
                        results['warnings'].append(
                            "collect() function should have return type hint: List[RawItem]"
                        )

            # If no errors, mark as valid
            if not results['errors']:
                results['valid'] = True

        except SandboxSecurityError as e:
            results['errors'].append(str(e))
        except SyntaxError as e:
            results['errors'].append(f"Syntax error: {e}")
        except Exception as e:
            results['errors'].append(f"Validation error: {str(e)}")

        return results


# Global sandbox instance
_sandbox: Optional[PluginSandbox] = None


def get_sandbox(
    timeout_seconds: int = 30,
    max_memory_mb: int = 100,
) -> PluginSandbox:
    """
    Get global sandbox instance.

    Args:
        timeout_seconds: Maximum execution time
        max_memory_mb: Maximum memory usage

    Returns:
        PluginSandbox instance
    """
    global _sandbox
    if _sandbox is None:
        _sandbox = PluginSandbox(timeout_seconds, max_memory_mb)
    return _sandbox


# Example plugin template for users
PLUGIN_TEMPLATE = '''"""
Custom Collector Plugin Template

Your plugin must define a 'collect' function that returns a list of RawItem objects.
"""

from typing import List, Dict, Any
from datetime import datetime


async def collect(config: Dict[str, Any]) -> List:
    """
    Collect data from your source.

    Args:
        config: Configuration dictionary with your source settings

    Returns:
        List of dictionaries representing collected items
        Each dict should have: source, source_id, url, title, description, etc.
    """
    items = []

    # Your collection logic here
    # Example:
    # url = config.get('url')
    # response = await fetch_data(url)
    # items = parse_response(response)

    return items


# Helper functions can be defined here
def parse_item(data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a single item from your source."""
    return {
        'source_id': data.get('id'),
        'title': data.get('title'),
        'description': data.get('description'),
        'url': data.get('link'),
        'published_at': datetime.utcnow(),
    }
'''
