"""
Django settings for web_interface project.
"""

from pathlib import Path
import os
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add trend_agent to Python path
sys.path.insert(0, str(BASE_DIR.parent / 'trend_agent'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'trends_viewer',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'trends_viewer.middleware.LanguagePreferenceMiddleware',  # Language persistence
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'web_interface.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'trends_viewer.context_processors.menu_translations',  # Menu translations
                'trends_viewer.context_processors.translation_settings',  # Translation settings
            ],
        },
    },
]

WSGI_APPLICATION = 'web_interface.wsgi.application'


# Database
# Database is stored in db/ subdirectory which is persisted via Docker volume
# Temporarily using /tmp for write permissions
import os
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DJANGO_DB_PATH', str(BASE_DIR / 'db' / 'db.sqlite3')),
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Directory for collectstatic

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============================================================================
# AUTO-TRANSLATION SETTINGS
# ============================================================================

# Enable automatic pre-translation after crawls
# When enabled, newly collected trends are automatically translated in background
AUTO_TRANSLATE_ENABLED = os.getenv('AUTO_TRANSLATE_ENABLED', 'true').lower() == 'true'

# Languages to automatically pre-translate
# Trends will be translated to these languages after each crawl
AUTO_TRANSLATE_LANGUAGES = [
    lang.strip()
    for lang in os.getenv('AUTO_TRANSLATE_LANGUAGES', 'zh').split(',')
]

# Only translate new trends (created in current crawl)
# If False, will translate all trends
AUTO_TRANSLATE_NEW_TRENDS_ONLY = os.getenv('AUTO_TRANSLATE_NEW_TRENDS_ONLY', 'true').lower() == 'true'

# Maximum daily translation cost limit in USD
# Translation tasks will be paused if daily cost exceeds this limit
MAX_DAILY_TRANSLATION_COST = float(os.getenv('MAX_DAILY_TRANSLATION_COST', '50.0'))

# Priority languages for translation (shown first in admin)
TRANSLATION_PRIORITY_LANGUAGES = [
    ('zh', 'Chinese (Simplified)'),
    ('es', 'Spanish'),
    ('fr', 'French'),
    ('de', 'German'),
    ('ja', 'Japanese'),
    ('ko', 'Korean'),
    ('ru', 'Russian'),
    ('ar', 'Arabic'),
]


# ==============================================================================
# CELERY CONFIGURATION
# ==============================================================================
# Celery broker (RabbitMQ) configuration
CELERY_BROKER_URL = f"amqp://{os.getenv('RABBITMQ_USER', 'trend_user')}:{os.getenv('RABBITMQ_PASSWORD', 'trend_password')}@{os.getenv('RABBITMQ_HOST', 'rabbitmq')}:{os.getenv('RABBITMQ_PORT', '5672')}//"

# Celery result backend (use RabbitMQ for simplicity and reliability)
# RabbitMQ avoids Redis authentication issues and provides better reliability
CELERY_RESULT_BACKEND = f"rpc://"

# Celery task configuration
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Task time limits (10 minutes soft, 15 minutes hard)
CELERY_TASK_SOFT_TIME_LIMIT = 600
CELERY_TASK_TIME_LIMIT = 900

# Task result expiration (7 days)
CELERY_RESULT_EXPIRES = 60 * 60 * 24 * 7

# Worker configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Task routing
CELERY_TASK_ROUTES = {
    'trends_viewer.tasks.pre_translate_trends': {'queue': 'translation'},
    'trends_viewer.tasks.bulk_translate_all_trends': {'queue': 'translation'},
    'trends_viewer.tasks.translate_single_trend': {'queue': 'translation'},
}

# Default queue
CELERY_TASK_DEFAULT_QUEUE = 'default'

# Disable eager result consumption (prevents auth issues with Redis)
CELERY_TASK_IGNORE_RESULT = False
CELERY_TASK_TRACK_STARTED = True
CELERY_RESULT_PERSISTENT = True

# Result backend configuration for better reliability
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
    'master_name': 'mymaster',
}
CELERY_REDIS_BACKEND_USE_SSL = False
