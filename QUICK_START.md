# Quick Start Guide - Parallel Development

## 🚀 Start Multiple Sessions

### Terminal Setup

```bash
# Open 6 terminals, in each:
cd ~/data/code/trend
claude code

# In Claude Code, say:
"I'm working on Session [1-6] from PARALLEL_DEVELOPMENT_GUIDE.md"
```

---

## 📋 Session Assignments

| Session | Component | Branch | Priority |
|---------|-----------|--------|----------|
| **1** | Storage Layer (PostgreSQL, Qdrant, Redis) | `feature/storage-layer` | 🔴 HIGHEST (Foundation) |
| **2** | Ingestion Plugins (Refactor collectors) | `feature/ingestion-plugins` | 🟡 HIGH |
| **3** | Processing Pipeline (Enhance pipeline) | `feature/processing-pipeline` | 🟡 MEDIUM |
| **4** | FastAPI REST/GraphQL API | `feature/fastapi-api` | 🟡 HIGH |
| **5** | Celery Task Queue | `feature/task-orchestration` | 🟢 MEDIUM |
| **6** | Observability (Metrics, Logging) | `feature/observability` | 🟢 LOW |

---

## 🎯 Session 1: Storage Layer (START HERE FIRST!)

### Create Branch
```bash
git checkout -b feature/storage-layer
```

### Tell Claude Code
```
I'm working on Session 1: Storage Layer from the parallel development plan.

Please implement:
1. PostgreSQL schema and SQLAlchemy models (trend_agent/storage/models.py)
2. PostgreSQL TrendRepository (trend_agent/storage/postgres.py)
3. Qdrant VectorRepository (trend_agent/storage/qdrant.py)
4. Redis CacheRepository (trend_agent/storage/redis.py)
5. Database initialization script (scripts/init-db.sql)

Use the interfaces defined in trend_agent/storage/interfaces.py as the contract.
```

### Start Services
```bash
docker-compose up postgres qdrant redis -d
docker-compose logs -f postgres qdrant redis
```

### When Complete
```bash
git add .
git commit -m "feat: implement storage layer with PostgreSQL, Qdrant, Redis"
git push origin feature/storage-layer
# Create PR and merge to main
```

---

## 🎯 Session 2: Ingestion Plugins (After Session 1 merges)

### Create Branch
```bash
git checkout main
git pull
git checkout -b feature/ingestion-plugins
```

### Tell Claude Code
```
I'm working on Session 2: Ingestion Plugins from the parallel development plan.

Please:
1. Implement PluginManager (trend_agent/ingestion/manager.py)
2. Implement HealthChecker (trend_agent/ingestion/health.py)
3. Implement Scheduler (trend_agent/ingestion/scheduler.py)
4. Refactor existing collectors to use CollectorPlugin interface:
   - trend_agent/collectors/reddit.py
   - trend_agent/collectors/hackernews.py
   - trend_agent/collectors/google_news.py
   - (and all others)

Use trend_agent/ingestion/base.py and interfaces.py as contracts.
For storage, use tests/mocks/storage.py initially.
```

---

## 🎯 Session 3: Processing Pipeline (After Session 1 merges)

### Create Branch
```bash
git checkout main
git pull
git checkout -b feature/processing-pipeline
```

### Tell Claude Code
```
I'm working on Session 3: Processing Pipeline from the parallel development plan.

Please implement:
1. Pipeline orchestrator (trend_agent/processing/pipeline.py)
2. Normalizer stage (trend_agent/processing/normalizer.py)
3. Language detector (trend_agent/processing/language.py)
4. Enhance existing deduplicate.py with 3-level deduplication
5. Enhance existing cluster.py with HDBSCAN
6. Enhance existing rank.py with trend state tracking

Use trend_agent/processing/interfaces.py as the contract.
Use tests/mocks/storage.py and tests/mocks/intelligence.py for dependencies.
```

---

## 🎯 Session 4: FastAPI API (After Session 1 merges)

### Create Branch
```bash
git checkout main
git pull
git checkout -b feature/fastapi-api
```

### Tell Claude Code
```
I'm working on Session 4: FastAPI REST API from the parallel development plan.

Please implement:
1. FastAPI app setup (api/main.py)
2. Trend endpoints (api/routers/trends.py)
3. Topic endpoints (api/routers/topics.py)
4. Search endpoints (api/routers/search.py)
5. Health check endpoints (api/routers/health.py)
6. Dependency injection (api/dependencies.py)
7. Authentication middleware

Use api/schemas/ for request/response models.
Use tests/mocks/storage.py initially for repositories.
```

### Start Services
```bash
docker-compose --profile api up -d
```

---

## 🎯 Session 5: Celery Tasks (After Sessions 2, 3 complete)

### Create Branch
```bash
git checkout main
git pull
git checkout -b feature/task-orchestration
```

