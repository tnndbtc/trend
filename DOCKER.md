# Docker Deployment Guide

Complete guide for deploying the AI Trend Intelligence Agent using Docker.

## Overview

The application is containerized using Docker, making deployment simple and consistent across different environments. All dependencies, configurations, and services are bundled into a single container.

## Architecture

```
┌─────────────────────────────────────┐
│     Docker Container                │
│                                     │
│  ┌───────────────────────────────┐ │
│  │   Django Web Application       │ │
│  │   (Port 11800)                 │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │   Trend Collection Engine      │ │
│  │   (trend_agent)                │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │   SQLite Database              │ │
│  │   (Persistent Volume)          │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
         ↓
    Host: localhost:11800
```

## Files

### Core Docker Files

- **Dockerfile**: Defines the container image
  - Base: python:3.11-slim
  - Installs dependencies from requirements.txt
  - Copies application code
  - Sets up entrypoint

- **docker-compose.yml**: Orchestrates container services
  - Defines web service
  - Configures volumes for persistence
  - Sets environment variables
  - Maps ports

- **docker-entrypoint.sh**: Container initialization script
  - Runs database migrations
  - Creates superuser
  - Collects static files
  - Starts web server

- **.dockerignore**: Excludes files from build context
  - Python cache files
  - Git repository
  - Local development files

- **.env.docker.example**: Environment variable template
  - API keys
  - Django settings
  - Admin credentials

- **setup.sh**: Automated setup script
  - Validates prerequisites
  - Builds container
  - Starts services

## Quick Start

### 1. Setup

```bash
# Copy environment template
cp .env.docker.example .env.docker

# Edit and add your CLAUDE_API_KEY
nano .env.docker
```

### 2. Build and Run

```bash
# Automated setup
./setup.sh

# Or manually
docker-compose up -d
```

### 3. Access

- Web Interface: http://localhost:11800
- Admin Panel: http://localhost:11800/admin
- Credentials: See .env.docker (default: admin/changeme123)

## Data Persistence

### Volumes

Two volumes are created for persistence:

```yaml
volumes:
  - ./data/db:/app/web_interface      # Database
  - ./data/cache:/root/.cache         # ML models
```

**Database Location**: `./data/db/db.sqlite3`

**Model Cache**: Sentence transformer models are cached in `./data/cache/`

### Backup

```bash
# Backup database
docker-compose exec web python manage.py dumpdata > backup.json

# Or copy the SQLite file
cp data/db/db.sqlite3 backup_$(date +%Y%m%d).sqlite3
```

### Restore

```bash
# Restore from dumpdata
docker-compose exec web python manage.py loaddata backup.json

# Or replace SQLite file
cp backup.sqlite3 data/db/db.sqlite3
docker-compose restart
```

## Operations

### Collecting Trends

```bash
# Collect trends with default settings
docker-compose exec web python manage.py collect_trends

# Limit number of trends
docker-compose exec web python manage.py collect_trends --max-trends 10
```

### Viewing Logs

```bash
# Follow logs in real-time
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100

# View logs for specific time
docker-compose logs --since 1h
```

### Container Management

```bash
# Start containers
docker-compose up -d

# Stop containers
docker-compose down

# Restart containers
docker-compose restart

# Rebuild after code changes
docker-compose up -d --build

# View running containers
docker-compose ps

# View resource usage
docker stats trend-intelligence-agent
```

### Shell Access

```bash
# Access container shell
docker-compose exec web bash

# Run Python shell
docker-compose exec web python manage.py shell

# Run database shell
docker-compose exec web python manage.py dbshell
```

## Configuration

### Environment Variables

Edit `.env.docker`:

```bash
# Required
CLAUDE_API_KEY=sk-ant-xxxxx

# Optional - Django settings
SECRET_KEY=your-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,localhost

# Optional - Superuser
DB_USER=admin
ADMIN_EMAIL=admin@example.com
DB_PASSWORD=secure-password

# Optional - Trend settings
MAX_TRENDS=30
EMBED_MODEL=all-MiniLM-L6-v2
MODEL=claude-sonnet-4-5-20250929
```

### Port Mapping

Change port in `docker-compose.yml`:

```yaml
ports:
  - "11800:8000"  # Map to different host port
```

## Production Deployment

### Security Recommendations

1. **Change default credentials**:
   ```bash
   # Edit .env.docker
   DB_PASSWORD=strong-random-password
   SECRET_KEY=long-random-secret-key
   ```

2. **Disable debug mode**:
   ```bash
   DJANGO_DEBUG=False
   ```

3. **Use production server** (modify CMD in Dockerfile):
   ```dockerfile
   CMD ["gunicorn", "web_interface.wsgi:application", "--bind", "0.0.0.0:8000"]
   ```

   Add to requirements.txt:
   ```
   gunicorn>=21.0.0
   ```

4. **Set allowed hosts**:
   ```bash
   DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   ```

5. **Use HTTPS**: Place behind reverse proxy (nginx/traefik)

### Automated Collection

Add to cron on host:

```bash
# Run every 6 hours
0 */6 * * * cd /path/to/agent2 && docker-compose exec -T web python manage.py collect_trends --max-trends 20
```

Or use systemd timer:

```ini
# /etc/systemd/system/trend-collect.timer
[Unit]
Description=Collect trends every 6 hours

[Timer]
OnCalendar=*-*-* 00/6:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Database locked errors

```bash
# Stop container
docker-compose down

# Remove database lock
rm data/db/db.sqlite3-journal

# Restart
docker-compose up -d
```

### Out of disk space

```bash
# Clean up Docker
docker system prune -a

# Remove unused volumes
docker volume prune
```

### Import errors

```bash
# Rebuild with updated requirements
docker-compose build --no-cache
docker-compose up -d
```

### Permission issues

```bash
# Fix volume permissions
sudo chown -R $(id -u):$(id -g) data/
```

## Advanced Usage

### Custom Dockerfile

Modify `Dockerfile` for customizations:

```dockerfile
# Add additional system packages
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install additional Python packages
RUN pip install redis celery
```

### Multi-Container Setup

Add services to `docker-compose.yml`:

```yaml
services:
  web:
    # ... existing config

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery:
    build: .
    command: celery -A web_interface worker
    depends_on:
      - redis
```

### Using PostgreSQL

Replace SQLite with PostgreSQL:

1. Add to docker-compose.yml:
   ```yaml
   postgres:
     image: postgres:15-alpine
     environment:
       POSTGRES_DB: trenddb
       POSTGRES_USER: trenduser
       POSTGRES_PASSWORD: trendpass
     volumes:
       - postgres_data:/var/lib/postgresql/data
   ```

2. Update settings.py to use PostgreSQL

3. Add psycopg2 to requirements.txt

## Monitoring

### Health Checks

Container includes health check:

```bash
docker inspect --format='{{.State.Health.Status}}' trend-intelligence-agent
```

### Resource Limits

Add to docker-compose.yml:

```yaml
services:
  web:
    # ... other config
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Verify environment: `docker-compose config`
- Test connectivity: `docker-compose exec web python manage.py check`

Happy containerizing! 🐳
