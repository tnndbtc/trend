"""
Flower configuration for Celery task monitoring.

Flower provides a web-based interface for monitoring Celery tasks,
workers, and queues in real-time.

Access Flower at: http://localhost:5555
"""

import os

# Broker URL (same as Celery)
broker_url = os.getenv(
    "CELERY_BROKER_URL",
    "amqp://guest:guest@localhost:5672//"
)

# Result backend
result_backend = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://localhost:6379/1"
)

# Server settings
address = os.getenv("FLOWER_HOST", "0.0.0.0")
port = int(os.getenv("FLOWER_PORT", "5555"))

# Authentication (optional)
# Uncomment and set credentials for basic auth
# basic_auth = [os.getenv("FLOWER_AUTH", "admin:password")]

# URL prefix (if running behind a proxy)
# url_prefix = "/flower"

# Auto-refresh interval (milliseconds)
auto_refresh = True
auto_refresh_interval = 3000  # 3 seconds

# Maximum number of tasks to keep in memory
max_tasks = 10000

# Persistent state
persistent = True
db = os.getenv("FLOWER_DB", "/tmp/flower.db")

# Enable/disable features
purge_offline_workers = 300  # Purge workers offline for 5+ minutes
natural_time = True  # Display time in natural format

# Timezone
timezone = "UTC"

# Logging
logging = "INFO"

# CORS (if needed for API access)
# cors_options = {
#     "allow_origins": ["*"],
#     "allow_methods": ["GET", "POST"],
#     "allow_headers": ["*"],
# }

# Task result visibility
task_runtime_metric_buckets = [
    0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0
]
