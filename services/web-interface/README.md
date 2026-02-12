# Trend Intelligence Platform - Web Interface

Django-based web interface for browsing and managing trends.

## Overview

This service provides a user-friendly web interface for the Trend Intelligence Platform, including:

- **Trend dashboard** - Browse trending topics by category and timeframe
- **Topic detail views** - Deep dive into specific trends
- **Admin panel** - Manage collectors, settings, and data
- **User authentication** - Secure access control
- **Responsive design** - Works on desktop and mobile

## Architecture

```
services/web-interface/
├── web_interface/        # Django project settings
│   ├── settings.py      # Configuration
│   ├── urls.py          # URL routing
│   ├── wsgi.py          # WSGI application
│   └── asgi.py          # ASGI application
├── trends_viewer/       # Main Django app
│   ├── views.py         # View logic
│   ├── models.py        # Database models
│   ├── urls.py          # App URLs
│   ├── templates/       # HTML templates
│   ├── static/          # CSS, JavaScript
│   ├── management/      # Management commands
│   └── templatetags/    # Custom template tags
├── static/              # Global static files
├── staticfiles/         # Collected static files
├── db/                  # SQLite database (dev only)
└── manage.py            # Django management script
```

## Dependencies

The web interface depends on:

1. **Infrastructure**:
   - PostgreSQL (port 5433) - user data, sessions
   - Redis (port 6380) - session storage, caching

2. **Shared Library**:
   - `trend-agent-core` - storage and observability modules

3. **Optional**:
   - API Service - for real-time data (can work standalone)

## Development

### Local Setup

1. **Install dependencies**:
   ```bash
   # From repo root
   pip install -e packages/trend-agent-core
   pip install -r services/web-interface/requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5433
   export POSTGRES_DB=trends
   export POSTGRES_USER=trend_user
   export POSTGRES_PASSWORD=trend_password
   export REDIS_HOST=localhost
   export REDIS_PORT=6380
   export SECRET_KEY="your-secret-key-here"
   ```

3. **Run migrations**:
   ```bash
   cd services/web-interface
   python manage.py migrate
   ```

4. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```

5. **Collect static files**:
   ```bash
   python manage.py collectstatic
   ```

6. **Run the development server**:
   ```bash
   python manage.py runserver 11800
   ```

7. **Access the web interface**:
   - Homepage: http://localhost:11800/
   - Admin: http://localhost:11800/admin/

### Docker Development

```bash
# Build the web interface service
docker build -f services/web-interface/Dockerfile -t trend-web:latest .

# Run the container
docker run -p 11800:11800 \
  -e POSTGRES_HOST=host.docker.internal \
  -e REDIS_HOST=host.docker.internal \
  -e SECRET_KEY="development-secret-key" \
  trend-web:latest
```

### Testing

```bash
# Run tests
pytest services/web-interface/trends_viewer/tests/

# Run with coverage
pytest services/web-interface/trends_viewer/tests/ --cov=trends_viewer --cov-report=html
```

## Features

### Trend Dashboard

- **Browse trends** by category (Technology, Business, Science, etc.)
- **Filter by timeframe** (Last hour, 24h, 7d, 30d)
- **Sort options** (Latest, Most viewed, Trending)
- **Search** trends by keyword
- **Language filter** - View trends in specific languages

### Topic Detail View

- **Full content** - Original text and translations
- **Source information** - URL, platform, timestamp
- **Related topics** - Semantically similar content
- **Engagement metrics** - Views, shares, comments
- **AI-generated summary** - LLM-powered insights

### Admin Panel

- **Collector management** - Start/stop data collectors
- **User management** - Create/edit users and permissions
- **Data management** - Bulk operations on trends
- **System health** - Service status and metrics
- **Settings** - Configure platform behavior

## Configuration

Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (required) | Django secret key |
| `DEBUG` | False | Enable debug mode |
| `ALLOWED_HOSTS` | localhost | Comma-separated hosts |
| `POSTGRES_HOST` | localhost | PostgreSQL host |
| `POSTGRES_PORT` | 5433 | PostgreSQL port |
| `POSTGRES_DB` | trends | Database name |
| `REDIS_HOST` | localhost | Redis host |
| `REDIS_PORT` | 6380 | Redis port |
| `USE_POSTGRESQL` | True | Use PostgreSQL vs SQLite |
| `SESSION_ENGINE` | django.contrib.sessions.backends.cache | Session backend |

## Database Backend

### PostgreSQL (Production)

```bash
export USE_POSTGRESQL=true
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
python manage.py migrate
```

### SQLite (Development)

```bash
export USE_POSTGRESQL=false
python manage.py migrate
```

**Note**: SQLite is for development only. Use PostgreSQL in production for better performance and concurrency.

## Static Files

### Development

Static files are served by Django's development server automatically.

### Production

Use WhiteNoise or serve via CDN/reverse proxy:

```bash
# Collect static files
python manage.py collectstatic --noinput

