# Monitoring & Observability Guide

**Trend Intelligence Platform - Observability Stack**

This guide explains how to use the monitoring and observability stack for the Trend Intelligence Platform, including Prometheus metrics, Grafana dashboards, and alerting.

---

## 📊 Overview

The platform includes a complete observability stack with:

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization dashboards
- **Exporters**: PostgreSQL, Redis, Node system metrics
- **Custom Metrics**: API, Celery tasks, business metrics

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Grafana Dashboards                    │
│  (Visualization & Analysis on port 3000)                │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                   Prometheus Server                      │
│  (Metrics Collection & Alerting on port 9090)           │
└──┬───┬───┬────┬────┬────┬────┬──────────────────────────┘
   │   │   │    │    │    │    │
   │   │   │    │    │    │    └─> Business Metrics
   │   │   │    │    │    └──────> Celery Worker (9091)
   │   │   │    │    └───────────> FastAPI App (8000)
   │   │   │    └────────────────> Node Exporter (9100)
   │   │   └─────────────────────> Redis Exporter (9121)
   │   └─────────────────────────> Postgres Exporter (9187)
   └─────────────────────────────> Prometheus Self-monitoring
```

---

## 🚀 Quick Start

### Starting the Monitoring Stack

Start all services including monitoring:

```bash
# Start with observability profile
docker compose --profile observability up -d

