# Session 5: Celery Task Queue - Implementation Complete ✅

## Overview

Session 5 successfully implemented a **production-ready Celery task queue** with background task processing, periodic scheduling, and comprehensive monitoring for the Trend Intelligence Platform.

---

## 🎯 Success Criteria

- [x] Celery app configured with proper broker and backend
- [x] Collection tasks implemented (plugin data collection)
- [x] Processing tasks implemented (pipeline execution)
- [x] Scheduled periodic tasks configured with Celery Beat
- [x] Flower monitoring UI configured
- [x] Task error handling and retry logic
- [x] Tests created for task execution
- [x] Documentation complete

---

## 📦 Components Implemented

### 1. **Celery Application** (`trend_agent/tasks/__init__.py`)

**Purpose**: Core Celery application configuration with broker, backend, and task routing.

**Features**:
- RabbitMQ message broker integration
- Redis result backend
- Task routing to specific queues
- Retry configuration with exponential backoff
- Periodic task scheduling with Celery Beat
- Task monitoring and error handling
- Multiple task queues (default, collection, processing, priority)

**Configuration Highlights**:
```python
# Broker and backend
broker_url = "amqp://guest:guest@localhost:5672//"
result_backend = "redis://localhost:6379/1"

# Task queues
- default: General tasks
- collection: Data collection tasks
- processing: Pipeline processing tasks
- priority: High-priority tasks

# Periodic schedules
- Hourly: Collect from all plugins
- Every 15min: High-frequency sources
- Every 30min: Process pending items
- Daily 3AM: Cleanup old data
- Every 5min: Health checks
```

---

### 2. **Collection Tasks** (`trend_agent/tasks/collection.py`)

**Purpose**: Background tasks for collecting data from plugins.

**Tasks Implemented**:

#### `collect_from_plugin_task(plugin_name)`
- Collect data from a specific plugin
- Save items to database
- Track collection metrics
- Auto-retry on failure (max 3 retries)

#### `collect_all_plugins_task()`
- Collect from all enabled plugins in parallel
- Uses Celery groups for concurrent execution
- Aggregates results from all plugins
- Returns total items collected

#### `collect_high_frequency_task()`
- Collect from high-frequency sources (Reddit, HackerNews)
- Runs every 15 minutes
- Optimized for quick updates

#### `collect_and_process_task(plugin_name)`
- Chained task: collect → process
- End-to-end workflow
- Returns combined results

#### `test_plugin_task(plugin_name)`
- Test plugin without saving data
- Useful for debugging
- Returns sample items

**Example Usage**:
```python
# Trigger collection asynchronously
from trend_agent.tasks.collection import collect_from_plugin_task

# Queue the task
result = collect_from_plugin_task.delay("reddit")

# Get result (blocks until complete)
collection_result = result.get(timeout=300)
print(f"Collected {collection_result['items_collected']} items")
```

---

### 3. **Processing Tasks** (`trend_agent/tasks/processing.py`)

**Purpose**: Background tasks for running the processing pipeline.

**Tasks Implemented**:

#### `process_pending_items_task(limit=1000)`
- Process unprocessed items through pipeline
- Generate topics and trends
- Save results to database
- Auto-retry on failure (max 2 retries)

#### `reprocess_trends_task(hours=24)`
- Update existing trends
- Recalculate scores and states
- Update trending status

#### `generate_embeddings_task(item_ids, limit=100)`
- Generate embeddings for items
- Store in Qdrant vector database
- Batch processing support

#### `test_pipeline_task(sample_size=10)`
- Test pipeline with sample data
- No database required
- Returns test results

**Example Usage**:
```python
from trend_agent.tasks.processing import process_pending_items_task

# Process up to 500 items
result = process_pending_items_task.delay(500)

# Wait for completion
process_result = result.get(timeout=900)  # 15 min timeout
print(f"Created {process_result['trends_created']} trends")
```

---

### 4. **Scheduler Tasks** (`trend_agent/tasks/scheduler.py`)

**Purpose**: Periodic maintenance and monitoring tasks.

**Tasks Implemented**:

#### `health_check_task()`
- Check all service health (PostgreSQL, Redis, Qdrant)
- Monitor system resources (disk, memory)
- Runs every 5 minutes
- Logs warnings for degraded services

#### `cleanup_old_data_task(days=30)`
- Delete old items and trends
- Clean up expired data
- Runs daily at 3 AM
- Prevents database bloat

#### `update_plugin_health_task()`
- Update plugin health metrics
- Track success rates
- Identify failing plugins

#### `generate_analytics_task()`
- Generate trend analytics
- Calculate statistics
- Store for reporting

#### `backup_database_task()`
- Create PostgreSQL backup
- Uses pg_dump
- Stores in configured location

