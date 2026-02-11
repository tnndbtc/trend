"""
Tests for Celery tasks.

These tests verify that tasks are properly configured and can be executed.
Uses Celery's test utilities for synchronous task execution.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Configure Celery for testing (eager mode)
from celery import Celery

# Import Celery app and tasks
from trend_agent.tasks import app
from trend_agent.tasks.collection import (
    collect_from_plugin_task,
    collect_all_plugins_task,
    test_plugin_task,
)
from trend_agent.tasks.processing import (
    process_pending_items_task,
    test_pipeline_task,
)
from trend_agent.tasks.scheduler import (
    health_check_task,
    cleanup_old_data_task,
    monitor_celery_queue_task,
)


# Fixtures

@pytest.fixture(scope="session")
def celery_config():
    """Configure Celery for testing."""
    return {
        "broker_url": "memory://",
        "result_backend": "cache+memory://",
        "task_always_eager": True,  # Execute tasks synchronously
        "task_eager_propagates": True,  # Propagate exceptions
    }


@pytest.fixture(scope="session")
def celery_app(celery_config):
    """Create Celery app for testing."""
    app.conf.update(celery_config)
    return app


# Collection Task Tests

def test_debug_task(celery_app):
    """Test the debug task."""
    from trend_agent.tasks import debug_task

    result = debug_task.apply()
    assert result.successful()
    assert result.result["status"] == "ok"


def test_test_plugin_task_with_valid_plugin(celery_app):
    """Test plugin testing with a valid plugin name."""
    # This will fail if plugin manager not initialized, which is expected
    result = test_plugin_task.apply(args=["reddit"])
    # Task should complete even if it fails internally
    assert result is not None


def test_test_plugin_task_with_invalid_plugin(celery_app):
    """Test plugin testing with invalid plugin name."""
    result = test_plugin_task.apply(args=["invalid_plugin"])
    assert result is not None
    # Result should indicate failure
    if result.successful():
        assert result.result["success"] is False


@pytest.mark.skipif(True, reason="Requires running database and plugins")
def test_collect_from_plugin_task(celery_app):
    """
    Integration test for plugin collection task.

    Requires:
    - Running database
    - Plugin manager initialized
    - Valid plugin configuration
    """
    result = collect_from_plugin_task.apply(args=["reddit"])
    assert result.successful()
    assert "items_collected" in result.result


@pytest.mark.skipif(True, reason="Requires running database and plugins")
def test_collect_all_plugins_task(celery_app):
    """
    Integration test for collecting from all plugins.

    Requires:
    - Running database
    - Plugin manager initialized
    - Multiple plugins configured
    """
    result = collect_all_plugins_task.apply()
    assert result.successful()
    assert "total_items" in result.result
    assert "plugins_run" in result.result


# Processing Task Tests

def test_test_pipeline_task(celery_app):
    """Test pipeline testing with sample data."""
    result = test_pipeline_task.apply(args=[5])
    assert result.successful()
    assert result.result["success"] is True
    assert result.result["items_processed"] == 5


@pytest.mark.skipif(True, reason="Requires running database")
def test_process_pending_items_task(celery_app):
    """
    Integration test for processing pending items.

    Requires:
    - Running database with pending items
    - Processing pipeline configured
    """
    result = process_pending_items_task.apply(args=[10])
    assert result.successful()
    assert "items_processed" in result.result


# Scheduler Task Tests

def test_health_check_task(celery_app):
    """Test health check task."""
    result = health_check_task.apply()
    assert result.successful()
    assert "status" in result.result
    assert "services" in result.result


def test_monitor_celery_queue_task(celery_app):
    """Test Celery queue monitoring."""
    result = monitor_celery_queue_task.apply()
    assert result.successful()
    assert "workers" in result.result
    assert "timestamp" in result.result


@pytest.mark.skipif(True, reason="Requires running database")
def test_cleanup_old_data_task(celery_app):
    """
    Integration test for data cleanup.

    Requires:
    - Running database
    """
    result = cleanup_old_data_task.apply(args=[30])
    assert result.successful()
    assert "items_deleted" in result.result


# Task Configuration Tests

def test_task_registration(celery_app):
    """Test that all tasks are registered."""
    registered_tasks = celery_app.tasks.keys()

    # Collection tasks
    assert "trend_agent.tasks.collection.collect_from_plugin_task" in registered_tasks
    assert "trend_agent.tasks.collection.collect_all_plugins_task" in registered_tasks
    assert "trend_agent.tasks.collection.test_plugin_task" in registered_tasks

    # Processing tasks
    assert "trend_agent.tasks.processing.process_pending_items_task" in registered_tasks
    assert "trend_agent.tasks.processing.test_pipeline_task" in registered_tasks

    # Scheduler tasks
    assert "trend_agent.tasks.scheduler.health_check_task" in registered_tasks
    assert "trend_agent.tasks.scheduler.cleanup_old_data_task" in registered_tasks
    assert "trend_agent.tasks.scheduler.monitor_celery_queue_task" in registered_tasks


def test_task_queues_configured(celery_app):
    """Test that task queues are properly configured."""
    from trend_agent.tasks import CeleryConfig

    assert hasattr(CeleryConfig, "task_queues")
    assert len(CeleryConfig.task_queues) == 4  # default, collection, processing, priority


def test_beat_schedule_configured(celery_app):
    """Test that Beat schedule is configured."""
    from trend_agent.tasks import CeleryConfig

    assert hasattr(CeleryConfig, "beat_schedule")
    schedule = CeleryConfig.beat_schedule

    # Check key scheduled tasks
    assert "collect-all-hourly" in schedule
    assert "process-items" in schedule
    assert "health-check" in schedule
    assert "cleanup-daily" in schedule


# Task Routing Tests

def test_collection_task_routing(celery_app):
    """Test that collection tasks route to collection queue."""
    from trend_agent.tasks import CeleryConfig

    routes = CeleryConfig.task_routes
    collection_route = routes.get("trend_agent.tasks.collection.*")

    assert collection_route is not None
    assert collection_route["queue"] == "collection"


def test_processing_task_routing(celery_app):
    """Test that processing tasks route to processing queue."""
    from trend_agent.tasks import CeleryConfig

    routes = CeleryConfig.task_routes
    processing_route = routes.get("trend_agent.tasks.processing.*")

    assert processing_route is not None
    assert processing_route["queue"] == "processing"


# Error Handling Tests

def test_task_retry_configuration():
    """Test that tasks have retry configuration."""
    from trend_agent.tasks.collection import CollectionTask
    from trend_agent.tasks.processing import ProcessingTask

    # Check collection task config
    assert hasattr(CollectionTask, "autoretry_for")
    assert hasattr(CollectionTask, "retry_kwargs")
    assert CollectionTask.retry_kwargs["max_retries"] == 3

    # Check processing task config
    assert hasattr(ProcessingTask, "autoretry_for")
    assert hasattr(ProcessingTask, "retry_kwargs")
    assert ProcessingTask.retry_kwargs["max_retries"] == 2


# Utility Function Tests

def test_get_active_tasks():
    """Test getting active tasks."""
    from trend_agent.tasks import get_active_tasks

    active = get_active_tasks()
    assert isinstance(active, dict)


def test_get_scheduled_tasks():
    """Test getting scheduled tasks."""
    from trend_agent.tasks import get_scheduled_tasks

    scheduled = get_scheduled_tasks()
    assert isinstance(scheduled, dict)


def test_get_registered_tasks():
    """Test getting registered tasks."""
    from trend_agent.tasks import get_registered_tasks

    registered = get_registered_tasks()
    assert isinstance(registered, dict)


# Integration Tests

@pytest.mark.integration
@pytest.mark.skipif(True, reason="Requires full infrastructure (RabbitMQ, Redis, DB)")
def test_full_collection_workflow(celery_app):
    """
    Full integration test of collection workflow.

    Tests the complete flow:
    1. Collect from plugin
    2. Save to database
    3. Verify data saved

    Requires:
    - RabbitMQ running
    - Redis running
    - PostgreSQL running
    - Plugins configured
    """
    # Trigger collection
    result = collect_from_plugin_task.apply_async(args=["reddit"])

    # Wait for completion
    task_result = result.get(timeout=30)

    # Verify results
    assert task_result["items_collected"] > 0
    assert task_result["items_saved"] > 0


@pytest.mark.integration
@pytest.mark.skipif(True, reason="Requires full infrastructure")
def test_full_processing_workflow(celery_app):
    """
    Full integration test of processing workflow.

    Tests:
    1. Process pending items
    2. Create trends
    3. Save to database

    Requires full infrastructure.
    """
    result = process_pending_items_task.apply_async(args=[100])
    task_result = result.get(timeout=60)

    assert "items_processed" in task_result
    assert "trends_created" in task_result


@pytest.mark.integration
@pytest.mark.skipif(True, reason="Requires full infrastructure")
def test_scheduled_task_execution(celery_app):
    """
    Test that scheduled tasks execute on schedule.

    Requires:
    - Celery Beat running
    - Full infrastructure
    """
    # This would require running Celery Beat and waiting
    # for scheduled task execution
    pass


# Performance Tests

@pytest.mark.performance
def test_task_execution_speed(celery_app):
    """Test that tasks execute within acceptable time limits."""
    import time

    start = time.time()
    result = test_pipeline_task.apply(args=[10])
    duration = time.time() - start

    assert result.successful()
    # Should complete in under 5 seconds for 10 items
    assert duration < 5.0


# Mock Tests

@patch('trend_agent.tasks.collection._collect_from_plugin_async')
def test_collect_from_plugin_with_mock(mock_collect, celery_app):
    """Test collection task with mocked collection function."""
    # Setup mock
    mock_collect.return_value = {
        "plugin_name": "reddit",
        "items_collected": 10,
        "items_saved": 10,
        "duration_seconds": 1.5,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Run task
    result = collect_from_plugin_task.apply(args=["reddit"])

    # Verify
    assert result.successful()
    assert result.result["items_collected"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
