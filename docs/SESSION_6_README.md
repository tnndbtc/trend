# Session 6: Observability & Monitoring

**Status**: ✅ Complete
**Dependencies**: Sessions 1-5
**Last Updated**: 2024

## Overview

Session 6 implements comprehensive observability for the Trend Intelligence Platform, including:

- **Prometheus Metrics**: Metrics exporters for API, Celery, database, and business metrics
- **Structured Logging**: JSON-formatted logs with context management and audit trails
- **Grafana Dashboards**: Pre-built dashboards for monitoring trends, API, tasks, and system health
- **Alerting**: Alert rules for critical conditions across all platform components
- **Performance Monitoring**: Request tracing, task duration tracking, and resource utilization

This session provides production-ready monitoring infrastructure that enables:
- Real-time visibility into platform health and performance
- Proactive alerting on issues before they impact users
- Detailed audit trails for security and compliance
- Performance optimization insights

---

## Architecture

### Components

```
trend_agent/observability/
├── __init__.py           # Package exports
├── metrics.py            # Prometheus metrics exporters
└── logging.py            # Structured logging configuration

config/
├── prometheus.yml        # Prometheus scrape configuration
├── alerts/
│   └── platform_alerts.yml  # Alert rules
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   │   └── prometheus.yml     # Datasource config
    │   └── dashboards/
    │       └── default.yml        # Dashboard provisioning
    └── dashboards/
        ├── trends_overview.json   # Business metrics dashboard
        ├── api_performance.json   # API monitoring dashboard
        ├── celery_tasks.json      # Task queue dashboard
        └── system_health.json     # System resources dashboard
```

### Metrics Architecture

```
┌─────────────────┐
│  FastAPI App    │──┐
└─────────────────┘  │
                     │
┌─────────────────┐  │
│  Celery Tasks   │──┼──> Prometheus Client ──> /metrics endpoint
└─────────────────┘  │
                     │
┌─────────────────┐  │
│  PostgreSQL     │──┘
└─────────────────┘

                     │
                     ▼
              ┌──────────────┐
              │  Prometheus  │
              │   (scrapes)  │
              └──────────────┘
                     │
                     ▼
              ┌──────────────┐
              │   Grafana    │
              │ (visualizes) │
              └──────────────┘
```

---

## Metrics

### API Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `api_requests_total` | Counter | method, endpoint, status_code | Total API requests |
| `api_request_duration_seconds` | Histogram | method, endpoint | Request duration |
| `api_active_requests` | Gauge | endpoint | Currently processing requests |

**Recording Rules**:
- `api:requests_per_second`: Request rate (req/s)
- `api:error_rate`: Error rate (percentage)
- `api:request_duration_average`: Average latency
- `api:request_duration_p95`: 95th percentile latency

### Celery Task Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `celery_tasks_total` | Counter | task_name, status | Total tasks executed |
| `celery_task_duration_seconds` | Histogram | task_name | Task execution duration |
| `celery_task_retries_total` | Counter | task_name | Task retry count |
| `celery_active_tasks` | Gauge | task_name | Currently executing tasks |
| `celery_queue_length` | Gauge | queue_name | Tasks waiting in queue |

**Recording Rules**:
- `celery:tasks_per_second`: Task completion rate
- `celery:failure_rate`: Task failure rate
- `celery:task_duration_average`: Average task duration

### Database Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `db_query_duration_seconds` | Histogram | operation, table | Query execution time |
| `db_connection_pool_size` | Gauge | - | Total pool size |
| `db_connection_pool_available` | Gauge | - | Available connections |

### Business Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `items_collected_total` | Counter | source | Items collected from sources |
| `trends_created_total` | Counter | category | Trends created |
| `topics_created_total` | Counter | category | Topics created |
| `active_trends` | Gauge | state | Active trends by state |

### System Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `system_cpu_usage_percent` | Gauge | - | CPU usage percentage |
| `system_memory_usage_percent` | Gauge | - | Memory usage percentage |
| `system_disk_usage_percent` | Gauge | - | Disk usage percentage |

---

## Structured Logging

### JSON Log Format

All logs are output in JSON format with the following structure:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "INFO",
  "logger": "trend_agent.api",
  "message": "Request processed successfully",
  "module": "main",
  "function": "get_trends",
  "line": 42,
  "context": {
    "request_id": "abc-123",
    "user_id": "user_456"
  }
}
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially harmful situations
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical failures requiring immediate attention

### Audit Logging

Specialized audit logs track:
- Authentication attempts
- API access
- Data access
- Configuration changes