#### `monitor_celery_queue_task()`
- Monitor queue sizes
- Check worker status
- Alert on high queue depths

**Example Schedule**:
```python
beat_schedule = {
    "collect-all-hourly": {
        "task": "collect_all_plugins_task",
        "schedule": crontab(minute=0),  # Every hour
    },
    "process-items": {
        "task": "process_pending_items_task",
        "schedule": crontab(minute="*/30"),  # Every 30 min
    },
    "cleanup-daily": {
        "task": "cleanup_old_data_task",
        "schedule": crontab(hour=3, minute=0),  # 3 AM daily
    },
}
```

---

### 5. **Flower Monitoring** (`config/flowerconfig.py`)

**Purpose**: Web-based Celery task monitoring interface.

**Features**:
- Real-time task monitoring
- Worker status tracking
- Task history and statistics
- Queue depth visualization
- Task retry monitoring
- Performance metrics
- Auto-refresh every 3 seconds

**Access**: http://localhost:5555

**Key Metrics**:
- Active tasks
- Queued tasks
- Completed tasks
- Failed tasks
- Worker health
- Task execution time

**Configuration**:
```python
# Flower settings
address = "0.0.0.0"
port = 5555
max_tasks = 10000
persistent = True
auto_refresh = True
```

---

## 🚀 Running Celery

### Start Celery Worker

```bash
# Start worker for all queues
celery -A trend_agent.tasks worker --loglevel=info

# Start worker for specific queue
celery -A trend_agent.tasks worker -Q collection --loglevel=info

# Start with concurrency setting
celery -A trend_agent.tasks worker --concurrency=4

# Start with autoscaling
celery -A trend_agent.tasks worker --autoscale=10,3
```

### Start Celery Beat (Scheduler)

```bash
# Start Beat scheduler
celery -A trend_agent.tasks beat --loglevel=info

# With custom schedule file
celery -A trend_agent.tasks beat -s /tmp/celerybeat-schedule
```

### Start Flower Monitoring

```bash
# Start Flower
flower -A trend_agent.tasks --conf=config/flowerconfig.py

# Or with basic auth
flower -A trend_agent.tasks --basic_auth=admin:password
```

### Docker Compose

```bash
# Start all Celery services
docker-compose up celery-worker celery-beat flower

# Scale workers
docker-compose up --scale celery-worker=3
```

---

## 🧪 Testing

### Run Task Tests

```bash
# Install dependencies
pip install -r requirements-tasks.txt

# Run all task tests
pytest tests/test_celery_tasks.py -v

# Run specific test
pytest tests/test_celery_tasks.py::test_test_pipeline_task -v

# Run integration tests (requires infrastructure)
pytest tests/test_celery_tasks.py -m integration -v
```

### Test Coverage

✅ **Task Registration** (3 tests)
- Task discovery
- Queue configuration
- Beat schedule

✅ **Collection Tasks** (5 tests)
- Plugin collection
- All plugins collection
- Test plugin

✅ **Processing Tasks** (3 tests)
- Process pending items
- Test pipeline
- Embedding generation

✅ **Scheduler Tasks** (3 tests)
- Health check
- Cleanup
- Queue monitoring

✅ **Configuration Tests** (4 tests)
- Task routing
- Retry configuration
- Queue setup

✅ **Integration Tests** (3 tests)
- Full collection workflow
- Full processing workflow
- Scheduled execution

**Total: 21+ test cases**

---

## 📊 Task Monitoring

### Using Flower UI

1. **Access Flower**: http://localhost:5555
2. **View Dashboard**: See active/queued/completed tasks
3. **Monitor Workers**: Check worker health and capacity
4. **View Task Details**: Click any task for full details
5. **Inspect Errors**: View failed tasks and tracebacks

### Using Celery Inspect

```python
from trend_agent.tasks import app

inspect = app.control.inspect()

# Get active tasks
active = inspect.active()
print(f"Active tasks: {active}")

# Get scheduled tasks
scheduled = inspect.scheduled()

# Get registered tasks
registered = inspect.registered()

# Get worker stats
stats = inspect.stats()
```

### Using Python API

```python
from trend_agent.tasks import (
    get_active_tasks,
    get_scheduled_tasks,
    get_registered_tasks,
)

# Get current task status
active = get_active_tasks()
scheduled = get_scheduled_tasks()
registered = get_registered_tasks()
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Celery Broker (RabbitMQ)
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//

# Result Backend (Redis)
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Flower
FLOWER_HOST=0.0.0.0
FLOWER_PORT=5555
FLOWER_DB=/tmp/flower.db

# Database (for tasks)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trends
POSTGRES_USER=trend_user
POSTGRES_PASSWORD=trend_password
```

### Worker Configuration

