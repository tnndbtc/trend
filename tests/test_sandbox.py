"""
Unit tests for plugin sandbox.
"""

import pytest
import asyncio

from trend_agent.ingestion.sandbox import (
    PluginSandbox,
    SandboxSecurityError,
    SandboxTimeoutError,
    PLUGIN_TEMPLATE,
)


class TestPluginSandbox:
    """Test cases for plugin sandbox."""

    @pytest.fixture
    def sandbox(self):
        """Create sandbox instance."""
        return PluginSandbox(timeout_seconds=5, max_memory_mb=50)

    def test_sandbox_initialization(self, sandbox):
        """Test sandbox initialization."""
        assert sandbox.timeout_seconds == 5
        assert sandbox.max_memory_mb == 50

    def test_validate_safe_code(self, sandbox):
        """Test validation of safe code."""
        safe_code = """
def collect(config):
    return []
"""
        # Should not raise exception
        sandbox._validate_code(safe_code)

    def test_validate_dangerous_import(self, sandbox):
        """Test rejection of dangerous imports."""
        dangerous_code = """
import os
def collect(config):
    return []
"""
        with pytest.raises(SandboxSecurityError):
            sandbox._validate_code(dangerous_code)

    def test_validate_file_operations(self, sandbox):
        """Test rejection of file operations."""
        dangerous_code = """
def collect(config):
    with open('/etc/passwd', 'r') as f:
        data = f.read()
    return []
"""
        with pytest.raises(SandboxSecurityError):
            sandbox._validate_code(dangerous_code)

    def test_validate_eval(self, sandbox):
        """Test rejection of eval."""
        dangerous_code = """
def collect(config):
    eval('malicious code')
    return []
"""
        with pytest.raises(SandboxSecurityError):
            sandbox._validate_code(dangerous_code)

    @pytest.mark.asyncio
    async def test_execute_simple_plugin(self, sandbox):
        """Test executing simple plugin."""
        plugin_code = """
def collect(config):
    return [{'title': 'Test Item', 'url': 'https://example.com'}]
"""
        result = await sandbox.execute_plugin_code(plugin_code)

        assert len(result) == 1
        assert result[0]['title'] == 'Test Item'

    @pytest.mark.asyncio
    async def test_execute_async_plugin(self, sandbox):
        """Test executing async plugin."""
        plugin_code = """
async def collect(config):
    return [{'title': 'Async Item'}]
"""
        result = await sandbox.execute_plugin_code(plugin_code)

        assert len(result) == 1
        assert result[0]['title'] == 'Async Item'

    @pytest.mark.asyncio
    async def test_plugin_with_config(self, sandbox):
        """Test plugin receiving configuration."""
        plugin_code = """
def collect(config):
    url = config.get('url', 'default')
    return [{'url': url}]
"""
        config = {'url': 'https://example.com/test'}
        result = await sandbox.execute_plugin_code(plugin_code, config=config)

        assert result[0]['url'] == config['url']

    @pytest.mark.asyncio
    async def test_plugin_timeout(self):
        """Test plugin timeout enforcement."""
        sandbox = PluginSandbox(timeout_seconds=1)

        plugin_code = """
import time
def collect(config):
    time.sleep(10)
    return []
"""
        with pytest.raises(SandboxTimeoutError):
            await sandbox.execute_plugin_code(plugin_code)

    @pytest.mark.asyncio
    async def test_missing_collect_function(self, sandbox):
        """Test error when collect function is missing."""
        plugin_code = """
def other_function():
    return []
"""
        with pytest.raises(SandboxSecurityError):
            await sandbox.execute_plugin_code(plugin_code)

    def test_validate_and_test_valid(self, sandbox):
        """Test validation of valid plugin."""
        plugin_code = """
def collect(config):
    '''Collect data.'''
    return []
"""
        result = sandbox.validate_and_test(plugin_code)

        assert result['valid'] is True
        assert result['has_collect_function'] is True
        assert len(result['errors']) == 0

    def test_validate_and_test_invalid(self, sandbox):
        """Test validation of invalid plugin."""
        plugin_code = """
def not_collect():
    return []
"""
        result = sandbox.validate_and_test(plugin_code)

        assert result['valid'] is False
        assert result['has_collect_function'] is False
        assert len(result['errors']) > 0

    def test_validate_and_test_syntax_error(self, sandbox):
        """Test validation of plugin with syntax error."""
        plugin_code = """
def collect(config):
    return [
"""
        result = sandbox.validate_and_test(plugin_code)

        assert result['valid'] is False
        assert 'Syntax error' in result['errors'][0]

    def test_safe_globals_creation(self, sandbox):
        """Test creation of safe globals namespace."""
        safe_globals = sandbox._create_safe_globals()

        # Check safe builtins are present
        assert 'len' in safe_globals
        assert 'range' in safe_globals
        assert 'list' in safe_globals

        # Check dangerous functions are not present
        assert 'eval' not in safe_globals.get('__builtins__', {})
        assert 'exec' not in safe_globals.get('__builtins__', {})
        assert 'open' not in safe_globals.get('__builtins__', {})

    @pytest.mark.asyncio
    async def test_plugin_using_allowed_imports(self, sandbox):
        """Test plugin using allowed imports."""
        plugin_code = """
from datetime import datetime
import json

def collect(config):
    now = datetime.utcnow()
    data = json.dumps({'time': str(now)})
    return [json.loads(data)]
"""
        result = await sandbox.execute_plugin_code(plugin_code)

        assert len(result) == 1
        assert 'time' in result[0]

    def test_plugin_template_validity(self, sandbox):
        """Test that plugin template is valid."""
        result = sandbox.validate_and_test(PLUGIN_TEMPLATE)

        # Template should be valid (though it may have warnings)
        assert result['has_collect_function'] is True


class TestSandboxResourceLimits:
    """Test cases for resource limit enforcement."""

    @pytest.fixture
    def sandbox(self):
        """Create sandbox with tight limits."""
        return PluginSandbox(timeout_seconds=2, max_memory_mb=10)

    @pytest.mark.asyncio
    async def test_cpu_time_limit(self, sandbox):
        """Test CPU time limit enforcement."""
        plugin_code = """
def collect(config):
    # Infinite loop (but timeout should catch it)
    result = 0
    for i in range(100000000):
        result += i
    return [result]
"""
        with pytest.raises((SandboxTimeoutError, SandboxSecurityError)):
            await sandbox.execute_plugin_code(plugin_code)
