#!/bin/bash
#
# Celery Worker Startup Script
# Reads concurrency setting from SystemSettings database
# Falls back to environment variable if database is unavailable
#

set -e

# Set Django settings module
export DJANGO_SETTINGS_MODULE=web_interface.settings
export PYTHONPATH=/app

# Default concurrency (fallback)
DEFAULT_CONCURRENCY="${CELERY_WORKER_CONCURRENCY:-4}"

echo "🔧 Starting Celery worker with dynamic concurrency..."

# Try to read concurrency from SystemSettings database
CONCURRENCY=$(python -c "
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')
sys.path.insert(0, '/app')
django.setup()

try:
    from trends_viewer.models_system import SystemSettings
    settings = SystemSettings.load()
    print(settings.celery_worker_concurrency)
except Exception as e:
    # Database not available or error - use fallback
    print('$DEFAULT_CONCURRENCY', file=sys.stderr)
    print('$DEFAULT_CONCURRENCY')
" 2>/dev/null)

# Validate concurrency value
if ! [[ "$CONCURRENCY" =~ ^[0-9]+$ ]] || [ "$CONCURRENCY" -lt 1 ] || [ "$CONCURRENCY" -gt 32 ]; then
    echo "⚠️  Invalid concurrency value: $CONCURRENCY, using fallback: $DEFAULT_CONCURRENCY"
    CONCURRENCY=$DEFAULT_CONCURRENCY
fi

echo "✅ Worker concurrency set to: $CONCURRENCY"
echo "   (Update via System Settings in Django admin)"

# Start Celery worker with configured concurrency
exec celery -A web_interface worker \
    --loglevel=info \
    --queues=translation,default \
    --concurrency=$CONCURRENCY
