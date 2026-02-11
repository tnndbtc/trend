# Quick Start Guide

Get the Trend Intelligence Platform running in 5 minutes!

---

## Prerequisites

- **Docker** & **Docker Compose** installed
- **4GB+ RAM** available  
- **10GB+ disk space**
- **OpenAI API Key** (get from [platform.openai.com](https://platform.openai.com))

---

## 1. Initial Setup

```bash
# Copy environment file
cp .env.docker.example .env.docker

# Edit and add your OpenAI API key
nano .env.docker
# Change: OPENAI_API_KEY=your_api_key_here
```

**💡 Tip**: If testing, set `MOCK_API=1` to avoid consuming API credits.

---

## 2. Start the Platform

### Option A: Full Platform (Recommended)

```bash
./setup.sh
# Select: 1) Full Platform Setup (All Services)
```

This starts:
- Django Web Interface (port 11800)
- FastAPI REST API (port 8000)
- PostgreSQL, Qdrant, Redis, RabbitMQ
- Celery workers + monitoring

### Option B: Web Only (Minimal)

```bash
./setup.sh
# Select: 2) Basic Setup (Web Interface Only)
```

---

## 3. Access the Platform

| Service | URL | Credentials |
|---------|-----|-------------|
| **Web Interface** | http://localhost:11800 | N/A |
| **Admin Panel** | http://localhost:11800/admin | admin / changeme123 |
| **API Docs** | http://localhost:8000/docs | API Key required |
| **Grafana** | http://localhost:3000 | admin / admin |

### Generate API Keys

```bash
./setup.sh → 10) Generate API Keys
```

---

## 4. Collect Trends

### Interactive:
```bash
./setup.sh → 4) Collect Trends
```

### Command Line:
```bash
docker compose exec web python manage.py collect_trends --max-posts-per-category 5
```

### API:
```bash
curl -X POST "http://localhost:8000/api/v1/admin/collect" \
  -H "X-API-Key: YOUR_ADMIN_KEY"
```

⏱️ Takes ~2-5 minutes

---

## 5. Common Commands

```bash
# Service status
./setup.sh → 6) Service Status & Health Check

# View logs  
./setup.sh → 7) View Logs

# Database backup
./setup.sh → 8) Database Operations → 2) Create Backup

# Clean old data
./setup.sh → 9) Clean Old Data
```

---

## Quick API Examples

```bash
# Get trends
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:8000/api/v1/trends?limit=10"

# Search
curl -X POST "http://localhost:8000/api/v1/search/semantic" \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI trends", "limit": 5}'

# Health
curl "http://localhost:8000/api/v1/health"
```

---

## Automatic Collection

With Celery (Full Platform), trends collect automatically:
- Every hour: All sources
- Every 15 min: High-frequency sources  
- Daily 3 AM: Cleanup

---

## Troubleshooting

### Services won't start
```bash
./setup.sh → 7) View Logs → 8) All Services
```

### Port conflicts
```bash
sudo lsof -i :11800
sudo lsof -i :8000
```

### Database reset
```bash
docker compose down -v
./setup.sh → 1) Full Platform Setup
```

---

## Stop Platform

```bash
docker compose down         # Stop all
docker compose down -v      # Stop + remove data
```

---

## Next Steps

1. Configure Categories: `./setup.sh → 5)`
2. View Monitoring: http://localhost:3000
3. Explore API: http://localhost:8000/docs
4. See SERVICES.md and API_GUIDE.md for details

---

**🎉 Happy trend hunting!**