```python
# In CeleryConfig
worker_prefetch_multiplier = 1  # Tasks per worker
worker_max_tasks_per_child = 1000  # Restart after N tasks
task_acks_late = True  # Acknowledge after completion
task_reject_on_worker_lost = True  # Requeue on crash
```

---

## 📈 Performance Optimization

### Concurrency Settings

```bash
# CPU-bound tasks
celery -A trend_agent.tasks worker --pool=prefork --concurrency=4

# I/O-bound tasks
celery -A trend_agent.tasks worker --pool=gevent --concurrency=100

# Autoscaling
celery -A trend_agent.tasks worker --autoscale=10,2
```

### Queue Prioritization

```python
# Send to priority queue
task.apply_async(queue="priority", priority=10)

# Route specific tasks to specific queues
task_routes = {
    "urgent_task": {"queue": "priority"},
    "bulk_task": {"queue": "default"},
}
```

### Task Time Limits

```python
# Hard time limit (kills task)
@app.task(time_limit=600)  # 10 minutes
def long_running_task():
    pass

# Soft time limit (raises exception)
@app.task(soft_time_limit=300)  # 5 minutes
def monitored_task():
    pass
```

---

## 🔗 Integration with Other Sessions

### With Session 2 (Ingestion)

```python
# Collection tasks use plugin manager
from trend_agent.ingestion.manager import DefaultPluginManager

# Collect from plugins
plugin_manager = DefaultPluginManager()
await plugin_manager.load_plugins()
```

### With Session 3 (Processing)

```python
# Processing tasks use pipeline
from trend_agent.processing import create_standard_pipeline

# Run pipeline
pipeline = create_standard_pipeline(embedding_svc)
result = await pipeline.run(raw_items)
```

### With Session 4 (API)

```python
# API can trigger tasks
from trend_agent.tasks.collection import collect_all_plugins_task

@router.post("/admin/collect")
async def trigger_collection():
    task = collect_all_plugins_task.delay()
    return {"task_id": task.id}
```

---

## 🐛 Error Handling

### Automatic Retries

```python
class CollectionTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True  # Exponential backoff
    retry_backoff_max = 600  # Max 10 minutes
    retry_jitter = True  # Add random jitter
```

### Manual Task Cancellation

```python
from trend_agent.tasks import cancel_task

# Cancel a running task
cancel_task(task_id)
```

### Failed Task Recovery

```python
# Retry failed task
from celery import current_app

task = current_app.tasks["task_name"]
task.retry(countdown=60)  # Retry in 60 seconds
```

---

## 📊 Scheduled Tasks Summary

| Task | Schedule | Purpose | Queue |
|------|----------|---------|-------|
| collect-all-hourly | Every hour | Collect from all plugins | collection |
| collect-high-frequency | Every 15 min | Quick updates (Reddit, HN) | collection |
| process-items | Every 30 min | Process pending items | processing |
| cleanup-daily | Daily 3 AM | Delete old data | default |
| health-check | Every 5 min | System health check | default |

---

## 🎉 Session 5 Complete!

**Status:** ✅ **COMPLETE**

**Delivered**:
- ✅ Celery app with RabbitMQ and Redis
- ✅ 3 task modules (collection, processing, scheduler)
- ✅ 15+ background tasks
- ✅ Periodic scheduling with Celery Beat
- ✅ Flower monitoring UI
- ✅ Error handling and retries
- ✅ Task routing and queues
- ✅ 21+ test cases
- ✅ Production-ready configuration

**Lines of Code**: ~2,000+ lines

**Files Created**: 6 files

**Next Session**: Session 6 - Observability (Prometheus, Grafana, Logging)

---

## 📞 Quick Reference

### Start All Services

```bash
# Terminal 1: RabbitMQ
docker-compose up rabbitmq

# Terminal 2: Redis
docker-compose up redis

# Terminal 3: Celery Worker
celery -A trend_agent.tasks worker --loglevel=info

# Terminal 4: Celery Beat
celery -A trend_agent.tasks beat --loglevel=info

# Terminal 5: Flower
flower -A trend_agent.tasks --conf=config/flowerconfig.py
```

### Trigger Tasks Manually

```bash
# Using Python
python -c "from trend_agent.tasks.collection import collect_all_plugins_task; collect_all_plugins_task.delay()"

# Using Celery CLI
celery -A trend_agent.tasks call trend_agent.tasks.collection.collect_all_plugins_task
```

### Monitor Tasks

```bash
# View active tasks
celery -A trend_agent.tasks inspect active

# View scheduled tasks
celery -A trend_agent.tasks inspect scheduled

# View worker stats
celery -A trend_agent.tasks inspect stats

# Purge all tasks
celery -A trend_agent.tasks purge
```

---

**Session 5 Team**
*Trend Intelligence Platform Development*
