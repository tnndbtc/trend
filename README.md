# AI Trend Intelligence Platform

A production-ready, multi-service AI platform for collecting, analyzing, and surfacing trending topics across technology, business, and science with autonomous agent governance.

**✨ New**: Full agent control plane with task arbitration, budget management, circuit breakers, and multi-tier memory architecture!

## ⚡ Quick Start

```bash
# 1. Set API key (environment variable - security best practice!)
export OPENAI_API_KEY='sk-proj-xxxxxxxxxxxxx'
# Get key from: https://platform.openai.com/api-keys

# 2. Run setup
./setup.sh
# Select: 1) Full Platform Setup (All Services)

# 3. Access services
# Web Interface: http://localhost:11800 (admin / changeme123)
# API Docs: http://localhost:8000/docs
# Grafana: http://localhost:3000 (admin / admin)

# 4. Collect trends
./setup.sh
# Select: 4) Collect Trends
```

**🔐 Security**: API keys are set via environment variables, never committed to files.

**📖 See [QUICKSTART.md](QUICKSTART.md) for detailed getting started guide**

---

## 🎯 Features

### Core Platform
- **🌐 Multi-Source Collection**: GitHub Trending, Hacker News, Reddit, Product Hunt, Google News, YouTube
- **🧠 AI-Powered Analysis**: GPT-4 trend analysis and summarization
- **🔍 Semantic Search**: Vector-based similarity search with Qdrant
- **🎯 Smart Deduplication**: Cross-language deduplication with embedding similarity
- **📊 Intelligent Clustering**: ML-based topic grouping and ranking
- **🌍 Multi-Language Support**: Translation pipeline (OpenAI, DeepL, LibreTranslate)
- **📈 Engagement Tracking**: Social metrics and trend scoring

### Web & API
- **🎨 Django Web Interface**: Full-featured dashboard with admin panel
- **⚡ FastAPI REST API**: High-performance API with OpenAPI docs
- **🔌 WebSocket Support**: Real-time trend updates
- **🔐 API Key Authentication**: Secure access with rate limiting
- **📡 GraphQL Support**: Flexible query interface (optional)

### Background Processing
- **⚙️ Celery Task Queue**: Asynchronous collection and processing
- **⏰ Scheduled Jobs**: Automatic periodic collection (hourly, daily)
- **🔄 Retry Logic**: Automatic retry with exponential backoff
- **📬 Alert System**: Email and Slack notifications

### Autonomous Agent Platform
- **🎛️ Task Arbitrator**: Deduplication, rate limiting, loop detection
- **💰 Budget Engine**: Multi-dimensional cost tracking (cost, tokens, time, concurrency)
- **⚡ Circuit Breaker**: Automatic failure recovery (CLOSED/OPEN/HALF_OPEN states)
- **🧠 Three-Tier Memory**: Ground truth, synthesized, ephemeral with lineage tracking
- **🔗 Causality Tracking**: Full operation lineage with cycle detection
- **🛡️ Risk Assessment**: Multi-factor risk scoring (0-100) with approval workflow
- **🏆 Trust Management**: Agent reputation system (5 trust levels)
- **🌳 Agent Hierarchy**: Supervisor/Worker/Specialist topology with capability routing
- **📊 Event Dampening**: Prevents event storms with deduplication and rate limits
- **📝 Audit Logging**: Immutable audit trail for compliance

### Observability & Monitoring
- **📊 Grafana Dashboards**: Real-time metrics visualization
- **📈 Prometheus Metrics**: Time-series metrics collection
- **🔍 Jaeger Tracing**: Distributed request tracing
- **📋 Loki Logging**: Centralized log aggregation
- **🔭 OpenTelemetry**: Unified observability pipeline
- **🚨 Alerting**: Configurable thresholds with multi-channel alerts

