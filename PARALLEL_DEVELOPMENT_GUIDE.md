# Parallel Development Guide

## Overview

This guide explains how to use multiple Claude Code sessions to develop different components of the Trend Intelligence Platform in parallel, leveraging the interface contracts and mock implementations.

---

## ✅ What's Been Set Up

### 1. **Interface Contracts** (Protocol-based)

All layer interfaces are defined as Protocol classes for type-safe development:

- **trend_agent/types.py** - Shared type definitions (RawItem, ProcessedItem, Topic, Trend, etc.)
- **trend_agent/storage/interfaces.py** - Storage layer interfaces (TrendRepository, VectorRepository, CacheRepository)
- **trend_agent/ingestion/base.py** - Plugin-based collector interface
- **trend_agent/ingestion/interfaces.py** - Plugin management interfaces (PluginManager, HealthChecker, Scheduler)
- **trend_agent/processing/interfaces.py** - Processing pipeline interfaces (Pipeline, Normalizer, Deduplicator, Clusterer, Ranker)
- **trend_agent/intelligence/interfaces.py** - AI service interfaces (EmbeddingService, LLMService, SemanticSearchService, TrendDetector)
- **api/schemas/** - FastAPI Pydantic schemas for API layer

### 2. **Mock Implementations**

All interfaces have working mock implementations for independent development:

- **tests/mocks/storage.py** - In-memory storage repositories
- **tests/mocks/intelligence.py** - Mock AI services
- **tests/mocks/processing.py** - Mock processing stages
- **tests/fixtures.py** - Sample data generators

### 3. **Infrastructure**

Production-ready docker-compose.yml with:

- PostgreSQL (primary database)
- Qdrant (vector database)
- Redis (cache)
- RabbitMQ (message queue)
- Prometheus + Grafana (observability - optional)
- Service profiles for selective startup

---

## 🚀 How to Start Parallel Development

### Step 1: Clone Your Repository (Per Session)

For each development session, you can either:

**Option A: Single Repository (Recommended)**
- Work in the same directory
- Use different git branches for each session
- Each Claude Code session will work on its own branch

**Option B: Multiple Clones** (if you prefer complete isolation)
```bash
# Terminal 1
cd ~/code/trend

# Terminal 2
cd ~/code/trend

# And so on...
```

### Step 2: Start Claude Code Sessions

Open 6 terminal windows and start Claude Code in each:

```bash
# Terminal 1-6
cd ~/code/trend
claude code
```

### Step 3: Assign Tasks to Each Session

**Session 1: Storage Layer** (Branch: `feature/storage-layer`)
```
Task: Implement PostgreSQL and Qdrant repositories
Files to create:
- trend_agent/storage/postgres.py (PostgreSQLTrendRepository)
- trend_agent/storage/qdrant.py (QdrantVectorRepository)
- trend_agent/storage/redis.py (RedisCacheRepository)
- trend_agent/storage/schema.sql (database schema)
- scripts/init-db.sql (initialization script)

Use: trend_agent/storage/interfaces.py as contract
Mock dependencies: Use tests/mocks/intelligence.py for embeddings
```

**Session 2: Ingestion Plugins** (Branch: `feature/ingestion-plugins`)
```
Task: Refactor collectors to plugin architecture
Files to create:
- trend_agent/ingestion/manager.py (PluginManager implementation)
- trend_agent/ingestion/health.py (HealthChecker implementation)
- trend_agent/ingestion/scheduler.py (Scheduler implementation)
- Refactor existing collectors/reddit.py, hackernews.py, etc.

Use: trend_agent/ingestion/base.py as contract
Mock dependencies: Use tests/mocks/storage.py for data persistence
```

**Session 3: Processing Pipeline** (Branch: `feature/processing-pipeline`)
```
Task: Create composable processing pipeline
Files to create:
- trend_agent/processing/pipeline.py (Pipeline orchestrator)
- trend_agent/processing/normalizer.py (NormalizerStage)
- trend_agent/processing/language.py (LanguageDetector)
- Enhance existing deduplicate.py, cluster.py, rank.py

Use: trend_agent/processing/interfaces.py as contract
Mock dependencies: Use tests/mocks/storage.py and tests/mocks/intelligence.py
```

**Session 4: FastAPI REST API** (Branch: `feature/fastapi-api`)
```
Task: Build FastAPI REST and GraphQL API
Files to create:
- api/main.py (FastAPI app)
- api/routers/trends.py (trend endpoints)
- api/routers/topics.py (topic endpoints)
- api/routers/search.py (search endpoints)
- api/routers/health.py (health checks)
- api/dependencies.py (dependency injection)

Use: api/schemas/ as request/response models
Mock dependencies: Use tests/mocks/storage.py for repositories
```

**Session 5: Celery Task Queue** (Branch: `feature/task-orchestration`)
```
Task: Implement task queue and scheduling
Files to create:
- trend_agent/tasks/__init__.py (Celery app)
- trend_agent/tasks/collection.py (collection tasks)
- trend_agent/tasks/processing.py (processing tasks)
- trend_agent/tasks/scheduler.py (APScheduler integration)

Use: Existing collectors and processing modules
Mock dependencies: Use tests/mocks/storage.py
```

**Session 6: Observability** (Branch: `feature/observability`)
```
Task: Add metrics, logging, and monitoring
Files to create:
- trend_agent/observability/metrics.py (Prometheus metrics)
- trend_agent/observability/logging.py (structured logging)
- config/prometheus.yml (Prometheus config)
- config/grafana/dashboards/ (Grafana dashboards)

Can start after other sessions have made progress
```

---

## 📋 Development Workflow

### For Each Session:

1. **Create your branch:**
   ```bash
   git checkout -b feature/your-component
   ```

2. **Tell Claude Code your task:**
   ```
   I'm working on [Session Name] from the parallel development plan.
   Please implement the [component] using the interface contracts in
   trend_agent/[layer]/interfaces.py. Use the mock implementations from
   tests/mocks/ for dependencies that aren't ready yet.
   ```

3. **Develop with mock dependencies:**
   - Import and use mocks from `tests/mocks/`
   - Example:
     ```python
     from tests.mocks.storage import MockTrendRepository

     # Use mock until real implementation is ready
     trend_repo = MockTrendRepository()
     ```

4. **Run your component in isolation:**
   ```bash
   # Start only the services you need
   docker-compose up postgres qdrant redis -d

   # Or start with a specific profile
   docker-compose --profile api up -d  # For Session 4
   docker-compose --profile celery up -d  # For Session 5
   ```

5. **Write tests as you go:**
   ```python
   # tests/test_your_component.py
   from tests.fixtures import Fixtures
   from tests.mocks.storage import MockTrendRepository

   async def test_your_feature():
       fixtures = Fixtures()
       trends = fixtures.get_trends(10)
       # Your test logic here
   ```

6. **Commit when feature is complete:**
   ```bash
   git add .
   git commit -m "feat: implement [component]"
   git push origin feature/your-component
   ```

---

## 🔗 Integration Strategy

### Phase 1: Foundation (Week 1)
1. **Session 1** (Storage) implements first
2. Merge to `main` when complete
3. Other sessions rebase on new `main`

### Phase 2: Parallel Development (Week 2)
1. **Sessions 2, 3, 4** develop in parallel
   - Each uses mocks for dependencies
   - Session 2: Uses mock storage
   - Session 3: Uses mock storage + intelligence
   - Session 4: Uses mock storage
2. Merge in order: Session 2 → Session 3 → Session 4

### Phase 3: Integration (Week 3)
1. **Session 5** (Tasks) integrates Sessions 2 & 3
2. **Session 6** (Observability) instruments everything
3. Replace mocks with real implementations
4. Integration testing

---

## 🛠️ Useful Commands

### Docker Compose Profiles

```bash
# Start just the database services (Session 1)
docker-compose up postgres qdrant redis rabbitmq -d

# Start API service (Session 4)
docker-compose --profile api up -d

# Start Celery services (Session 5)
docker-compose --profile celery up -d

# Start observability stack (Session 6)
docker-compose --profile observability up -d

# Start everything
docker-compose --profile api --profile celery --profile observability up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service-name]
```

### Testing with Mocks

```python
# Import mocks for dependencies
from tests.mocks.storage import (
    MockTrendRepository,
    MockVectorRepository,
    MockCacheRepository,
)
from tests.mocks.intelligence import (
    MockEmbeddingService,
    MockLLMService,
)
from tests.fixtures import Fixtures

# Create fixtures
fixtures = Fixtures()
trends = fixtures.get_trends(10)
topics = fixtures.get_topics(5)

# Use mocks
trend_repo = MockTrendRepository()
await trend_repo.save(trends[0])
```

### Environment Variables

Create `.env` file for your session:

```bash
# Database (for Session 1)
POSTGRES_DB=trends
POSTGRES_USER=trend_user
POSTGRES_PASSWORD=trend_password

# Vector DB
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Cache
REDIS_HOST=localhost
REDIS_PORT=6379

# Message Queue (for Session 5)
RABBITMQ_HOST=localhost
RABBITMQ_USER=trend_user
RABBITMQ_PASSWORD=trend_password

# API Keys
OPENAI_API_KEY=your_key_here
```

---

## 📁 File Organization

```
trend/
├── trend_agent/              # Core library
│   ├── types.py             # ✅ Shared type definitions
│   ├── storage/             # Session 1
│   │   ├── __init__.py      # ✅ Interface exports
│   │   ├── interfaces.py    # ✅ Protocol definitions
│   │   ├── postgres.py      # 🔨 To implement
│   │   ├── qdrant.py        # 🔨 To implement
│   │   └── redis.py         # 🔨 To implement
│   ├── ingestion/           # Session 2
│   │   ├── base.py          # ✅ CollectorPlugin ABC
│   │   ├── interfaces.py    # ✅ Manager interfaces
│   │   ├── manager.py       # 🔨 To implement
│   │   └── scheduler.py     # 🔨 To implement
│   ├── processing/          # Session 3
│   │   ├── interfaces.py    # ✅ Pipeline interfaces
│   │   ├── pipeline.py      # 🔨 To implement
│   │   └── normalizer.py    # 🔨 To implement
│   ├── intelligence/        # Built on Session 1
│   │   ├── interfaces.py    # ✅ AI service interfaces
│   │   ├── embeddings.py    # 🔨 To enhance
│   │   └── semantic.py      # 🔨 To implement
│   └── tasks/               # Session 5
│       └── __init__.py      # 🔨 To create
├── api/                     # Session 4
│   ├── main.py              # 🔨 To create
│   ├── routers/             # 🔨 To create
│   └── schemas/             # ✅ Pydantic models
├── tests/
│   ├── mocks/               # ✅ Mock implementations
│   └── fixtures.py          # ✅ Sample data
└── docker-compose.yml       # ✅ Updated with services

✅ = Ready to use
🔨 = To be implemented
```

---

## 🎯 Success Criteria

### Session 1 (Storage)
- [ ] PostgreSQL schema created
- [ ] TrendRepository implemented
- [ ] VectorRepository (Qdrant) implemented
- [ ] CacheRepository (Redis) implemented
- [ ] Integration tests passing
- [ ] Docker services running

### Session 2 (Ingestion)
- [ ] PluginManager implemented
- [ ] All 9 collectors refactored to plugin interface
- [ ] Plugin health monitoring working
- [ ] Scheduler integrated
- [ ] Unit tests with mocks passing

### Session 3 (Processing)
- [ ] Pipeline orchestrator implemented
- [ ] All processing stages refactored
- [ ] HDBSCAN clustering integrated
- [ ] Language detection added
- [ ] Integration tests passing

### Session 4 (API)
- [ ] FastAPI app running
- [ ] All REST endpoints implemented
- [ ] GraphQL endpoint working
- [ ] WebSocket real-time updates
- [ ] OpenAPI docs generated
- [ ] Authentication working

### Session 5 (Tasks)
- [ ] Celery app configured
- [ ] Collection tasks implemented
- [ ] Processing tasks implemented
- [ ] Scheduler working
- [ ] Task monitoring via Flower

### Session 6 (Observability)
- [ ] Prometheus metrics exposed
- [ ] Grafana dashboards created
- [ ] Structured logging implemented
- [ ] Health checks comprehensive
- [ ] Alerting configured

---

## 🆘 Troubleshooting

### "Module not found" errors
- Make sure `PYTHONPATH=/app` is set
- Import from root: `from trend_agent.types import Trend`

### "Service unhealthy" in Docker
- Check logs: `docker-compose logs [service]`
- Verify environment variables in .env file
- Ensure ports aren't already in use

### Mock vs Real Implementation Confusion
- Always check your imports
- Mocks are in `tests/mocks/`
- Real implementations are in `trend_agent/[layer]/`

### Merge Conflicts
- Use smaller, focused commits
- Communicate with other sessions about interface changes
- Rebase frequently on main

---

## 📞 Communication Between Sessions

If you need to change an interface:

1. **Discuss in the team** (or create an issue)
2. **Update the Protocol** in the interface file
3. **Update all mocks** to match
4. **Notify other sessions** to update their implementations
5. **Update tests** that use the interface

---

## 🎉 Ready to Start!

Each session can begin immediately with:

1. Create your branch
2. Tell Claude Code which session you're working on
3. Use the interface contracts as your specification
4. Use mocks for dependencies
5. Develop, test, commit
6. Merge when ready

**Estimated Timeline:**
- Week 1: Session 1 (Storage) → merge to main
- Week 2: Sessions 2, 3, 4 in parallel → merge incrementally
- Week 3: Sessions 5, 6 → final integration

**Total: 3-4 weeks with parallel development vs 10-12 weeks sequential!** 🚀

---

## 📚 Additional Resources

- Architecture docs: `docs/architecture-*.md`
- Type definitions: `trend_agent/types.py`
- Mock examples: `tests/mocks/`
- Sample data: `tests/fixtures.py`
- Docker services: `docker-compose.yml`

Good luck with your parallel development! 🎯
