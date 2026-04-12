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

# Use a separate Redis DB for dev cache
CACHES['default']['LOCATION'] = 'redis://localhost:6379/2'  # noqa: F405

# Whitenoise for static during dev
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
