"""
Unit tests for the ingestion plugin system.

Tests cover:
- Plugin registration and discovery
- PluginManager functionality
- HealthChecker monitoring
- RateLimiter enforcement
- Scheduler execution
"""

import asyncio
import pytest
from datetime import datetime
from typing import List

from trend_agent.ingestion.base import (
    CollectorPlugin,
    PluginRegistry,
    register_collector,
    CollectionError,
)
from trend_agent.ingestion.manager import DefaultPluginManager
from trend_agent.ingestion.health import DefaultHealthChecker
from trend_agent.ingestion.rate_limiter import InMemoryRateLimiter
from trend_agent.ingestion.scheduler import DefaultScheduler
from trend_agent.types import Metrics, PluginMetadata, RawItem, SourceType


# ============================================================================
# Test Fixtures
# ============================================================================


class MockSuccessCollector(CollectorPlugin):
    """Mock collector that always succeeds."""

    metadata = PluginMetadata(
        name="mock_success",
        version="1.0.0",
        author="Test",
        description="Mock successful collector",
        source_type=SourceType.CUSTOM,
        schedule="*/5 * * * *",
        enabled=True,
        rate_limit=10,
        timeout_seconds=30,
        retry_count=3,
    )

    async def collect(self) -> List[RawItem]:
        """Return mock items."""
        return [
            RawItem(
                source=SourceType.CUSTOM,
                source_id="test-1",
                url="https://example.com/1",
                title="Test Item 1",
                published_at=datetime.utcnow(),
                metrics=Metrics(),
            ),
            RawItem(
                source=SourceType.CUSTOM,
                source_id="test-2",
                url="https://example.com/2",
                title="Test Item 2",
                published_at=datetime.utcnow(),
                metrics=Metrics(),
            ),
        ]