### Data Layer
- **🗄️ PostgreSQL**: Primary relational database
- **🔢 Qdrant**: Vector database for semantic search
- **⚡ Redis**: High-speed caching and session storage
- **🐰 RabbitMQ**: Message queue for task distribution
- **📊 InfluxDB**: Time-series metrics (optional)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  Django Web UI (11800) │ FastAPI REST (8000) │ Grafana (3000)  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                             │
├─────────────────────────────────────────────────────────────────┤
│  Trend Agents │ Celery Workers │ Background Tasks │ WebSockets  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                   Agent Control Plane                            │
├─────────────────────────────────────────────────────────────────┤
│  Arbitration │ Budget │ Circuit Breaker │ Memory │ Hierarchy    │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL │ Qdrant │ Redis │ RabbitMQ │ InfluxDB             │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                   Observability Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  Prometheus │ Jaeger │ Loki │ OpenTelemetry │ Grafana          │
└─────────────────────────────────────────────────────────────────┘
```

### Project Structure

```
trend/
├── trend_agent/              # Core trend intelligence engine
│   ├── agents/              # Agent Control Plane (Session 11)
│   │   ├── arbitration.py   # Task arbitrator (dedup, rate limit, loops)
│   │   ├── budget.py        # Multi-dimensional budget engine
│   │   ├── circuit_breaker.py # Circuit breaker pattern
│   │   ├── memory.py        # Three-tier memory architecture
│   │   ├── lineage.py       # Causality tracking
│   │   ├── safety.py        # Risk assessment & trust management
│   │   ├── hierarchy.py     # Agent hierarchy & routing
│   │   ├── events.py        # Event bus with dampening
│   │   ├── observability.py # Metrics & audit logging
│   │   └── correlation.py   # Correlation context
│   │
│   ├── collectors/          # Data source collectors
│   │   ├── github.py        # GitHub Trending
│   │   ├── hackernews.py    # Hacker News
│   │   ├── reddit.py        # Reddit
│   │   ├── producthunt.py   # Product Hunt
│   │   └── youtube.py       # YouTube
│   │
│   ├── processing/          # Data processing pipeline
│   │   ├── deduplication.py # Cross-language deduplication
│   │   ├── clustering.py    # Topic clustering
│   │   ├── translation.py   # Multi-provider translation
│   │   └── embeddings.py    # Vector embeddings
│   │
│   └── llm/                # LLM integration
│       ├── openai_client.py # OpenAI API client
│       └── summarizer.py    # Trend summarization
│
├── trend_project/           # Django project
│   ├── settings/           # Environment-specific settings
│   ├── celery.py           # Celery configuration
│   └── urls.py             # URL routing
│
├── trends/                 # Django app
│   ├── models.py           # Database models
│   ├── views.py            # View logic
│   ├── tasks.py            # Celery tasks
│   ├── management/         # Custom commands
│   │   └── commands/
│   │       └── collect_trends.py
│   └── templates/          # HTML templates
│
├── api/                    # FastAPI REST API
│   ├── main.py            # FastAPI application
│   ├── routes/            # API endpoints
│   ├── middleware/        # Auth, rate limiting
│   └── schemas/           # Pydantic models
│
├── monitoring/            # Observability configuration
│   ├── prometheus/        # Prometheus config
│   ├── grafana/          # Grafana dashboards
│   └── loki/             # Loki config
│
├── docs/                 # Documentation
│   ├── QUICKSTART.md     # Getting started guide
│   ├── SERVICES.md       # Service documentation
│   ├── API_GUIDE.md      # API reference
│   ├── TROUBLESHOOTING.md # Common issues
│   └── architecture/     # Architecture docs
│
├── docker-compose.yml    # Docker orchestration
├── setup.sh             # Interactive setup script
└── .env.docker.example  # Environment template
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[QUICKSTART.md](QUICKSTART.md)** | Get up and running in 5 minutes |
| **[SERVICES.md](SERVICES.md)** | Detailed service documentation |
| **[API_GUIDE.md](API_GUIDE.md)** | Complete API reference and examples |
| **[docs/SECURITY.md](docs/SECURITY.md)** | Security best practices and API key management |
| **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Common issues and solutions |
| **[ARCHITECTURE_GAP_ANALYSIS.md](ARCHITECTURE_GAP_ANALYSIS.md)** | Architecture compliance (95% complete) |
| **[trend_agent/agents/QUICKSTART.md](trend_agent/agents/QUICKSTART.md)** | Agent Control Plane guide |

---

## 🚀 Installation

### Prerequisites