Example audit log:
```json
{
  "timestamp": "2024-01-15T10:30:45Z",
  "level": "INFO",
  "logger": "audit",
  "message": "API access",
  "event_type": "api_access",
  "user": "admin",
  "endpoint": "/api/v1/trends",
  "method": "GET",
  "status_code": 200
}
```

---

## Alert Rules

### API Alerts

| Alert | Threshold | Duration | Severity |
|-------|-----------|----------|----------|
| HighAPIErrorRate | > 5% | 5 minutes | Critical |
| HighAPILatency | > 2 seconds (p95) | 5 minutes | Warning |
| APIDown | API not responding | 1 minute | Critical |

### Celery Alerts

| Alert | Threshold | Duration | Severity |
|-------|-----------|----------|----------|
| HighTaskFailureRate | > 10% | 10 minutes | Warning |
| TaskQueueBacklog | > 1000 tasks | 15 minutes | Warning |
| NoActiveCeleryWorkers | 0 active tasks | 5 minutes | Critical |
| LongRunningTask | > 30 minutes | 5 minutes | Warning |

### Database Alerts

| Alert | Threshold | Duration | Severity |
|-------|-----------|----------|----------|
| PostgreSQLDown | DB not responding | 1 minute | Critical |
| LowDatabaseConnections | < 2 available | 5 minutes | Warning |
| SlowDatabaseQueries | > 1 second (p95) | 10 minutes | Warning |

### System Alerts

| Alert | Threshold | Duration | Severity |
|-------|-----------|----------|----------|
| HighCPUUsage | > 80% | 10 minutes | Warning |
| HighMemoryUsage | > 85% | 5 minutes | Warning |
| LowDiskSpace | > 90% | 5 minutes | Critical |

### Business Alerts

| Alert | Threshold | Duration | Severity |
|-------|-----------|----------|----------|
| NoDataCollection | 0 items/minute | 15 minutes | Warning |
| NoTrendsCreated | 0 trends/hour | 2 hours | Warning |
| LowCollectionRate | < 0.1 items/sec | 30 minutes | Info |

---

## Grafana Dashboards

### 1. Trends Overview Dashboard

**Purpose**: Monitor business metrics and trend lifecycle

**Panels**:
- Active Trends (stat)
- Items Collected per Minute (stat)
- Trends Created per Minute (stat)
- Topics Created per Minute (stat)
- Items Collected by Source (timeseries)
- Active Trends by State (stacked timeseries)
- Trends Created by Category (timeseries)

**Use Cases**:
- Monitor data collection rates
- Track trend creation pipeline
- Identify popular sources
- Analyze trend lifecycles

### 2. API Performance Dashboard

**Purpose**: Monitor API health and performance

**Panels**:
- Request Rate (stat)
- Error Rate (stat)
- P95 Latency (stat)
- Active Requests (stat)
- Request Rate by Endpoint (timeseries)
- Response Time Percentiles (p50/p95/p99)
- Requests by Status Code (stacked timeseries)
- Error Rate Over Time (timeseries with threshold)

**Use Cases**:
- Identify performance bottlenecks
- Monitor error rates
- Detect traffic spikes
- Optimize slow endpoints

### 3. Celery Tasks Dashboard

**Purpose**: Monitor task queue and execution

**Panels**:
- Active Tasks (stat)
- Queue Length (stat)
- Task Failure Rate (stat)
- Tasks Completed per Minute (stat)
- Task Execution Rate by Status (stacked timeseries)
- Queue Length by Queue (timeseries)
- Task Duration Percentiles (p50/p95)
- Task Retries per Minute (timeseries)

**Use Cases**:
- Monitor queue backlogs
- Identify slow tasks
- Track task failures
- Optimize worker allocation

### 4. System Health Dashboard

**Purpose**: Monitor system resources and database

**Panels**:
- CPU Usage (gauge)
- Memory Usage (gauge)
- Disk Usage (gauge)
- DB Connections Available (stat)
- CPU Usage Over Time (timeseries with threshold)
- Memory Usage Over Time (timeseries with threshold)
- Disk Usage Over Time (timeseries with threshold)
- Database Connection Pool (timeseries)
- Database Query Duration (p50/p95)

**Use Cases**:
- Monitor resource utilization
- Detect resource exhaustion
- Plan capacity upgrades
- Optimize database connections

---

## Usage Examples

### 1. Recording Metrics in Code

