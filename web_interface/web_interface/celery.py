"""
Celery configuration for Django web interface.

This is separate from the FastAPI celery worker (trend_agent.tasks).
Handles background tasks for the Django web interface including:
- Pre-translation of trends after crawls
- Bulk translation operations
- Translation status tracking
"""

import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')

# Create Celery app
app = Celery('web_interface')

# Load configuration from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery configuration."""
    print(f'Request: {self.request!r}')