### Tell Claude Code
```
I'm working on Session 5: Task Orchestration from the parallel development plan.

Please implement:
1. Celery app setup (trend_agent/tasks/__init__.py)
2. Collection tasks (trend_agent/tasks/collection.py)
3. Processing tasks (trend_agent/tasks/processing.py)
4. APScheduler integration (trend_agent/tasks/scheduler.py)
5. Task monitoring and error handling

Use existing collectors and processing modules.
```

### Start Services
```bash
docker-compose --profile celery up -d
docker-compose logs -f celery-worker celery-beat
```

---

## 🎯 Session 6: Observability (After Session 4 completes)

### Create Branch
```bash
git checkout main
git pull
git checkout -b feature/observability
```

### Tell Claude Code
```
I'm working on Session 6: Observability from the parallel development plan.

Please implement:
1. Prometheus metrics (trend_agent/observability/metrics.py)
2. Structured logging (trend_agent/observability/logging.py)
3. Prometheus config (config/prometheus.yml)
4. Grafana dashboards (config/grafana/dashboards/)
5. Health check endpoints
6. Alerting rules
```

### Start Services
```bash
docker-compose --profile observability up -d
```

---

## 📦 Key Files Reference

### Interface Contracts (READ THESE FIRST!)
- `trend_agent/types.py` - Shared type definitions
- `trend_agent/storage/interfaces.py` - Storage contracts
- `trend_agent/ingestion/base.py` - Collector plugin interface
- `trend_agent/processing/interfaces.py` - Pipeline contracts
- `trend_agent/intelligence/interfaces.py` - AI service contracts
- `api/schemas/` - API request/response models

### Mock Implementations (USE FOR DEPENDENCIES)
- `tests/mocks/storage.py` - Mock repositories
- `tests/mocks/intelligence.py` - Mock AI services
- `tests/mocks/processing.py` - Mock processing stages
- `tests/fixtures.py` - Sample data generators

### Configuration
- `docker-compose.yml` - All services
- `.env.docker.example` - Environment template
- `PARALLEL_DEVELOPMENT_GUIDE.md` - Detailed guide

---

## 🔧 Common Commands

### Docker Management
```bash
# Start specific services
docker-compose up postgres qdrant redis -d

# Start with profile
docker-compose --profile api up -d

# View logs
docker-compose logs -f [service-name]

# Stop all
docker-compose down

# Clean everything (WARNING: deletes data)
docker-compose down -v
```

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/your-component

# Commit your work
git add .
git commit -m "feat: implement [component]"

# Push to remote
git push origin feature/your-component

# Rebase on main (get latest changes)
git checkout main
git pull
git checkout feature/your-component
git rebase main
```

### Python Testing
```bash
# Run tests
pytest tests/

# Run specific test file
pytest tests/test_storage.py

# Run with coverage
pytest --cov=trend_agent tests/
```

---

## 🆘 Quick Troubleshooting

### Import Errors
```python
# ❌ Wrong
from types import Trend

# ✅ Correct
from trend_agent.types import Trend
```

### Using Mocks
```python
# Import mocks for dependencies not yet implemented
from tests.mocks.storage import MockTrendRepository
from tests.fixtures import Fixtures

# Create test data
fixtures = Fixtures()
trends = fixtures.get_trends(10)

# Use mock repository
repo = MockTrendRepository()
await repo.save(trends[0])
```

### Service Not Starting
```bash
# Check service logs
docker-compose logs [service-name]

# Check service health
docker-compose ps

# Restart service
docker-compose restart [service-name]
```

---

## ✅ Completion Checklist

**Session 1 (Storage):**
- [ ] PostgreSQL schema created
- [ ] Repositories implemented
- [ ] Tests passing
- [ ] Merged to main

**Session 2 (Ingestion):**
- [ ] Collectors refactored
- [ ] Plugin manager working
- [ ] Tests passing
- [ ] Merged to main

**Session 3 (Processing):**
- [ ] Pipeline implemented
- [ ] All stages enhanced
- [ ] Tests passing
- [ ] Merged to main

**Session 4 (API):**
- [ ] FastAPI endpoints working
- [ ] Authentication implemented
- [ ] OpenAPI docs available
- [ ] Merged to main

**Session 5 (Tasks):**
- [ ] Celery tasks working
- [ ] Scheduler active
- [ ] Monitoring setup
- [ ] Merged to main

**Session 6 (Observability):**
- [ ] Metrics exposed
- [ ] Dashboards created
- [ ] Logging structured
- [ ] Merged to main

---

## 🎉 You're Ready!

1. **Choose your session** (Start with Session 1 if you're first!)
2. **Create your branch**
3. **Start Claude Code**
4. **Tell Claude which session you're working on**
5. **Let Claude Code implement while you monitor progress**
6. **Test, commit, and merge when complete**

**Questions?** Check `PARALLEL_DEVELOPMENT_GUIDE.md` for detailed explanations.

Good luck! 🚀