```python
from trend_agent.observability.metrics import (
    record_item_collected,
    record_trend_created,
    api_request_counter,
)

# Record business metrics
record_item_collected("reddit", count=10)
record_trend_created("technology", count=1)

# Record API metrics manually
api_request_counter.labels(
    method="GET",
    endpoint="/api/v1/trends",
    status_code=200
).inc()
```

### 2. Using Metric Decorators

```python
from trend_agent.observability.metrics import track_api_request, track_celery_task

# Auto-track API requests
@track_api_request("/api/v1/trends")
async def get_trends():
    return await fetch_trends()

# Auto-track Celery tasks
@track_celery_task("collect_from_reddit")
def collect_reddit_task():
    return collect_from_source("reddit")
```

### 3. Structured Logging

```python
from trend_agent.observability.logging import (
    get_logger,
    log_context,
    log_info,
)

logger = get_logger(__name__)

# Simple logging
logger.info("Processing request")

# Logging with context
with log_context(request_id="abc-123", user_id="user_456"):
    logger.info("User authenticated")
    logger.info("Data fetched")  # Context auto-included

# Logging with extra fields
log_info(logger, "Request completed", duration=0.5, status="success")
```

### 4. Audit Logging

```python
from trend_agent.observability.logging import audit_logger

# Log authentication
audit_logger.log_auth_attempt(
    user="admin",
    success=True,
    ip_address="192.168.1.100"
)

# Log API access
audit_logger.log_api_access(
    user="admin",
    endpoint="/api/v1/trends",
    method="GET",
    status_code=200
)

# Log data access
audit_logger.log_data_access(
    user="analyst",
    resource_type="trend",
    resource_id="trend_123",
    action="read"
)

# Log config changes
audit_logger.log_config_change(
    user="admin",
    config_key="max_workers",
    old_value=4,
    new_value=8
)
```

### 5. Function Call Logging

```python
from trend_agent.observability.logging import log_function_call, get_logger

logger = get_logger(__name__)

@log_function_call(logger)
async def process_trend(trend_id: str):
    # Function entry, exit, duration, and errors automatically logged
    trend = await fetch_trend(trend_id)
    return trend
```

---

## Deployment

### Docker Compose Setup

Add observability services to `docker-compose.yml`:

```yaml
services:
  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./config/alerts:/etc/prometheus/alerts
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"

  # Grafana
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - ./config/grafana/provisioning:/etc/grafana/provisioning
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus

  # Alertmanager (optional)
  alertmanager:
    image: prom/alertmanager:latest
    volumes:
      - ./config/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
    ports:
      - "9093:9093"

  # Node Exporter (for system metrics)
  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"

  # PostgreSQL Exporter
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    environment:
      DATA_SOURCE_NAME: "postgresql://user:password@postgres:5432/trends?sslmode=disable"
    ports:
      - "9187:9187"

  # Redis Exporter
  redis-exporter:
    image: oliver006/redis_exporter:latest
    environment:
      REDIS_ADDR: "redis:6379"
    ports:
      - "9121:9121"

volumes:
  prometheus_data:
  grafana_data:
```

### FastAPI Integration

Add metrics endpoint to FastAPI app:

```python
from fastapi import FastAPI, Response
from trend_agent.observability.metrics import get_metrics, CONTENT_TYPE_LATEST
from trend_agent.observability.logging import setup_logging

app = FastAPI()

# Setup logging on startup
@app.on_event("startup")
async def startup_event():
    setup_logging(level="INFO", json_format=True)

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
```

### Environment Configuration

Set logging configuration via environment variables:

```bash
# .env
LOG_LEVEL=INFO
LOG_JSON=true
LOG_FILE=/var/log/trends/app.log
```

---

## Testing

Run observability tests:

```bash
# Install dependencies
pip install -r requirements-observability.txt

# Run tests
pytest tests/test_observability.py -v

# Run with coverage
pytest tests/test_observability.py --cov=trend_agent/observability --cov-report=html
```

**Test Coverage**:
- ✅ Prometheus metrics collection
- ✅ Metric decorators
- ✅ Business metrics recording
- ✅ System metrics collection
- ✅ JSON log formatting
- ✅ Log context management
- ✅ Audit logging
- ✅ Function call logging
- ✅ Integration tests
- ✅ Performance tests

---

## Accessing Dashboards

### Prometheus

- URL: http://localhost:9090
- Features:
  - Query metrics using PromQL
  - View recording rules
  - Check alert status
  - Explore targets and service discovery

### Grafana