class MockFailureCollector(CollectorPlugin):
    """Mock collector that always fails."""

    metadata = PluginMetadata(
        name="mock_failure",
        version="1.0.0",
        author="Test",
        description="Mock failing collector",
        source_type=SourceType.CUSTOM,
        schedule="*/10 * * * *",
        enabled=True,
        rate_limit=10,
        timeout_seconds=30,
        retry_count=3,
    )

    async def collect(self) -> List[RawItem]:
        """Always raise an error."""
        raise CollectionError("Mock collection failure")


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear plugin registry before each test."""
    PluginRegistry.clear()
    yield
    PluginRegistry.clear()


# ============================================================================
# Plugin Registration Tests
# ============================================================================


def test_plugin_registration():
    """Test that plugins can be registered."""
    PluginRegistry.register(MockSuccessCollector)

    assert "mock_success" in PluginRegistry.get_plugin_names()
    plugin = PluginRegistry.get_plugin("mock_success")
    assert plugin is not None
    assert plugin.metadata.name == "mock_success"


def test_duplicate_plugin_registration():
    """Test that duplicate plugin registration raises error."""
    PluginRegistry.register(MockSuccessCollector)

    with pytest.raises(ValueError, match="already registered"):
        PluginRegistry.register(MockSuccessCollector)


def test_register_decorator():
    """Test the @register_collector decorator."""

    @register_collector
    class DecoratedCollector(CollectorPlugin):
        metadata = PluginMetadata(
            name="decorated",
            version="1.0.0",
            author="Test",
            description="Decorated collector",
            source_type=SourceType.CUSTOM,
            schedule="0 * * * *",
            enabled=True,
        )

        async def collect(self) -> List[RawItem]:
            return []

    assert "decorated" in PluginRegistry.get_plugin_names()


def test_get_enabled_plugins():
    """Test getting only enabled plugins."""
    PluginRegistry.register(MockSuccessCollector)
    PluginRegistry.register(MockFailureCollector)

    enabled = PluginRegistry.get_enabled_plugins()
    assert len(enabled) == 2  # Both are enabled by default

    # Test with disabled plugin
    class DisabledCollector(CollectorPlugin):
        metadata = PluginMetadata(
            name="disabled",
            version="1.0.0",
            author="Test",
            description="Disabled collector",
            source_type=SourceType.CUSTOM,
            schedule="0 * * * *",
            enabled=False,
        )

        async def collect(self) -> List[RawItem]:
            return []

    PluginRegistry.register(DisabledCollector)
    enabled = PluginRegistry.get_enabled_plugins()
    assert len(enabled) == 2  # Still only 2 enabled


# ============================================================================
# PluginManager Tests
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_manager_load_plugins():
    """Test plugin manager loads plugins from directory."""
    manager = DefaultPluginManager()

    # Note: In a real test, you'd need actual plugin files
    # For now, we test with manually registered plugins
    PluginRegistry.register(MockSuccessCollector)

    plugins = await manager.load_plugins()
    # The actual number depends on what's in the collectors directory
    assert isinstance(plugins, list)


@pytest.mark.asyncio
async def test_plugin_manager_enable_disable():
    """Test enabling and disabling plugins."""
    PluginRegistry.register(MockSuccessCollector)
    manager = DefaultPluginManager()

    # Disable plugin
    result = await manager.disable_plugin("mock_success")
    assert result is True

    status = await manager.get_plugin_status("mock_success")
    assert status["enabled"] is False

    # Enable plugin
    result = await manager.enable_plugin("mock_success")
    assert result is True

    status = await manager.get_plugin_status("mock_success")
    assert status["enabled"] is True


@pytest.mark.asyncio
async def test_plugin_manager_get_status():
    """Test getting plugin status."""
    PluginRegistry.register(MockSuccessCollector)
    manager = DefaultPluginManager()

    status = await manager.get_plugin_status("mock_success")
    assert status is not None
    assert status["name"] == "mock_success"
    assert status["version"] == "1.0.0"
    assert status["enabled"] is True


@pytest.mark.asyncio
async def test_plugin_manager_get_all_status():
    """Test getting status for all plugins."""
    PluginRegistry.register(MockSuccessCollector)
    PluginRegistry.register(MockFailureCollector)
    manager = DefaultPluginManager()

    all_status = await manager.get_all_plugin_status()
    assert len(all_status) == 2
    assert "mock_success" in all_status
    assert "mock_failure" in all_status


# ============================================================================
# HealthChecker Tests
# ============================================================================


@pytest.mark.asyncio
async def test_health_checker_record_success():
    """Test recording successful collection."""
    PluginRegistry.register(MockSuccessCollector)
    checker = DefaultHealthChecker()

    plugin = PluginRegistry.get_plugin("mock_success")
    await checker.record_success("mock_success")

    health = await checker.check_health(plugin)
    assert health.is_healthy is True
    assert health.consecutive_failures == 0
    assert health.total_runs == 1


@pytest.mark.asyncio
async def test_health_checker_record_failure():
    """Test recording failed collection."""
    PluginRegistry.register(MockFailureCollector)
    checker = DefaultHealthChecker()

    plugin = PluginRegistry.get_plugin("mock_failure")
    await checker.record_failure("mock_failure", "Test error")

    health = await checker.check_health(plugin)
    assert health.is_healthy is True  # Still healthy after 1 failure
    assert health.consecutive_failures == 1
    assert health.last_error == "Test error"


@pytest.mark.asyncio
async def test_health_checker_failure_threshold():
    """Test that plugin becomes unhealthy after threshold failures."""
    PluginRegistry.register(MockFailureCollector)
    checker = DefaultHealthChecker(failure_threshold=3)

    plugin = PluginRegistry.get_plugin("mock_failure")

    # Record 3 failures
    for i in range(3):
        await checker.record_failure("mock_failure", f"Error {i}")

    health = await checker.check_health(plugin)
    assert health.is_healthy is False
    assert health.consecutive_failures == 3


@pytest.mark.asyncio
async def test_health_checker_success_resets_failures():
    """Test that success resets consecutive failures."""
    PluginRegistry.register(MockSuccessCollector)
    checker = DefaultHealthChecker()

    # Record some failures
    await checker.record_failure("mock_success", "Error 1")
    await checker.record_failure("mock_success", "Error 2")

    # Then a success
    await checker.record_success("mock_success")

    health = await checker.get_current_health("mock_success")
    assert health.consecutive_failures == 0
    assert health.is_healthy is True


@pytest.mark.asyncio
async def test_health_checker_check_all():
    """Test checking health of all plugins."""
    PluginRegistry.register(MockSuccessCollector)
    PluginRegistry.register(MockFailureCollector)
    checker = DefaultHealthChecker()

    all_health = await checker.check_all_health()
    assert len(all_health) == 2
    assert "mock_success" in all_health
    assert "mock_failure" in all_health


# ============================================================================
# RateLimiter Tests
# ============================================================================


@pytest.mark.asyncio
async def test_rate_limiter_allows_requests():
    """Test that rate limiter allows requests under limit."""
    PluginRegistry.register(MockSuccessCollector)
    limiter = InMemoryRateLimiter(default_limit=10)

    # Should allow first request
    can_run = await limiter.check_rate_limit("mock_success")
    assert can_run is True

    # Record the request
    await limiter.record_request("mock_success")

    # Should still allow more requests
    can_run = await limiter.check_rate_limit("mock_success")
    assert can_run is True


@pytest.mark.asyncio
async def test_rate_limiter_blocks_excess_requests():
    """Test that rate limiter blocks requests over limit."""
    PluginRegistry.register(MockSuccessCollector)
    limiter = InMemoryRateLimiter(default_limit=2)

    # Make 2 requests
    for _ in range(2):
        await limiter.record_request("mock_success")

    # Third request should be blocked
    can_run = await limiter.check_rate_limit("mock_success")
    assert can_run is False


@pytest.mark.asyncio
async def test_rate_limiter_get_remaining_quota():
    """Test getting remaining quota."""
    PluginRegistry.register(MockSuccessCollector)
    limiter = InMemoryRateLimiter(default_limit=10)

    # Initially should have full quota
    remaining = await limiter.get_remaining_quota("mock_success")
    assert remaining == 10

    # After 3 requests, should have 7 remaining
    for _ in range(3):
        await limiter.record_request("mock_success")

    remaining = await limiter.get_remaining_quota("mock_success")
    assert remaining == 7


@pytest.mark.asyncio
async def test_rate_limiter_reset_quota():
    """Test resetting quota."""
    PluginRegistry.register(MockSuccessCollector)
    limiter = InMemoryRateLimiter(default_limit=5)

    # Use up quota
    for _ in range(5):
        await limiter.record_request("mock_success")

    # Reset quota
    await limiter.reset_quota("mock_success")

    # Should have full quota again
    remaining = await limiter.get_remaining_quota("mock_success")
    assert remaining == 5


# ============================================================================
# Scheduler Tests
# ============================================================================


@pytest.mark.asyncio
async def test_scheduler_schedule_plugin():
    """Test scheduling a plugin."""
    PluginRegistry.register(MockSuccessCollector)
    scheduler = DefaultScheduler()

    await scheduler.start()

    try:
        plugin = PluginRegistry.get_plugin("mock_success")
        job_id = await scheduler.schedule_plugin(plugin, "*/5 * * * *")

        assert job_id is not None
        assert job_id.startswith("plugin_")

        # Check next run time
        next_run = await scheduler.get_next_run("mock_success")
        assert next_run is not None
        assert isinstance(next_run, datetime)

    finally:
        await scheduler.shutdown()


@pytest.mark.asyncio
async def test_scheduler_trigger_now():
    """Test triggering immediate plugin execution."""
    PluginRegistry.register(MockSuccessCollector)
    checker = DefaultHealthChecker()
    scheduler = DefaultScheduler(health_checker=checker)

    await scheduler.start()

    try:
        task_id = await scheduler.trigger_now("mock_success")
        assert task_id is not None
        assert task_id.startswith("task_")

        # Wait a bit for execution
        await asyncio.sleep(0.5)

        # Check health was updated
        health = await checker.get_current_health("mock_success")
        assert health is not None

    finally:
        await scheduler.shutdown()


@pytest.mark.asyncio
async def test_scheduler_unschedule_plugin():
    """Test unscheduling a plugin."""
    PluginRegistry.register(MockSuccessCollector)
    scheduler = DefaultScheduler()

    await scheduler.start()

    try:
        plugin = PluginRegistry.get_plugin("mock_success")
        await scheduler.schedule_plugin(plugin, "*/5 * * * *")

        # Unschedule
        result = await scheduler.unschedule_plugin("mock_success")
        assert result is True

        # Next run should be None
        next_run = await scheduler.get_next_run("mock_success")
        assert next_run is None

    finally:
        await scheduler.shutdown()


@pytest.mark.asyncio
async def test_scheduler_get_schedule():
    """Test getting schedule for all plugins."""
    PluginRegistry.register(MockSuccessCollector)
    PluginRegistry.register(MockFailureCollector)
    scheduler = DefaultScheduler()

    await scheduler.start()

    try:
        # Schedule both plugins
        plugin1 = PluginRegistry.get_plugin("mock_success")
        plugin2 = PluginRegistry.get_plugin("mock_failure")

        await scheduler.schedule_plugin(plugin1, "*/5 * * * *")
        await scheduler.schedule_plugin(plugin2, "*/10 * * * *")

        # Get full schedule
        schedule = await scheduler.get_schedule()
        assert len(schedule) == 2
        assert "mock_success" in schedule
        assert "mock_failure" in schedule

    finally:
        await scheduler.shutdown()


@pytest.mark.asyncio
async def test_scheduler_integration_with_health():
    """Test scheduler integration with health checker."""
    PluginRegistry.register(MockFailureCollector)
    checker = DefaultHealthChecker()
    scheduler = DefaultScheduler(health_checker=checker)

    await scheduler.start()

    try:
        # Trigger the failing collector
        task_id = await scheduler.trigger_now("mock_failure")
        assert task_id is not None

        # Wait for execution
        await asyncio.sleep(0.5)

        # Health should record the failure
        health = await checker.get_current_health("mock_failure")
        assert health is not None
        assert health.consecutive_failures > 0

    finally:
        await scheduler.shutdown()


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_plugin_system_integration():
    """Test full integration of plugin system components."""
    # Register plugins
    PluginRegistry.register(MockSuccessCollector)

    # Initialize components
    manager = DefaultPluginManager()
    checker = DefaultHealthChecker()
    limiter = InMemoryRateLimiter()
    scheduler = DefaultScheduler(
        health_checker=checker,
        rate_limiter=limiter
    )

    await scheduler.start()

    try:
        # Get plugin status
        status = await manager.get_plugin_status("mock_success")
        assert status is not None

        # Trigger collection
        task_id = await scheduler.trigger_now("mock_success")
        await asyncio.sleep(0.5)

        # Check health was updated
        plugin = PluginRegistry.get_plugin("mock_success")
        health = await checker.check_health(plugin)
        assert health.is_healthy is True
        assert health.total_runs > 0

        # Check rate limit was recorded
        remaining = await limiter.get_remaining_quota("mock_success")
        assert remaining < 10  # Should have used one

    finally:
        await scheduler.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