- **Docker** & **Docker Compose** installed
- **4GB+ RAM** available
- **10GB+ disk space**
- **OpenAI API Key** ([get one here](https://platform.openai.com))

### Setup (5 minutes)

```bash
# 1. Clone repository
git clone <repository-url>
cd trend

# 2. Set API key as environment variable (security best practice!)
export OPENAI_API_KEY='sk-proj-xxxxxxxxxxxxx'
# Get from: https://platform.openai.com/api-keys

# Make it permanent (optional):
echo "export OPENAI_API_KEY='sk-proj-xxxxxxxxxxxxx'" >> ~/.bashrc
source ~/.bashrc

# 3. Run setup
./setup.sh
# Select: 1) Full Platform Setup (All Services)

# 4. Access services
# • Web Interface: http://localhost:11800
# • API Docs: http://localhost:8000/docs
# • Grafana: http://localhost:3000

# 5. Collect trends
./setup.sh
# Select: 4) Collect Trends
```

**🔐 Security Note**:
- API keys are **never stored in files** - they come from environment variables
- `.env.docker` contains only placeholders and is safe to commit to git
- This follows the [12-factor app](https://12factor.net/config) security pattern

**🎉 That's it!** See [QUICKSTART.md](QUICKSTART.md) for more details.

---

## 🎮 Usage

### Setup Script (Interactive)

The `setup.sh` script provides an interactive menu for all common operations:

```bash
./setup.sh
```

**Available Options**:
1. Full Platform Setup (All Services)
2. Basic Setup (Web Interface Only)
3. Start/Stop Services
4. Collect Trends
5. Manage Categories
6. Service Status & Health Check
7. View Logs
8. Database Operations
9. Clean Old Data
10. Generate API Keys
11. Show All Access URLs

### Web Interface

Access the Django dashboard at http://localhost:11800

- **Default Login**: `admin` / `changeme123`
- Browse trends, filter by category, view statistics
- Admin panel: http://localhost:11800/admin

### REST API

Explore the FastAPI docs at http://localhost:8000/docs

```bash
# Generate API key
./setup.sh → 10) Generate API Keys

# List trends
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:8000/api/v1/trends?limit=10"

# Semantic search
curl -X POST "http://localhost:8000/api/v1/search/semantic" \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI breakthroughs", "limit": 5}'

# Trigger collection (admin key)
curl -X POST "http://localhost:8000/api/v1/admin/collect" \
  -H "X-API-Key: YOUR_ADMIN_KEY"
```

**📖 See [API_GUIDE.md](API_GUIDE.md) for complete API reference**

### Command Line

```bash
# Collect trends (via Django)
docker compose exec web python manage.py collect_trends --max-posts-per-category 5

# Django shell
docker compose exec web python manage.py shell

# Database migrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python manage.py createsuperuser
```

### Monitoring

Access Grafana dashboards at http://localhost:3000

- **Login**: `admin` / `admin`
- Pre-configured dashboards for platform monitoring
- Real-time metrics, logs, and traces

**📖 See [SERVICES.md](SERVICES.md) for monitoring details**

---

## ☸️ Kubernetes Deployment

The platform includes production-ready Kubernetes configurations with secure secret management.

### Quick Deploy

```bash
# 1. Set environment variables (security best practice!)
export OPENAI_API_KEY='sk-proj-xxxxx'
export POSTGRES_PASSWORD='secure-password'

# 2. Use interactive deployment script
cd k8s
./deploy.sh
```

### Three Secret Management Options

#### 1. Script from Environment Variables (Development)

```bash
# Quick start for dev/test
cd k8s/secrets
./create-from-env.sh
kubectl apply -k k8s/base
```

#### 2. Sealed Secrets (GitOps)

```bash
# For ArgoCD/Flux workflows
cd k8s/secrets/sealed-secrets
./create-sealed-secrets.sh
git add *-sealed.yaml  # Safe to commit (encrypted)
git commit && git push
```

#### 3. External Secrets Operator (Production)

```bash
# For AWS/GCP/Azure secret managers
aws secretsmanager create-secret \
  --name prod/trend-platform/openai-api-key \
  --secret-string "$OPENAI_API_KEY"

kubectl apply -f k8s/secrets/external-secrets/aws-secrets-manager.yaml
```

### Features

- ✅ **Secure secrets management** - 3 production-ready approaches
- ✅ **Interactive deployment** - Menu-driven deployment script
- ✅ **Horizontal scaling** - HPA for API and Celery workers
- ✅ **StatefulSets** - For PostgreSQL and Qdrant
- ✅ **Ingress** - NGINX ingress with TLS support
- ✅ **ConfigMaps** - Environment-specific configuration
- ✅ **Health checks** - Liveness and readiness probes
- ✅ **Resource limits** - CPU and memory limits per pod
- ✅ **Multi-cloud** - AWS (EKS), GCP (GKE), Azure (AKS)

### Supported Secret Managers

- AWS Secrets Manager
- Google Secret Manager
- Azure Key Vault
- HashiCorp Vault

### Resources

- **[k8s/README.md](k8s/README.md)** - Complete Kubernetes deployment guide
- **[k8s/secrets/README.md](k8s/secrets/README.md)** - Secret management comparison
- **[docs/SECURITY.md](docs/SECURITY.md#kubernetes-deployment-security)** - K8s security best practices

**🔐 Security**: All approaches follow 12-factor app pattern - secrets come from environment variables, never hardcoded in files!

---

## 🛠️ Agent Control Plane

The platform includes a complete governance layer for autonomous agents:

```python
from trend_agent.agents import (
    TaskArbitrator,     # Prevent duplicate tasks, enforce rate limits
    BudgetEngine,       # Multi-dimensional budget tracking
    CircuitBreaker,     # Automatic failure recovery
    MemoryStore,        # Three-tier memory (ground truth, synthesized, ephemeral)
    RiskScorer,         # Risk assessment (0-100 score)
    TrustManager,       # Agent reputation system
    AgentHierarchy,     # Supervisor/Worker/Specialist topology
    LineageTracker,     # Full causality tracking
    AuditLogger,        # Immutable audit trail
)

# Example: Governed task execution
arbitrator = TaskArbitrator()
breaker = CircuitBreaker()
budget = BudgetEngine()

# Check if task can proceed
accepted, record, reason = await arbitrator.submit_task(task)
if accepted and breaker.can_proceed("agent_id"):
    budget.reserve_budget("agent_id", BudgetType.COST, 2.0, "task_id")
    result = await execute_task(task)
    budget.commit_reservation("task_id", actual_cost=1.23)
```

**📖 See [trend_agent/agents/QUICKSTART.md](trend_agent/agents/QUICKSTART.md) for complete agent governance guide**

---

## 📊 Services

### Core Services

| Service | Port | Profile | Description |
|---------|------|---------|-------------|
| **Django Web** | 11800 | default | Web interface and admin panel |
| **FastAPI REST** | 8000 | api | REST API with OpenAPI docs |
| **PostgreSQL** | 5432 | default | Primary database |
| **Qdrant** | 6333 | default | Vector database for semantic search |
| **Redis** | 6379 | default | Cache and session storage |
| **RabbitMQ** | 5672, 15672 | celery | Message queue |
| **Celery Worker** | - | celery | Background task processing |
| **Celery Beat** | - | celery | Scheduled tasks |

### Observability Services

| Service | Port | Profile | Description |
|---------|------|---------|-------------|
| **Grafana** | 3000 | observability | Dashboards and visualization |
| **Prometheus** | 9090 | observability | Metrics collection |
| **Jaeger** | 16686 | observability | Distributed tracing |
| **Loki** | 3100 | observability | Log aggregation |

**Start All Services**:
```bash
docker compose --profile api --profile celery --profile observability up -d
# Or use: ./setup.sh → 1) Full Platform Setup
```

**📖 See [SERVICES.md](SERVICES.md) for detailed service documentation**

---

## 🔧 Configuration

All configuration is managed through `.env.docker`:

```bash
# API Configuration
OPENAI_API_KEY=your_api_key_here
MODEL=gpt-4o-mini
EMBED_MODEL=text-embedding-3-small

# Collection Settings
MAX_ITEMS_PER_CATEGORY=5
COLLECTION_INTERVAL_DEFAULT=60  # minutes
DEDUP_SIMILARITY_THRESHOLD=0.85

# Translation
ENABLE_TRANSLATION=true
# Supports: OpenAI, DeepL, LibreTranslate

# Monitoring
OTEL_ENABLED=true
JAEGER_ENABLED=true
PROMETHEUS_PORT=9090

# Performance
CELERY_WORKER_CONCURRENCY=4
DB_POOL_SIZE=20
CACHE_TTL_DEFAULT=300

# Security
API_KEYS=generated_key_here
ADMIN_API_KEYS=admin_key_here
ENABLE_RATE_LIMITING=true
```

**Generate Secure Keys**:
```bash
./setup.sh → 10) Generate API Keys
```

---

## 🔍 Data Sources

The platform collects trends from multiple sources:

- **GitHub Trending**: Popular repositories and developers
- **Hacker News**: Top stories and discussions
- **Reddit**: r/all, r/technology, r/programming, etc.
- **Product Hunt**: New product launches
- **Google News**: Technology news articles
- **YouTube** (optional): Trending tech videos

**Configure Sources**:
```bash
./setup.sh → 5) Manage Categories
```

---

## 📈 Monitoring

### Health Checks

```bash
# All services
./setup.sh → 6) Service Status & Health Check

# Individual checks
curl http://localhost:11800                  # Django Web
curl http://localhost:8000/api/v1/health     # FastAPI API
curl http://localhost:6333/collections       # Qdrant
curl http://localhost:9090/-/healthy         # Prometheus
```

### Dashboards

Access Grafana at http://localhost:3000:
- Platform Overview
- API Performance
- Celery Task Metrics
- Database Performance
- Agent Control Plane Metrics

### Logs

```bash
# Via setup.sh
./setup.sh → 7) View Logs

# Via docker compose
docker compose logs -f <service>
docker compose logs web
docker compose logs api
docker compose logs celery-worker
```

---

## 🧪 Development

### Local Development

```bash
# Start in development mode
DEV_RELOAD=true docker compose up -d

# Enable SQL logging
SQL_ECHO=true docker compose restart web

# Use mock API (no API costs)
MOCK_API=1 docker compose restart web
```

### Database

```bash
# Run migrations
docker compose exec web python manage.py migrate

# Create migrations
docker compose exec web python manage.py makemigrations

# Database shell
docker compose exec postgres psql -U trend_user -d trends

# Backup
./setup.sh → 8) Database Operations → 2) Create Backup

# Restore
./setup.sh → 8) Database Operations → 3) Restore from Backup
```

### Testing

```bash
# Run Django tests
docker compose exec web python manage.py test

# Run with coverage
docker compose exec web pytest --cov

# Agent Control Plane tests
docker compose exec web python -m pytest trend_agent/agents/tests/
```

---

## 🚨 Troubleshooting

### Common Issues

**Services Won't Start**:
```bash
docker compose logs <service>
./setup.sh → 7) View Logs
```

**Port Conflicts**:
```bash
sudo lsof -i :11800
sudo lsof -i :8000
# Change ports in docker-compose.yml if needed
```

**Database Connection Errors**:
```bash
docker compose ps postgres  # Check if running
docker compose restart postgres
./setup.sh → 8) Database Operations → 1) Run Migrations
```

**API Errors**:
```bash
# Verify API key is set
cat .env.docker | grep API_KEYS
# Generate new keys
./setup.sh → 10) Generate API Keys
```

**Memory Issues**:
```bash
docker stats  # Check usage
# Reduce worker concurrency in .env.docker:
CELERY_WORKER_CONCURRENCY=2
```

**📖 See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for comprehensive troubleshooting guide**

---

## 📦 Technology Stack

- **Backend**: Python 3.11+, Django 5.0, FastAPI 0.109
- **Databases**: PostgreSQL 16, Qdrant (vector), Redis
- **Queue**: RabbitMQ, Celery
- **AI/ML**: OpenAI API, sentence-transformers, scikit-learn
- **Monitoring**: Prometheus, Grafana, Jaeger, Loki
- **Deployment**: Docker, Docker Compose

---

## 🗺️ Roadmap

- [x] Multi-source trend collection
- [x] AI-powered summarization
- [x] Semantic search
- [x] REST API with authentication
- [x] Background task processing
- [x] Full observability stack
- [x] Agent Control Plane (Session 11)
- [x] **Kubernetes deployment with secure secret management** (Session 12)
- [ ] Multi-language translation (in progress)
- [ ] Viral prediction engine
- [ ] Early trend detection
- [ ] Content strategy recommendations
- [ ] Mobile app
- [ ] GraphQL API

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📞 Support

- **Documentation**: See docs/ directory
- **Issues**: GitHub Issues
- **Questions**: GitHub Discussions

---

**🎉 Happy trend hunting!**