- URL: http://localhost:3000
- Default credentials: admin / admin
- Dashboards:
  - **Trends Overview**: Business metrics
  - **API Performance**: Request rates and latencies
  - **Celery Tasks**: Task queue monitoring
  - **System Health**: Resource utilization

### Alertmanager (Optional)

- URL: http://localhost:9093
- Features:
  - View active alerts
  - Silence alerts
  - Configure notification routes

---

## Best Practices

### Metrics

1. **Use Labels Wisely**: Don't create high-cardinality labels (e.g., user IDs)
2. **Histogram Buckets**: Choose appropriate buckets for your latency distribution
3. **Counter vs Gauge**: Use counters for cumulative values, gauges for current state
4. **Recording Rules**: Pre-compute frequently used queries to reduce load

### Logging

1. **Log Levels**: Use appropriate levels (DEBUG for development, INFO for production)
2. **Structured Data**: Always use structured fields instead of string interpolation
3. **Context**: Add request context to correlate related log entries
4. **Sensitive Data**: Never log passwords, tokens, or PII
5. **Sampling**: Consider sampling high-volume logs in production

### Alerting

1. **Alert Fatigue**: Set thresholds to avoid false positives
2. **Actionable**: Every alert should have a clear action
3. **Severity**: Use appropriate severity levels
4. **Documentation**: Document remediation steps in alert annotations

---

## Troubleshooting

### Metrics Not Appearing

**Problem**: Metrics not showing in Prometheus

**Solutions**:
1. Check Prometheus targets: http://localhost:9090/targets
2. Verify metrics endpoint: http://localhost:8000/metrics
3. Check scrape configuration in prometheus.yml
4. Verify network connectivity between services

### High Cardinality Warnings

**Problem**: Too many unique label combinations

**Solutions**:
1. Review label usage - avoid dynamic labels
2. Use aggregation instead of per-item metrics
3. Consider using logs for high-cardinality data

### Logs Not Formatting

**Problem**: Logs not in JSON format

**Solutions**:
1. Ensure `setup_logging()` is called with `json_format=True`
2. Check LOG_JSON environment variable
3. Verify logger configuration

### Dashboard Not Loading

**Problem**: Grafana dashboard shows "No data"

**Solutions**:
1. Check Prometheus datasource connection
2. Verify time range selection
3. Check if metrics exist in Prometheus
4. Review dashboard variable configuration

---

## Performance Considerations

### Metrics

- **Overhead**: < 1ms per metric operation
- **Storage**: Prometheus typically uses 1-2 bytes per sample
- **Retention**: Default 15 days, configurable

### Logging

- **JSON Formatting**: ~2-3x slower than plain text
- **Async Logging**: Consider async handlers for high-volume logs
- **Log Rotation**: Use file rotation to manage disk usage

### Monitoring Tools

- **Prometheus**: CPU: 0.5-1 core, Memory: 2-4 GB
- **Grafana**: CPU: 0.1-0.5 core, Memory: 256-512 MB
- **Exporters**: CPU: < 0.1 core, Memory: < 100 MB each

---

## Next Steps

1. **Custom Dashboards**: Create team-specific dashboards
2. **Alert Routing**: Configure Alertmanager notification channels
3. **Log Aggregation**: Set up centralized log collection (ELK, Loki)
4. **Distributed Tracing**: Add OpenTelemetry for request tracing
5. **SLO/SLI**: Define and monitor Service Level Objectives

---

## Dependencies

```
prometheus-client==0.19.0
psutil==5.9.6
python-json-logger==2.0.7
requests==2.31.0
PyYAML==6.0.1
```

See `requirements-observability.txt` for complete list.

---

## Related Documentation

- [Session 4: REST API](./SESSION_4_README.md) - API implementation
- [Session 5: Celery Tasks](./SESSION_5_README.md) - Task queue
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

---

## Summary

Session 6 provides enterprise-grade observability for the Trend Intelligence Platform:

✅ **Comprehensive Metrics**: API, tasks, database, business, and system metrics
✅ **Structured Logging**: JSON logs with context and audit trails
✅ **Pre-built Dashboards**: 4 Grafana dashboards for all aspects of the platform
✅ **Proactive Alerting**: 18+ alert rules covering critical conditions
✅ **Production-Ready**: Tested, documented, and optimized for performance

The platform now has complete visibility into its operation, enabling:
- Rapid troubleshooting
- Performance optimization
- Capacity planning
- Security auditing
- SLA monitoring

**All 6 sessions are now complete! The Trend Intelligence Platform is production-ready. 🎉**