# Or start specific services
docker compose up -d prometheus grafana
```

### Accessing Dashboards

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | None |
| **RabbitMQ Management** | http://localhost:15672 | trend_user / trend_password |

### Initial Setup

1. **Access Grafana** at http://localhost:3000
2. **Login** with admin/admin (change password on first login)
3. **Navigate** to Dashboards → Browse
4. **View** pre-configured dashboards:
   - Trends Overview
   - API Performance
   - Celery Tasks
   - System Health

---

## 📈 Available Metrics

### API Metrics

**Counter metrics:**
- `api_requests_total{method, endpoint, status_code}` - Total API requests
- Labels: HTTP method, endpoint path, status code

**Histogram metrics:**
- `api_request_duration_seconds{method, endpoint}` - Request latency
- Buckets: 0.01s, 0.05s, 0.1s, 0.5s, 1.0s, 2.5s, 5.0s, 10.0s

**Gauge metrics:**
- `api_active_requests{endpoint}` - Currently processing requests

**Recording rules (pre-computed):**
- `api:error_rate` - Percentage of 5xx responses
- `api:request_duration_p95` - 95th percentile latency

### Celery Task Metrics

**Counter metrics:**
- `celery_tasks_total{task_name, status}` - Total tasks executed
- `celery_task_retries_total{task_name}` - Task retry count

**Histogram metrics:**
- `celery_task_duration_seconds{task_name}` - Task execution time
- Buckets: 1s, 5s, 10s, 30s, 60s, 120s, 300s, 600s, 1800s

**Gauge metrics:**
- `celery_active_tasks{task_name}` - Currently executing tasks
- `celery_queue_length{queue_name}` - Tasks waiting in queue

**Recording rules:**
- `celery:failure_rate` - Percentage of failed tasks
- `celery:task_duration_average` - Average task duration

### Business Metrics

**Counter metrics:**
- `items_collected_total{source}` - Items collected per source
- `trends_created_total{category}` - Trends created per category
- `topics_created_total{category}` - Topics created per category

**Gauge metrics:**
- `active_trends{state}` - Active trends by state
  - States: emerging, viral, sustained, declining

### Database Metrics

**Histogram metrics:**
- `db_query_duration_seconds{operation, table}` - Query execution time
- Operations: SELECT, INSERT, UPDATE, DELETE

**Gauge metrics:**
- `db_connection_pool_size` - Total pool size
- `db_connection_pool_available` - Available connections

**PostgreSQL Exporter metrics:**
- `pg_stat_database_*` - Database statistics
- `pg_stat_user_tables_*` - Table statistics
- `pg_locks_count` - Active locks

### System Metrics

**Gauge metrics (custom):**
- `system_cpu_usage_percent` - CPU usage
- `system_memory_usage_percent` - Memory usage
- `system_disk_usage_percent` - Disk usage

**Node Exporter metrics:**
- `node_cpu_seconds_total` - CPU time
- `node_memory_*` - Memory details
- `node_disk_*` - Disk I/O
- `node_network_*` - Network statistics

---

## 📊 Grafana Dashboards

### 1. Trends Overview Dashboard

**Purpose:** Monitor business metrics and data collection

**Panels:**
- Active Trends (gauge)
- Items Collected per Minute (stat)
- Trends Created per Minute (stat)
- Topics Created per Minute (stat)
- Items Collected by Source (timeseries)
- Active Trends by State (timeseries)
- Trends Created by Category (timeseries)

**Use Cases:**
- Monitor data collection health
- Track trend creation rate
- Identify which sources are most active
- Analyze trend lifecycle distribution

### 2. API Performance Dashboard

**Purpose:** Monitor API health and performance

**Panels:**
- Request Rate (stat with thresholds)
- Error Rate (stat with thresholds)
- P95 Latency (stat with thresholds)
- Active Requests (stat)
- Request Rate by Endpoint (timeseries)
- Response Time Percentiles (p50, p95, p99)
- Requests by Status Code (timeseries)
- Error Rate Over Time (timeseries)

**Thresholds:**
- Error Rate: Green < 1%, Yellow < 5%, Red ≥ 5%
- Latency: Green < 0.5s, Yellow < 2s, Red ≥ 2s

### 3. Celery Tasks Dashboard

**Purpose:** Monitor task queue and worker performance

**Panels:**
- Active Tasks (stat)
- Queue Length (stat with thresholds)
- Task Failure Rate (stat)
- Tasks Completed per Minute (stat)
- Task Execution Rate by Status (timeseries)
- Queue Length by Queue (timeseries)
- Task Duration Percentiles (p50, p95)
- Task Retries per Minute (timeseries)

**Thresholds:**
- Queue Length: Green < 500, Yellow < 1000, Red ≥ 1000
- Failure Rate: Green < 5%, Yellow < 10%, Red ≥ 10%

### 4. System Health Dashboard

**Purpose:** Monitor system resources and infrastructure

**Panels:**
- CPU Usage (gauge with thresholds)
- Memory Usage (gauge with thresholds)
- Disk Usage (gauge with thresholds)
- DB Connections Available (stat)
- CPU Usage Over Time (timeseries)
- Memory Usage Over Time (timeseries)
- Disk Usage Over Time (timeseries)
- Database Connection Pool (timeseries)
- Database Query Duration (timeseries)

**Thresholds:**
- CPU: Green < 60%, Yellow < 80%, Red ≥ 80%
- Memory: Green < 70%, Yellow < 85%, Red ≥ 85%
- Disk: Green < 80%, Yellow < 90%, Red ≥ 90%

---

## 🚨 Alert Rules

Alerts are defined in `config/alerts/platform_alerts.yml` and organized into groups:

### API Alerts

| Alert | Condition | Duration | Severity |
|-------|-----------|----------|----------|
| HighAPIErrorRate | Error rate > 5% | 5 min | Critical |
| HighAPILatency | P95 latency > 2s | 5 min | Warning |
| APIDown | API not responding | 1 min | Critical |

### Celery Alerts

| Alert | Condition | Duration | Severity |
|-------|-----------|----------|----------|
| HighTaskFailureRate | Failure rate > 10% | 10 min | Warning |
| TaskQueueBacklog | Queue > 1000 tasks | 15 min | Warning |
| NoActiveCeleryWorkers | No active tasks | 5 min | Critical |
| LongRunningTask | Task running > 30 min | 5 min | Warning |

### Database Alerts

| Alert | Condition | Duration | Severity |
|-------|-----------|----------|----------|
| PostgreSQLDown | DB not responding | 1 min | Critical |
| LowDatabaseConnections | < 2 connections available | 5 min | Warning |
| SlowDatabaseQueries | P95 query time > 1s | 10 min | Warning |

### System Alerts

| Alert | Condition | Duration | Severity |
|-------|-----------|----------|----------|
| HighCPUUsage | CPU > 80% | 10 min | Warning |
| HighMemoryUsage | Memory > 85% | 5 min | Warning |
| LowDiskSpace | Disk > 90% | 5 min | Critical |

### Business Alerts

| Alert | Condition | Duration | Severity |
|-------|-----------|----------|----------|
| NoDataCollection | No items collected | 15 min | Warning |
| NoTrendsCreated | No trends created | 2 hours | Warning |
| LowCollectionRate | < 0.1 items/sec | 30 min | Info |

---

## 🔧 Configuration

### Prometheus Configuration

**File:** `config/prometheus.yml`

**Scrape Targets:**
- `trend-api:8000/metrics` - FastAPI metrics
- `celery-worker:9091` - Celery worker metrics
- `postgres-exporter:9187` - PostgreSQL metrics
- `redis-exporter:9121` - Redis metrics
- `node-exporter:9100` - System metrics

**Scrape Interval:** 15 seconds
**Evaluation Interval:** 15 seconds

### Grafana Provisioning

Dashboards are automatically provisioned from:
- `config/grafana/dashboards/` - Dashboard JSON files
- `config/grafana/datasources/` - Datasource configuration

To add a new dashboard:
1. Create/export dashboard JSON
2. Place in `config/grafana/dashboards/`
3. Restart Grafana or wait for auto-reload

---

## 📝 Instrumentation Guide

### Adding Metrics to Code

#### 1. API Endpoint Metrics

```python
from trend_agent.observability.metrics import (
    api_request_counter,
    api_request_duration,
    api_active_requests,
)