# Static files will be in staticfiles/
# Configure nginx or WhiteNoise to serve them
```

## Templates

Templates use Django's template language with custom tags:

```django
{% load trend_tags %}

<!-- Format numbers with commas -->
{{ trend.views|format_number }}

<!-- Truncate text -->
{{ trend.content|truncate_chars:200 }}

<!-- Relative timestamps -->
{{ trend.created_at|timesince }} ago
```

Custom template tags are in `trends_viewer/templatetags/trend_tags.py`.

## Management Commands

Custom management commands:

```bash
# Sync trends from API
python manage.py sync_trends

# Clean old trends
python manage.py clean_old_trends --days 90

# Export trends to CSV
python manage.py export_trends --output trends.csv

# Import trends from JSON
python manage.py import_trends --file trends.json
```

## Authentication

### User Types

1. **Anonymous users** - Can browse public trends
2. **Registered users** - Can save favorites, get notifications
3. **Staff users** - Can access admin panel
4. **Superusers** - Full admin access

### Login

- Local authentication: `/admin/login/`
- OAuth support (optional): Google, GitHub

## Observability

### Logging

```python
import logging
logger = logging.getLogger(__name__)
logger.info("User viewed trend", extra={"trend_id": 123})
```

Logs are written to stdout in JSON format.

### Metrics

Django metrics are exposed at `/metrics/` (when prometheus-client is installed):

- Request count and latency
- Database query count
- Cache hit/miss rates
- Template rendering time

### Monitoring

Configure monitoring in `settings.py`:

```python
MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    # ... other middleware ...
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]
```

## Deployment

### Docker Compose

```bash
cd infrastructure/docker
docker-compose up web
```

### Kubernetes

```bash
kubectl apply -k k8s/overlays/production
```

### Environment-Specific Settings

Create environment-specific settings files:

```python
# web_interface/settings_production.py
from .settings import *

DEBUG = False
ALLOWED_HOSTS = ['trends.example.com']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

Load with:
```bash
export DJANGO_SETTINGS_MODULE=web_interface.settings_production
```

## Troubleshooting

### Static Files Not Loading

```
GET /static/css/main.css 404
```

**Solution**: Collect static files:
```bash
python manage.py collectstatic --noinput
```

### Database Connection Error

```
django.db.utils.OperationalError: could not connect to server
```

**Solution**: Check PostgreSQL connection:
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
docker-compose up postgres
```

### Import Error for trend_agent

```
ModuleNotFoundError: No module named 'trend_agent'
```

**Solution**: Install core library:
```bash
pip install -e packages/trend-agent-core
```

### Migration Conflicts

```
django.db.migrations.exceptions.InconsistentMigrationHistory
```

**Solution**: Reset migrations (dev only):
```bash
python manage.py migrate --fake trends_viewer zero
python manage.py migrate
```

## Performance

### Optimization Tips

1. **Use database connection pooling**:
   ```python
   DATABASES = {
       'default': {
           'CONN_MAX_AGE': 600,  # 10 minutes
       }
   }
   ```

2. **Enable caching**:
   ```python
   CACHES = {
       'default': {
           'BACKEND': 'django_redis.cache.RedisCache',
           'LOCATION': 'redis://localhost:6380/1',
       }
   }
   ```

3. **Use select_related and prefetch_related**:
   ```python
   trends = Trend.objects.select_related('category').prefetch_related('tags')
   ```

4. **Enable template caching**:
   ```python
   TEMPLATES = [{
       'OPTIONS': {
           'loaders': [
               ('django.template.loaders.cached.Loader', [
                   'django.template.loaders.filesystem.Loader',
                   'django.template.loaders.app_directories.Loader',
               ]),
           ],
       },
   }]
   ```

## Security

### Security Checklist

- [ ] Set `SECRET_KEY` to a random value
- [ ] Set `DEBUG = False` in production
- [ ] Configure `ALLOWED_HOSTS` properly
- [ ] Enable HTTPS with `SECURE_SSL_REDIRECT`
- [ ] Set `SESSION_COOKIE_SECURE = True`
- [ ] Set `CSRF_COOKIE_SECURE = True`
- [ ] Use environment variables for secrets
- [ ] Regularly update dependencies

### CSRF Protection

Django's CSRF protection is enabled by default. For AJAX requests:

```javascript
// Get CSRF token from cookie
const csrftoken = getCookie('csrftoken');

// Include in request headers
fetch('/api/endpoint/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrftoken,
    },
    body: JSON.stringify(data),
});
```

## Related Services

- **API Service**: `services/api/` - REST API for trend data
- **Crawler**: `services/crawler/` - Data collection
- **Celery Worker**: `services/celery-worker/` - Background tasks
- **Translation**: `services/translation-service/` - Translation pipeline

## Contributing

See the root `README.md` for contribution guidelines.

## License

See `LICENSE` in the root directory.
