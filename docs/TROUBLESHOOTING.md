# Troubleshooting Guide

Common issues and solutions for the AI Trend Intelligence Platform.

---

## Table of Contents

1. [Services Won't Start](#services-wont-start)
2. [Port Conflicts](#port-conflicts)
3. [Database Issues](#database-issues)
4. [API Errors](#api-errors)
5. [Collection Failures](#collection-failures)
6. [Performance Issues](#performance-issues)
7. [Memory Problems](#memory-problems)
8. [Network Issues](#network-issues)
9. [Authentication Problems](#authentication-problems)
10. [Docker Issues](#docker-issues)

---

## Services Won't Start

### Symptom
Services fail to start or immediately exit.

### Check Service Logs

```bash
# Via setup.sh
./setup.sh → 7) View Logs → 8) All Services

# Via docker compose
docker compose logs --tail=50

# Specific service
docker compose logs web
docker compose logs postgres
docker compose logs api
```

### Common Causes

#### 1. Missing Environment Variables

**Error**:
```
Error: OPENAI_API_KEY environment variable not set
```

**Solution**:
```bash
# Check .env.docker exists
ls -la .env.docker

# If not, copy from example
cp .env.docker.example .env.docker

# Edit and add your API key
nano .env.docker
# Set: OPENAI_API_KEY=your_actual_key_here

# Restart services
docker compose down
docker compose up -d
```

#### 2. Docker Daemon Not Running

**Error**:
```
Cannot connect to the Docker daemon
```

**Solution**:
```bash
# Check Docker status
sudo systemctl status docker

# Start Docker
sudo systemctl start docker

# Enable Docker on boot
sudo systemctl enable docker
```

#### 3. Insufficient Permissions

**Error**:
```
Permission denied while trying to connect to the Docker daemon socket
```

**Solution**:
```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Apply group changes (requires logout/login or:)
newgrp docker

# Or run with sudo (not recommended)
sudo docker compose up -d
```

#### 4. Previous Containers Not Stopped

**Error**:
```
Container name already in use
```

**Solution**:
```bash
# Stop all containers
docker compose down

# Remove all containers (keeps volumes)
docker compose down --remove-orphans

# Remove containers and volumes (CAUTION: deletes data)
docker compose down -v

# Start fresh
docker compose up -d
```

---

## Port Conflicts

### Symptom
Service fails to start with "address already in use" error.

### Check Port Usage

```bash
# Check all conflicting ports
sudo lsof -i :11800  # Django Web
sudo lsof -i :8000   # FastAPI
sudo lsof -i :5432   # PostgreSQL
sudo lsof -i :6333   # Qdrant
sudo lsof -i :6379   # Redis
sudo lsof -i :5672   # RabbitMQ
sudo lsof -i :3000   # Grafana
sudo lsof -i :9090   # Prometheus

# Or check all at once
sudo netstat -tulpn | grep -E '(11800|8000|5432|6333|6379|5672|3000|9090)'
```

### Solutions

#### Option 1: Stop Conflicting Service

```bash
# Find process using port
sudo lsof -i :11800

# Kill process (replace PID)
sudo kill -9 <PID>

# Restart platform
docker compose up -d
```

#### Option 2: Change Platform Ports

Edit `docker-compose.yml`:

```yaml
services:
  web:
    ports:
      - "11801:11800"  # Changed from 11800:11800

  api:
    ports:
      - "8001:8000"    # Changed from 8000:8000
```

Update `.env.docker`:
```bash
ALLOWED_HOSTS=localhost:11801,127.0.0.1
CORS_ORIGINS=http://localhost:11801
```

Restart:
```bash
docker compose down
docker compose up -d
```

---

## Database Issues

### PostgreSQL Won't Start

#### Check Logs

```bash
docker compose logs postgres
```

#### Common Issues

**Issue 1: Data Directory Permissions**

```bash
# Remove corrupted volume
docker compose down -v

# Start fresh (CAUTION: deletes all data)
docker compose up -d
```

**Issue 2: Port Already Used**

```bash
# Check if PostgreSQL is running on host
sudo systemctl status postgresql

# Stop host PostgreSQL if not needed
sudo systemctl stop postgresql
sudo systemctl disable postgresql

# Or change container port in docker-compose.yml
```

### Database Connection Errors

#### Symptom
```
django.db.utils.OperationalError: could not connect to server
```

#### Solutions

**1. Check PostgreSQL is Running**

```bash
docker compose ps postgres
# Should show "running" and "healthy"

# If not healthy, check logs
docker compose logs postgres
```

**2. Verify Connection Settings**

```bash
# Check .env.docker has correct values
cat .env.docker | grep POSTGRES

# Should show:
# POSTGRES_HOST=postgres
# POSTGRES_PORT=5432
# POSTGRES_DB=trends
# POSTGRES_USER=trend_user
# POSTGRES_PASSWORD=trend_password
```

**3. Test Connection**

```bash
# From host (requires psql)
PGPASSWORD=trend_password psql -h localhost -p 5432 -U trend_user -d trends

# From container
docker compose exec postgres psql -U trend_user -d trends

# If successful, you'll see:
# trends=#
```

**4. Reset Database**

```bash
# Via setup.sh
./setup.sh → 8) Database Operations → 1) Run Migrations

# Manual
docker compose exec web python manage.py migrate

# If still failing, reset completely
docker compose down -v
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

### Database Performance Issues

#### Symptom
Slow queries, high CPU usage

#### Solutions

**1. Check Connection Pool**

```bash
# In .env.docker, adjust:
DB_POOL_SIZE=20          # Increase if many concurrent requests
DB_MAX_OVERFLOW=10       # Allow burst capacity
DB_POOL_TIMEOUT=30       # Connection timeout
```

**2. Analyze Slow Queries**

```sql
-- Connect to database
docker compose exec postgres psql -U trend_user -d trends

-- Enable query logging
ALTER DATABASE trends SET log_statement = 'all';
ALTER DATABASE trends SET log_min_duration_statement = 1000;  -- Log queries > 1s

-- Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

**3. Add Indexes**

```sql
-- Example: Add index on frequently queried field
CREATE INDEX idx_trends_collected_at ON trends_trend(collected_at);
CREATE INDEX idx_trends_category ON trends_trend(category_id);
CREATE INDEX idx_trends_source ON trends_trend(source);
```

---

## API Errors

### 401 Unauthorized

#### Symptom
```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Invalid API key"
  }
}
```

#### Solutions

**1. Check API Key**

```bash
# View current API keys in .env.docker
cat .env.docker | grep API_KEYS

# Generate new keys
./setup.sh → 10) Generate API Keys

# Or manual
openssl rand -hex 32
```

**2. Use Correct Header**

```bash
# Correct
curl -H "X-API-Key: YOUR_KEY" http://localhost:8000/api/v1/trends

# Wrong (missing header)
curl http://localhost:8000/api/v1/trends
```

**3. Verify API Service is Running**

```bash
docker compose ps api

# If not running, start it
docker compose --profile api up -d
```

### 429 Rate Limit Exceeded

#### Symptom
```json
{
  "detail": "Rate limit exceeded. Try again in 45 seconds.",
  "status_code": 429
}
```

#### Solutions

**1. Wait for Reset**

```bash
# Check Retry-After header
curl -I -H "X-API-Key: YOUR_KEY" \
  http://localhost:8000/api/v1/trends
```

**2. Increase Rate Limits**

In `.env.docker`:
```bash
RATE_LIMIT_DEFAULT=200/minute     # Increased from 100
RATE_LIMIT_SEARCH=60/minute       # Increased from 30
RATE_LIMIT_ADMIN=2000/hour        # Increased from 1000
```

Restart API:
```bash
docker compose restart api
```

**3. Use Admin Key**

Admin keys have higher limits:
```bash
curl -H "X-API-Key: YOUR_ADMIN_KEY" \
  http://localhost:8000/api/v1/trends
```

**4. Disable Rate Limiting (Development Only)**

In `.env.docker`:
```bash
ENABLE_RATE_LIMITING=false
```

### 500 Internal Server Error

#### Check Logs

```bash
docker compose logs api --tail=50

# Look for Python tracebacks
docker compose logs api | grep -A 20 "Traceback"
```

#### Common Causes

**1. Missing Database Connection**

```bash
# Check database is running
docker compose ps postgres

# Test connection
docker compose exec api python -c "import psycopg2; conn = psycopg2.connect('postgresql://trend_user:trend_password@postgres:5432/trends'); print('OK')"
```

**2. Qdrant Not Available**

```bash
# Check Qdrant
docker compose ps qdrant

# Test connection
curl http://localhost:6333/collections
```

**3. Redis Not Available**

```bash
# Check Redis
docker compose ps redis

# Test connection
docker compose exec redis redis-cli ping
# Should return: PONG
```

---

## Collection Failures

### Trends Not Being Collected

#### Check Celery Worker

```bash
# Check worker status
docker compose ps celery-worker

# View worker logs
docker compose logs celery-worker --tail=50

# Check for errors
docker compose logs celery-worker | grep ERROR
```

#### Check Celery Beat (Scheduler)

```bash
# Check beat status
docker compose ps celery-beat

# View schedule
docker compose logs celery-beat | grep "Scheduler: Sending"
```

#### Check RabbitMQ

```bash
# RabbitMQ status
docker compose ps rabbitmq

# View queues
docker compose exec rabbitmq rabbitmqctl list_queues

# Should show celery queue with pending tasks
```

#### Manual Test

```bash
# Trigger collection manually
curl -X POST http://localhost:8000/api/v1/admin/collect \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"max_items": 5}'

# Check task status (use task_id from response)
curl -H "X-API-Key: YOUR_ADMIN_KEY" \
  http://localhost:8000/api/v1/admin/tasks/TASK_ID
```

### API Rate Limits Hit

#### Symptom
```
OpenAI API error: Rate limit exceeded
```

#### Solutions

**1. Use Mock Mode**

In `.env.docker`:
```bash
MOCK_API=1  # Enable mock responses
```

**2. Reduce Collection Frequency**

In `.env.docker`:
```bash
COLLECTION_INTERVAL_DEFAULT=120      # Every 2 hours instead of 1
MAX_ITEMS_PER_CATEGORY=3             # Reduce from 5
```

**3. Add Delays**

In `trends/tasks.py`:
```python
import time

def collect_from_source(source):
    result = source.fetch()
    time.sleep(2)  # 2-second delay between sources
    return result
```

---

## Performance Issues

### Slow API Response

#### Check Response Times

```bash
# Via Prometheus
curl http://localhost:9090/api/v1/query?query=http_request_duration_seconds

# Via logs
docker compose logs api | grep "duration"
```

#### Common Causes

**1. Cache Not Working**

```bash
# Check Redis
docker compose exec redis redis-cli INFO stats

# Check hit rate
docker compose exec redis redis-cli INFO stats | grep keyspace_hits

# Clear cache if corrupted
docker compose exec redis redis-cli FLUSHALL
```

**2. Database Queries**

Enable SQL logging in `.env.docker`:
```bash
SQL_ECHO=true
```

View logs:
```bash
docker compose logs api | grep "SELECT"
```

**3. Missing Indexes**

```sql
-- Check missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND n_distinct > 100
  AND correlation < 0.1;
```

#### Solutions

**1. Increase Cache TTL**

In `.env.docker`:
```bash
CACHE_TTL_DEFAULT=600      # 10 minutes
CACHE_TTL_TRENDS=120       # 2 minutes
CACHE_TTL_SEARCH=300       # 5 minutes
```

**2. Add Database Connection Pool**

In `.env.docker`:
```bash
DB_POOL_SIZE=30           # Increase from 20
DB_MAX_OVERFLOW=20        # Increase from 10
```

**3. Scale Workers**

```bash
# Scale Celery workers
docker compose up -d --scale celery-worker=3

# Scale API instances (requires load balancer)
docker compose up -d --scale api=2
```

### High Memory Usage

#### Check Memory

```bash
docker stats --no-stream

# Or via setup.sh
./setup.sh → 6) Service Status & Health Check
```

#### Solutions

**1. Reduce Worker Concurrency**

In `.env.docker`:
```bash
CELERY_WORKER_CONCURRENCY=2    # Reduce from 4
```

**2. Limit Worker Task Count**

In `.env.docker`:
```bash
CELERY_WORKER_MAX_TASKS_PER_CHILD=50   # Reduce from 100
```

**3. Set Container Limits**

In `docker-compose.yml`:
```yaml
services:
  celery-worker:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

**4. Clear Old Data**

```bash
# Via setup.sh
./setup.sh → 9) Clean Old Data

# Manual
docker compose exec web python manage.py cleanup_old_trends --days=30
```

---

## Memory Problems

### Out of Memory Errors

#### Symptom
```
MemoryError: Unable to allocate array
docker: Error response: container killed by OOM killer
```

#### Check Available Memory

```bash
# System memory
free -h

# Docker memory
docker system df

# Container memory usage
docker stats --no-stream
```

#### Solutions

**1. Increase Docker Memory**

For Docker Desktop:
- Settings → Resources → Memory → Increase to 6-8GB

For Linux:
```bash
# No limit by default, but check:
docker info | grep -i memory
```

**2. Reduce Platform Memory Footprint**

```bash
# Stop observability services (saves ~2GB)
docker compose --profile observability down

# Use basic setup only
./setup.sh → 2) Basic Setup

# Or stop specific services
docker compose stop grafana prometheus jaeger loki
```

**3. Configure Memory Limits**

In `docker-compose.yml`:
```yaml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 512M
```

**4. Clean Docker System**

```bash
# Remove unused images/containers
docker system prune -a

# Remove unused volumes (CAUTION: deletes data)
docker volume prune
```

---

## Network Issues

### Services Can't Communicate

#### Symptom
```
django.db.utils.OperationalError: could not translate host name "postgres"
```

#### Solutions

**1. Check Network**

```bash
# List networks
docker network ls

# Inspect network
docker network inspect trend_default

# Services should be on same network
```

**2. Restart Networking**

```bash
docker compose down
docker network prune
docker compose up -d
```

**3. Check DNS Resolution**

```bash
# From web container
docker compose exec web ping postgres
docker compose exec web ping redis
docker compose exec web ping qdrant

# Should resolve to container IP
```

### External API Timeouts

#### Symptom
```
requests.exceptions.ConnectionError: HTTPSConnectionPool: Max retries exceeded
```

#### Solutions

**1. Check Internet Connection**

```bash
# From host
ping 8.8.8.8
curl https://api.openai.com

# From container
docker compose exec web curl https://api.openai.com
```

**2. Configure Proxy (if needed)**

In `docker-compose.yml`:
```yaml
services:
  web:
    environment:
      - HTTP_PROXY=http://proxy.example.com:8080
      - HTTPS_PROXY=http://proxy.example.com:8080
```

**3. Increase Timeouts**

In code:
```python
import requests

response = requests.get(
    url,
    timeout=30  # Increase from default 10s
)
```

---

## Authentication Problems

### Can't Login to Admin Panel

#### Default Credentials

```
URL: http://localhost:11800/admin
Username: admin
Password: changeme123
```

#### Create New Superuser

```bash
# Via setup.sh
./setup.sh → 5) Manage Categories → Create Superuser

# Manual
docker compose exec web python manage.py createsuperuser
```

#### Reset Password

```bash
docker compose exec web python manage.py shell

# In Python shell:
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(username='admin')
user.set_password('new_password')
user.save()
exit()
```

### API Key Not Working

#### Verify Key is Set

```bash
# Check .env.docker
cat .env.docker | grep API_KEYS
```

#### Verify Service Loaded Key

```bash
# Check API logs for loaded keys (first 8 chars only)
docker compose logs api | grep "API key"
```

#### Generate Fresh Keys

```bash
./setup.sh → 10) Generate API Keys

# Copy output to .env.docker
nano .env.docker

# Restart API
docker compose restart api
```

---

## Docker Issues

### Docker Compose Command Not Found

```bash
# Check Docker Compose version
docker compose version

# If not found, might be using old version:
docker-compose version

# Update Docker to latest version
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

### Image Pull Failures

#### Symptom
```
Error response from daemon: Get https://registry-1.docker.io/v2/: net/http: TLS handshake timeout
```

#### Solutions

```bash
# Retry pull
docker compose pull

# Use different registry mirror (if available)
# Or configure Docker daemon with mirror

# Build images locally if needed
docker compose build
```

### Disk Space Full

```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Clean up
docker system prune -a --volumes  # CAUTION: deletes all unused data

# Remove specific items
docker image prune -a
docker volume prune
docker container prune
```

---

## Quick Diagnostic Commands

### Complete Health Check

```bash
# Via setup.sh (recommended)
./setup.sh → 6) Service Status & Health Check

# Manual checks
curl http://localhost:11800                  # Django Web
curl http://localhost:8000/api/v1/health     # FastAPI API
curl http://localhost:6333/collections       # Qdrant
docker compose exec redis redis-cli ping     # Redis
docker compose exec postgres pg_isready      # PostgreSQL
curl http://localhost:15672                  # RabbitMQ
curl http://localhost:3000/api/health        # Grafana
```

### View All Logs

```bash
# All services
docker compose logs --tail=100 --follow

# Specific service
docker compose logs web --tail=50
docker compose logs api --tail=50
docker compose logs celery-worker --tail=50

# Filter for errors
docker compose logs | grep -i error
docker compose logs | grep -i exception
```

### Check Resource Usage

```bash
docker stats

# Or detailed view
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
```

### Reset Everything

```bash
# Stop all services
docker compose down

# Remove all data (CAUTION: deletes database!)
docker compose down -v

# Clean Docker system
docker system prune -a

# Start fresh
./setup.sh → 1) Full Platform Setup
```

---

## Getting Help

If issues persist:

1. **Check Documentation**:
   - QUICKSTART.md
   - SERVICES.md
   - API_GUIDE.md

2. **View Detailed Logs**:
   ```bash
   ./setup.sh → 7) View Logs
   ```

3. **Check Service Health**:
   ```bash
   ./setup.sh → 6) Service Status & Health Check
   ```

4. **Verify Configuration**:
   ```bash
   cat .env.docker
   docker compose config
   ```

5. **Test Individual Components**:
   ```bash
   # Database
   docker compose exec postgres psql -U trend_user -d trends -c "SELECT 1;"

   # Redis
   docker compose exec redis redis-cli ping

   # API
   curl http://localhost:8000/api/v1/health
   ```

6. **Check GitHub Issues**: Look for similar problems in the repository

7. **Create Issue**: If all else fails, create a detailed issue with:
   - Error messages
   - Logs (`docker compose logs`)
   - Configuration (`.env.docker` with secrets removed)
   - Steps to reproduce

---

## Common Error Messages

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| `could not connect to server` | PostgreSQL not running | Check `docker compose ps postgres` |
| `Connection refused` | Service not started | Start with `docker compose up -d` |
| `Address already in use` | Port conflict | Check ports with `lsof -i :PORT` |
| `No such container` | Container not created | Run `docker compose up -d` |
| `Permission denied` | Docker permissions | Add user to docker group |
| `Out of memory` | Insufficient RAM | Increase Docker memory or reduce services |
| `API key required` | Missing auth header | Add `X-API-Key` header |
| `Rate limit exceeded` | Too many requests | Wait or increase limits |
| `Timeout` | Service taking too long | Check logs and resource usage |

---

## Prevention Tips

1. **Monitor Resources**: Keep an eye on memory/CPU usage
2. **Regular Backups**: Use `./setup.sh → 8) Database Operations → 2) Create Backup`
3. **Update Regularly**: Pull latest changes and rebuild
4. **Review Logs**: Check logs periodically for warnings
5. **Test After Changes**: Verify platform works after config changes
6. **Use Mock Mode**: Set `MOCK_API=1` during development
7. **Set Resource Limits**: Configure memory/CPU limits in docker-compose.yml
8. **Clean Old Data**: Run `./setup.sh → 9) Clean Old Data` periodically

---

**Still having issues?** Check the logs with `./setup.sh → 7)` and review the error messages above!