@router.get("/api/v1/trends")
async def get_trends():
    start_time = time.time()
    api_active_requests.labels(endpoint="/api/v1/trends").inc()

    try:
        result = await fetch_trends()
        status_code = 200
        return result
    except Exception as e:
        status_code = 500
        raise
    finally:
        duration = time.time() - start_time
        api_request_duration.labels(
            method="GET",
            endpoint="/api/v1/trends"
        ).observe(duration)

        api_request_counter.labels(
            method="GET",
            endpoint="/api/v1/trends",
            status_code=status_code
        ).inc()

        api_active_requests.labels(endpoint="/api/v1/trends").dec()
```

#### 2. Celery Task Metrics

Use the provided decorator:

```python
from trend_agent.observability.metrics import track_celery_task

@app.task
@track_celery_task("collect_from_reddit")
def collect_from_reddit_task():
    # Task logic here
    pass
```

Or manually instrument:

```python
from trend_agent.observability.metrics import (
    celery_task_counter,
    celery_task_duration,
    celery_active_tasks,
)

def my_task():
    start_time = time.time()
    celery_active_tasks.labels(task_name="my_task").inc()

    try:
        # Task logic
        status = "success"
    except Exception:
        status = "failure"
        raise
    finally:
        duration = time.time() - start_time
        celery_task_duration.labels(task_name="my_task").observe(duration)
        celery_task_counter.labels(task_name="my_task", status=status).inc()
        celery_active_tasks.labels(task_name="my_task").dec()
```

#### 3. Business Metrics

```python
from trend_agent.observability.metrics import (
    record_item_collected,
    record_trend_created,
    update_active_trends,
)

# After collecting items
for item in collected_items:
    record_item_collected(source="reddit", count=1)

# After creating trend
record_trend_created(category="technology", count=1)

# Update active trends gauge
update_active_trends(state="viral", count=5)
```

#### 4. Database Metrics

Use the decorator for automatic query tracking:

```python
from trend_agent.observability.metrics import track_db_query

@track_db_query("SELECT", "trends")
async def get_trend_by_id(trend_id: str):
    query = "SELECT * FROM trends WHERE id = $1"
    result = await conn.fetchrow(query, trend_id)
    return result
```

---

## 🔍 Common Queries

### Prometheus Queries

**Request rate by endpoint:**
```promql
rate(api_requests_total[5m])
```

**Error percentage:**
```promql
sum(rate(api_requests_total{status_code=~"5.."}[5m])) /
sum(rate(api_requests_total[5m])) * 100
```

**P95 latency:**
```promql
histogram_quantile(0.95,
  rate(api_request_duration_seconds_bucket[5m]))
