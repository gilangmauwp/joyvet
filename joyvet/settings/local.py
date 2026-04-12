"""Local development settings — not for production."""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ['*']

# Relax CORS for local development
CORS_ALLOW_ALL_ORIGINS = True

# Show SQL queries in console
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO'},
        'django.db.backends': {'handlers': ['console'], 'level': 'WARNING'},
        'apps': {'handlers': ['console'], 'level': 'DEBUG'},
        'celery': {'handlers': ['console'], 'level': 'INFO'},
        'channels': {'handlers': ['console'], 'level': 'INFO'},
    },
}

# Run Celery tasks synchronously in tests when needed
# CELERY_TASK_ALWAYS_EAGER = True

# Use Redis from environment (works both locally and inside Docker)
import os  # noqa: E402
_redis_base = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
_redis_host = _redis_base.rsplit('/', 1)[0]  # strip DB index
CACHES['default']['LOCATION'] = f'{_redis_host}/2'  # noqa: F405

# Whitenoise for static during dev
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