```

**Task success rate:**
```promql
sum(rate(celery_tasks_total{status="success"}[5m])) /
sum(rate(celery_tasks_total[5m])) * 100
```

**Items collected per source (last hour):**
```promql
sum by(source) (
  increase(items_collected_total[1h])
)
```

**Slow database queries:**
```promql
histogram_quantile(0.99,
  sum by(operation, le) (
    rate(db_query_duration_seconds_bucket[5m])
  )
) > 0.5
```

---

## 🐛 Troubleshooting

### Prometheus Not Scraping Metrics

**Symptoms:** No data in Grafana, empty graphs

**Solutions:**
1. Check Prometheus targets: http://localhost:9090/targets
2. Verify service is exposing metrics:
   ```bash
   curl http://localhost:8000/metrics
   curl http://localhost:9091/metrics
   ```
3. Check Docker network:
   ```bash
   docker compose ps
   docker compose logs prometheus
   ```
4. Verify service names in `prometheus.yml` match docker-compose

### Grafana Dashboard Shows No Data

**Solutions:**
1. Check Prometheus datasource:
   - Grafana → Configuration → Data Sources
   - Test connection
2. Verify time range matches data availability
3. Check Prometheus has data:
   - Visit http://localhost:9090
   - Run query: `up{job="trend-api"}`
4. Review panel queries for syntax errors

### Celery Metrics Not Appearing

**Solutions:**
1. Verify Celery worker is running:
   ```bash
   docker compose ps celery-worker
   ```
2. Check if metrics exporter is started:
   ```bash
   docker compose logs celery-worker | grep "Prometheus metrics"
   ```
3. Ensure `start_metrics_exporter()` is called in worker startup
4. Verify port 9091 is exposed in docker-compose.yml

### High Memory Usage in Prometheus

**Solutions:**
1. Reduce retention period in prometheus.yml:
   ```yaml
   --storage.tsdb.retention.time=30d
   ```
2. Reduce scrape frequency for less critical targets
3. Use recording rules to pre-compute expensive queries
4. Increase Prometheus resource limits in docker-compose

### Alerts Not Firing

**Solutions:**
1. Check alert rules are loaded:
   - Prometheus → Status → Rules
2. Verify alertmanager is running:
   ```bash
   docker compose ps alertmanager
   ```
3. Check alert conditions in `config/alerts/platform_alerts.yml`
4. View pending/firing alerts: http://localhost:9090/alerts

---

## 📚 Best Practices

### Metric Naming

Follow Prometheus naming conventions:
- Use lowercase with underscores: `api_requests_total`
- Include unit suffix: `_seconds`, `_bytes`, `_percent`
- Counters end in `_total`: `items_collected_total`
- Use labels for dimensions, not metric names

### Cardinality

Keep label cardinality low to avoid performance issues:
- ✅ Good: `endpoint="/api/v1/trends"` (10-20 unique values)
- ❌ Bad: `user_id="12345"` (thousands/millions of values)
- Use aggregation and sampling for high-cardinality data

### Dashboard Design

- Group related metrics together
- Use appropriate visualization types:
  - **Gauge**: Resource usage (CPU, memory)
  - **Stat**: Latest value (current queue length)
  - **Timeseries**: Trends over time (request rate)
  - **Heatmap**: Distribution (latency percentiles)
- Set meaningful thresholds with colors
- Include time context (e.g., "per second", "per minute")

### Alert Tuning

- Set appropriate `for` duration to avoid flapping
- Use severity levels: info, warning, critical
- Include actionable information in annotations
- Test alerts with simulated conditions
- Review and tune alert thresholds regularly

---

## 🔗 Related Documentation

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards Guide](https://grafana.com/docs/grafana/latest/dashboards/)
- [PostgreSQL Exporter](https://github.com/prometheus-community/postgres_exporter)
- [Redis Exporter](https://github.com/oliver006/redis_exporter)
- [Node Exporter](https://github.com/prometheus/node_exporter)

---

## 📞 Support

For monitoring-related issues:
1. Check Prometheus logs: `docker compose logs prometheus`
2. Check Grafana logs: `docker compose logs grafana`
3. Review exporter logs: `docker compose logs postgres-exporter`
4. Verify metrics endpoint: `curl http://localhost:8000/metrics`

---

**Last Updated:** February 2026
**Version:** 1.0.0
